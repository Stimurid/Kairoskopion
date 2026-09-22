from kairoskopion.kairon_provider import (
    ArtiklStatePointer,
    KaironProviderRequest,
    KaironProviderResponse,
    TargetWorldSnapshot,
    pressure_pack_from_diagnostics,
)


def test_provider_request_keeps_artikl_authority_pointer():
    state = ArtiklStatePointer(
        state_id="state-1",
        state_type="MANUSCRIPT",
        article_seed_pointer="seed-1",
    )
    req = KaironProviderRequest(
        call_id="call-1",
        artikl_state=state,
        target_request={"venue": "Example Journal"},
    )
    assert req.to_dict()["artikl_state"]["authority"] == "ARTIKL"
    assert req.to_dict()["artikl_state"]["article_seed_pointer"] == "seed-1"


def test_pressure_pack_omits_strong_axes_and_preserves_unknowns():
    fit = {
        "axes": [
            {"axis": "topic", "value": "strong"},
            {"axis": "genre", "value": "weak", "notes": "genre mismatch", "evidence_refs": ["src:g"]},
            {"axis": "method", "value": "unknown"},
        ]
    }
    pack = pressure_pack_from_diagnostics(
        target_id="venue-1",
        snapshot_id="snap-1",
        fit=fit,
        evidence_refs=["src:root"],
    )
    assert [p.dimension for p in pack.items] == ["genre", "method"]
    assert pack.items[0].evidence_refs == ["src:root", "src:g"]
    assert "fit:method" in pack.unknowns


def test_core_touching_mismatch_escalates_depth():
    mismatch_map = {
        "mismatches": [
            {
                "mismatch_id": "mm-1",
                "axis": "argument_structure",
                "severity": "major",
                "field_core_risk": "core_touching",
                "description": "Target expects a different argumentative object.",
            }
        ]
    }
    pack = pressure_pack_from_diagnostics(
        target_id="venue-1",
        snapshot_id="snap-1",
        mismatch_map=mismatch_map,
    )
    assert pack.items[0].transformation_depth_hint == "identity_or_reseed_review"


def test_provider_response_can_carry_partial_snapshot_without_erasing_errors():
    snap = TargetWorldSnapshot(snapshot_id="snap-1", target_id="venue-1")
    response = KaironProviderResponse(
        call_id="call-1",
        run_id="run-1",
        status="partial",
        target_snapshot=snap,
        errors=["editor_profile_timeout"],
    )
    data = response.to_dict()
    assert data["target_snapshot"]["snapshot_id"] == "snap-1"
    assert data["errors"] == ["editor_profile_timeout"]
