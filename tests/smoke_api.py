"""API smoke test — run against local dev server on port 8000."""
import requests
import sys

BASE = "http://localhost:8000"
results = []


def test(name, method, path, body=None, expect_status=200):
    try:
        url = f"{BASE}{path}"
        if method == "GET":
            r = requests.get(url, timeout=10)
        else:
            r = requests.post(url, json=body or {}, timeout=10)
        ct = r.headers.get("content-type", "")
        ok = r.status_code == expect_status
        data = r.json() if "json" in ct else {}
        results.append((name, "PASS" if ok else "FAIL", r.status_code, str(data)[:120]))
    except Exception as e:
        results.append((name, "FAIL", 0, str(e)[:120]))


# 1. Health
test("health", "GET", "/health")

# 2. Create case
test("create_case", "POST", "/cases", {"title": "Smoke Test Case"})

# Get case ID
r = requests.get(f"{BASE}/cases", timeout=10)
cases = r.json()
case_id = cases[0]["case_id"] if cases else None

if not case_id:
    print("FAIL: no case created")
    sys.exit(1)

# 3. List cases
test("list_cases", "GET", "/cases")

# 4. Get case
test("get_case", "GET", f"/cases/{case_id}")

# 5. Intake article text
abstract = (
    "This paper examines the philosophical implications of artificial intelligence "
    "for human subjectivity and agency. Drawing on phenomenological traditions and "
    "Science and Technology Studies (STS), we argue that AI systems restructure the "
    "conditions of human self-understanding. We analyze three domains: epistemic agency, "
    "moral reasoning, and creative expression. Our analysis reveals that AI does not "
    "simply augment or replace human capacities but transforms the very categories "
    "through which we understand them."
)
test("intake_text", "POST", f"/cases/{case_id}/intake/text", {
    "text": abstract, "input_type": "abstract",
})

# 6. Get article model
test("get_article_model", "GET", f"/cases/{case_id}/article-model")

# 7. Confirm article model
test("confirm_article", "POST", f"/cases/{case_id}/article-model/confirm", {
    "protected_core": ["epistemic agency", "phenomenological framework"],
    "corrections": {},
})

# 8. Set scenario
test("set_scenario", "POST", f"/cases/{case_id}/scenario", {
    "goal": "first_publication",
    "rewrite_depth_allowed": "moderate",
    "language": "English",
    "risk_tolerance": "moderate",
})

# 9. Map pathways
test("get_pathways", "GET", f"/cases/{case_id}/pathways")

# 10. Discover venue pool
test("discover_venues", "POST", f"/cases/{case_id}/discover-venues")

# 11. Get venue pool
test("get_venue_pool", "GET", f"/cases/{case_id}/venue-pool")

# Get first candidate ID
r2 = requests.get(f"{BASE}/cases/{case_id}/venue-pool", timeout=10)
pool = r2.json()
candidates = pool.get("candidates", [])
cand_id = candidates[0]["venue_candidate_id"] if candidates else "none"

# 12. Select venue (triggers fit chain)
if candidates:
    test("select_venue", "POST", f"/cases/{case_id}/select-venue/{cand_id}")
else:
    results.append(("select_venue", "SKIP", 0, "No candidates in pool"))

# 13. Mismatch map
test("get_mismatch_map", "GET", f"/cases/{case_id}/mismatch-map")

# 14. Quality gates
test("get_quality_gates", "GET", f"/cases/{case_id}/quality-gates")

# 15. Adaptation plan
test("get_adaptation_plan", "GET", f"/cases/{case_id}/adaptation-plan")

# 16. Decision log
test("get_decision_log", "GET", f"/cases/{case_id}/decision-log")

# 17. Dossier
test("get_dossier", "GET", f"/cases/{case_id}/dossier")

# 18. Evidence
test("get_evidence", "GET",
     f"/cases/{case_id}/evidence/article/title")

# 19. Fit (unused endpoint but exists)
test("get_fit", "GET", f"/cases/{case_id}/fit")

print(f"\n{'=' * 70}")
print(f"API SMOKE TEST RESULTS ({len(results)} endpoints)")
print(f"{'=' * 70}")
for name, status, code, detail in results:
    print(f"  {status:5s}  {code:3d}  {name:25s}  {detail[:80]}")
passed = sum(1 for _, s, _, _ in results if s == "PASS")
failed = sum(1 for _, s, _, _ in results if s == "FAIL")
skipped = sum(1 for _, s, _, _ in results if s == "SKIP")
print(f"\n  TOTAL: {passed} pass, {failed} fail, {skipped} skip")
