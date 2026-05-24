# Reasoning Router

Use the cheapest adequate reasoning effort. Reasoning is a scarce budget; spend it only where it improves correctness.

## Low

Use for scouts and deterministic operations:

- file/symbol discovery;
- code-path mapping without deep design;
- bounded docs/source contract checks;
- exact verification commands;
- handoff routing and final summaries.

Low agents must stay narrow. Do not spawn several low scouts when one implementer must read the same files anyway.

Do not use low/medium scout or docs-research workers as a reflex before implementation. If the implementer must inspect the same files, put those files in `MUST READ` and make the implementer perform context coverage before editing.

## Medium

Use for normal production work:

- one small implementation bundle;
- several related files in one module/user flow;
- ordinary debugging with a plausible owner;
- browser QA and verification matrices;
- test design where failure interpretation matters.

Medium is the default for normal writing and deep verification.

## High

Use for complex writes or reviews:

- non-trivial business logic;
- migrations or data-model changes;
- concurrency-sensitive code;
- security-sensitive review;
- broad regression review after risky changes.

High should be scoped by a clear Dispatch Packet and required files. It is not a substitute for missing context.

## XHigh

Use only for very large ambiguous planning or critical architecture/feature-structure decisions. Prefer read-only strategy first. Do not use it as the default debugger or implementer.

Use `strategy_architect_xhigh` when the root needs a plan, invariants, risk model, or architectural decomposition before workers implement.

Do not use xhigh for bounded read-only reviews, short security reviews, docs research, evidence checks, scouts, mappers, routers, finalizers, or focused test/report validation. Those should be handled by root synthesis, low/medium research, or one high reviewer when security-sensitive.

## Anti-patterns

- xhigh for routine updates, simple debugging, isolated files, CSS, imports, or mechanical fixes.
- xhigh for a short read-only review or a focused security audit packet.
- xhigh for docs lookup, evidence checking, mapping, routing, or final summaries.
- xhigh as an implementation worker for normal changes.
- high for changes that tests can mechanically verify.
- several low agents for a cohesive two-file patch; use one medium worker instead.
- a scout that reads the same files the implementer must read anyway; include those files in the Dispatch Packet instead.
- a docs researcher that only repeats root Context7 lookup for a normal implementation task.
