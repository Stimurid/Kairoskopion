# P10 Operational Harvest — Preflight

**Date:** 2026-06-27
**Branch:** `feature/p10-ru-education-ai-operational-harvest`
**Base:** main at `b6c4d61`

## Pre-flight checks

| check | result |
|-------|--------|
| Branch created from main | Yes (`b6c4d61`) |
| pytest | 3014 passed, 0 failed |
| typecheck (`tsc --noEmit`) | clean |
| build (`vite build`) | clean |
| Working tree | clean (no staged/modified tracked) |
| Untracked | seed outputs + old docs — not staged |

## Constraints

- No paid LLM / No paid API / No 302.ai
- No prod deploy
- No force push
- No merge without explicit owner authorization
- No fabricated facts / No model-memory facts
- Every factual output: source-packet-backed, adapter-confirmed, local-evidence-backed, or provisional/acquisition_needed/blocked
- Do not auto-promote records to accepted
- `data/input/private/` and `data/private_work/` gitignored, never committed

## Scope

First operational harvest for RU education/AI venue universe using existing P7.3/P7.4/P8/P9 system.
NOT new architecture. Uses: SourceAuthorityRegistry, ExternalSourceAdapter registry, SourceAcquisitionLoop, VerificationGate, ReviewPacketExporter, CLI, SeedRegistryWorkflow.
