#!/usr/bin/env python3
"""Static orchestration budget governor.

This is intentionally conservative. It stops obvious over-orchestration before
subagents are spawned: too many workers, too much reasoning, or oversized
Dispatch Packets.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from pathlib import Path
try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python <3.11 fallback for runtime only.
    tomllib = None

EFFORT_POINTS = {"low": 1, "medium": 2, "high": 4, "xhigh": 8}
AGENT_BASE = 2
SIZE_BUDGET = {"XS": 4, "S": 7, "M": 14, "L": 25, "XL": 40}
SIZE_AGENT_CAP = {"XS": 1, "S": 2, "M": 3, "L": 5, "XL": 6}
DISPATCH_CHAR_UNIT = 1400
AGENT_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{1,79}$")


def split_csv(s: str) -> list[str]:
    return [x.strip() for x in s.split(",") if x.strip()]


def split_aliases(s: str) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for item in split_csv(s):
        if "=" not in item:
            continue
        source, target = item.split("=", 1)
        source = source.strip()
        target = target.strip()
        if source and target:
            aliases[source] = target
    return aliases


def load_agent_registry(path: str | None) -> set[str] | None:
    """Load an optional configured agent allowlist.

    The package ships default subagent profiles, but many Codex installs use
    native user-defined agents instead. Budgeting should therefore validate
    against an allowlist only when the caller supplies one.
    """
    if not path:
        env_value = os.environ.get("AOC_ALLOWED_AGENTS", "")
        return set(split_csv(env_value)) if env_value.strip() else None
    p = Path(path)
    names: set[str] = set()
    if p.is_dir():
        for child in sorted(p.glob("*.toml")):
            if child.name == "config.toml":
                continue
            if tomllib is not None:
                try:
                    data = tomllib.loads(child.read_text(encoding="utf-8"))
                    name = data.get("name")
                    if isinstance(name, str) and name.strip():
                        names.add(name.strip())
                        continue
                except Exception:
                    pass
            names.add(child.stem.replace("-", "_"))
        return names
    text = p.read_text(encoding="utf-8")
    if p.suffix == ".json":
        data = json.loads(text)
        if isinstance(data, list):
            return {str(x).strip() for x in data if str(x).strip()}
        if isinstance(data, dict):
            agents = data.get("agents")
            if isinstance(agents, list):
                return {str(x).strip() for x in agents if str(x).strip()}
            if isinstance(agents, dict):
                return {str(x).strip() for x in agents if str(x).strip()}
    return set(split_csv(text.replace("\n", ",")))


def infer_reasoning(agent: str, fallback: str) -> str:
    for k in ["xhigh", "high", "medium", "low"]:
        if agent.endswith("_" + k) or agent.endswith("-" + k):
            return k
    return fallback


def estimate(
    agents: list[str],
    reasoning: str,
    size: str,
    browser: bool,
    full_matrix: bool,
    dispatch_chars: int = 0,
    allowed_agents: set[str] | None = None,
    recommended_agents: set[str] | None = None,
    agent_aliases: dict[str, str] | None = None,
) -> dict:
    detail = []
    score = 0
    recommendations: list[str] = []
    for a in agents:
        r = infer_reasoning(a, reasoning)
        pts = AGENT_BASE + EFFORT_POINTS.get(r, EFFORT_POINTS[reasoning])
        # Scouting is useful but should stay cheap.
        if any(k in a for k in ["scout", "mapper", "researcher", "router", "finalizer"]):
            pts = min(pts, AGENT_BASE + EFFORT_POINTS["low"])
        score += pts
        detail.append({"agent": a, "reasoning": r, "points": pts})
    if browser:
        score += 4
    if full_matrix:
        score += 5
    if dispatch_chars:
        # Packet size is a repeated cost if broadcast to workers. Penalize it.
        score += max(0, math.ceil(dispatch_chars / DISPATCH_CHAR_UNIT) - 1)
    allowed = SIZE_BUDGET[size]
    hard_failures: list[str] = []
    invalid_agents = [a for a in agents if not AGENT_NAME_RE.match(a)]
    if invalid_agents:
        hard_failures.append(f"Invalid agent name syntax: {', '.join(invalid_agents)}")
        recommendations.append("Use stable configured worker IDs; avoid spaces and shell-like punctuation in agent names.")
    unknown_agents = [a for a in agents if allowed_agents is not None and a not in allowed_agents]
    if unknown_agents:
        hard_failures.append(f"Unknown agent names for configured registry: {', '.join(unknown_agents)}")
        recommendations.append("Use agent names from the configured registry/allowlist, or omit the allowlist when budgeting user-defined native Codex agents.")
    if recommended_agents is not None:
        aliases = agent_aliases or {}
        expected_agents = set(recommended_agents)
        expected_agents.update(target for source, target in aliases.items() if source in recommended_agents)
        unexpected_agents = [a for a in agents if a not in expected_agents]
        if unexpected_agents:
            hard_failures.append(f"Agents not recommended by decider or mapped aliases: {', '.join(unexpected_agents)}")
            recommendations.append("Budget only decider-recommended roles, or map recommended roles to custom worker IDs with --agent-aliases role=custom_worker.")
    if len(agents) > SIZE_AGENT_CAP[size]:
        hard_failures.append(f"Too many agents for {size}: {len(agents)} > {SIZE_AGENT_CAP[size]}")
        recommendations.append("Merge related work into one bundled worker or run phases serially.")
    if size in {"XS", "S", "M"} and any(infer_reasoning(a, reasoning) == "xhigh" for a in agents):
        hard_failures.append("xhigh is not allowed for XS/S/M orchestration.")
        recommendations.append("Use medium for normal writes, high for complex writes, and reserve xhigh for large read-only strategy.")
    if any(infer_reasoning(a, reasoning) == "xhigh" and any(k in a for k in ["scout", "mapper", "researcher", "reviewer", "router", "finalizer"]) for a in agents):
        hard_failures.append("xhigh is not allowed for scout/mapper/researcher/reviewer/router/finalizer workers.")
        recommendations.append("Use low/medium for research and high only for focused security or regression review.")
    if dispatch_chars > 7000:
        hard_failures.append(f"Dispatch Packet too large: {dispatch_chars} chars > 7000")
        recommendations.append("Pass a narrower Context Capsule slice instead of broadcasting full context.")
    if score > allowed:
        recommendations.append("Reduce fan-out, downgrade reasoning, remove redundant scout, or shorten dispatch packets.")
    status = "OKAY" if score <= allowed and not hard_failures else "OVER_BUDGET"
    return {
        "score": score,
        "budget": allowed,
        "status": status,
        "agent_cap": SIZE_AGENT_CAP[size],
        "detail": detail,
        "hard_failures": hard_failures,
        "recommendations": recommendations,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Check orchestration fan-out against a token-cost budget")
    ap.add_argument("--size", choices=list(SIZE_BUDGET), required=True)
    ap.add_argument("--agents", required=True, help="Comma-separated agent names")
    ap.add_argument("--reasoning", choices=list(EFFORT_POINTS), default="medium")
    ap.add_argument("--browser", action="store_true")
    ap.add_argument("--full-matrix", action="store_true")
    ap.add_argument("--dispatch-chars", type=int, default=0, help="Largest Dispatch Packet char count, if known")
    ap.add_argument("--allowed-agents", default="", help="Optional comma-separated configured agent allowlist")
    ap.add_argument("--agent-registry", default="", help="Optional file or directory containing configured agent names")
    ap.add_argument("--recommended-agents", default="", help="Optional comma-separated decider-recommended roles/agents")
    ap.add_argument("--agent-aliases", default="", help="Optional comma-separated role=custom_worker mappings for custom native agents")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    allowed_agents = set(split_csv(args.allowed_agents)) if args.allowed_agents.strip() else load_agent_registry(args.agent_registry or None)
    recommended_agents = set(split_csv(args.recommended_agents)) if args.recommended_agents.strip() else None
    result = estimate(
        split_csv(args.agents),
        args.reasoning,
        args.size,
        args.browser,
        args.full_matrix,
        args.dispatch_chars,
        allowed_agents=allowed_agents,
        recommended_agents=recommended_agents,
        agent_aliases=split_aliases(args.agent_aliases),
    )
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"{result['status']}: score {result['score']} / budget {result['budget']} | agent cap {result['agent_cap']}")
        for d in result["detail"]:
            print(f"- {d['agent']}: {d['reasoning']} -> {d['points']} points")
        for f in result["hard_failures"]:
            print(f"Hard stop: {f}")
        for r in result["recommendations"]:
            print(f"Recommendation: {r}")
    sys.exit(1 if result["status"] == "OVER_BUDGET" else 0)


if __name__ == "__main__":
    main()
