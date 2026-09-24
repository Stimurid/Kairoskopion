from kairoskopion.prompts.academic_world_resolution import (
    validate_academic_world_resolution,
)


def _result(path, *, supported=False, scaffold=False):
    return {
        "trajectories": [{
            "path_node_ids": path,
            "disciplinary_pathway_ref": "path:1",
            "fit_status": "supported" if supported else "plausible",
            "evidence_refs": [],
            "routing_scaffold_only": scaffold,
            "reasoning": "routing",
        }],
        "coverage_gaps": [],
        "acquisition_tasks": [],
        "unknowns": [],
        "confidence": "low",
        "reasoning": "test",
    }


def test_academic_world_resolution_rejects_nonlocal_node_reference():
    warnings = validate_academic_world_resolution(
        _result(["ecology:invented"]),
        local_node_ids={"ecology:anglophone"},
    )
    assert any("non-local" in warning for warning in warnings)


def test_routing_scaffold_alone_cannot_support_substantive_fit():
    warnings = validate_academic_world_resolution(
        _result(["ecology:anglophone"], supported=True, scaffold=True),
        local_node_ids={"ecology:anglophone"},
    )
    assert any("routing scaffold alone" in warning for warning in warnings)