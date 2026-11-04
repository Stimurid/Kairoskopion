"""F4 existing Factory revision: guard against forged postresearch permission."""
from pathlib import Path
from unittest import mock
import pytest

from kairoskopion.kairon_provider import native_science_revision as m
from kairoskopion.kairon_provider.publication_runner import EvidenceBlocked

ROOT=Path(r"C:\projects\trimurti\_ops\T3-TALK-20261019\F4_REVIEW_RETURN_20261104")
FACTORY=ROOT/"F4_native_return"/"12f432c51f58209260ad29f05da42ebb10b95228a54c03fd7317064a044fe3b5"
EVIDENCE=Path(r"C:\Users\Homee\.openclaw\hestia-body\INDAGO_STATE\add006_ops\state\add006_claims\c5ab41486981053ec7ca0053a10d7a37\evidence_return.json")
SCI=Path(r"C:\projects\trimurti-t3-articles\runs\T3-Factory")
PINS={
 "manifest":ROOT/"editorial_return_input_manifest.json",
 "manifest_sha":"5220e2bd147e8bf677c30f0f8bb06950f9c1a5e103c403e1fbfd1535e741ae66",
 "factory_state":FACTORY/"native_factory_state.json",
 "factory_sha":"2f04f04daa71890d9d2a825fab4d15a4085a1361c1227e1396feb18b46bef303",
 "native_artikl_stdout":FACTORY/"native_artikl_stdout.json",
 "artikl_sha":"3b6614ce93ec6328ca061f2dd5fa21983d13a8a146c418e8241c238f896b062d",
 "evidence":EVIDENCE,
 "evidence_sha":"affa334286d2823dc6130fa40ec928b478f57b546b5842ecdc42fe21a71eb95f",
 "whitecrow_report":FACTORY/"whitecrow"/"whitecrow_d24_after_add006.json",
 "report_sha":"0e7357f00359408572500738f0f52b3acf14fb924ef93600de7cb6b1f34ea047",
 "request":SCI/"F4_M117_research_request_PENDING.json",
 "request_sha":"f9b175b4b9641f0dd38d04a9b9df7b8bef692d14a248758e496d04a1bc3d2810",
}

def test_real_f4_reaches_native_writer_but_not_replay_hunt(tmp_path):
    with mock.patch.object(m,"native_call",side_effect=RuntimeError("TEST_REACHED_NATIVE_WRITER_NO_MODEL")) as native:
        with pytest.raises(RuntimeError,match="TEST_REACHED_NATIVE_WRITER_NO_MODEL"):
            m.run(**PINS,output_root=tmp_path/"draft")
    assert native.call_count==1
    assert native.call_args.args[1]=="return_writer"
    assert (tmp_path/"draft"/"science_revision.lock").exists() is False

def test_f4_bad_pins_block_before_any_model(tmp_path):
    wrong=dict(PINS, evidence_sha="0"*64)
    with mock.patch.object(m,"native_call",side_effect=AssertionError("model must not run")):
        with pytest.raises(EvidenceBlocked,match="SHA|sha|mismatch|hash|source"):
            m.run(**wrong,output_root=tmp_path/"draft")

def test_f4_cannot_repurpose_more_research_as_revision(tmp_path):
    with mock.patch.object(m,"_assert_science_choice",return_value="MORE_RESEARCH"),\
         mock.patch.object(m,"native_call",side_effect=AssertionError("model must not run")):
        with pytest.raises(EvidenceBlocked,match="science_revision_native_artikl_chose_no_revision"):
            m.run(**PINS,output_root=tmp_path/"draft")


def test_f4_original_stored_revision_recovery_is_byte_pinned(tmp_path):
    from shutil import copyfile
    root=tmp_path/"recovered"
    root.mkdir()
    original=ROOT/"F4_science_revision"
    for name in ("return_writer.gateway.json","draft_v0_7.md"):
        copyfile(original/name,root/name)
    mat=ROOT/"F4_writer_materialize_gateway.json"
    trace=ROOT/".openclaw"/"trajectory-exports"/"f4-author-revision-original-run"/"events.jsonl"
    get=dict(
        root=root,target=root/"draft_v0_7.md",
        materialization_gateway=mat,
        materialization_sha="f7606df1281113c1ce842c5950987375a18d8eb137250d2d380fa677b4be3041",
        trajectory=trace,
        trajectory_sha="4bcabfc70653aff19d3fd5cf5c5556b0fefd693720f77ffe90641207bf3d51cb",
    )
    ret=m._original_session_store_recovery(**get)
    assert ret["sha256"]=="f666305599484901a0569d0fdf0a60a5272c3ea5ed269e5c7c9a3f7282d03c75"
    import json
    receipt=json.loads((root/"return_writer_store_recovery_receipt.json").read_text(encoding="utf-8"))
    assert receipt["original_store_content_sha256_available"] is False
    assert receipt["source_by_session_continuity_not_byte_comparison"] is True
    assert receipt["materialized_file_chars"] == 48741
    assert receipt["author_gate"]=="HOLD" and receipt["send"] is False
    wrong=dict(get,materialization_sha="f"*64)
    with pytest.raises(EvidenceBlocked):
        m._original_session_store_recovery(**wrong)
    (root/"draft_v0_7.md").write_text("# short",encoding="utf-8")
    with pytest.raises(EvidenceBlocked,match="byte_count_invalid"):
        m._original_session_store_recovery(**get)
