# Source Adapters — Offline Fixtures

All fixtures are synthetic, invented API-like data. They do NOT represent real
journals or real API responses. They are designed to exercise adapter parsing
logic and authority enforcement without network calls.

## Fixture locations

Each adapter has its fixture data embedded as a module-level constant:

| Adapter | Fixture constant | File |
|---------|-----------------|------|
| OpenAlex | `OPENALEX_FIXTURE` | `adapters/venue/openalex.py` |
| Crossref | `CROSSREF_FIXTURE` | `adapters/venue/crossref.py` |
| DOAJ | `DOAJ_FIXTURE` | `adapters/venue/doaj.py` |
| Unpaywall | `UNPAYWALL_FIXTURE` | `adapters/venue/unpaywall.py` |
| OpenCitations | `OPENCITATIONS_FIXTURE` | `adapters/venue/opencitations.py` |
| Snapshot | Inline HTML string | `adapters/venue/snapshot_crawler.py` |

## Fixture design rules

1. **Synthetic only.** All journal names, ISSNs, DOIs, and publishers are invented.
2. **API-structure-faithful.** Fixture JSON mimics the real API response structure
   so parsing logic is exercised realistically.
3. **Marked as synthetic.** Fixture venue name is "Synthetic Philosophy of Technology
   Journal" or similar obviously synthetic names.
4. **Cross-adapter conflict.** OpenAlex fixture says publisher is "Springer Nature";
   Crossref fixture says "Springer Science and Business Media LLC". This intentional
   mismatch exercises cross-adapter conflict detection.
5. **No copyrighted content.** Fixtures contain no text from real journals, papers,
   or API responses.

## How fixtures are used

- **OFFLINE_STUB mode** (default): adapter returns its built-in fixture
- **FIXTURE mode**: adapter parses caller-provided fixture dict via `parse_response()`
- **Test suite**: all 67 adapter tests run against fixtures, no network
- **CLI**: `acquire-venue-sources` runs fixtures by default (no `--live` flag)

## Injecting custom fixtures

```python
from kairoskopion.services.real_source_acquisition import acquire_venue_sources

result = acquire_venue_sources(
    venue_name="My Test Journal",
    adapter_fixtures={
        "openalex_venue": {"display_name": "Custom", "issn_l": "0000-0001"},
    },
    enabled_adapters=["openalex_venue"],
)
```

The `adapter_fixtures` dict maps adapter_id → fixture data dict. When provided,
the adapter uses FIXTURE mode and parses the given data instead of its built-in
fixture or a live API call.
