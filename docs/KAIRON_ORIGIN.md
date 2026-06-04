# Kairoskopion — Origin and Naming

## Name

**Kairoskopion** (Καιροσκόπιον) — "instrument for observing the right moment."

From Greek *kairos* (καιρός, the opportune moment) + *-skopion* (-σκόπιον,
instrument for seeing/observing).  The name reflects the system's purpose:
making the publication situation of a text *visible* and *timely* — not just
answering "where to submit?" but showing when, how, and whether a text is ready
for a specific publication container.

## Previous names

- **Journal-Yuga** — working name during specification phase (Waves 1–7).
  "Yuga" referenced the Sanskrit concept of a cosmic age/era, reflecting the
  system's role in understanding the *publication epoch* of a text.
- **Venue-Fit Engine** — technical subtitle used in the spec.

## Position in the ecosystem

Kairoskopion is a **bounded context** inside the Litops–WhiteCrow ecosystem:

- **Litops** — source/provenance/corpus layer.  Kairoskopion inherits evidence
  discipline: every claim must trace to a registered source.
- **WhiteCrow** — field/manuscript formation layer.  Kairoskopion inherits
  protected-core logic: it must not silently destroy the semantic nucleus of a
  text during adaptation.
- **Kairoskopion** — publication-positioning layer.  Its own domain: article
  models, venue models, fit assessments, mismatch maps, adaptation plans,
  citation ecology, compliance, submission packs, review-loop memory.

Kairoskopion is **sidecar-first, standalone-capable**: the core domain works
from CLI, API, Telegram intake and web UI without depending on a specific
frontend.

## Design principles

1. Evidence-first: no claim without a traceable source or explicit `UNKNOWN`.
2. Multi-dimensional fit, never a single black-box score.
3. Protected core preservation: adaptation must not silently flatten the text.
4. Separate knowledge statuses: fact, vendor claim, corpus observation,
   inference, tacit signal, user note, prior outcome, unknown, inaccessible,
   stale, conflicting.
5. Human-in-the-loop: the system proposes, the author decides.
