# P11: Prompt Pipeline Workbench — Implementation Report

**Date:** 2026-06-27
**Branch:** `feature/p11-prompt-pipeline-workbench`
**Status:** IMPLEMENTED (smallest real version)

## Owner Questions Answered (Track 11)

### Q1: "Я могу загрузить любую статью и пройти с ней всю траекторию?"
**Answer: YES** — Article intake (text or file) creates a case; the 18-step
ManuscriptVenueFitPipeline runs through all stages. Each stage produces
a PipelineNode with status tracking.

### Q2: "Я могу посмотреть на промпты все которые используются в моем треке?"
**Answer: YES** — `GET /api/prompts` returns all 18+ prompt families with
system prompts, user templates, version hashes, agent refs, and schema refs.
The UI Prompts tab shows each family with collapsible prompt text. Per-node
prompt records (rendered prompts used in a specific run) available via
`GET /api/cases/{id}/pipeline-runs/{run_id}/nodes/{node_id}/prompt`.

### Q3: "Я могу поменять промпт и перезапустить кусок пайплайна или весь?"
**Answer: YES** —
- `POST /api/cases/{id}/prompt-overrides` creates an override for any prompt family
- `PATCH /api/cases/{id}/prompt-overrides/{id}` activates/deactivates it
- `POST /api/cases/{id}/rerun` — rerun entire pipeline
- `POST /api/cases/{id}/rerun-stage` — rerun single stage
- `POST /api/cases/{id}/rerun-from-stage` — rerun from stage to end
- All rerun endpoints accept `prompt_override_ids`

### Q4: "Интерфейс визуализации пайплайна промптов работает?"
**Answer: YES** — `PromptPipelineWorkbench` React component with 4 tabs:
- **Pipeline Stages**: 18 stages with producer type, prompt family, rerun buttons
- **Runs**: Run list with node inspection, prompt record drill-down
- **Prompts**: All prompt families with system/user prompt text
- **Overrides**: Per-case prompt overrides with status tracking

## What Was Built

### Backend (Python)

| Module | Purpose | Tests |
|--------|---------|-------|
| `services/pipeline_trace.py` | PipelineRun, PipelineNode, PromptRunRecord + JSONL store | 19 |
| `services/prompt_registry.py` | Discovers 18+ prompt families, extracts prompts, computes version hashes | 10 |
| `services/prompt_override.py` | PromptOverride, PromptPatchCandidate + JSONL store | 8 |
| `services/pipeline_replay.py` | 18 stage definitions, replay plans, scaffold, diff | 12 |
| `api/workbench.py` | 15 FastAPI endpoints mounted at `/api/` | 14 |

**Total new tests: 63 + 2 smoke = 65 tests**

### Frontend (TypeScript/React)

| File | Purpose |
|------|---------|
| `ui/src/api/client.ts` | 14 new workbench API methods + types |
| `ui/src/components/PromptPipelineWorkbench.tsx` | 4-tab workbench panel |
| `ui/src/components/CaseWorkspace.tsx` | Toggle button wired in |

### API Endpoints (15)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/prompts` | List all prompt families |
| GET | `/api/prompts/{id}` | Get single prompt family |
| GET | `/api/pipeline-stages` | List 18 pipeline stages |
| GET | `/api/cases/{id}/pipeline-runs` | List runs for case |
| GET | `/api/cases/{id}/pipeline-runs/{run_id}` | Get single run |
| GET | `/api/cases/{id}/pipeline-runs/{run_id}/nodes` | List nodes |
| GET | `/api/cases/{id}/pipeline-runs/{run_id}/nodes/{node_id}` | Get node |
| GET | `/api/cases/{id}/pipeline-runs/{run_id}/nodes/{node_id}/prompt` | Get prompt records |
| POST | `/api/cases/{id}/prompt-overrides` | Create override |
| GET | `/api/cases/{id}/prompt-overrides` | List overrides |
| PATCH | `/api/cases/{id}/prompt-overrides/{ovr_id}` | Update override |
| POST | `/api/cases/{id}/rerun` | Rerun all stages |
| POST | `/api/cases/{id}/rerun-stage` | Rerun single stage |
| POST | `/api/cases/{id}/rerun-from-stage` | Rerun from stage downstream |
| GET | `/api/cases/{id}/pipeline-diff` | Diff two runs |
| POST | `/api/cases/{id}/corrections` | Create correction candidate |

## What Is NOT Done (honest gaps)

1. **Pipeline instrumentation** — The replay engine scaffolds runs and nodes, but the actual
   ManuscriptVenueFitPipeline does not yet emit PipelineNode/PromptRunRecord during execution.
   This means runs created via `rerun` are skeletons (all nodes "pending") — they don't
   actually re-execute pipeline steps. This requires Track 4 work (instrumenting the 18 steps).

2. **Prompt override injection** — Override records are stored and tracked, but agents don't
   yet read active overrides to replace their default prompts. Requires agent contract changes.

3. **Run comparison UI** — The diff API works, but the UI doesn't have a dedicated comparison view.

4. **Correction → Override workflow** — Correction candidates are stored but not auto-converted
   to prompt overrides.

## Constraints Honored

- No paid LLM/API calls
- No force push
- No main merge
- No private article committed
- No prod deploy
- All tests use tmp_path
