# UC-1 Demo Pack v0

## Overview

The UC-1 Demo Pack is a fully reproducible offline demonstration of the Kairoskopion publication-positioning pipeline. It runs the complete UC-1 scenario — from a prototype scholarly article through venue discovery, fit assessment, mismatch mapping, and evidence-audited reporting — without requiring an LLM, network access, or any external API.

## What the demo demonstrates

The UC-1 pipeline path:

```
draft_article → ArticleModel → SemanticProfile → DisciplinaryPathways
  → VenueDiscovery → FitAssessment → MismatchMap → RewritePlan
  → CitationReport → RiskReport → ComplianceAudit → EvidenceAudit
  → UC1_DEMO_REPORT.md
```

All 12 steps complete successfully in deterministic mode.

## Demo content

The demo uses a synthetic scholarly article about AI-assisted publication positioning, drawing on Simondon's philosophy of individuation and STS frameworks. This topic is self-referential to Kairoskopion's own domain, making the demo both a functional test and a conceptual illustration.

### Venue pool (5 synthetic seeds)

| Venue | Expected fit |
|-------|-------------|
| Techné: Research in Philosophy and Technology | High (Simondon + phil. of tech.) |
| Philosophy & Technology | High (AI + philosophy + Simondon) |
| Social Studies of Science | Moderate (STS framing, but lacks empirical grounding) |
| AI & Society | Moderate (AI theme, but less philosophical depth expected) |
| Synthese — Technology & Information Section | Lower (broad scope, less specialized) |

## File structure

```
tests/fixtures/uc1_demo_pack/
├── draft_article.md          — ~1200-word synthetic article
├── scenario.json             — demo scenario metadata
├── venue_seeds.json          — 5 venue seed records
├── expected_demo_notes.md    — expected behavior documentation
├── venue_guidelines/
│   ├── techne_guidelines.md
│   ├── social_studies_of_science_guidelines.md
│   └── philosophy_and_technology_guidelines.md
└── corpus/
    ├── techne_corpus.json
    ├── social_studies_of_science_corpus.json
    └── philosophy_and_technology_corpus.json
```

## Code modules

| Module | Path | Role |
|--------|------|------|
| Demo loader | `src/kairoskopion/demo/uc1_demo_loader.py` | Load + validate demo pack from fixtures |
| Demo runner | `src/kairoskopion/demo/uc1_runner.py` | Run UC-1 workflow with loaded pack |
| Report generator | `src/kairoskopion/demo/uc1_report.py` | Generate UC1_DEMO_REPORT.md |

## CLI usage

```bash
# Run with console output only
python -c "from kairoskopion.cli import main; main(['run-uc1-demo'])"

# Run with artifact output
python -c "from kairoskopion.cli import main; main(['run-uc1-demo', '--output-dir', 'demo_output'])"

# Run with custom pack directory
python -c "from kairoskopion.cli import main; main(['run-uc1-demo', '--pack-dir', '/path/to/pack'])"
```

## Output artifacts (when --output-dir is set)

| File | Content |
|------|---------|
| `workflow_trace.json` | Full workflow execution trace |
| `article.json` | ArticleModel from draft parsing |
| `semantic_profile.json` | Article semantic profile |
| `pathways.json` | Disciplinary pathway mapping |
| `venue_pool.json` | Discovered venue candidates |
| `fit_assessment.json` | Fit assessment for primary venue |
| `mismatch_map.json` | Mismatch mapping |
| `rewrite_plan.json` | Rewrite plan for adaptation |
| `citation_report.json` | Citation ecology analysis |
| `risk_report.json` | Submission risk assessment |
| `compliance.json` | Compliance checklist |
| `submission_pack.json` | Submission pack with cover letter |
| `evidence_gate.json` | Evidence audit gate result |
| `venue.json` | Primary venue seed data |
| `scenario.json` | Demo scenario metadata |
| `UC1_DEMO_REPORT.md` | Human-readable demo report |

## Tests

35 tests in `tests/test_uc1_demo_pack.py`:

- **TestDemoPackDir** (6 tests) — fixture directory existence and completeness
- **TestDemoLoader** (12 tests) — loader validation, error handling, edge cases
- **TestDemoRunner** (10 tests) — workflow execution, 12/12 step completion, hardened agent entities, output writing
- **TestDemoReport** (4 tests) — report generation and content verification
- **TestCLIRunUC1Demo** (3 tests) — CLI command integration

## Constraints

- No LLM inference — all analysis is deterministic/heuristic
- No network access — all data from bundled fixtures
- No external databases — venue data is synthetic
- Evidence gaps (L5-L7) are explicitly reported, not fabricated
- All 12 UC-1 workflow steps complete successfully (agent attribute bugs fixed in this pass)
