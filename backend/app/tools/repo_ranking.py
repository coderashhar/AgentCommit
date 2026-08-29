"""Experience-tiered repository ranking.

Decides which repositories are realistic contribution targets for a developer at a
given experience level, and scores them.

The core problem this solves: ranking repositories by stars surfaces the most popular
projects on GitHub (microsoft/vscode, freeCodeCamp, TheAlgorithms/*), which are the
*worst* targets for a first contribution — long PR queues, high maintainer bandwidth
cost, and a codebase that takes hours to build locally. Each experience tier therefore
gets a star *ceiling* as well as a floor, plus activity, size, and labelled-issue bands.

Every function here is pure: no network, no ADK, no Pydantic. `today`/`now` are
injectable so query building and scoring are deterministic under test.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from enum import StrEnum

# Signal weights, summing to 100. Redistributed when a signal is unavailable — see
# `_effective_weights`.
WEIGHT_STAR_FIT = 30.0
WEIGHT_LANGUAGE_MATCH = 25.0
WEIGHT_TOPIC_OVERLAP = 15.0
WEIGHT_ISSUE_SUPPLY = 15.0
WEIGHT_RECENCY = 15.0

# A score of exactly 100 reads as "perfect match" and is never honest; 0 reads as
# broken. Clamp to a band that communicates ranking without overclaiming.
MAX_SCORE = 99.0
MIN_SCORE = 5.0

PENALTY_FORK = 0.85
PENALTY_OUT_OF_BAND = 0.6

# Signal strength above which a signal is considered to have "fired" and may be
# quoted in the human-readable match reason.
REASON_THRESHOLD = 0.6


class ExperienceTier(StrEnum):
    """Contribution-readiness tier derived from a developer's profile."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

    @classmethod
    def from_experience_level(cls, value: str) -> "ExperienceTier":
        """Map a free-form experience level onto a tier.

        Unrecognised input falls back to BEGINNER: over-constraining the search is
        recoverable (the relaxed query pass widens it), while under-constraining is
        the exact failure this module exists to prevent.
        """
        normalized = (value or "").strip().lower()
        for tier in cls:
            if tier.value == normalized:
                return tier
        return cls.BEGINNER


@dataclass(frozen=True, slots=True)
class TierBand:
    """Search and scoring bounds for one experience tier.

    `min_*`/`max_*` are hard bounds emitted into the GitHub query. `ideal_*` is used
    only by scoring, so a repo at the edge of the band ranks below one in the sweet
    spot. `reject_star_ceiling` applies only on the LLM path, where the query did not
    constrain anything.
    """

    tier: ExperienceTier
    min_stars: int
    max_stars: int | None
    ideal_min_stars: int
    ideal_max_stars: int
    reject_star_ceiling: int | None
    pushed_within_days: int
    min_size_kb: int
    max_size_kb: int | None
    min_forks: int
    max_forks: int | None
    min_good_first_issues: int | None
    min_help_wanted_issues: int | None
    ideal_min_open_issues: int
    ideal_max_open_issues: int


