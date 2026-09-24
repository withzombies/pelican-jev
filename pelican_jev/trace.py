"""Jev selects proposed Logo strokes; save enough evidence to replay every command."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .jev import JevClient
from .proposer import PROPOSER_MODEL, CodexProposer, Proposal, drawing_state
from .turtle import Turtle

TRACE_VERSION = 3
QUESTION = (
    "Which proposed Logo sequence should the turtle draw next "
    "for a recognizable, funny picture?"
)


def _save(path: Path, trace: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(trace, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _pose(turtle: Turtle) -> dict[str, float | bool]:
    return drawing_state(turtle)["turtle"]


def _criteria(proposals: list[Proposal]) -> dict[str, str]:
    return {
        proposal.id: (
            f"{proposal.label}. Logo commands: {'; '.join(proposal.commands)}. "
            f"New lines: {json.dumps(proposal.added_segments, separators=(',', ':'))}"
        )
        for proposal in proposals
    }


def _apply_record(turtle: Turtle, record: dict[str, Any]) -> None:
    if record.get("start") != _pose(turtle):
        raise ValueError("recorded command start does not match turtle state")
    try:
        turtle.execute(record["choice"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("trace contains an unavailable command") from error
    if record.get("end") != _pose(turtle):
        raise ValueError("recorded command end does not match turtle state")


def replay_trace(path: Path) -> Turtle:
    trace = json.loads(Path(path).read_text(encoding="utf-8"))
    if trace.get("schema_version") != TRACE_VERSION:
        raise ValueError("unsupported trace format")
    rounds, steps = trace.get("rounds"), trace.get("steps")
    if not isinstance(rounds, list) or not isinstance(steps, list):
        raise ValueError("trace has no round or command list")
    if len(rounds) > trace.get("max_rounds", 0):
        raise ValueError("trace exceeds its round budget")
    turtle = Turtle()
    step_index = 0
    for round_index, round_record in enumerate(rounds, start=1):
        if round_record.get("state") != drawing_state(turtle):
            raise ValueError("recorded round state does not match turtle state")
        proposals = round_record.get("proposals")
        if not isinstance(proposals, list):
            raise ValueError("trace round has no proposals")
        selected = next(
            (proposal for proposal in proposals
             if proposal.get("id") == round_record.get("choice")),
            None,
        )
        if not isinstance(selected, dict) or not isinstance(selected.get("commands"), list):
            raise ValueError("trace has no selected proposal")
        for command in selected["commands"]:
            if step_index >= len(steps) or steps[step_index].get("choice") != command:
                raise ValueError("trace command differs from the selected proposal")
            if steps[step_index].get("round") != round_index:
                raise ValueError("trace command has the wrong round")
            _apply_record(turtle, steps[step_index])
            step_index += 1
    if step_index != len(steps):
        raise ValueError("trace has extra commands")
    if trace.get("complete") and len(rounds) != trace["max_rounds"]:
        raise ValueError("complete trace is missing rounds")
    return turtle


def generate_trace(
    client: JevClient,
    path: Path,
    *,
    proposer: CodexProposer | None = None,
    resume: bool = False,
    max_rounds: int = 10,
    on_progress: Callable[[int, int, str], None] | None = None,
) -> dict[str, Any]:
    if max_rounds < 1:
        raise ValueError("max_rounds must be positive")
    path = Path(path)
    proposer = proposer or CodexProposer()
    if resume:
        trace = json.loads(path.read_text(encoding="utf-8"))
        turtle = replay_trace(path)
        if trace.get("model") != client.model or trace.get("max_rounds") != max_rounds:
            raise ValueError("trace settings differ from the requested run")
        if trace.get("complete"):
            return trace
    else:
        trace = {
            "schema_version": TRACE_VERSION,
            "model": client.model,
            "proposer": f"Codex CLI ({PROPOSER_MODEL})",
            "max_rounds": max_rounds,
            "complete": False,
            "rounds": [],
            "steps": [],
        }
        turtle = Turtle()
    while len(trace["rounds"]) < max_rounds:
        state = drawing_state(turtle)
        proposals = proposer.propose(turtle)
        options = _criteria(proposals)
        decision = client.choose(state, options, instructions=QUESTION)
        selected = next(proposal for proposal in proposals if proposal.id == decision.choice)
        round_index = len(trace["rounds"]) + 1
        round_record = {
            "index": round_index,
            "state": state,
            "proposals": [
                {"id": proposal.id, "label": proposal.label,
                 "commands": proposal.commands, "added_segments": proposal.added_segments}
                for proposal in proposals
            ],
            "question": QUESTION,
            "options": options,
            "choice": decision.choice,
            "confidence": decision.confidence,
            "probabilities": decision.probabilities,
            "response_model": decision.model,
        }
        for command in selected.commands:
            start = _pose(turtle)
            turtle.execute(command)
            trace["steps"].append({
                "round": round_index,
                "choice": command,
                "start": start,
                "end": _pose(turtle),
                "question": QUESTION,
                "options": options,
                "candidate_labels": {proposal.id: proposal.label for proposal in proposals},
                "jev_choice": decision.choice,
                "jev_confidence": decision.confidence,
                "proposer_label": selected.label,
            })
        trace["rounds"].append(round_record)
        _save(path, trace)
        if on_progress:
            on_progress(round_index, max_rounds, selected.label)
    trace["complete"] = True
    _save(path, trace)
    return trace
