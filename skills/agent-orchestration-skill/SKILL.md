---
name: agent-orchestration-skill
description: EXPLICIT ONLY. Use only when prompt contains `$agent-orchestration-skill`; root-only token-aware subagent orchestration with control-room events.
---

# Agent Orchestration Skill

Use this skill only when the user prompt contains the exact literal `$agent-orchestration-skill`. Do not use this skill for ordinary coding, testing, audit, debugging, or subagent tasks when that literal invocation is absent. Use it only in the root Codex session. Never instruct spawned subagents to invoke this or any other repo skill, and never instruct spawned subagents to spawn more agents. This is a no nested delegation workflow.

## Step 0 — Runtime mode guard

This skill is explicit-only and root-only. If the current user prompt does not contain `$agent-orchestration-skill`, stop using this skill and continue in normal mode. If the prompt says `You are a subagent`, `verification subagent`, `Run exactly these commands`, `Do not edit files`, `LEAF_EXEC_MODE`, or `Return only a YAML Handoff Packet`, do **not** use this skill, do **not** spawn agents, and perform only the bounded leaf task.

## Step 0.1 - Worker launch policy

In an interactive Codex root session, the root orchestrator must use native Codex subagent spawning for workers. The expected transcript should look like:

```text
Spawned <agent-id> (<model> <reasoning>)
```

Do not launch mapper, implementer, verifier, reviewer, or any other orchestration worker through an external CLI process. Worker execution is native-spawn only.

When spawning native workers, the root prompt must make the leaf boundary explicit:

```text
LEAF_EXEC_MODE. You are a <role> leaf worker. Do not spawn agents. Do not invoke skills. Use only the provided Dispatch Packet. Return the requested Handoff Packet.
```

Spawned workers are leaf workers. They must not spawn, request, recommend, coordinate, or plan child subagents. If a worker needs another worker, it must return `ESCALATE_TO_PARENT` with the blocker and let the root orchestrator decide.

## Step 0.2 - Immediate AOC run attachment

When this skill is invoked in the root session, attach to AOC before docs lookup, Context Capsule creation, DAG planning, or worker spawning:

```bash
aoc current --repo . --json
```

If no current run exists for the repo, initialize one immediately:

```bash
aoc init --repo . --task "<task derived from the user prompt>" --json
```

Store the selected `run_id` in root context and use it for every later event, capsule, dispatch, handoff, verification record, and final summary. Do not create a second run if `aoc current` already selected an active repo run. Emit a compact `skill_invoked` event after attach/init when a run ledger exists.

`aoc current` is an active-run lookup, not a historical lookup. If the previous run has a terminal status or a `final_status`/`run_completed` event, start a new run with `aoc init` instead of appending fresh work to the old run.

## Prime directive

Act as a **task compiler, context-preserving control-plane operator, and event-driven run supervisor**, not a prompt broadcaster. Classify the work, preserve the essential context, choose the cheapest adequate reasoning tier, batch related actions, compile minimal Dispatch Packets, track state, and collect concise Handoff Packets. The Context Capsule is persistent storage; a Dispatch Packet is only a small scoped slice for one worker. The capsule stays on disk; workers receive only the narrow slice they need.

## Command surface

For normal project use, prefer the public CLI:

```bash
npm install -g agentic-orchestration-control
aoc --help
aoc install-skill --strict
aoc init --repo . --task "<task>"
aoc tui --repo .
aoc gui --repo .
```

The direct `python3 "$AOC_SKILL_DIR/scripts/*.py"` examples below are low-level internal control-plane commands for the root skill operator. Use them only when the public `aoc` route does not expose the required operation.

For internal helper scripts, resolve the globally installed skill directory first, before any direct `python3 "$AOC_SKILL_DIR/scripts/..."` call. This keeps commands working after `npm install -g agentic-orchestration-control`, even when the target repo does not contain a repo-local `skills/` copy:

```bash
AOC_SKILL_DIR="${AOC_SKILL_DIR:-${CODEX_HOME:-$HOME/.codex}/skills/agent-orchestration-skill}"
test -d "$AOC_SKILL_DIR/scripts"
```

## Hard constraints

