"""LOKI R1: hostile tests for read-only Artikl/Kairon official-rule admission."""
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest

from kairoskopion.loki import (
    GameHypothesis, GameModel, ProbeKind, ProbeRecord, StrategyPolicy,
    Decision, Verification,
)
from kairoskopion.loki.read_only import (
    SourceNotAdmitted, admit_official_policy_quote, admitted_probe_outcome,
    game_from_artikl_target,
)
from kairoskopion.schema import SourceSnapshot, VenueClaim, VenueSource
from kairoskopion.source_authority import SourceAuthorityClaim
from kairoskopion.enums import AuthorityStrength, SourceAccessMode, SourceAuthorityScope
from kairoskopion.kairon_provider.models import (
    ArtiklArticleProjection, ArtiklStatePointer, TargetWorldSnapshot,
)


HOST = "think.taylorandfrancis.com"
PAGE_URL = "https://think.taylorandfrancis.com/special_issues/the-politics-of-assessment/"
QUOTE = "We welcome conceptual and philosophical studies in educational assessment."
VENUE = "VENUE:ASSESSMENT"
ARTICLE = "ARTIKL:EDUCATIONAL-EVENT"


def snapshot_bundle(tmp_path, *,
                    html=None, venue=VENUE, category="CONCEPTUAL_ALLOWED",
                    url=PAGE_URL, official=True):
    content = html or (
        "<html><head><script>ignore this script</script></head><body>"
        "<p>We welcome conceptual and philosophical studies in educational assessment.</p>"
        "<p>Abstract deadline: 02 November 2026</p></body></html>"
    )
    source_path = tmp_path / "publisher.html"
    source_path.write_text(content, encoding="utf-8")
    digest = sha256(source_path.read_bytes()).hexdigest()
    snap = SourceSnapshot(
        snapshot_id="snapshot:official:1",
        source_id="publisher:policy:1", url=url, raw_ref="publisher.html",
        content_hash=digest, retrieved_at="2026-10-20T14:00:00Z",
        content_type="text/html", extraction_status="html_parsed",
    )
    claim = SourceAuthorityClaim(
        claim_id="claim:formal:1", source_ref=snap.snapshot_id,
        evidence_ref=snap.snapshot_id,
        access_mode=(SourceAccessMode.OFFICIAL_WEBPAGE.value if official
                     else SourceAccessMode.MANUAL_NOTE.value),
        authority_scope=SourceAuthorityScope.FORMAL_REQUIREMENTS.value,
        claim_key="scope.accepts_conceptual",
        claim_value=category,
        authority_strength=AuthorityStrength.AUTHORITATIVE.value,
        supported_entity_id=venue,
    )
    venue_source = VenueSource(
        venue_source_id="venue:source:1", venue_record_id=venue,
        source_url=url, source_type="official_call",
    )
    venue_claim = VenueClaim(
        venue_claim_id="venue:claim:1", venue_source_id=venue_source.venue_source_id,
        venue_record_id=venue,
        claim_path=claim.claim_key, claim_value=claim.claim_value,
        quote_or_summary=QUOTE,
        evidence_status="source_anchored",
    )
    return snap, claim, venue_source, venue_claim


def admit(tmp_path, bundle=None, **kwargs):
    source, claim, venue_source, venue_claim = bundle or snapshot_bundle(tmp_path)
    return admit_official_policy_quote(
        source, claim, venue_source, venue_claim,
        expected_target_id=kwargs.pop("expected_target_id", VENUE),
        source_root=kwargs.pop("source_root", tmp_path),
        official_hosts=kwargs.pop("official_hosts", frozenset({HOST})),
        **kwargs,
    )


def game():
    return GameModel(game_id="G:FIELD:VENUE", scope_ref=f"{ARTICLE} x {VENUE}",
                     objective_ids=("scientific_integrity", "venue_suitability"),
                     protected_field_ref="FIELD:E", source_revisions=("x",))


def hypothesis_pair():
    return (
        GameHypothesis("H:EXCLUDES_CONCEPTUAL", game().game_id,
                       "Conceptual work excluded", "genre rule"),
        GameHypothesis("H:PERMITS_CONCEPTUAL", game().game_id,
                       "Conceptual work admitted", "scope and evidence regime"),
    )


def probe():
    return ProbeRecord(
        probe_id="P:PASSIVE_RULE", game_id=game().game_id,
        kind=ProbeKind.PASSIVE_ANALYSIS, cost=0.0,
        predictions=(("H:EXCLUDES_CONCEPTUAL", "CONCEPTUAL_EXCLUDED"),
                     ("H:PERMITS_CONCEPTUAL", "CONCEPTUAL_ALLOWED")),
        source_refs=("snapshot:official:1",),
    )


