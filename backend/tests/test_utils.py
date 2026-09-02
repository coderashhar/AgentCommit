"""Tests for app.tools.utils — cache key building and text truncation."""

from app.tools.utils import build_cache_key, truncate_text, CACHE_SCHEMA_VERSION


# ---------- build_cache_key ----------


class TestBuildCacheKey:
    def test_stability(self):
        """Same inputs must always produce the same key."""
        key1 = build_cache_key("repos", "python", "beginner")
        key2 = build_cache_key("repos", "python", "beginner")
        assert key1 == key2

    def test_version_prefix(self):
        key = build_cache_key("repos", "python")
        assert key.startswith(f"agentcommit:{CACHE_SCHEMA_VERSION}:")

    def test_namespace_in_key(self):
        key = build_cache_key("profile", "alice")
        assert ":profile:" in key

    def test_different_inputs_different_keys(self):
        key1 = build_cache_key("repos", "python", "beginner")
        key2 = build_cache_key("repos", "rust", "advanced")
        assert key1 != key2

    def test_sequence_sorted(self):
        """Sequence parts are sorted, so differently-ordered lists collide."""
        key1 = build_cache_key("repos", ["python", "javascript"])
        key2 = build_cache_key("repos", ["javascript", "python"])
        assert key1 == key2

    def test_case_insensitive(self):
        key1 = build_cache_key("repos", "Python")
        key2 = build_cache_key("repos", "python")
        assert key1 == key2

    def test_long_input_hashed(self):
        """Input longer than 120 chars gets sha256-hashed."""
        long_part = "a" * 200
        key = build_cache_key("repos", long_part)
        # The tail should be a 64-char hex digest, not the raw string
        tail = key.split(":")[-1]
        assert len(tail) == 64  # sha256 hex length

    def test_short_input_inline(self):
        key = build_cache_key("repos", "py")
        tail = key.split(":")[-1]
        assert tail == "py"

    def test_whitespace_stripped(self):
        key1 = build_cache_key("repos", "  python  ")
        key2 = build_cache_key("repos", "python")
        assert key1 == key2


# ---------- truncate_text ----------


class TestTruncateText:
    def test_short_text_unchanged(self):
        text = "Hello world"
        assert truncate_text(text, 200) == text

    def test_exact_length_unchanged(self):
        text = "x" * 200
        assert truncate_text(text, 200) == text

    def test_long_text_truncated(self):
        text = "word " * 100  # 500 chars
        result = truncate_text(text, 50)
        assert len(result) <= 53  # 50 + "..."
        assert result.endswith("...")

    def test_preserves_word_boundary(self):
        text = "hello world this is a test"
        result = truncate_text(text, 12)
        assert result.endswith("...")
        # Should break at word boundary, not mid-word
        assert "hell..." not in result or "hello..." in result

    def test_empty_text(self):
        assert truncate_text("", 200) == ""

    def test_default_max_length(self):
        text = "x " * 200  # 400 chars
        result = truncate_text(text)  # default is 200
        assert len(result) <= 203