1. **Root-only skill:** subagents receive plain dispatch text, not skill names.
2. **Context never depends on memory alone:** store essential facts in a Context Capsule before multi-phase or multi-worker execution.
3. **No worker edits without Context Coverage:** a worker must read required files/areas and report coverage before changing code.
4. **No one-agent-per-file fan-out:** batch related files by user flow, module, package, or owner.
5. **No redundant waves:** if one worker can inspect, patch, and test a small change, use one worker.
6. **No raw output broadcast:** route only facts, blockers, file ownership, commands run, failures, and next actions.
7. **No full capsule broadcast:** keep the Context Capsule on disk and pass only a scoped slice to each worker.
8. **Dispatch budgets:** cap must-read files, facts, decisions, tests, and context text before spawning. If the packet is large, narrow the scope instead of spawning.
9. **Write workers must complete a loop:** context coverage → inspect → patch → targeted validation → Handoff Packet.
10. **Read-heavy work can be parallel; write-heavy work should be serialized or batched carefully.**
11. **Leaf-worker boundary:** only the root orchestrator session may spawn native Codex subagents. Workers return `ESCALATE_TO_PARENT` when they need help.
12. **Plan and budget gates before broad work:** medium/large tasks need a compact phase plan and budget check before implementation.
13. **Inspectable state:** when a run ledger exists, emit compact events so the control-room TUI can show sessions, worker lanes, gates, evidence, and memory without parsing raw logs.
14. **Native spawn only:** launch workers through native Codex subagent spawning. Do not shell out to external CLI processes for orchestration workers.
15. **Run lifecycle first:** attach/init the AOC run before any broad research, capsule, DAG, or worker spawn so the control room can show the whole run.
16. **No empty capsules for M/L/XL:** medium and larger runs must not create a Context Capsule with zero `must_read` entries. If ownership is unclear, first identify required files/areas, then create or update the capsule before dispatch.
17. **No xhigh for short read-only work:** read-only reviews, security reviews with a bounded focus, docs lookups, evidence checks, scouts, mappers, routers, and finalizers must not use `xhigh`. Use root synthesis or one focused `medium`/`high` reviewer.
18. **No non-action workers:** do not spawn a mapper/scout/docs researcher that only reads the same files the implementer must read. For cohesive implementation tasks, dispatch one implementer with context coverage instead. “Go deep” means stricter coverage and verification, not more agents.
19. **Map-only stays read-only:** if the user asks only to map, research, audit, inventory, or discover, spawn at most one read-only worker and do not add implementers/reviewers unless the user asks to proceed.
20. **No spawn before gates:** before the first native worker spawn, the root must run `orchestration_decider.py` and `budget_governor.py` using the intended worker IDs. Do not spawn a scout first and justify it afterward.
21. **Declared worker identities:** budget and dispatch must use stable native Codex worker IDs from the active environment. The package profiles in `subagents/*.toml` are defaults, not a required registry. If the user has custom agents, map decider roles to those IDs with `--agent-aliases` and optionally pass an allowlist with `--allowed-agents` or `--agent-registry`; do not invent one-off nicknames during the run.
22. **Budget actual reasoning:** budget checks must use the exact reasoning tier that will be used for each native worker. For custom agents whose names do not include `_low`, `_medium`, `_high`, or `_xhigh`, pass `--agent-reasoning worker=effort`.
23. **No micro follow-up waves:** do not spawn a new worker just to add a low-risk assertion, tiny formatting cleanup, or one-line test hardening after verification. Route it to an active owner if still running, fold it into the verifier only when already planned, or report it as a follow-up unless it is a blocking defect or failed validation.
24. **Worker events are structured:** every `worker_dispatched` event must include `--agent <worker-id>` and `--reasoning <actual-effort>` so the control room can track lanes and cost accurately.
25. **No invented known-file counts:** pass `known-files > 0` only when the user named concrete paths or the root has allowed source evidence. Do not expand “go deep” into an audit/re-audit prompt or inflate known file count to force L/XL orchestration.

## Step 1 — Classify before spawning

Classify the task using:

- Known files: 0, 1, 2–3, 4–8, 9+
- Surfaces: frontend, backend, database, infra, docs, tests, browser, security
- Ambiguity: low, medium, high
- Risk: low, medium, high, critical
- Required evidence: none, targeted test, full test matrix, browser QA, security review
- Parallel value: low, medium, high
- Worktree state: clean, dirty, unknown

