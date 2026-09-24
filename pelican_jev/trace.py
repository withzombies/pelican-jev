"""Ask Jev for freeform Logo commands, persist and replay the exact run."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .jev import JevClient
from .turtle import HEIGHT, WIDTH, Turtle, available_commands

TRACE_VERSION = 2
QUESTION = "What Logo command should the turtle execute next to draw a pelican on a bicycle?"


def _save(path: Path, trace: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(trace, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _pose(turtle: Turtle) -> dict[str, float | bool]:
    return {
        "x": round(turtle.x, 3),
        "y": round(turtle.y, 3),
        "heading_degrees_clockwise": round(turtle.heading, 3),
        "pen_down": turtle.pen_down,
    }


def _state(turtle: Turtle) -> dict[str, Any]:
    return {
        "goal": "Draw a pelican on a bicycle with a Logo turtle",
        "canvas": {
            "width": WIDTH, "height": HEIGHT, "origin": "top left",
            "positive_y": "down", "heading_zero": "right",
        },
        "turtle": _pose(turtle),
        "drawing_so_far": [
            [round(s.start[0], 2), round(s.start[1], 2),
             round(s.end[0], 2), round(s.end[1], 2)]
            for s in turtle.segments
        ],
    }


def _apply_record(turtle: Turtle, record: dict[str, Any]) -> None:
    if record.get("start") != _pose(turtle):
        raise ValueError("recorded command start does not match turtle state")
    choice = record.get("choice")
    if choice not in available_commands(turtle):
        raise ValueError("trace contains an unavailable command")
    turtle.execute(choice)
    if record.get("end") != _pose(turtle):
        raise ValueError("recorded command end does not match turtle state")


def replay_trace(path: Path) -> Turtle:
    trace = json.loads(Path(path).read_text(encoding="utf-8"))
    if trace.get("schema_version") != TRACE_VERSION or not isinstance(trace.get("steps"), list):
        raise ValueError("unsupported trace format")
    if len(trace["steps"]) > trace.get("max_steps", 0):
        raise ValueError("trace exceeds its command budget")
    turtle = Turtle()
    for index, record in enumerate(trace["steps"]):
        if index < len(trace["steps"]) - 1 and record.get("choice") == "DONE":
            raise ValueError("trace contains commands after DONE")
        _apply_record(turtle, record)
    return turtle


def generate_trace(
    client: JevClient,
    path: Path,
    *,
    resume: bool = False,
    max_steps: int = 180,
    on_progress: Callable[[int, int, str], None] | None = None,
) -> dict[str, Any]:
    if max_steps < 1:
        raise ValueError("max_steps must be positive")
    path = Path(path)
    if resume:
        trace = json.loads(path.read_text(encoding="utf-8"))
        turtle = replay_trace(path)
        if trace.get("model") != client.model or trace.get("max_steps") != max_steps:
            raise ValueError("trace settings differ from the requested run")
        if trace.get("complete"):
            return trace
    else:
        trace = {
            "schema_version": TRACE_VERSION,
            "model": client.model,
            "max_steps": max_steps,
            "complete": False,
            "stop_reason": None,
            "steps": [],
        }
        turtle = Turtle()
    while len(trace["steps"]) < max_steps:
        options = available_commands(turtle)
        start = _pose(turtle)
        decision = client.choose(_state(turtle), options,
                                 instructions=QUESTION)
        turtle.execute(decision.choice)
        trace["steps"].append({
            "question": QUESTION,
            "options": options,
            "choice": decision.choice,
            "confidence": decision.confidence,
            "probabilities": decision.probabilities,
            "response_model": decision.model,
            "start": start,
            "end": _pose(turtle),
        })
        _save(path, trace)
        if on_progress:
            on_progress(len(trace["steps"]), max_steps, decision.choice)
        if decision.choice == "DONE":
            trace["stop_reason"] = "jev_done"
            break
    else:
        trace["stop_reason"] = "step_limit"
    trace["complete"] = True
    _save(path, trace)
    return trace