TIER_BANDS: Mapping[ExperienceTier, TierBand] = {
    ExperienceTier.BEGINNER: TierBand(
        tier=ExperienceTier.BEGINNER,
        # 20k is the load-bearing number: it excludes freeCodeCamp (~410k),
        # TheAlgorithms/JavaScript (~190k) and microsoft/vscode (~170k), while
        # keeping projects where a maintainer still triages within days.
        min_stars=500,
        max_stars=20_000,
        ideal_min_stars=1_000,
        ideal_max_stars=8_000,
        reject_star_ceiling=60_000,
        pushed_within_days=30,
        # Floor drops README-only starter repos; ceiling drops monorepos where just
        # getting a local build working is a multi-hour prerequisite.
        min_size_kb=1_000,
        max_size_kb=150_000,
        min_forks=50,
        max_forks=8_000,
        # >3 means at least four open starter issues, so a couple being claimed still
        # leaves work available.
        min_good_first_issues=3,
        min_help_wanted_issues=3,
        ideal_min_open_issues=10,
        ideal_max_open_issues=300,
    ),
    ExperienceTier.INTERMEDIATE: TierBand(
        tier=ExperienceTier.INTERMEDIATE,
        min_stars=1_000,
        max_stars=60_000,
        ideal_min_stars=4_000,
        ideal_max_stars=25_000,
        reject_star_ceiling=150_000,
        pushed_within_days=45,
        min_size_kb=500,
        max_size_kb=400_000,
        min_forks=100,
        max_forks=25_000,
        min_good_first_issues=1,
        min_help_wanted_issues=3,
        ideal_min_open_issues=20,
        ideal_max_open_issues=800,
    ),
    ExperienceTier.ADVANCED: TierBand(
        tier=ExperienceTier.ADVANCED,
        min_stars=2_000,
        max_stars=None,
        ideal_min_stars=10_000,
        ideal_max_stars=120_000,
        reject_star_ceiling=None,
        pushed_within_days=60,
        min_size_kb=200,
        max_size_kb=None,
        min_forks=50,
        max_forks=None,
        # Requiring good-first-issues would filter out exactly the deep repos this
        # tier wants; help-wanted still signals openness to outside contributors.
        min_good_first_issues=None,
        min_help_wanted_issues=5,
        ideal_min_open_issues=50,
        ideal_max_open_issues=2_000,
    ),
}


@dataclass(frozen=True, slots=True)
class RepoScore:
    """Result of scoring one repository against a tier and skill profile."""

    score: float
    reasons: tuple[str, ...]
    signals: Mapping[str, float]


def _relaxed_band(band: TierBand) -> TierBand:
    """Widen a band for the retry pass when the strict query returns too few rows.

    Deliberately does NOT widen `max_stars`. Relaxing the ceiling is precisely how
    mega-repos get back into the results, so it stays fixed while everything else
    loosens.
    """
    return TierBand(
        tier=band.tier,
        min_stars=max(0, int(band.min_stars * 0.6)),
        max_stars=band.max_stars,
        ideal_min_stars=band.ideal_min_stars,
        ideal_max_stars=band.ideal_max_stars,
        reject_star_ceiling=band.reject_star_ceiling,
        pushed_within_days=band.pushed_within_days * 2,
        min_size_kb=0,
        max_size_kb=None,
        min_forks=0,
        max_forks=None,
        min_good_first_issues=(
            None if band.min_good_first_issues is None else band.min_good_first_issues // 2
        ),
        min_help_wanted_issues=(
            None if band.min_help_wanted_issues is None else band.min_help_wanted_issues // 2
        ),
        ideal_min_open_issues=band.ideal_min_open_issues,
        ideal_max_open_issues=band.ideal_max_open_issues,
    )


def build_repo_query(
    tier: ExperienceTier,
    *,
    language: str = "",
    topic: str = "",
    relaxed: bool = False,
    today: date | None = None,
) -> str:
    """Build a GitHub repository-search query constrained to a tier's bands.

    Args:
        tier: Experience tier whose bands constrain the search.
        language: Optional `language:` qualifier value.
        topic: Optional `topic:` qualifier value.
        relaxed: Use the widened retry band (keeps the star ceiling).
        today: Reference date for the `pushed:` window. Defaults to the current UTC date.

    Returns:
        A GitHub search query string.
    """
    band = TIER_BANDS[tier]
    if relaxed:
        band = _relaxed_band(band)

    reference_date = today or datetime.now(timezone.utc).date()
    pushed_since = reference_date - timedelta(days=band.pushed_within_days)

    parts: list[str] = []
    if language:
        parts.append(f"language:{language}")
    if topic:
        parts.append(f"topic:{topic}")

    parts.append(_range_qualifier("stars", band.min_stars, band.max_stars))

    if band.min_forks or band.max_forks is not None:
        parts.append(_range_qualifier("forks", band.min_forks, band.max_forks))

    if band.min_size_kb or band.max_size_kb is not None:
        parts.append(_range_qualifier("size", band.min_size_kb, band.max_size_kb))

    parts.append(f"pushed:>{pushed_since.isoformat()}")

    if band.min_good_first_issues:
        parts.append(f"good-first-issues:>{band.min_good_first_issues}")
    if band.min_help_wanted_issues:
        parts.append(f"help-wanted-issues:>{band.min_help_wanted_issues}")

    # Archived, mirrored and template repos cannot meaningfully accept a PR.
    parts.append("archived:false")
    parts.append("is:public")
    if not relaxed:
        parts.append("mirror:false")
        parts.append("template:false")

    return " ".join(parts)