Run `$AOC_SKILL_DIR/scripts/orchestration_decider.py` before any worker spawn. This is mandatory for every non-trivial task and for every proposed scout/research/review worker.

Use the user’s actual task wording for `--task`. Do not rewrite a cohesive implementation request into “audit architecture, implement, verify, and re-audit” merely because the user said “go deep”. If the root has not read source and the user did not name files, use `--known-files 0`.

```bash
python3 "$AOC_SKILL_DIR/scripts/orchestration_decider.py" \
  --task "<task>" \
  --known-files <n> \
  --surfaces backend,tests \
  --risk medium \
  --ambiguity high \
  --requires-docs true \
  --root-can-edit false \
  --force-delegate true \
  --json
```

## Step 2 — Pick the minimum viable orchestration mode

| Mode | Criteria | Default behavior |
|---|---|---|
| XS | Known tiny task | Usually no subagent. If root edits are forbidden, exactly one `micro_implementer_medium` |
| S | 1–3 related files | One bundled `micro_implementer_medium` or `batch_implementer_medium`; optional exact `test_runner_low` only when useful |
| M | 3–8 files or unclear owner | Short DAG; `code_mapper_low` only if discovery is needed; one batched implementer; verifier |
| L | Multi-surface feature/fix | Ledger + DAG + bounded scout/research + 1–2 implementers + verification |
| XL | Very large or critical ambiguous work | Ledger + DAG + plan gate + optional `strategy_architect_xhigh`, then scoped high/medium workers |

Do not spawn agents just to satisfy a habit. Spawn only when the worker has a meaningful bundle of work or isolates noisy verification/browser output. A useful worker must perform at least two valuable actions, such as inspect + patch, patch + validate, browser reproduce + evidence, or mapping + ownership summary.

Mapper/scout hard stop: do not spawn a read-only mapper if the implementer must read the same files anyway. A mapper is allowed only when it inspects a substantially different surface, reduces unknown ownership across broad independent domains, or the root cannot compile a safe implementation Dispatch Packet without it. Otherwise one implementer owns context coverage, inspection, patching, focused validation, and handoff.

First-scout exception: if ownership is genuinely unknown and the root cannot produce a safe implementation packet, the scout is allowed only after the decider recommends `code_mapper_low` or `scope_scout_low` and budget passes. The scout packet must be narrow, read-only, use `low` reasoning by default, cap must-read areas, and stop after recommending one bounded implementation bundle. Do not run a pre-gate scout.

## Step 3 — Preserve context before dispatch

For every task with more than one phase or worker, create/update a Context Capsule. It is the root-owned source of truth for facts that must not be lost when a new subagent context opens. It is **not** prompt payload and must not be pasted wholesale into every worker prompt.

For M/L/XL runs, do not initialize a capsule with zero `must_read` entries. Include the specific files/areas a worker must inspect before editing. If the first pass cannot identify exact files, perform a bounded read-only ownership scout first, then create/update the capsule with the discovered `must_read` list before any write worker is spawned.

```bash
python3 "$AOC_SKILL_DIR/scripts/context_capsule.py" init \
  --task "<task>" \
  --goal "<goal>" \
  --run-id <run_id> \
  --must-read path/to/file_a \
  --must-read path/to/file_b \
  --require-must-read \
  --acceptance "<observable acceptance criterion>" \
  --validation "<command or QA check>" \
  --out .orchestration/context_capsule.json
```

Keep the capsule compact. Store confirmed facts, rejected assumptions, decisions, ownership, required files/areas, forbidden files/areas, acceptance criteria, validation commands, blockers, and evidence references. Do not store raw logs, transcripts, broad summaries, or private reasoning.

When dispatching a worker, use a narrow slice:

```bash
python3 "$AOC_SKILL_DIR/scripts/context_capsule.py" slice \
  --file .orchestration/context_capsule.json \
  --focus "<worker objective/scope>" \
  --max-items 4
```

Use:

```bash
python3 "$AOC_SKILL_DIR/scripts/context_capsule.py" render --file .orchestration/context_capsule.json --focus "<worker objective/scope>" --max-chars 1200
```

Read `references/context-capsule.md` when needed.

## Step 4 — Create control-plane state when needed

For XS/S, avoid unnecessary artifacts unless useful. For medium/large tasks, use the run attached in Step 0.2. If Step 0.2 was skipped because the task expanded after classification, attach/init now before any worker spawn:

