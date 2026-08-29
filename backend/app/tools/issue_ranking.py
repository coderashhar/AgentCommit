"""Issue filtering, difficulty classification, and scoring.

Replaces the label-substring test that could only ever classify an issue as "easy" or
"medium" with a real three-way rubric, and adds the filters GitHub's issues-list
endpoint does not apply server-side: dropping pull requests, already-claimed issues,
and stale issues.

Pure module: no network, no ADK. `now` is injectable for deterministic tests.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.tools.repo_ranking import ExperienceTier, as_int, as_sequence, parse_datetime

# Labels that mark an issue as a design/architecture discussion or a large, risky
# change rather than a single tractable task.
HARD_LABEL_PATTERNS: frozenset[str] = frozenset(
    {
        "epic",
        "rfc",
        "architecture",
        "refactor",
        "breaking change",
        "breaking-change",
        "performance",
        "security",
        "difficulty: hard",
        "difficulty/hard",
        "complex",
        "priority: critical",
        "p0",
    }
)

# Labels that mark an issue as approachable for a first-time contributor.
EASY_LABEL_PATTERNS: frozenset[str] = frozenset(
    {
        "good first issue",
        "good-first-issue",
        "beginner",
        "beginner friendly",
        "beginner-friendly",
        "first-timers-only",
        "documentation",
        "docs",
        "typo",
        "easy",
        "difficulty: easy",
        "e-easy",
        "starter",
        "low hanging fruit",
        "low-hanging-fruit",
    }
)

STALE_UPDATED_DAYS = 180
STALE_UNANSWERED_DAYS = 365

# Body/discussion thresholds used by the difficulty rubric.
HARD_BODY_CHARS = 4_000
HARD_COMMENT_COUNT = 25
HARD_CODE_FENCE_COUNT = 3
HARD_CHECKLIST_ITEM_COUNT = 6
EASY_BODY_CHARS = 1_500
EASY_COMMENT_COUNT = 10

WEIGHT_TIER_FIT = 35.0
WEIGHT_FRESHNESS = 25.0
WEIGHT_DISCUSSION_HEALTH = 20.0
WEIGHT_BODY_QUALITY = 10.0
WEIGHT_LANGUAGE_MATCH = 10.0

MAX_SCORE = 99.0
MIN_SCORE = 5.0


def is_pull_request(issue: Mapping[str, object]) -> bool:
    """Return True when a GitHub issues-list entry is actually a pull request.

    The REST issues-list endpoint returns pull requests alongside issues; the
    documented discriminator is the presence of a `pull_request` key.
    """
    return "pull_request" in issue


def is_claimed(issue: Mapping[str, object]) -> bool:
    """Return True when the issue already has an assignee."""
    if issue.get("assignee") is not None:
        return True
    assignees = issue.get("assignees")
    return bool(assignees) if isinstance(assignees, (list, tuple)) else False


def is_stale_issue(issue: Mapping[str, object], *, now: datetime | None = None) -> bool:
    """Return True when an issue is a dead end for a new contributor.

    An issue untouched for six months, or never commented on in a year, is unlikely to
    get a maintainer's attention regardless of its label.
    """
    reference = now or datetime.now(timezone.utc)

    updated = parse_datetime(issue.get("updated_at"))
    if updated is not None and (reference - updated).days > STALE_UPDATED_DAYS:
        return True

    created = parse_datetime(issue.get("created_at"))
    comments = as_int(issue.get("comments"))
    if created is not None and comments == 0 and (reference - created).days > STALE_UNANSWERED_DAYS:
        return True

    return False


def classify_issue_difficulty(
    labels: Sequence[str],
    body: str,
    comments: int,
) -> str:
    """Classify an issue as "easy", "medium", or "hard".

    This is deliberately tier-independent: difficulty describes the issue itself, not
    the developer looking at it, so the same issue shows the same difficulty badge to
    everyone. Tier only affects the developer-relative *score* — see
    `_TIER_FIT_MATRIX` in `score_issue` below.

    Evaluated hard-first so a starter label on a large tracking issue or a design
    debate is not mislabelled easy just because someone also tagged it
    "good first issue".
    """
    label_text = {label.strip().lower() for label in labels if label}
    body_text = body or ""

    if _matches_any(label_text, HARD_LABEL_PATTERNS):
        return "hard"
    if len(body_text) > HARD_BODY_CHARS:
        return "hard"
    if comments > HARD_COMMENT_COUNT:
        return "hard"
    if body_text.count("```") // 2 >= HARD_CODE_FENCE_COUNT:
        return "hard"
    if body_text.count("- [ ]") + body_text.count("- [x]") >= HARD_CHECKLIST_ITEM_COUNT:
        return "hard"

    is_easy_labelled = _matches_any(label_text, EASY_LABEL_PATTERNS)
    if is_easy_labelled and len(body_text) < EASY_BODY_CHARS and comments <= EASY_COMMENT_COUNT:
        return "easy"

    return "medium"


def _matches_any(label_text: set[str], patterns: frozenset[str]) -> bool:
    return any(pattern in label for label in label_text for pattern in patterns) or bool(
        label_text & patterns
    )


@dataclass(frozen=True, slots=True)
class IssueScore:
    """Result of scoring one issue against a tier and skill profile."""

    score: float
    difficulty: str
    reasons: tuple[str, ...]


_TIER_FIT_MATRIX: Mapping[ExperienceTier, Mapping[str, float]] = {
    ExperienceTier.BEGINNER: {"easy": 1.0, "medium": 0.5, "hard": 0.1},
    ExperienceTier.INTERMEDIATE: {"easy": 0.7, "medium": 1.0, "hard": 0.5},
    ExperienceTier.ADVANCED: {"easy": 0.4, "medium": 0.85, "hard": 1.0},
}


def score_issue(
    issue: Mapping[str, object],
    tier: ExperienceTier,
    languages: Sequence[str],
    repo_language: str = "",
    *,
    now: datetime | None = None,
) -> IssueScore:
    """Score a raw GitHub issue payload against a tier and skill profile."""
    reference = now or datetime.now(timezone.utc)

    labels = [
        str(label.get("name", ""))
        for label in as_sequence(issue.get("labels"))
        if isinstance(label, Mapping) and label.get("name")
    ]
    body = str(issue.get("body") or "")
    comments = as_int(issue.get("comments"))

    difficulty = classify_issue_difficulty(labels, body, comments)

    signals = {
        "tier_fit": _TIER_FIT_MATRIX[tier][difficulty],
        "freshness": _score_freshness(issue.get("updated_at"), reference),
        "discussion_health": _score_discussion_health(comments),
        "body_quality": _score_body_quality(body),
        "language_match": _score_language_match(languages, repo_language),
    }
    weighted = (
        signals["tier_fit"] * WEIGHT_TIER_FIT
        + signals["freshness"] * WEIGHT_FRESHNESS
        + signals["discussion_health"] * WEIGHT_DISCUSSION_HEALTH
        + signals["body_quality"] * WEIGHT_BODY_QUALITY
        + signals["language_match"] * WEIGHT_LANGUAGE_MATCH
    )
    score = max(MIN_SCORE, min(MAX_SCORE, weighted))

    reasons = _build_reasons(difficulty, signals, comments)
    return IssueScore(score=round(score, 1), difficulty=difficulty, reasons=reasons)


def _score_freshness(updated_at: object, now: datetime) -> float:
    updated = parse_datetime(updated_at)
    if updated is None:
        return 0.4
    days = (now - updated).days
    if days <= 7:
        return 1.0
    if days <= 30:
        return 0.8
    if days <= 90:
        return 0.45
    return 0.15


def _score_discussion_health(comments: int) -> float:
    if comments == 0:
        return 0.6
    if comments <= 5:
        return 1.0
    if comments <= 15:
        return 0.7
    return 0.25


def _score_body_quality(body: str) -> float:
    if len(body) >= 120:
        return 1.0
    if body.strip():
        return 0.3
    return 0.0


def _score_language_match(languages: Sequence[str], repo_language: str) -> float:
    if not repo_language:
        return 0.5
    normalized_language = repo_language.strip().lower()
    ranked = [lang.strip().lower() for lang in languages if lang and lang.strip()]
    if normalized_language in ranked:
        return 1.0
    return 0.3


def _build_reasons(difficulty: str, signals: Mapping[str, float], comments: int) -> tuple[str, ...]:
    candidates: list[tuple[float, str]] = []

    if signals["tier_fit"] >= 0.85:
        candidates.append((signals["tier_fit"], f"Difficulty ({difficulty}) matches your level."))
    if signals["freshness"] >= 0.8:
        candidates.append((signals["freshness"], "Recently updated by maintainers."))
    if signals["discussion_health"] >= 0.9 and comments > 0:
        candidates.append((signals["discussion_health"], f"{comments} comments show active discussion."))
    if signals["body_quality"] >= 1.0:
        candidates.append((signals["body_quality"], "Clearly described in the issue body."))
    if signals["language_match"] >= 1.0:
        candidates.append((signals["language_match"], "Matches a language you know."))

    fired = [text for _, text in sorted(candidates, key=lambda pair: pair[0], reverse=True)]
    return tuple(fired[:2])
