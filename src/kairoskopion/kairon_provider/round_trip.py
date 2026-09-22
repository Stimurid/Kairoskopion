"""Round-trip comparison for Kairon ↔ Kairoskopion closed loops."""

from __future__ import annotations

from .models import ArtiklStatePointer, RoundTripComparison, TargetPressurePack


def compare_round_trip(
    *,
    call_id: str,
    prior_state: ArtiklStatePointer,
    current_state: ArtiklStatePointer,
    prior_pack: TargetPressurePack,
    current_pack: TargetPressurePack,
) -> RoundTripComparison:
    if prior_pack.snapshot_id != current_pack.snapshot_id:
        note = (
            "target snapshot changed between runs; pressure delta mixes manuscript "
            "change with target-world refresh"
        )
    else:
        note = "same frozen target snapshot used for round-trip comparison"

    prior = {p.pressure_id for p in prior_pack.items}
    current = {p.pressure_id for p in current_pack.items}
    return RoundTripComparison(
        call_id=call_id,
        prior_state=prior_state,
        current_state=current_state,
        target_snapshot_id=current_pack.snapshot_id,
        prior_pressure_ids=sorted(prior),
        current_pressure_ids=sorted(current),
        resolved_pressure_ids=sorted(prior - current),
        persistent_pressure_ids=sorted(prior & current),
        new_pressure_ids=sorted(current - prior),
        notes=[note],
    )