```bash
aoc current --repo . --json
aoc init --repo . --task "<task>" --json
```

Use the existing selected run when present. Use the ledger to record phases, dispatches, Handoff Packets, claimed files, evidence, failures, context capsule path, and final status. Before spawning any worker, check the ledger for duplicate active/completed work.

When a ledger exists, treat the run as event-driven. Emit compact state changes so the optional control-room TUI can show the orchestration without parsing raw logs:

```bash
python3 "$AOC_SKILL_DIR/scripts/event_emit.py" --root . --run-id <run_id> --event worker_dispatched --agent batch_implementer_medium --reasoning medium --summary "frontend cart implementation bundle dispatched"
```

Use events for run creation, classification, DAG/budget gates, worker dispatch, Context Coverage, commands, handoffs, failures, memory updates, and final status. Worker dispatch events must include both `--agent` and `--reasoning`. Events are compact JSONL records; long logs belong in `evidence/` files.

## Step 5 — Build a DAG only when orchestration is justified

Do not use a DAG for tiny tasks. For medium/large tasks, create a compact dependency-aware DAG with at most 7 phases:

```bash
python3 "$AOC_SKILL_DIR/scripts/dag_planner.py" --task "<task>" --size M --surfaces frontend,backend > .orchestration/plan.json
python3 "$AOC_SKILL_DIR/scripts/plan_gate.py" .orchestration/plan.json
```

If the gate rejects the plan, fix the plan before spawning. The plan gate checks executability, dependencies, acceptance criteria, validation, context policy, and worker leaf policy.

## Step 6 — Reasoning router

Use the cheapest adequate reasoning tier:

- `low`: scouts, file/symbol discovery, code-path mapping, docs contract checks, exact command execution, routing/finalization.
- `medium`: normal code writing, small-to-medium implementation bundles, browser QA, meaningful test design, verification matrices.
- `high`: complex implementation, non-trivial business logic, migrations, concurrency suspicion, security-sensitive review, hard regression audit.
- `xhigh`: very large ambiguous planning, architecture/feature structuring, critical design tradeoffs, or repeated high-effort failure with evidence.

Do not use `xhigh` for routine updates, isolated fixes, simple debugging, or single-file implementation. Prefer `strategy_architect_xhigh` as read-only planning; use `complex_implementer_high` for hard writes.

Never use `xhigh` for bounded read-only reviews, short security reviews, docs research, evidence verification, mappers, scouts, routers, finalizers, or focused test/report checks. A prompt like “Read-only security review for ORC-009…” should be root synthesis plus at most one `security_reviewer_high`, not multiple scouts and not `xhigh`.

Use `$AOC_SKILL_DIR/scripts/budget_governor.py` before spawning. Use the worker IDs and reasoning tiers that will actually be spawned. The bundled `subagents/*.toml` names are examples; custom user agents are valid. To enforce a configured registry, pass `--agent-registry <path>` or `--allowed-agents <csv>`. To keep decider gating with custom agents, pass the decider roles through `--recommended-agents` and map them with `--agent-aliases role=custom_worker`. For custom agents, pass `--agent-reasoning worker=effort` unless the agent registry declares `model_reasoning_effort`. Reasoning above the decider role is rejected unless `--allow-reasoning-upgrade` is explicitly used and the gate event records why:

```bash
python3 "$AOC_SKILL_DIR/scripts/budget_governor.py" --size M --agents code_mapper_low,batch_implementer_medium --reasoning medium --dispatch-chars <largest_packet_chars>
python3 "$AOC_SKILL_DIR/scripts/budget_governor.py" --size M --recommended-agents batch_implementer_medium,verification_engine_medium --agents my_backend_worker,my_verifier --agent-aliases batch_implementer_medium=my_backend_worker,verification_engine_medium=my_verifier --agent-reasoning my_backend_worker=medium,my_verifier=medium --reasoning medium --dispatch-chars <largest_packet_chars>
```

If `budget_governor.py` returns `OVER_BUDGET`, do not spawn. Reclassify, merge workers, reduce reasoning, or narrow the Dispatch Packet.

## Step 7 — Compile Native Spawn Dispatch Packets with required context

A Dispatch Packet must be short, targeted, and include only a scoped Context Capsule slice. Do not paste the whole plan, whole capsule, raw logs, or previous transcripts. Include:

