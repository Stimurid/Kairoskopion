from kairoskopion.kairon_provider.bibliography_ledger import BibliographyEvidenceEntry,BibliographyLedger,verify_bibliography_ledger

def e(i,kind="MANUSCRIPT_BIBLIOGRAPHY",rev="m1",status="VERIFIED",src=None):
    return BibliographyEvidenceEntry(entry_id=str(i),carrier_ref="doc:1",carrier_kind=kind,raw_ref=f"raw {i}",source_ref_id=src or f"source:{i}",verification_status=status,bound_manuscript_revision=rev)

def test_complete_current_verified_ledger_projects_count():
    l=BibliographyLedger("L1","A","m1",[e(1),e(2)],"VERIFIED_COMPLETE",["explicit complete reference-list scope"])
    r=verify_bibliography_ledger(l)
    assert (r.bibliography_status,r.reference_count_status,r.reference_count,r.decision)==("VERIFIED_COMPLETE","VERIFIED",2,"PROJECT_REFERENCE_COUNT")

def test_source_map_never_becomes_complete_without_complete_scope():
    l=BibliographyLedger("L2","F02","v0.3-working",[e(1,"SOURCE_MAP")],"UNKNOWN",source_needs=["complete bibliography"])
    r=verify_bibliography_ledger(l)
    assert r.bibliography_status=="SOURCE_MAP_ONLY" and r.reference_count is None

def test_donor_traces_remain_unknown_count():
    l=BibliographyLedger("L3","F09","working-copy",[e(1,"DONOR")],"UNKNOWN",source_needs=["source verification"])
    r=verify_bibliography_ledger(l)
    assert r.bibliography_status=="SOURCE_TRACES_ONLY" and r.reference_count is None

def test_stale_entry_blocks_projection():
    l=BibliographyLedger("L4","A","m2",[e(1,rev="m1")],"VERIFIED_COMPLETE")
    r=verify_bibliography_ledger(l)
    assert r.reference_count is None and r.bibliography_status=="PRESENT_UNVERIFIED"

def test_unresolved_entry_blocks_projection():
    l=BibliographyLedger("L5","A","m1",[e(1,status="UNRESOLVED",src=None)],"VERIFIED_COMPLETE")
    r=verify_bibliography_ledger(l)
    assert r.reference_count is None

def test_open_locator_need_blocks_complete_projection():
    l=BibliographyLedger("L6","A","m1",[e(1)],"VERIFIED_COMPLETE",locator_needs=["page locator"])
    assert verify_bibliography_ledger(l).reference_count is None