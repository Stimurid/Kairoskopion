# Kairoskopion Alpha Demo

This directory contains sample files for running the Kairoskopion pipeline.

## Quick start

```bash
# Install (from project root)
pip install -e ".[dev]"

# Run the demo pipeline
kairoskopion run-local \
  --manuscript examples/sample_manuscript.md \
  --venue-guidelines examples/sample_venue_guidelines.md \
  --scenario examples/sample_scenario.json \
  --storage-root .kairoskopion_demo

# Generate vault indexes and manifest
kairoskopion vault-index --storage-root .kairoskopion_demo

# Export as portable bundle
kairoskopion export-bundle --storage-root .kairoskopion_demo --output kairoskopion_demo_bundle.zip

# Validate the bundle
kairoskopion validate-bundle --bundle kairoskopion_demo_bundle.zip

# Inspect stored results
kairoskopion inspect-storage --storage-root .kairoskopion_demo
```

## What happens

The pipeline reads the sample manuscript, venue guidelines, and submission
scenario, then produces:

1. **ArticleModel** — structured model of the paper (genre, discipline, method,
   claims, protected core, unknowns)
2. **VenueModel** — structured model of the journal (scope, requirements,
   publication regime)
3. **FitAssessment** — multi-axis comparison (topic, discipline, genre, method,
   citation ecology, language, compliance, publication regime)
4. **MismatchMap** — specific differences between article and venue
5. **RewritePlan** — actionable changes to improve fit
6. **RiskReport** — publication risks with severity
7. **ComplianceChecklist** — venue requirement compliance
8. **BibliographyProfile** — reference analysis
9. **CitationEcologyReport** — citation gaps and tasks

All results are persisted to JSONL registries and human-readable markdown vault
cards.

## Files

| File | Description |
|------|-------------|
| `sample_manuscript.md` | Philosophy of mind paper on artificial subjectivity |
| `sample_venue_guidelines.md` | Social Studies of Science (STS journal) guidelines |
| `sample_scenario.json` | Submission scenario: Q1 STS journal, medium rewrite depth |

## Expected output

See `EXPECTED_OUTPUT.md` for what the pipeline produces with these inputs.

## Clean up

```bash
rm -rf .kairoskopion_demo kairoskopion_demo_bundle.zip
```
