# Corpus Profiler

## Overview

Two-stage corpus analysis pipeline: **sampling** (build a representative corpus from article fixtures) → **analysis** (extract method, school, and citation patterns).

## Stage 1: Corpus Sampler

`sample_venue_corpus()` builds a `PublishedArticleCorpus` from provided article fixtures.

### Input
- `venue_model_id` — venue identifier
- `article_fixtures` — list of article dicts with fields: title, abstract, method, genre, language, year, word_count, reference_count, fulltext
- `config` — `CorpusSampleConfig` (target_sample_size, selection_strategy, require_fulltext, max_age_years)

### Output
`CorpusSampleResult` containing:
- `corpus` — `PublishedArticleCorpus` with distributions (genre, method, topic_clusters, language, word_count_range, reference_count_range)
- `representativeness_notes` — warnings about sample quality
- `bias_notes` — potential biases detected
- `missing_fulltext_notes` — articles lacking full text

### Selection strategies
- `recent_first` — newest articles first (default)
- `random` — random selection
- `cited_first` — highest-cited first

## Stage 2: Corpus Analyzer

`analyze_venue_corpus()` extracts patterns from article fixtures.

### Detected patterns
- **Methods**: qualitative, quantitative, mixed_methods, experimental, survey, ethnographic, case_study, meta_analysis, conceptual, empirical, computational, simulation
- **Schools**: phenomenology, grounded_theory, critical_theory, post_structuralism, pragmatism, systems_theory, actor_network_theory, feminist_theory, postcolonial, marxist, discourse_analysis, constructivism, interpretivism, positivism

### Output
`CorpusAnalysisResult` containing:
- `method_patterns` — detected methods with frequency and confidence
- `school_patterns` — detected schools/traditions
- `citation_stats` — mean/median/min/max reference counts
- `corpus_notes` — overall observations

## CLI usage

```bash
# Sample corpus from fixture file
python -c "from kairoskopion.cli import main; main(['sample-venue-corpus', '--fixture', 'tests/fixtures/venue_evidence/synthetic_corpus.json', '--venue-id', 'test_journal'])"

# Analyze corpus patterns
python -c "from kairoskopion.cli import main; main(['analyze-venue-corpus', '--fixture', 'tests/fixtures/venue_evidence/synthetic_corpus.json'])"
```

## Code locations

- `src/kairoskopion/services/corpus_sampler.py` — sampling service
- `src/kairoskopion/services/corpus_analyzer.py` — pattern analysis
- `src/kairoskopion/agents/venue/corpus_sampler_agent.py` — agent wrapper
- `tests/fixtures/venue_evidence/synthetic_corpus.json` — 6 synthetic articles
