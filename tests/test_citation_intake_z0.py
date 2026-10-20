"""Z0 acceptance: read already inserted / author-wanted citations without patching."""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from kairoskopion.services.citation_intake_z0 import (
    VERSION, audit_manuscript, persist_audit,
)

WORD = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG = "http://schemas.openxmlformats.org/package/2006/relationships"


def _docx(path: Path, body: str, *, comments: str | None = None,
          footnotes: str | None = None, rels: str | None = None,
          extra: dict[str, str] | None = None) -> Path:
    doc = (
        f'<w:document xmlns:w="{WORD}" xmlns:r="{REL}">'
        f"<w:body>{body}</w:body></w:document>"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", doc)
        if comments is not None:
            archive.writestr(
                "word/comments.xml",
                f'<w:comments xmlns:w="{WORD}">{comments}</w:comments>',
            )
        if footnotes is not None:
            archive.writestr(
                "word/footnotes.xml",
                f'<w:footnotes xmlns:w="{WORD}">{footnotes}</w:footnotes>',
            )
        if rels is not None:
            archive.writestr(
                "word/_rels/document.xml.rels",
                f'<Relationships xmlns="{PKG}">{rels}</Relationships>',
            )
        for name, content in (extra or {}).items():
            archive.writestr(name, content)
    return path


def _p(text: str) -> str:
    return f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>"


def _kinds(audit):
    return {ci.kind for ci in audit.intakes}


def _origin(audit, origin):
    return [ci for ci in audit.intakes if ci.origin_type == origin]


def test_author_wish_and_existing_author_year_are_independent(tmp_path):
    manuscript = tmp_path / "paper.md"
    manuscript.write_text(
        "Операция памяти: [нужна цитата Выготского].\n"
        "См. также (Выготский, 1978, с. 22).\n", encoding="utf-8"
    )
    audit = audit_manuscript(manuscript)
    assert _origin(audit, "AUTHOR_DESIRED")
    assert "AUTHOR_YEAR" in _kinds(audit)
    assert audit.source["byte_length"] == len(manuscript.read_bytes())
    assert all(ci.verification_status == "NOT_CHECKED" for ci in audit.intakes)
    assert all(case.verification["V5"] == "NOT_CHECKED"
               for case in audit.repair_cases)
    assert len(audit.intakes) == len(audit.repair_cases)


def test_implicit_author_wish_is_not_claim_certification(tmp_path):
    p = tmp_path / "draft.txt"
    p.write_text(
        "Как говорил Эйзенштейн, здесь есть монтаж мышления.\n"
        "А тут цитата Выготского.\n"
        "кто-то из великих сказал, что это нужно помнить.",
        encoding="utf-8",
    )
    result = audit_manuscript(p)
    assert len(_origin(result, "AUTHOR_DESIRED")) >= 3
    assert all(c.verification_status == "NOT_CHECKED" for c in result.intakes)


def test_placed_quote_and_bibliography_generate_separate_work_orders(tmp_path):
    p = tmp_path / "paper.md"
    p.write_text(
        "«Слишком длинная цитата, которую надо сверить с оригинальным "
        "источником исследования»\n"
        "Вывод согласно (Декарт, 1641, с. 360).\n"
        "## Список литературы\n"
        "Декарт Р. Regulae ad directionem ingenii. AT X.\n",
        encoding="utf-8",
    )
    result = audit_manuscript(p)
    assert "UNATTRIBUTED_QUOTE_CANDIDATE" in _kinds(result)
    assert "BIBLIOGRAPHY_ENTRY" in _kinds(result)
    assert "AUTHOR_YEAR" in _kinds(result)
    assert len(result.repair_cases) == len(result.intakes)
    for case in result.repair_cases:
        assert case.status == "OPEN_UNVERIFIED"
        assert case.original_preserved
        assert case.proposed_patch is None


def test_quote_with_nearby_reference_not_labeled_orphan(tmp_path):
    p = tmp_path / "paper.txt"
    p.write_text(
        "«Здесь длинная реальная цитата внутри иллюстративного текста» "
        "(Выготский, 1978, с. 45)", encoding="utf-8",
    )
    result = audit_manuscript(p)
    assert "AUTHOR_YEAR" in _kinds(result)
    assert "UNATTRIBUTED_QUOTE_CANDIDATE" not in _kinds(result)


def test_doi_citekeys_numeric_and_latex_preserved_as_unverified(tmp_path):
    p = tmp_path / "article.md"
    p.write_text(
        "Основания [1] см. также @smith2020 и "
        r"\cite{vygotsky1978}. DOI: 10.1234/test.2024", encoding="utf-8"
    )
    result = audit_manuscript(p)
    assert {"NUMERIC_REFERENCE", "CITEKEY", "LATEX_CITE",
            "DOI_REFERENCE"} <= _kinds(result)
    assert result.coverage["all_citations_scientifically_verified"] is False


def test_docx_reads_comment_wish_and_body_citation_with_parent_anchor(tmp_path):
    body = (
        '<w:p><w:commentRangeStart w:id="5"/>'
        '<w:r><w:t>Основной тезис (Декарт, 1641).</w:t></w:r>'
        '<w:commentReference w:id="5"/></w:p>'
    )
    comments = (
        '<w:comment w:id="5"><w:p><w:r><w:t>'
        "тут цитата Выготского"
        "</w:t></w:r></w:p></w:comment>"
    )
    p = _docx(tmp_path / "paper.docx", body, comments=comments)
    result = audit_manuscript(p)
    desired = [x for x in _origin(result, "AUTHOR_DESIRED")
               if x.surface == "comment"]
    assert len(desired) == 1
    assert desired[0].parent_anchor == "word/document.xml/p[0]"
    assert "AUTHOR_YEAR" in _kinds(result)
    assert "Выготского" in desired[0].original_fragment
    assert result.coverage["surfaces"]["comment"] == "SCANNED"


def test_docx_reads_split_word_zotero_field(tmp_path):
    body = (
        '<w:p><w:r><w:t>Ссылка [Smith 2020]</w:t></w:r>'
        '<w:r><w:instrText>ADDIN ZOTERO_</w:instrText></w:r>'
        '<w:r><w:instrText>ITEM CSL_CITATION {"citationID":"abc"}</w:instrText></w:r>'
        "</w:p>"
    )
    p = _docx(tmp_path / "field.docx", body)
    result = audit_manuscript(p)
    field = [ci for ci in result.intakes if ci.kind == "ZOTERO_FIELD"]
    assert len(field) == 1
    assert "CSL_CITATION" in field[0].original_fragment
    assert "ZOTERO_ITEM" in field[0].original_fragment
    assert field[0].verification_status == "NOT_CHECKED"


def test_docx_footnote_and_endnote_wish(tmp_path):
    body = (
        '<w:p><w:r><w:t>Обоснование</w:t></w:r>'
        '<w:footnoteReference w:id="2"/>'
        "</w:p>"
    )
    foot = (
        '<w:footnote w:id="2"><w:p><w:r><w:t>'
        "[нужна ссылка]"
        "</w:t></w:r></w:p></w:footnote>"
    )
    p = _docx(tmp_path / "with_notes.docx", body, footnotes=foot)
    result = audit_manuscript(p)
    assert any(x.surface == "footnote" and x.origin_type == "AUTHOR_DESIRED"
               for x in result.intakes)
    assert result.coverage["surfaces"]["footnote"] == "SCANNED"


def test_docx_external_hyperlink_captured_without_dereferencing(tmp_path):
    body = (
        '<w:p><w:hyperlink r:id="rId9"><w:r><w:t>'
        "Primary paper"
        "</w:t></w:r></w:hyperlink></w:p>"
    )
    rel = (
        '<Relationship Id="rId9" TargetMode="External" '
        'Target="https://doi.org/10.1234/example" Type="link"/>'
    )
    p = _docx(tmp_path / "links.docx", body, rels=rel)
    result = audit_manuscript(p)
    links = [x for x in result.intakes if x.kind == "EMBEDDED_HYPERLINK"]
    assert len(links) == 1
    assert links[0].original_fragment.startswith("https://doi.org/")


def test_missing_docx_comment_anchor_is_coverage_debt(tmp_path):
    body = _p("Размышление без привязанного комментария")
    comments = (
        '<w:comment w:id="42"><w:p><w:r><w:t>'
        "[citation needed]"
        "</w:t></w:r></w:p></w:comment>"
    )
    p = _docx(tmp_path / "stray.docx", body, comments=comments)
    result = audit_manuscript(p)
    assert result.coverage["status"] == "PARTIAL_WITH_COVERAGE_DEBT"
    assert any("no body anchor" in x for x in result.coverage["debts"])
    assert len(_origin(result, "AUTHOR_DESIRED")) == 1


def test_original_bytes_saved_and_idempotent(tmp_path):
    p = tmp_path / "original.md"
    p.write_text("Тут цитата Выготского. (Декарт, 1641).", encoding="utf-8")
    sha = hashlib.sha256(p.read_bytes()).hexdigest()
    out = tmp_path / "audit_data"
    first, receipt = persist_audit(p, out)
    second, again = persist_audit(p, out)
    assert receipt == again
    assert first.source["original_snapshot_sha256_verified"]
    assert receipt.exists()
    assert sha == hashlib.sha256(p.read_bytes()).hexdigest()
    assert sha == hashlib.sha256(
        Path(first.source["original_snapshot_path"]).read_bytes()
    ).hexdigest()
    assert receipt.read_bytes() == again.read_bytes()
    assert [x.intake_id for x in first.intakes] == [
        x.intake_id for x in second.intakes
    ]


def test_original_change_keeps_old_immutable_snapshot(tmp_path):
    p = tmp_path / "original.txt"
    p.write_text("[citation needed]", encoding="utf-8")
    a, report1 = persist_audit(p, tmp_path / "out")
    p.write_text("[citation needed] (Smith 2020)", encoding="utf-8")
    b, report2 = persist_audit(p, tmp_path / "out")
    assert a.source["sha256"] != b.source["sha256"]
    assert report1 != report2
    assert Path(a.source["original_snapshot_path"]).read_text() == (
        "[citation needed]"
    )


def test_no_editor_mutation_and_no_fake_verified_claim(tmp_path):
    p = tmp_path / "paper.md"
    p.write_text("Важный тезис (Смит, 2020, с. 18).", encoding="utf-8")
    before = p.read_bytes()
    report = audit_manuscript(p)
    assert p.read_bytes() == before
    assert all(set(x.verification.values()) == {"NOT_CHECKED"}
               for x in report.repair_cases)
    assert all(x.author_gate == "REQUIRED_IF_MEANING_CHANGES"
               for x in report.repair_cases)



def test_wish_preserves_requested_author_exactly(tmp_path):
    p = tmp_path / "wish.txt"
    p.write_text("а тут цитата Выготского", encoding="utf-8")
    audit = audit_manuscript(p)
    assert any(ci.original_fragment == "тут цитата Выготского"
               for ci in _origin(audit, "AUTHOR_DESIRED"))


def test_bibliography_scope_ends_at_next_heading(tmp_path):
    p = tmp_path / "appendix.md"
    p.write_text(
        "## References\n- Descartes (1641). Regulae.\n"
        "## Appendix\nЗдесь [citation needed] для новой мысли.",
        encoding="utf-8",
    )
    audit = audit_manuscript(p)
    assert any(ci.origin_type == "AUTHOR_DESIRED"
               for ci in audit.intakes)
    assert len([ci for ci in audit.intakes
                if ci.kind == "BIBLIOGRAPHY_ENTRY"]) == 1


def test_docx_heading_stops_bibliography_scope(tmp_path):
    body = (
        _p("References") + _p("Descartes (1641). Regulae.")
        + f'<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr>'
        + '<w:r><w:t>Appendix</w:t></w:r></w:p>'
        + _p("Как говорил Выготский, это нужно проверить.")
    )
    p = _docx(tmp_path / "appendix.docx", body)
    audit = audit_manuscript(p)
    assert any(ci.origin_type == "AUTHOR_DESIRED"
               for ci in audit.intakes)
    assert len([ci for ci in audit.intakes
                if ci.kind == "BIBLIOGRAPHY_ENTRY"]) == 1



def test_parenthetical_compound_cluster_preserves_all_sources(tmp_path):
    manuscript = tmp_path / "compound.md"
    manuscript.write_text(
        "This is a claim (Smith et al. 2021; Lee and Brown 2019; "
        "de Vries 2007).",
        encoding="utf-8",
    )
    audit = audit_manuscript(manuscript)
    clusters = [i for i in audit.intakes if i.kind == "AUTHOR_YEAR_CLUSTER"]
    members = [i for i in audit.intakes if i.kind == "AUTHOR_YEAR_MEMBER"]
    assert len(clusters) == 1
    assert len(members) == 3
    group = clusters[0]
    assert len(group.source_hints) == 3
    assert group.original_fragment == (
        "(Smith et al. 2021; Lee and Brown 2019; de Vries 2007)"
    )
    assert {i.group_index for i in members} == {0, 1, 2}
    for item in members:
        assert item.group_id == group.intake_id
        assert item.original_cluster == group.original_fragment
        assert (
            item.claim_context[
                item.anchor["start_codepoint"]:item.anchor["end_codepoint"]
            ] == item.original_fragment
        )
        assert item.verification_status == "NOT_CHECKED"
    cases = {c.intake_id: c for c in audit.repair_cases}
    assert "Z2_DECOMPOSE_CLAIM_TO_EACH_CITED_SOURCE" in (
        cases[group.intake_id].required_operations
    )


def test_mixed_cluster_member_retained_as_debt(tmp_path):
    p = tmp_path / "mixed.txt"
    p.write_text(
        "Some claim (Smith 2020; unpublished correspondence; Lee 2015).",
        encoding="utf-8",
    )
    report = audit_manuscript(p)
    assert sum(i.kind == "AUTHOR_YEAR_CLUSTER" for i in report.intakes) == 1
    assert sum(i.kind == "AUTHOR_YEAR_MEMBER_UNPARSED"
               for i in report.intakes) == 1
    assert any("SOURCE_CLUSTER_REQUIRES_MEMBER_RESOLUTION"
               in case.reason_codes for case in report.repair_cases)


def test_single_parenthetical_reference_retained(tmp_path):
    p = tmp_path / "single.txt"
    p.write_text("Claim (Выготский, 1978, с. 45).", encoding="utf-8")
    audit = audit_manuscript(p)
    singles = [i for i in audit.intakes if i.kind == "AUTHOR_YEAR"]
    assert len(singles) == 1
    assert singles[0].original_fragment == "(Выготский, 1978, с. 45)"
    assert singles[0].source_hints == ("Выготский, 1978, с. 45",)


def test_parenthesized_year_without_author_is_not_citation(tmp_path):
    p = tmp_path / "not_reference.txt"
    p.write_text(
        "Total (2021). Figure (Figure 2, 2020). (ISO 9001:2015).",
        encoding="utf-8",
    )
    audit = audit_manuscript(p)
    assert not any(i.kind.startswith("AUTHOR_YEAR") for i in audit.intakes)


def test_compound_quote_nearby_does_not_create_orphan(tmp_path):
    p = tmp_path / "cluster_quote.txt"
    p.write_text(
        "«Словосочетание с достаточно длинным содержанием для проверки» "
        "(Ivanov 2018; Petrov 2020).",
        encoding="utf-8",
    )
    audit = audit_manuscript(p)
    assert any(i.kind == "AUTHOR_YEAR_CLUSTER" for i in audit.intakes)
    assert not any(i.kind == "UNATTRIBUTED_QUOTE_CANDIDATE"
                   for i in audit.intakes)



def test_json_native_envelope_keeps_coverage_debt(tmp_path):
    p = tmp_path / "doc_sections.json"
    p.write_text(json.dumps({
        "format": "trm-cite-sections-v1",
        "revision_id": "r-17",
        "sections": [{
            "surface": "comment", "locator": "comment-1",
            "parent_anchor": "body-p-3", "text": "тут цитата Декарта",
        }],
        "coverage": {"body": "SCANNED", "comments": "SCANNED"},
    }, ensure_ascii=False), encoding="utf-8")
    a = audit_manuscript(p)
    assert a.coverage["status"] == "PARTIAL_WITH_COVERAGE_DEBT"
    assert any(x.surface == "comment" for x in a.intakes)
    assert any("footnotes" in x for x in a.coverage["debts"])


def test_bad_json_not_certified(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text('{"sections":[]}', encoding="utf-8")
    with pytest.raises(ValueError):
        audit_manuscript(p)


def test_cli_writes_original_receipt_and_unverified_work_orders(tmp_path, capsys):
    from kairoskopion.cli import main
    manuscript = tmp_path / "paper.md"
    manuscript.write_text("[нужна цитата] (Descartes 1641)", encoding="utf-8")
    output = tmp_path / "out"
    assert main(["cite-intake", "--manuscript", str(manuscript),
                 "--output-dir", str(output)]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["schema_version"] == VERSION
    assert data["original_snapshot_verified"] is True
    assert data["origins"]["AUTHOR_DESIRED"] >= 1
    assert data["origins"]["EXISTING"] >= 1
    report = json.loads(Path(data["report_file"]).read_text(encoding="utf-8"))
    assert report["coverage"]["manuscript_mutated"] is False
    assert report["source"]["original_snapshot_sha256_verified"] is True
    assert report["repair_cases"]
