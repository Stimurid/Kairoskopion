# Venue Seed Corpus

Synthetic seed corpus for the Kairoskopion venue registry.

## Purpose

This corpus provides example venue data for testing the venue registry import
and evidence pack build pipeline. All data is **synthetic** — no real scraped
pages, no copyrighted content, no private source notes.

## Files

| File | Format | Description |
|------|--------|-------------|
| `venues.jsonl` | JSONL | VenueRecord entries (one per line) |
| `sources.jsonl` | JSONL | VenueSource entries (one per line) |
| `claims.jsonl` | JSONL | VenueClaim entries (one per line) |

## Venues included

1. **Philosophy & Social Theory Review** (`vrec_synth_philo`) — English-language philosophy/social-theory journal with full evidence.
2. **Voprosy Gumanitarnykh Nauk** (`vrec_synth_russian`) — Russian-only humanities journal.
3. **Journal of Organizational Behavior Research** (`vrec_synth_empirical`) — Empirical social-science journal accepting only empirical work.
4. **Emerging Perspectives Quarterly** (`vrec_synth_incomplete`) — Venue with mostly unknown fields (minimal evidence).
5. **IEEE Transactions on Formal Methods** (`vrec_synth_formal`) — Formal-heavy technical venue with strict formatting rules.

## Evidence status distribution

Each venue has claims with mixed evidence statuses:
- `official_fact` — from synthetic official venue pages
- `external_claim` — from synthetic third-party sources
- `inference` — derived from indirect signals
- `unknown` — no evidence available
- `conflicting` — multiple sources disagree (venue 5)
- `stale` — past freshness window (venue 4)

## Usage

```bash
kairoskopion import-venue-seed --corpus examples/venue_seed_corpus --storage-root .kairoskopion_test
kairoskopion build-venue-evidence-pack --venue-id vrec_synth_philo --storage-root .kairoskopion_test --output venue_pack.md
```
