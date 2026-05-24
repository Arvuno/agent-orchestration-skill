# Leaf Worker Boundary

Goal: spawned subagents are workers, not orchestrators. Only the root session may spawn agents.

## Why this exists

Worker containment must be enforced at multiple layers:

1. The root orchestrator is the only session allowed to spawn native Codex subagents.
2. Every custom worker TOML sets `[features].multi_agent = false`.
3. Every custom worker TOML prevents nested fan-out through its agent/thread limits.
4. Every worker prompt/Dispatch Packet says `Do not spawn/request/recommend child agents`.
5. Handoff and context coverage validators reject nested-delegation fields and multi-agent tool names.
6. Workers return `ESCALATE_TO_PARENT` instead of delegating.

## Worker response when blocked

```text
STATUS: ESCALATE_TO_PARENT
WHY: <specific blocker>
PROPOSED_NEXT_ACTION: <serial action or agent type, if truly needed>
MINIMAL_CONTEXT: <facts only>
FILES_TOUCHED: <list>
VALIDATION_DONE: <commands/results>
```

## Bad worker behavior

- “I will spawn another agent.”
- “Ask another subagent to inspect this.”
- “Use the browser QA agent from inside this worker.”
- “I delegated the tests to test_runner.”

Correct behavior: do as much as possible inside the assigned bundle, then report the exact blocker to the root.
