# Access and Transport Policy

**Canonical version.** This document is the single source of truth for
transport selection, SSH handling, and deployment blocking semantics.

---

## SSH policy

SSH, SCP and SFTP are not the primary, required, or preferred transport
in this environment.

Defaults:

```
SSH_POLICY=DISABLED_BY_DEFAULT
SSH_AUTOMATIC_RETRY_LIMIT=0
```

The agent MUST NOT:

- begin a task with SSH;
- probe SSH "just in case";
- increase timeout on an SSH connection;
- retry SSH after a failure;
- treat SSH as the only way to obtain evidence;
- use SSH unavailability as grounds to stop development;
- mark an entire program task `BLOCKED` when only production deploy is
  unavailable.

SSH is permitted only when **one** of these conditions holds:

1. The owner explicitly wrote "use SSH" in the **current** session.
2. A versioned runbook contains a proven (post-policy) working SSH
   contour AND the owner explicitly authorized its use.

In all other cases SSH is not invoked at all.

## Non-blocking rule

SSH unavailability never blocks:

- reading and modifying code;
- testing (unit, integration, E2E);
- local runtime;
- browser E2E;
- fake-provider E2E;
- live-provider tests via an available HTTP contour;
- commit;
- merge;
- push;
- migrations;
- creating a release artifact;
- preparing deployment automation;
- documentation and handoff.

It may block exactly one thing:

**`PRODUCTION_DEPLOYMENT_EXECUTION`**

The correct status is then:

```
RELEASE_READY_AWAITING_NON_SSH_DEPLOYMENT
```

Not a general `BLOCKED` or `DEPLOYMENT_BLOCKED_NO_NON_SSH_CONTOUR`.

## Fallback ladder

For every operation, use channels in this order:

1. Local code and tests
2. Browser / UI
3. HTTP API
4. GitHub / API / CI
5. Cloud control plane or hosting panel
6. Pull-based deployment mechanism
7. Exact one-time owner action

SSH does not appear in the automatic ladder.

After one channel is unavailable, immediately proceed to the next.
Do not spend time retrying the same transport.

## Deprecated patterns

The following patterns in historical documents are **deprecated** and
must not be followed:

- `DEPLOYMENT_BLOCKED_NO_NON_SSH_CONTOUR` as a final status
- "SSH is intermittent" — implies retry is appropriate
- "retry SSH" or "try SSH with a longer timeout"
- "SSH disabled" used as a blocker for code-phase work

Historical reports that contain these patterns are not rewritten, but
agents must not act on them.