def _range_qualifier(name: str, minimum: int, maximum: int | None) -> str:
    """Render a GitHub numeric range qualifier (`n..n`, `>=n`)."""
    if maximum is None:
        return f"{name}:>={minimum}"
    return f"{name}:{minimum}..{maximum}"


def repo_is_rejected(item: Mapping[str, object], tier: ExperienceTier) -> bool:
    """Return True when a repository must never be recommended at this tier.

    Applied to results the search query did not constrain — i.e. repositories the LLM
    proposed. This is what removes microsoft/vscode from a beginner's list even when
    Gemini insists on it.
    """
    band = TIER_BANDS[tier]

    if _as_bool(item.get("archived")) or _as_bool(item.get("disabled")):
        return True

    # `has_issues` is absent on some payload shapes; only reject on an explicit False.
    if item.get("has_issues") is False:
        return True

    if as_int(item.get("open_issues_count")) <= 0:
        return True

    if band.reject_star_ceiling is not None:
        if _stars(item) > band.reject_star_ceiling:
            return True

    return False


def score_repo(
    item: Mapping[str, object],
    tier: ExperienceTier,
    languages: Sequence[str],
    frameworks: Sequence[str] = (),
    domains: Sequence[str] = (),
    *,
    now: datetime | None = None,
) -> RepoScore:
    """Score a raw GitHub repository payload against a tier and skill profile.

    Operates on the raw search/repo dict so the same function serves both the
    deterministic search path and verification of LLM-proposed repositories.
    """
    band = TIER_BANDS[tier]
    reference = now or datetime.now(timezone.utc)

    wanted_topics = _normalize_terms([*frameworks, *domains])
    # `/search/repositories` returns `topics`, but `GET /repos/{owner}/{repo}` may not.
    # Treating a missing key as zero overlap would silently cost a verified repo 15
    # points and lose it the sort, so the weight is redistributed instead.
    has_topic_signal = bool(wanted_topics) and "topics" in item

    signals: dict[str, float] = {
        "star_fit": _score_star_fit(_stars(item), band),
        "language_match": _score_language_match(item, languages),
        "issue_supply": _score_issue_supply(as_int(item.get("open_issues_count")), band),
        "recency": _score_recency(item.get("pushed_at"), reference),
    }
    if has_topic_signal:
        signals["topic_overlap"] = _score_topic_overlap(item, wanted_topics)

    weights = _effective_weights(has_topic_signal)
    weighted = sum(signals[name] * weights[name] for name in signals)

    penalty = 1.0
    if _as_bool(item.get("fork")):
        penalty *= PENALTY_FORK
    if not _within_star_band(_stars(item), band):
        penalty *= PENALTY_OUT_OF_BAND

    score = max(MIN_SCORE, min(MAX_SCORE, weighted * penalty))

    reasons = _build_reasons(item, signals, band, reference)
    return RepoScore(score=round(score, 1), reasons=reasons, signals=signals)


def _effective_weights(has_topic_signal: bool) -> Mapping[str, float]:
    """Return signal weights, rescaled to sum to 100 when topics are unavailable."""
    weights = {
        "star_fit": WEIGHT_STAR_FIT,
        "language_match": WEIGHT_LANGUAGE_MATCH,
        "issue_supply": WEIGHT_ISSUE_SUPPLY,
        "recency": WEIGHT_RECENCY,
    }
    if has_topic_signal:
        weights["topic_overlap"] = WEIGHT_TOPIC_OVERLAP
        return weights

    total = sum(weights.values())
    scale = 100.0 / total
    return {name: weight * scale for name, weight in weights.items()}