```text
LEAF_EXEC_MODE. You are a <role> leaf worker. Do not spawn agents. Do not invoke skills. Use only this Dispatch Packet. Return only the requested Handoff Packet.

AOC RUN CONTEXT:
ROLE:
MODE / REASONING BUDGET:
OBJECTIVE:
SCOPE OWNERSHIP:
MUST READ BEFORE EDITING:
FILES / AREAS ALLOWED:
FILES / AREAS FORBIDDEN:
CONTEXT CAPSULE SLICE:
CONFIRMED FACTS:
REJECTED ASSUMPTIONS:
TASK BUNDLE:
ACCEPTANCE CRITERIA:
VALIDATION REQUIRED:
CONTEXT COVERAGE CHECK:
STOP CONDITIONS:
SKILL / DELEGATION POLICY:
OUTPUT:
```

The native spawn prompt is not complete unless it includes run context, role, reasoning budget, objective, scope ownership, must-read context, allowed/forbidden areas, a scoped capsule slice, concrete tasks, validation, stop conditions, and a routing-free output schema.

Use this output schema for workers:

```text
STATUS: success | partial | blocked | failed | ESCALATE_TO_PARENT
SUMMARY:
CONTEXT_COVERAGE:
FILES_READ:
FILES_CHANGED:
CHANGES_MADE:
VALIDATION:
EVIDENCE:
RISKS:
PARENT_ACTION:
```

Use `$AOC_SKILL_DIR/scripts/dispatch_compiler.py` when useful. It caps the capsule slice by default: 8 must-read items, 6 forbidden items, 5 facts, 3 rejected assumptions, 3 decisions, 5 acceptance criteria, 4 validation checks, and about 900 context characters. Workers must treat the packet as complete. If a required file/area is unavailable, they must return `ESCALATE_TO_PARENT` instead of guessing.

If the compiled packet is too large, do not spawn yet. Narrow the worker objective, reduce must-read files, or split by dependency phase. Never solve token pressure by broadcasting a larger packet.

## Step 8 — Batch tasks

Before spawning implementers, group work by ownership:

- Before any spawn, ask: can the root do this directly, or can the assigned worker do the full loop alone?
- Same user flow → one worker.
- Same package/module → one worker.
- Frontend + small API touch for the same feature → one `batch_implementer_medium`, not two agents.
- Independent read-only audits → parallel agents are okay.
- Independent write-heavy modules → separate workers only if file ownership does not overlap.
- Do not spawn a scout if the implementer must read the same files anyway; put those files in `MUST READ`.
- Do not spawn docs/research workers for ordinary implementation just because docs were checked; root should do bounded Context7/docs lookup before dispatch.
- Treat “go deep” as a request for stronger context coverage, validation, and review, not extra scouts.
- Before any spawn, confirm the worker appears in the decider recommendation or the root has mapped the decider role to a declared custom worker ID, and the budget passed for the exact worker ID that will be spawned.
- Do not spawn a fresh worker for low-risk test-hardening or a single missing assertion after successful verification. If the original worker is no longer active, record the gap in the final report unless it blocks acceptance.

Use `$AOC_SKILL_DIR/scripts/batch_tasks.py` when useful.

## Step 9 — Handoff validation and context coverage gate

Use `communication_router_low` only from the root session, and only when there are multiple Handoff Packets, conflicts, overlapping files, or many test results.

Validate leaf handoffs:

```bash
python3 "$AOC_SKILL_DIR/scripts/handoff_validate.py" <handoff-file>
```

For context-sensitive work, validate coverage against the worker Dispatch Packet. This avoids forcing one worker to cover the whole capsule:

```bash
python3 "$AOC_SKILL_DIR/scripts/context_coverage_gate.py" --dispatch <dispatch-file> --handoff <handoff-file>
```

Use `--capsule --full-capsule` only when a single worker was explicitly assigned every must-read item in the capsule.

Workers must not return `next_handoff`, `target_agent`, or child-agent plans. The root orchestrator owns all routing decisions.

## Step 10 — Failure recovery

Do not respond to failure by blindly spawning another agent.

- Classify failure.
- Retry transient failures once.
- Send compile/test failures back to the same implementation owner with exact evidence.
- Escalate sandbox, permission, dirty-worktree, or scope conflicts to the root/user.
- Replan after repeated systematic failure.

Use:

