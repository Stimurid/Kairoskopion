from kairoskopion.adapters.venue.fulltext_fetch import (
    acquire_explicit_fulltext,
)


def test_html_interstitial_is_not_validated_as_fulltext(tmp_path):
    body = (
        b"<!doctype html><html><head><title>Just a moment...</title></head>"
        b"<body>Please verify you are human."
        + (b"x" * 6000)
        + b"</body></html>"
    )
    result = acquire_explicit_fulltext(
        "https://example.org/article/1",
        output_dir=tmp_path,
        fixture_bytes=body,
        fixture_content_type="text/html; charset=utf-8",
    )
    assert result["status"] == "acquired_unvalidated"
    assert result["validation"]["reason"] == "html_interstitial_or_challenge"


def test_tiny_html_is_not_validated_as_fulltext(tmp_path):
    body = (
        b"<!doctype html><html><head><title>Article</title></head><body>"
        + (b"short page " * 150)
        + b"</body></html>"
    )
    assert len(body) < 5000
    result = acquire_explicit_fulltext(
        "https://example.org/article/2",
        output_dir=tmp_path,
        fixture_bytes=body,
        fixture_content_type="text/html; charset=utf-8",
    )
    assert result["status"] == "acquired_unvalidated"
    assert result["validation"]["reason"] == "html_too_small_for_fulltext"


def test_substantive_html_shape_can_still_validate(tmp_path):
    body = (
        b"<!doctype html><html><head><title>Article</title></head><body>"
        + (b"substantive scholarly paragraph with claims and evidence. " * 140)
        + b"</body></html>"
    )
    assert len(body) > 5000
    result = acquire_explicit_fulltext(
        "https://example.org/article/3",
        output_dir=tmp_path,
        fixture_bytes=body,
        fixture_content_type="text/html; charset=utf-8",
    )
    assert result["status"] == "validated"
    assert result["validation"]["reason"] == "html_shape_ok"