def _within_star_band(stars: int, band: TierBand) -> bool:
    if stars < band.min_stars:
        return False
    if band.max_stars is not None and stars > band.max_stars:
        return False
    return True


def _score_star_fit(stars: int, band: TierBand) -> float:
    """Score a star count by its position within the tier's band, in log10 space.

    Star counts span five orders of magnitude, so linear distance is meaningless —
    the gap between 500 and 5,000 matters far more than between 100,000 and 104,500.
    """
    log_stars = math.log10(max(stars, 1))
    log_ideal_min = math.log10(max(band.ideal_min_stars, 1))
    log_ideal_max = math.log10(max(band.ideal_max_stars, 1))

    if log_ideal_min <= log_stars <= log_ideal_max:
        return 1.0

    if log_stars < log_ideal_min:
        log_hard_min = math.log10(max(band.min_stars, 1))
        if log_stars >= log_hard_min:
            return _ramp(log_stars, log_hard_min, log_ideal_min, 0.45, 1.0)
        # Below the hard floor: decay over one decade.
        return max(0.0, _ramp(log_stars, log_hard_min - 1.0, log_hard_min, 0.0, 0.45))

    # Above the ideal ceiling.
    if band.max_stars is None:
        # No hard ceiling (advanced): taper but never disqualify.
        return max(0.55, _ramp(log_stars, log_ideal_max, log_ideal_max + 1.0, 1.0, 0.55))

    log_hard_max = math.log10(max(band.max_stars, 1))
    if log_stars <= log_hard_max:
        return _ramp(log_stars, log_ideal_max, log_hard_max, 1.0, 0.45)
    return max(0.0, _ramp(log_stars, log_hard_max, log_hard_max + 1.0, 0.45, 0.0))


def _ramp(value: float, start: float, end: float, start_score: float, end_score: float) -> float:
    """Linearly interpolate `value` in [start, end] onto [start_score, end_score]."""
    if end <= start:
        return end_score
    ratio = (value - start) / (end - start)
    ratio = max(0.0, min(1.0, ratio))
    return start_score + (end_score - start_score) * ratio


def _score_language_match(item: Mapping[str, object], languages: Sequence[str]) -> float:
    """Score the repo's primary language against the developer's ranked languages."""
    if not languages:
        return 0.5

    ranked = [lang.strip().lower() for lang in languages if lang and lang.strip()]
    if not ranked:
        return 0.5

    repo_language = str(item.get("language") or "").strip().lower()
    if repo_language:
        if repo_language == ranked[0]:
            return 1.0
        if repo_language in ranked[1:3]:
            return 0.85
        if repo_language in ranked[3:]:
            return 0.6

    topics = {str(topic).strip().lower() for topic in as_sequence(item.get("topics"))}
    if topics & set(ranked):
        return 0.4

    return 0.0


def _score_topic_overlap(item: Mapping[str, object], wanted: set[str]) -> float:
    """Score overlap between the developer's frameworks/domains and the repo's topics."""
    haystack = {
        *_normalize_terms(str(topic) for topic in as_sequence(item.get("topics"))),
        *_normalize_terms(_tokenize(str(item.get("name") or ""))),
        *_normalize_terms(_tokenize(str(item.get("description") or ""))),
    }
    overlap = len(wanted & haystack)
    return min(1.0, overlap / 2.0)


def _score_issue_supply(open_issues: int, band: TierBand) -> float:
    """Score the repo's open-issue count against the tier's ideal supply band."""
    if open_issues <= 0:
        return 0.0
    if band.ideal_min_open_issues <= open_issues <= band.ideal_max_open_issues:
        return 1.0
    if open_issues < band.ideal_min_open_issues:
        return _ramp(float(open_issues), 1.0, float(band.ideal_min_open_issues), 0.2, 1.0)

    # A huge backlog is noisy but not disqualifying — floor rather than zero.
    log_issues = math.log10(max(open_issues, 1))
    log_ideal_max = math.log10(max(band.ideal_max_open_issues, 1))
    return max(0.3, _ramp(log_issues, log_ideal_max, log_ideal_max + 1.0, 1.0, 0.3))


