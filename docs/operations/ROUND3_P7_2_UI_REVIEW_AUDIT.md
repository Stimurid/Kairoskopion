# Round III — P7.2 UI Registry Review Panel Audit

**Date:** 2026-06-27
**Commit:** `e2a82c1`

## Files Changed

| file | change | lines |
| ---- | ------ | ----: |
| `ui/src/api/client.ts` | Added `RegistryRecord` interface + 7 API methods | +26 |
| `ui/src/components/RegistryReviewPanel.tsx` | New component (243 lines) | +243 |
| `ui/src/styles/cockpit.css` | Registry panel CSS (dark theme) | +179 |
| `ui/src/components/CaseWorkspace.tsx` | Import + mount `<RegistryReviewPanel />` | +2 |

## Verification Checklist

| criterion | status | evidence |
| --------- | ------ | -------- |
| API methods added correctly | PASS | 7 methods: `listRegistryTypes`, `listRegistryRecords`, `getRegistryRecord`, `acceptRegistryRecord`, `rejectRegistryRecord`, `getReviewQueue`, `listOpenTasks` |
| RegistryReviewPanel compiles | PASS | `npx tsc --noEmit` — clean |
| Panel mounted in intended location | PASS | `CaseWorkspace.tsx` imports and renders `<RegistryReviewPanel />` in dossier view |
| Review queue endpoint path matches backend | PASS | Client calls `/registry/review-queue`; backend `registry_router.py:133` defines `@router.get("/review-queue")` |
| Accept/reject calls hit correct API | PASS | Client: `PUT /registry/{type}/{id}/accept` and `/reject`; backend router has matching routes |
| Loading state handled | PASS | `registry-loading` div shown during fetch |
| Error state handled | PASS | `registry-error` div shows error message on catch |
| Empty state handled | PASS | Queue: "Нет записей, ожидающих рецензии"; Browse: "Нет записей" / "Выберите тип записи" |
| Auth/session bypass | N/A | Registry API routes are not behind Bearer auth (by design — registry is infrastructure, not case data) |
| TypeScript typecheck | PASS | `npx tsc --noEmit` — zero errors |
| Vite build | PASS | `npx vite build` — `dist/` produced, 358 KB JS bundle |

## Endpoint Mapping

| UI action | API call | Backend handler |
| --------- | -------- | --------------- |
| Load types | `GET /registry/types` | `registry_router.py` |
| Load records | `GET /registry/{type}/records` | `registry_router.py` |
| Load queue | `GET /registry/review-queue` | `registry_router.py:133` |
| Accept record | `PUT /registry/{type}/{id}/accept` | `registry_router.py` |
| Reject record | `PUT /registry/{type}/{id}/reject` | `registry_router.py` |

## Component Architecture

- Two tabs: **Queue** (provisional/unknown records with accept/reject buttons) and **Browse** (type selector + search)
- Expandable record cards with JSON detail view
- `StatusBadge` component with canonical/provisional/rejected/unknown styles
- `recordLabel()` and `recordId()` helpers for polymorphic record display
- Dark theme CSS following project design system

## UI Limitations

- No pagination (queue limited to 200, browse to 100)
- No bulk accept/reject
- No confirmation dialog before accept/reject
- No undo for accept/reject actions
- Record detail is raw JSON, not formatted fields

## P6 Deferred UI Review Surface

This panel satisfies the P6 deferred requirement for a curator/operator UI to review provisional registry records. The review queue surfaces provisional and unknown-status records for human triage.

## Verdict: ACCEPT

TypeScript clean, Vite build clean, endpoints match backend, all UI states handled. Limitations are known and acceptable for operator staging preview.
