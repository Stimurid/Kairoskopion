"""Fail-closed D24/D25 bibliography resolver over existing Kairoskopion adapters."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any
from ..adapters.crossref import lookup_doi_auto, search_works_auto
from ..services.bibliography_parsing import build_bibliography_profile, extract_references_section
from .bibliography_ledger import BibliographyEvidenceEntry, BibliographyLedger, verify_bibliography_ledger

@dataclass
class BibliographyResolutionResult:
    ledger: BibliographyLedger
    report: Any
    network_queries: int = 0
    ambiguous_matches: int = 0
    unresolved_entries: int = 0
    def to_dict(self):
        return {"ledger":asdict(self.ledger),"report":self.report.to_dict(),
                "network_queries":self.network_queries,"ambiguous_matches":self.ambiguous_matches,
                "unresolved_entries":self.unresolved_entries}

def _norm(s:str|None)->str:
    return " ".join((s or "").lower().replace("—"," ").replace("–"," ").split())

def _score(ref:dict[str,Any], rec:dict[str,Any])->float:
    title=SequenceMatcher(None,_norm(ref.get("title_fragment")),_norm(rec.get("title"))).ratio()
    year=1.0 if ref.get("year") and rec.get("year")==ref.get("year") else (0.5 if not ref.get("year") else 0.0)
    author=_norm(ref.get("author_fragment"))
    authors=_norm(" ".join(rec.get("authors") or []))
    auth=SequenceMatcher(None,author,authors).ratio() if author else 0.5
    return round(.7*title+.15*year+.15*auth,4)

def resolve_manuscript_bibliography(*, article_id:str, manuscript_revision:str,
    manuscript_text:str, mode:str="mock", cache_dir:str|None=None,
    min_match_score:float=.86, min_margin:float=.08)->BibliographyResolutionResult:
    section=extract_references_section(manuscript_text)
    profile=build_bibliography_profile(manuscript_text,manuscript_id=manuscript_revision)
    entries=[]; queries=ambiguous=unresolved=0
    for i,ref in enumerate(profile.references or [],1):
        doi=ref.get("doi"); resolved=None; caveats=[]; status="UNRESOLVED"
        if doi:
            out=lookup_doi_auto(doi,mode=mode,cache_dir=Path(cache_dir) if cache_dir else None); queries+=1
            if out.records:
                resolved=out.records[0]; status="VERIFIED"
            else: caveats.append("DOI did not resolve")
        elif ref.get("title_fragment"):
            q=" ".join(x for x in [ref.get("title_fragment"),ref.get("author_fragment"),str(ref.get("year") or "")] if x)
            out=search_works_auto(q,mode=mode,max_results=5,cache_dir=Path(cache_dir) if cache_dir else None); queries+=1
            ranked=sorted(((_score(ref,x),x) for x in out.records),key=lambda x:x[0],reverse=True)
            if ranked and ranked[0][0]>=min_match_score and (len(ranked)==1 or ranked[0][0]-ranked[1][0]>=min_margin):
                resolved=ranked[0][1]; status="VERIFIED"
            else:
                ambiguous+=1; caveats.append("no unique high-confidence metadata match")
        else: caveats.append("insufficient structured reference fields for resolver")
        if status!="VERIFIED": unresolved+=1
        source_id=None
        if resolved:
            source_id=f"doi:{resolved.get('doi')}" if resolved.get("doi") else f"crossref:{resolved.get('record_id')}"
        entries.append(BibliographyEvidenceEntry(
            entry_id=f"{article_id}:ref:{i}",carrier_ref=f"manuscript:{manuscript_revision}",
            carrier_kind="MANUSCRIPT_BIBLIOGRAPHY",raw_ref=ref.get("raw_text") or "",
            source_ref_id=source_id,locator_status="EXACT" if doi else "PARTIAL",
            verification_status=status,bound_manuscript_revision=manuscript_revision,
            provenance=[f"bibliography_profile:{profile.bibliography_profile_id}"] + ([f"crossref:{source_id}"] if source_id else []),
            caveats=caveats))
    complete_claim="VERIFIED_COMPLETE" if section is not None and entries else "UNKNOWN"
    source_needs=[] if entries and unresolved==0 else (["resolve all manuscript bibliography entries"] if entries else ["current manuscript has no parseable bibliography"])
    ledger=BibliographyLedger(ledger_id=f"bib:{article_id}:{manuscript_revision}",article_id=article_id,
        manuscript_revision=manuscript_revision,entries=entries,completeness_claim=complete_claim,
        completeness_basis=["explicit references section parsed from current manuscript"] if section is not None else [],
        source_needs=source_needs,provenance=[f"manuscript:{manuscript_revision}"])
    report=verify_bibliography_ledger(ledger)
    return BibliographyResolutionResult(ledger,report,queries,ambiguous,unresolved)