def test_admit_existing_source_and_venue_models_by_exact_anchored_quote(tmp_path):
    receipt = admit(tmp_path)
    assert receipt.declared_outcome == "CONCEPTUAL_ALLOWED"
    assert receipt.scope == "FORMAL_REQUIREMENTS_ONLY"
    assert receipt.sha256_digest == sha256((tmp_path / "publisher.html").read_bytes()).hexdigest()
    evidence, statuses = admitted_probe_outcome(game(), probe(), hypothesis_pair(), receipt)
    assert receipt.origin_verification == "LOCAL_BYTES_ANCHORED_ORIGIN_NOT_AUTHENTICATED"
    assert evidence.verification is Verification.PARTIAL
    assert set(statuses.values()) == {"INDETERMINATE"}
    # Local byte/quote matching alone is not a publisher authenticity receipt.
    assert evidence.outcome == "CONCEPTUAL_ALLOWED"


def test_missing_data_or_fake_hash_fails(tmp_path):
    bundle = snapshot_bundle(tmp_path)
    snap = replace(bundle[0], content_hash="a" * 64)
    with pytest.raises(SourceNotAdmitted, match="altered"):
        admit(tmp_path, (snap, *bundle[1:]))
    with pytest.raises(SourceNotAdmitted, match="timestamp"):
        admit(tmp_path, (replace(bundle[0], retrieved_at=None), *bundle[1:]))


def test_source_file_tamper_does_not_change_admission_silently(tmp_path):
    bundle = snapshot_bundle(tmp_path)
    path = tmp_path / "publisher.html"
    path.write_text("Page updated with new policy", encoding="utf-8")
    with pytest.raises(SourceNotAdmitted, match="altered"):
        admit(tmp_path, bundle)


@pytest.mark.parametrize("invalid_url", [
    "http://think.taylorandfrancis.com/special_issues/the-politics-of-assessment/",
    "https://think.taylorandfrancis.com.evil.invalid/special_issue",
    "https://user:pass@think.taylorandfrancis.com/page",
    "https://evil.invalid/page",
])
def test_publisher_host_is_exact_allowlisted_https(tmp_path, invalid_url):
    bundle = snapshot_bundle(tmp_path, url=invalid_url)
    with pytest.raises(SourceNotAdmitted, match="approved publisher host"):
        admit(tmp_path, bundle)


def test_root_escape_rejected(tmp_path):
    inside = tmp_path / "inside"
    inside.mkdir()
    bundle = snapshot_bundle(tmp_path)
    outside = replace(bundle[0], raw_ref=str(tmp_path / "publisher.html"))
    with pytest.raises(SourceNotAdmitted, match="escapes"):
        admit(tmp_path, (outside, *bundle[1:]), source_root=inside)


def test_wrong_venue_or_cross_venue_ref_rejected(tmp_path):
    bundle = snapshot_bundle(tmp_path)
    with pytest.raises(SourceNotAdmitted, match="cross-venue"):
        admit(tmp_path, (bundle[0], bundle[1], bundle[2],
                         replace(bundle[3], venue_record_id="VENUE:OTHER")))
    with pytest.raises(SourceNotAdmitted, match="does not match"):
        admit(tmp_path, bundle, expected_target_id="VENUE:OTHER")


def test_unsupported_policy_and_editorial_scope_cannot_be_certified(tmp_path):
    bundle = snapshot_bundle(tmp_path)
    wrong_scope = replace(bundle[1],
                          authority_scope=SourceAuthorityScope.PRIOR_OUTCOME.value)
    with pytest.raises(SourceNotAdmitted, match="formal"):
        admit(tmp_path, (bundle[0], wrong_scope, bundle[2], bundle[3]))
    manual = replace(bundle[1], access_mode=SourceAccessMode.MANUAL_NOTE.value)
    with pytest.raises(SourceNotAdmitted, match="formal"):
        admit(tmp_path, (bundle[0], manual, bundle[2], bundle[3]))


def test_claim_disagreement_and_unanchored_quote_rejected(tmp_path):
    bundle = snapshot_bundle(tmp_path)
    bad = replace(bundle[3], quote_or_summary="This official page prohibits conceptual papers in all cases.")
    with pytest.raises(SourceNotAdmitted, match="not present"):
        admit(tmp_path, (bundle[0], bundle[1], bundle[2], bad))
    changed = replace(bundle[3], claim_value="CONCEPTUAL_EXCLUDED")
    with pytest.raises(SourceNotAdmitted, match="disagree"):
        admit(tmp_path, (bundle[0], bundle[1], bundle[2], changed))


def test_script_injected_quote_is_not_evidence(tmp_path):
    content = ("<html><script>" + QUOTE + "</script><body>"
               "Only empirical research is invited.</body></html>")
    with pytest.raises(SourceNotAdmitted, match="not present"):
        admit(tmp_path, snapshot_bundle(tmp_path, html=content))


