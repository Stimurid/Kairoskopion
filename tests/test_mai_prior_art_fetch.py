"""Regression tests for real Crossref/OpenAlex source capture and replay."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import fetch_mai_prior_art as mod
from tests.test_mai_w12_indago_bind import prepare
from scripts.build_mai_w12_science_index import build

class APIResponse:
    status=200
    def __init__(self,value):
        self.value=json.dumps(value,ensure_ascii=False).encode("utf-8")
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def read(self,n):return self.value[:n]

def make_world(tmp_path:Path):
    source,head,donors=prepare(tmp_path)
    science=tmp_path/"science"
    build(source,head,donors,science)
    return source,science

def test_publication_abstract_source_identity_and_cold_replay(tmp_path,monkeypatch):
    src,sci=make_world(tmp_path)
    calls=[]
    def fake(url,timeout=18):
        u=url.full_url
        calls.append(u)
        assert "api." in u and ("crossref.org/" in u or "openalex.org/" in u)
        d="10.1007/paper-a" if "/paper-a" in u else "10.1007/test"
        if "crossref.org" in u:
            return APIResponse({"message":{
                "DOI":d,"title":["Policy, action, evidence"],
                "publisher":"Test Press","container-title":["Test Journal"],
                "abstract":"<jats:p>Published abstract with a criterion <i>and</i> a counterclaim.</jats:p>",
                "URL":"https://example.test","published":{"date-parts":[[2026,9,1]]}}})
        return APIResponse({
            "doi":"https://doi.org/"+d,"title":"Policy action and evidence",
            "abstract_inverted_index":{"Evidence":[0],"and":[1],"counterclaim":[2]},
            "primary_location":{"landing_page_url":"https://example.test","source":{"display_name":"Test Journal"}},
        })
    monkeypatch.setattr(mod,"urlopen",fake)
    r1=mod.execute(src,sci,tmp_path/"out",limit=1)
    assert r1["route_count"]==1
    assert r1["unique_requested_doi"]==2
    assert r1["cache_hits"]==0
    assert r1["provider_queries"]==4
    assert r1["non_success_provider_responses"]==0
    snap=(tmp_path/"out"/"routes"/"MAI-W12-001.json").read_bytes()
    assert mod.effective_abstract([])["read_depth"]=="NOT_FOUND_OR_UNVERIFIED"
    saved=json.loads(snap)
    assert saved["published_work_count"]==2
    assert saved["database_abstract_count"]==2
    assert all(z["abstract"]["read_depth"]=="DATABASE_ABSTRACT" for z in saved["published_works"])
    assert all(z["abstract"]["doi_identity_match"] for z in saved["published_works"])
    assert all(not z["abstract"].get("source_is_primary_publisher_fulltext",False) for z in saved["published_works"])
    assert saved["science_gate"]=="HOLD"
    assert saved["independent_scholarly_claim_adjudications"]==0
    assert saved["external_send_count"]==0
    r2=mod.execute(src,sci,tmp_path/"out",limit=1)
    assert r2["cache_hits"]==4
    assert len(calls)==4
    assert (tmp_path/"out"/"routes"/"MAI-W12-001.json").read_bytes()==snap


def test_forged_publisher_doi_cannot_be_accepted(tmp_path,monkeypatch):
    src,sci=make_world(tmp_path)
    def fake(url,timeout=18):
        if "crossref" in url.full_url:
            return APIResponse({"message":{"DOI":"10.9999/forged","title":["fake"],"abstract":"<p>Fake prose</p>"}})
        return APIResponse({"doi":"https://doi.org/10.9999/forged","title":"fake"})
    monkeypatch.setattr(mod,"urlopen",fake)
    result=mod.execute(src,sci,tmp_path/"out",limit=1)
    assert result["non_success_provider_responses"]==0
    assert result["abstracts_retrieved_route_bindings"]==0
    j=json.loads((tmp_path/"out"/"routes"/"MAI-W12-001.json").read_text(encoding="utf-8"))
    assert j["operation_status"]=="SOURCE_READS_NOT_AVAILABLE"
    assert all(x["abstract"]["read_depth"]=="NOT_FOUND_OR_UNVERIFIED" for x in j["published_works"])


def test_raw_api_response_digest_is_verified_on_replay(tmp_path,monkeypatch):
    src,sci=make_world(tmp_path)
    def fake(url,timeout=18):
        d="10.1007/paper-a" if "paper-a" in url.full_url else "10.1007/test"
        if "crossref" in url.full_url:
            return APIResponse({"message":{"DOI":d,"title":["T"],"abstract":"<p>Result</p>"}})
        return APIResponse({"doi":"https://doi.org/"+d,"title":"T"})
    monkeypatch.setattr(mod,"urlopen",fake)
    mod.execute(src,sci,tmp_path/"out",limit=1)
    h=hashlib.sha256("10.1007/paper-a".encode()).hexdigest()[:20]
    blob=tmp_path/"out"/"published_work_cache"/h/"crossref.response.json"
    blob.write_bytes(b"INVALID TAMPER")
    with pytest.raises(RuntimeError,match="raw bytes drift"):
        mod.execute(src,sci,tmp_path/"out",limit=1)


@pytest.mark.parametrize("bad",[
    "not-a-doi","https://evil.test/doi/10.1007/x","10.1007/id with spaces",
])
def test_bad_doi_rejected(bad):
    with pytest.raises(ValueError,match="invalid DOI"):
        mod.normalize_doi(bad)