```bash
python3 "$AOC_SKILL_DIR/scripts/failure_classifier.py" --file <failure-log>
```

## Step 11 — Verification gate

- XS/S: targeted tests or commands relevant to touched files.
- M: targeted tests + relevant lint/typecheck/build/integration gate.
- L/XL: full matrix, browser QA if UI flow changed, security/regression review if high-risk.

Use `$AOC_SKILL_DIR/scripts/test_matrix.py` and `$AOC_SKILL_DIR/scripts/quality_gate.py` for deterministic command discovery/execution.

## Step 12 — Worktree isolation when appropriate

For large tasks, dirty checkouts, or high-risk multi-file edits, consider isolated worktree planning before implementation:

```bash
python3 "$AOC_SKILL_DIR/scripts/worktree_guard.py" --root . --run-id <run_id>
```

Only create a worktree when it is clearly useful and safe.

## Step 13 — Durable learning and inspectable control room

At the end of meaningful runs, write a tiny notepad entry only if the insight will help future work:

```bash
python3 "$AOC_SKILL_DIR/scripts/notepad.py" --kind learnings --context "..." --insight "..." --impact "..."
```

Build an inspectable memory index when the run produced decisions, handoffs, or evidence that should be searchable:

```bash
aoc memory build --run-id <run_id>
```

Open the local control-room TUI or GUI when the user asks to inspect orchestration state:

```bash
aoc

# GUI
aoc gui
```

Initialize a production run ledger when the user explicitly asks to start an observable orchestration session before work begins:

```bash
aoc init --run-id <run_id> --task "<task title>"
```

Optional Codex app-server/codexui visibility is safe and opt-in:

```bash
aoc codex doctor
aoc gui --with-codex --codex-url http://127.0.0.1:<port>
```

Keep `.orchestration/` as the source of truth for orchestration state. Treat Codex app-server/codexui as optional live-runtime context, not as a replacement for the run ledger, Context Capsule, Dispatch Packets, Handoffs, or evidence.

Do not store raw logs, private reasoning, or generic summaries. The memory layer should explain what was remembered and why, using source artifacts and evidence references.


## Step 14 — Usage control and cost visibility

Track usage separately from orchestration state. The control room should show both:

- **real/imported usage** when available from local tools such as `ccusage`;
- **estimated orchestration pressure** derived from Dispatch Packets, Handoff Packets, Context Capsule slices, evidence files, and event volume.

Never treat estimated pressure as provider billing. It is a local signal for token waste, prompt bloat, and fan-out risk. Real token usage must come from a trusted source such as a Codex log export or imported `ccusage` JSON.

For a run-scoped usage report including the derived estimate:

```bash
aoc usage --run-id <run_id>
```

For optional `ccusage` integration when it is installed:

```bash
aoc ccusage run --run-id <run_id>
```

Use budget checks before approving more workers, broad test matrices, high reasoning, or xhigh strategy:

```bash
aoc budget 12000 --run-id <run_id>
```

If usage pressure is high, prefer narrowing the Dispatch Packet, merging worker batches, downgrading reasoning, reusing previous results, or stopping at a gate before spawning more workers.

## Step 15 — Final output

Return a PR-ready summary:

- Classification and why the chosen agent count/reasoning was sufficient.
- Run ID if a ledger was created.
- Context Capsule path if used.
- Agents used and why.
- Files changed.
- Tests/commands/browser checks run and results.
- Failures and recovery decisions.
- Known residual risks or skipped checks.
- Follow-up only when genuinely useful.

## Reference modules

Read these only when needed:

- `references/spawn-economics.md`
- `references/thinking-router.md`
- `references/context-capsule.md`
- `references/context-coverage-gate.md`
- `references/dispatch-packet.md`
- `references/worker-contract.md`
- `references/test-gate.md`
- `references/skill-scope-policy.md`
- `references/leaf-worker-boundary.md`
- `references/control-plane.md`
- `references/control-room.md`
- `references/event-bus.md`
- `references/stop-gates.md`
- `references/memory-layer.md`
- `references/dag-plan-gate.md`
- `references/session-lifecycle.md`
- `references/failure-recovery.md`
- `references/worktree-isolation.md`
- `references/wisdom-notepads.md`
- `references/source-contract-proof.md`
- `references/evaluation-harness.md`
- `references/usage-control.md`