def _score_recency(pushed_at: object, now: datetime) -> float:
    """Score how recently the repo was pushed to."""
    pushed = parse_datetime(pushed_at)
    if pushed is None:
        # Neutral rather than punitive — a missing field is our gap, not the repo's.
        return 0.5

    days = (now - pushed).days
    if days <= 7:
        return 1.0
    if days <= 30:
        return 0.85
    if days <= 90:
        return 0.5
    if days <= 180:
        return 0.2
    return 0.0


def _build_reasons(
    item: Mapping[str, object],
    signals: Mapping[str, float],
    band: TierBand,
    reference: datetime,
) -> tuple[str, ...]:
    """Build reason fragments from signals that actually fired, strongest first."""
    candidates: list[tuple[float, str]] = []

    language = str(item.get("language") or "").strip()
    if signals.get("language_match", 0.0) >= 0.85 and language:
        candidates.append(
            (signals["language_match"], f"Written in {language}, one of your strongest languages.")
        )

    if signals.get("star_fit", 0.0) >= 0.9 and band.tier is ExperienceTier.BEGINNER:
        candidates.append(
            (
                signals["star_fit"],
                f"At {_humanize_count(_stars(item))} stars it's established but small enough "
                "that a first PR actually gets reviewed.",
            )
        )

    if signals.get("topic_overlap", 0.0) >= 0.5:
        topics = [str(topic) for topic in as_sequence(item.get("topics"))][:2]
        if topics:
            candidates.append(
                (signals["topic_overlap"], f"Overlaps with your {' and '.join(topics)} work.")
            )

    open_issues = as_int(item.get("open_issues_count"))
    if signals.get("issue_supply", 0.0) >= 0.8 and open_issues:
        candidates.append(
            (
                signals["issue_supply"],
                f"{open_issues} open issues, including labelled starter work.",
            )
        )

    if signals.get("recency", 0.0) >= 0.85:
        pushed = parse_datetime(item.get("pushed_at"))
        if pushed is not None:
            days = max(0, (reference - pushed).days)
            when = "today" if days == 0 else f"{days} day{'s' if days != 1 else ''} ago"
            candidates.append((signals["recency"], f"Actively maintained — last pushed {when}."))

    fired = [text for value, text in sorted(candidates, key=lambda pair: pair[0], reverse=True)]
    return tuple(fired[:3])


def format_match_reason(reasons: Sequence[str], tier: ExperienceTier) -> str:
    """Join reason fragments into a single sentence, with a tier-generic fallback."""
    if not reasons:
        return f"Matches your {tier.value} profile."
    return " ".join(reasons)


def _normalize_terms(terms) -> set[str]:
    """Lowercase, trim, and collapse separators so 'Next.js' and 'next-js' unify."""
    normalized: set[str] = set()
    for term in terms:
        cleaned = re.sub(r"[\s_.-]+", "", str(term).strip().lower())
        if cleaned:
            normalized.add(cleaned)
    return normalized


def _tokenize(text: str) -> list[str]:
    return re.split(r"[^A-Za-z0-9+#]+", text)


def _stars(item: Mapping[str, object]) -> int:
    """Read a star count, tolerating both the API field and our own schema field."""
    if "stargazers_count" in item:
        return as_int(item.get("stargazers_count"))
    return as_int(item.get("stars"))


def as_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return 0
    return 0


def _as_bool(value: object) -> bool:
    return value is True


def as_sequence(value: object) -> Sequence[object]:
    if isinstance(value, (list, tuple)):
        return value
    return ()


def parse_datetime(value: object) -> datetime | None:
    """Parse a GitHub ISO8601 timestamp into an aware UTC datetime."""
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _humanize_count(value: int) -> str:
    if value >= 1_000:
        return f"{value / 1_000:.1f}k".replace(".0k", "k")
    return str(value)