def test_empty_or_unreadable_source_status_rejected(tmp_path):
    bundle = snapshot_bundle(tmp_path)
    bad = replace(bundle[0], extraction_status="not_read", content_hash="f" * 64)
    with pytest.raises(SourceNotAdmitted, match="readable"):
        admit(tmp_path, (bad, *bundle[1:]))


def test_observer_cannot_change_what_the_probe_registered(tmp_path):
    receipt = admit(tmp_path)
    bad = replace(probe(), predictions=(
        ("H:EXCLUDES_CONCEPTUAL", "CATEGORY_A"),
        ("H:PERMITS_CONCEPTUAL", "CATEGORY_B"),
    ))
    with pytest.raises(SourceNotAdmitted, match="preregistered"):
        admitted_probe_outcome(game(), bad, hypothesis_pair(), receipt)


def test_observer_cannot_reuse_venue_evidence_for_another_game(tmp_path):
    receipt = admit(tmp_path)
    bad_game = replace(game(), scope_ref="ARTIKL:X x VENUE:UNRELATED")
    with pytest.raises(SourceNotAdmitted, match="scope"):
        admitted_probe_outcome(bad_game, probe(), hypothesis_pair(), receipt)


def test_non_passive_action_cannot_pass_official_page_as_its_result(tmp_path):
    receipt = admit(tmp_path)
    bad = replace(probe(), kind=ProbeKind.AUTHORIZED_REAL_ACTION, access_approved=True)
    with pytest.raises(SourceNotAdmitted, match="active"):
        admitted_probe_outcome(game(), bad, hypothesis_pair(), receipt)


def test_requires_prior_registration_of_source_id(tmp_path):
    receipt = admit(tmp_path)
    bad = replace(probe(), source_refs=("snapshot:other",))
    with pytest.raises(SourceNotAdmitted, match="pre-register"):
        admitted_probe_outcome(game(), bad, hypothesis_pair(), receipt)


def test_article_world_link_uses_existing_artikl_and_kairon_types():
    art = ArtiklArticleProjection(
        artikl_state=ArtiklStatePointer(
            state_id="ARTIKL:E:seed", state_type="ArticleModel", version="revision-3",
            source_refs=("LITOPS:SOURCE:1",)),
        problem_statement="What is valid evidence of student choice?",
        core_claims=["An artefact alone does not prove educational choice"],
        protected_core=["Distinguish observable product and causal process"],
    )
    target = TargetWorldSnapshot(snapshot_id="TARGET:VI:4",
                                 target_id="VENUE:ASSESSMENT")
    got = game_from_artikl_target(
        art, target, owner_objective_ids=("scientific_integrity", "venue_suitability"),
        protected_field_ref="WHITE_CROW:FIELD:E:17",
        source_snapshot_refs=("SNAPSHOT:1",),
    )
    assert "revision-3" in got.scope_ref
    assert got.explicit_rule_refs == ("SNAPSHOT:1",)
    assert "WHITE_CROW:FIELD:E:17" == got.protected_field_ref
    assert "authenticity" in got.unknowns[0]


def test_artikl_not_attested_cannot_be_promoted_to_canon():
    art = ArtiklArticleProjection(artikl_state=ArtiklStatePointer(
        state_id="S:1", state_type="seed", version="1", authority="UNKNOWN"))
    target = TargetWorldSnapshot(snapshot_id="TW:1", target_id="V:1")
    with pytest.raises(SourceNotAdmitted, match="Artikl"):
        game_from_artikl_target(
            art, target, owner_objective_ids=("science",),
            protected_field_ref="FIELD:1", source_snapshot_refs=(),
        )


def test_no_field_reentry_pointer_no_game_certification():
    art = ArtiklArticleProjection(artikl_state=ArtiklStatePointer(
        state_id="S:1", state_type="seed", version="1"))
    target = TargetWorldSnapshot(snapshot_id="TW:1", target_id="V:1")
    with pytest.raises(SourceNotAdmitted, match="protected"):
        game_from_artikl_target(
            art, target, owner_objective_ids=("science",),
            protected_field_ref="", source_snapshot_refs=(),
        )


def test_locally_forged_approved_domain_page_cannot_become_verified_real(tmp_path):
    """Matching caller-supplied bytes and hostname do not prove remote origin."""
    bundle = snapshot_bundle(
        tmp_path,
        html=(
            "<html><body><p>" + QUOTE + "</p>"
            "<p>This text was invented by the local fixture author.</p></body></html>"
        ),
    )
    receipt = admit(tmp_path, bundle)
    evidence, status = admitted_probe_outcome(game(), probe(), hypothesis_pair(), receipt)
    assert receipt.origin_verification == "LOCAL_BYTES_ANCHORED_ORIGIN_NOT_AUTHENTICATED"
    assert evidence.verification is Verification.PARTIAL
    assert not evidence.is_verified_real
    assert set(status.values()) == {"INDETERMINATE"}
