"""Tests for prompt override and correction models (Track 6)."""
from __future__ import annotations

import pytest

from kairoskopion.services.prompt_override import (
    PromptOverride,
    PromptOverrideStore,
    PromptPatchCandidate,
)


class TestPromptOverride:
    def test_create(self):
        ovr = PromptOverride(
            case_id="c1",
            base_prompt_family_id="article_modeling",
            base_prompt_version_hash="abc123",
        )
        assert ovr.override_id.startswith("povr_")
        assert ovr.status == "draft"
        assert ovr.scope == "case"

    def test_roundtrip(self):
        ovr = PromptOverride(
            case_id="c1",
            base_prompt_family_id="fit_assessment",
            edited_system_prompt="Custom system prompt",
            status="active",
        )
        d = ovr.to_dict()
        restored = PromptOverride.from_dict(d)
        assert restored.edited_system_prompt == "Custom system prompt"
        assert restored.status == "active"

    def test_none_fields_omitted(self):
        ovr = PromptOverride(edited_system_prompt=None, edited_user_template=None)
        d = ovr.to_dict()
        assert "edited_system_prompt" not in d
        assert "edited_user_template" not in d


class TestPromptPatchCandidate:
    def test_create(self):
        corr = PromptPatchCandidate(
            case_id="c1",
            node_id="pnode-1",
            correction_type="output_wrong",
            user_note="Title was extracted incorrectly",
            affected_prompt_family_id="article_modeling",
        )
        assert corr.candidate_id.startswith("ppatch_")
        assert corr.status == "pending_review"

    def test_roundtrip(self):
        corr = PromptPatchCandidate(
            case_id="c1",
            correction_type="missing_field",
            proposed_change="Add explicit instruction for method extraction",
        )
        d = corr.to_dict()
        restored = PromptPatchCandidate.from_dict(d)
        assert restored.proposed_change == "Add explicit instruction for method extraction"


class TestPromptOverrideStore:
    def test_in_memory(self):
        store = PromptOverrideStore()
        ovr = PromptOverride(case_id="c1", base_prompt_family_id="article_modeling")
        store.save_override(ovr)
        assert store.get_override(ovr.override_id) is ovr
        assert len(store.list_overrides("c1")) == 1
        assert len(store.list_overrides("c2")) == 0

    def test_active_override_lookup(self):
        store = PromptOverrideStore()
        draft = PromptOverride(case_id="c1", base_prompt_family_id="art", status="draft")
        active = PromptOverride(case_id="c1", base_prompt_family_id="art", status="active")
        store.save_override(draft)
        store.save_override(active)
        found = store.get_active_override("c1", "art")
        assert found is active

    def test_no_active_override(self):
        store = PromptOverrideStore()
        store.save_override(PromptOverride(case_id="c1", base_prompt_family_id="art", status="draft"))
        assert store.get_active_override("c1", "art") is None

    def test_update_status(self):
        store = PromptOverrideStore()
        ovr = PromptOverride(case_id="c1", status="draft")
        store.save_override(ovr)
        store.update_status(ovr.override_id, "active")
        assert store.get_override(ovr.override_id).status == "active"

    def test_corrections(self):
        store = PromptOverrideStore()
        corr = PromptPatchCandidate(case_id="c1", correction_type="wrong_output")
        store.save_correction(corr)
        assert len(store.list_corrections("c1")) == 1
        assert len(store.list_corrections("c2")) == 0

    def test_persistence(self, tmp_path):
        store = PromptOverrideStore(data_dir=tmp_path)
        ovr = PromptOverride(case_id="c1", base_prompt_family_id="art")
        corr = PromptPatchCandidate(case_id="c1", correction_type="x")
        store.save_override(ovr)
        store.save_correction(corr)

        store2 = PromptOverrideStore(data_dir=tmp_path)
        assert len(store2.list_overrides("c1")) == 1
        assert len(store2.list_corrections("c1")) == 1
