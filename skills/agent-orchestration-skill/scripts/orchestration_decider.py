#!/usr/bin/env python3
"""Recommend minimal useful orchestration, agent count, and reasoning effort."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass

RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}
AMB_ORDER = {"low": 0, "medium": 1, "high": 2}
HIGH_RISK_SURFACES = {"auth", "payment", "payments", "security", "database", "data", "migration", "concurrency", "production"}
UI_SURFACES = {"frontend", "ui", "browser"}
DOC_SURFACES = {"docs", "research", "dependency"}
PATHLIKE_RE = r"[/\\]|\.(py|js|ts|tsx|jsx|go|rs|java|kt|swift|md|toml|yaml|yml|json|sql)\b"
IMPLEMENTATION_TERMS = {
    "fix", "improve", "implement", "patch", "change", "update", "proceed",
    "build", "add", "harden", "cleanup", "clean up", "go deep",
}
SCOUT_TERMS = {
    "map", "mapper", "scout", "research", "investigate", "audit", "survey",
    "inventory", "discover", "explore", "triage",
}
COHESIVE_SURFACE_GROUPS = [
    {"backend", "data", "database", "tests"},
    {"frontend", "ui", "browser", "tests"},
    {"infra", "devops", "docker", "ci", "tests"},
    {"docs", "research"},
]


@dataclass
class Recommendation:
    size: str
    max_agents: int
    default_agents: list[str]
    reasoning: str
    context_capsule_required: bool
    router_required: bool
    browser_qa: bool
    verification: str
    spawn_policy: str
    notes: list[str]


def parse_bool(v: str | bool) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"1", "true", "yes", "y"}


def dedupe_cap(agents: list[str], cap: int) -> list[str]:
    out: list[str] = []
    for a in agents:
        if a not in out:
            out.append(a)
    return out[:cap]


def has_any(task_l: str, terms: set[str]) -> bool:
    return any(term in task_l for term in terms)


def cohesive_surfaces(sset: set[str]) -> bool:
    meaningful = {s for s in sset if s}
    if not meaningful:
        return True
    for group in COHESIVE_SURFACE_GROUPS:
        if meaningful <= group:
            return True
    return False


def task_mentions_files(task_l: str) -> bool:
    import re
    return bool(re.search(PATHLIKE_RE, task_l))


def should_spawn_mapper(task_l: str, known_files: int, sset: set[str], amb_i: int, needs_architecture: bool, requires_docs: bool) -> bool:
    """Return true only when a mapper has distinct value over implementer coverage."""
    implementation_intent = has_any(task_l, IMPLEMENTATION_TERMS)
    explicit_scout = has_any(task_l, SCOUT_TERMS) and not implementation_intent
    if needs_architecture:
        return True
    if explicit_scout:
        return True
    if implementation_intent and cohesive_surfaces(sset):
        return False
    if known_files == 0 and amb_i >= 2 and not cohesive_surfaces(sset) and not requires_docs:
        return True
    return False


def decide(
    task: str,
    known_files: int,
    surfaces: list[str],
    risk: str,
    ambiguity: str,
    requires_browser: bool,
    requires_docs: bool,
    failing_tests: int,
    needs_architecture: bool = False,
    root_can_edit: bool = True,
    force_delegate: bool = False,
) -> Recommendation:
    sset = {s.strip().lower() for s in surfaces if s.strip()}
    risk_i = RISK_ORDER[risk]
    amb_i = AMB_ORDER[ambiguity]
    high_risk_surface = bool(sset & HIGH_RISK_SURFACES)
    task_l = task.lower()
    notes: list[str] = []
    if known_files > 0 and not task_mentions_files(task_l) and not root_can_edit:
        known_files = 0
        notes.append("Known files reset to 0 because the prompt contains no concrete file/path evidence and root source inspection is disabled.")
    read_only_terms = [
        "read-only", "readonly", "do not edit", "do not modify", "do not delete",
        "do not format", "do not stage", "no edits", "no write", "no writes",
    ]
    review_terms = ["review", "audit", "security review", "regression review"]
    read_only_review = any(t in task_l for t in read_only_terms) and any(t in task_l for t in review_terms)
    architecture_terms = ["system design", "redesign", "refactor architecture", "architectural redesign", "major feature", "new feature"]
    if not needs_architecture and any(term in task_l for term in architecture_terms) and (amb_i >= 1 or risk_i >= 1 or len(sset) >= 2 or known_files == 0):
        needs_architecture = True
    requires_browser = requires_browser or bool(sset & UI_SURFACES)
    requires_docs = requires_docs or bool(sset & DOC_SURFACES)
    implementation_intent = has_any(task_l, IMPLEMENTATION_TERMS)
    explicit_research = has_any(task_l, SCOUT_TERMS) and not implementation_intent
    mapper_needed = should_spawn_mapper(task_l, known_files, sset, amb_i, needs_architecture, requires_docs)
    if read_only_review:
        size = "S" if known_files <= 8 and risk_i <= 2 else "M"
        max_agents = 1
        agents = ["security_reviewer_high"] if ("security" in task_l or "security" in sset or risk_i >= 2) else ["regression_reviewer_medium"]
        reasoning = "high" if agents[0] == "security_reviewer_high" else "medium"
        verification = "targeted"
        spawn_policy = "single_read_only_reviewer"
        needs_architecture = False
        requires_docs = False
        notes.append("Read-only reviews must use root synthesis or one focused reviewer; do not spawn scouts for the same review packet.")
        notes.append("xhigh is forbidden for short read-only reviews, security reviews, evidence checks, and docs lookups.")
        notes.append("Run only focused checks that are already relevant to the review; avoid broad exploratory fan-out.")
    elif explicit_research:
        size = "S" if known_files <= 8 and risk_i <= 1 else "M"
        max_agents = 1
        agents = ["docs_researcher_low"] if sset <= DOC_SURFACES or "docs" in task_l else ["code_mapper_low"]
        reasoning = "low" if agents[0].endswith("_low") else "medium"
        verification = "read-only"
        spawn_policy = "single_read_only_mapper"
        needs_architecture = False
        notes.append("Explicit mapping/research without implementation intent gets one read-only worker only.")
        notes.append("Do not add implementers, reviewers, routers, or xhigh unless the user asks to proceed after the map.")
    elif known_files <= 1 and risk_i == 0 and amb_i == 0 and failing_tests <= 1 and not needs_architecture and not requires_browser and not requires_docs:
        size = "XS"
        max_agents = 1 if (force_delegate or not root_can_edit) else 0
        agents = ["micro_implementer_medium"] if max_agents else []
        reasoning = "medium" if agents else "low"
        verification = "targeted"
        spawn_policy = "one_worker_due_to_root_edit_boundary" if agents else "no_subagent_preferred"
        notes.append("Do not create ledger, DAG, router, or Context Capsule unless the task expands.")
        if not agents:
            notes.append("Direct execution is cheaper than opening a fresh worker context for a tiny known-scope task.")
    elif known_files <= 3 and risk_i <= 1 and amb_i <= 1 and not needs_architecture:
        size = "S"
        max_agents = 1
        agents = ["batch_implementer_medium" if known_files > 1 else "micro_implementer_medium"]
        reasoning = "medium"
        verification = "targeted"
        spawn_policy = "single_bundled_worker"
        notes.append("One worker should inspect, patch, and run targeted validation. Do not spawn a separate scout unless owner is unknown.")
        if requires_browser:
            notes.append("Keep browser checks targeted; spawn browser_qa only if separate evidence is required.")
        if requires_docs:
            notes.append("Keep docs lookup bounded; spawn docs_researcher only if the implementation contract is unclear.")
    elif known_files <= 8 and risk_i <= 2 and not needs_architecture:
        size = "M"
        max_agents = 3
        agents: list[str] = []
        if mapper_needed:
            agents.append("code_mapper_low")
        if requires_docs and amb_i >= 1 and explicit_research:
            agents.append("docs_researcher_low")
        agents.append("batch_implementer_medium")
        if failing_tests > 1 or risk_i >= 1 or requires_browser:
            agents.append("verification_engine_medium")
        if requires_browser and risk_i >= 1:
            agents.append("browser_qa_medium")
        reasoning = "medium"
        verification = "matrix" if failing_tests > 1 or risk_i >= 1 else "targeted+selected-matrix"
        spawn_policy = "small_wave_with_batched_write"
    elif known_files <= 20 and risk_i <= 2 and not needs_architecture:
        size = "L"
        max_agents = 4
        agents = []
        if mapper_needed:
            agents.append("code_mapper_low")
        if requires_docs and explicit_research:
            agents.append("docs_researcher_low")
        agents.append("complex_implementer_high" if high_risk_surface or amb_i == 2 else "batch_implementer_medium")
        agents.append("verification_engine_medium")
        if requires_browser:
            agents.append("browser_qa_medium")
        if high_risk_surface:
            agents.append("security_reviewer_high")
        reasoning = "high" if high_risk_surface or amb_i == 2 else "medium"
        verification = "full"
        spawn_policy = "bounded_control_plane"
    else:
        size = "XL"
        max_agents = 5
        agents = []
        if needs_architecture or amb_i == 2 or risk_i >= 2:
            agents.append("strategy_architect_xhigh")
        else:
            agents.append("code_mapper_low")
        if requires_docs and explicit_research:
            agents.append("docs_researcher_low")
        agents.append("complex_implementer_high")
        agents.append("verification_engine_medium")
        if requires_browser:
            agents.append("browser_qa_medium")
        if high_risk_surface or risk_i >= 2:
            agents.append("security_reviewer_high")
        reasoning = "xhigh" if "strategy_architect_xhigh" in agents else "high"
        verification = "full+review"
        spawn_policy = "architecture_first_then_bounded_workers"

    agents = dedupe_cap(agents, max_agents)
    context_capsule_required = size in {"M", "L", "XL"} or len(agents) > 1
    router_required = len(agents) > 2
    if size in {"M", "L", "XL"}:
        notes.append("Use Context Capsule as persistent storage, but dispatch only a scoped slice to each worker.")
    if not mapper_needed and any(a in agents for a in ["batch_implementer_medium", "complex_implementer_high"]):
        notes.append("Skip separate mapper/scout: implementer must perform context coverage, inspect, patch, and validate in one loop.")
    if requires_docs and implementation_intent:
        notes.append("Perform required docs lookup in the root before dispatch; do not spawn a docs researcher for normal implementation.")
    if router_required:
        notes.append("Use communication_router_low only after multiple handoffs or conflicts; never pre-route a single worker result.")
    if "strategy_architect_xhigh" in agents:
        notes.append("xhigh is read-only planning/architecture; implementation should be high/medium after the plan is clear.")
    if len(agents) == 1 and verification == "read-only":
        notes.append("Single read-only worker must complete: context coverage -> inspect -> evidence-backed handoff.")
    elif len(agents) == 1:
        notes.append("Single worker must complete: context coverage -> inspect -> patch/verify -> handoff.")

    return Recommendation(size, max_agents, agents, reasoning, context_capsule_required, router_required, requires_browser, verification, spawn_policy, notes)


def main() -> None:
    ap = argparse.ArgumentParser(description="Recommend token-efficient orchestration.")
    ap.add_argument("--task", required=True)
    ap.add_argument("--known-files", type=int, default=0)
    ap.add_argument("--surfaces", default="")
    ap.add_argument("--risk", choices=list(RISK_ORDER), default="medium")
    ap.add_argument("--ambiguity", choices=list(AMB_ORDER), default="medium")
    ap.add_argument("--requires-browser", default="false")
    ap.add_argument("--requires-docs", default="false")
    ap.add_argument("--failing-tests", type=int, default=0)
    ap.add_argument("--needs-architecture", default="false")
    ap.add_argument("--root-can-edit", default="true")
    ap.add_argument("--force-delegate", default="false")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    rec = decide(
        task=args.task,
        known_files=args.known_files,
        surfaces=args.surfaces.split(","),
        risk=args.risk,
        ambiguity=args.ambiguity,
        requires_browser=parse_bool(args.requires_browser),
        requires_docs=parse_bool(args.requires_docs),
        failing_tests=args.failing_tests,
        needs_architecture=parse_bool(args.needs_architecture),
        root_can_edit=parse_bool(args.root_can_edit),
        force_delegate=parse_bool(args.force_delegate),
    )
    data = asdict(rec)
    data["task"] = args.task
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print(f"Task: {args.task}")
        print(f"Size: {rec.size}")
        print(f"Reasoning: {rec.reasoning}")
        print(f"Spawn policy: {rec.spawn_policy}")
        print(f"Max agents: {rec.max_agents}")
        print(f"Agents: {', '.join(rec.default_agents) if rec.default_agents else 'none'}")
        print(f"Context Capsule required: {rec.context_capsule_required}")
        print(f"Router required: {rec.router_required}")
        print(f"Verification: {rec.verification}")
        for note in rec.notes:
            print(f"- {note}")


if __name__ == "__main__":
    main()
