from kairoskopion.kairon_provider.bibliography_resolver import resolve_manuscript_bibliography

def test_no_bibliography_fails_closed():
 r=resolve_manuscript_bibliography(article_id="A",manuscript_revision="m1",manuscript_text="# Text\nNo refs.")
 assert r.report.reference_count is None and r.report.bibliography_status=="ABSENT"

def test_mock_doi_complete_projects_verified_count():
 text="# References\n\n- Nagel, Thomas. (1974). What Is It Like to Be a Bat? doi:10.2307/2183914"
 r=resolve_manuscript_bibliography(article_id="A",manuscript_revision="m1",manuscript_text=text)
 assert r.report.reference_count==1 and r.report.bibliography_status=="VERIFIED_COMPLETE"
 assert r.ledger.entries[0].source_ref_id=="doi:10.2307/2183914"

def test_unresolvable_doi_keeps_count_unknown():
 text="# References\n\n- Nobody. (2020). Missing. doi:10.9999/does-not-exist"
 r=resolve_manuscript_bibliography(article_id="A",manuscript_revision="m1",manuscript_text=text)
 assert r.report.reference_count is None and r.unresolved_entries==1

def test_title_search_requires_unique_high_confidence_match():
 text="# References\n\n- Chalmers, David. (1995). Facing Up to the Problem of Consciousness."
 r=resolve_manuscript_bibliography(article_id="A",manuscript_revision="m1",manuscript_text=text,min_match_score=.7)
 assert r.report.reference_count==1