"""Run live Jev choices, persist them, and replay them without a key."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from math import hypot
from pathlib import Path
from typing import Any

from .guide import Stroke, build_strokes
from .jev import JevClient
from .turtle import Move, Turtle, candidate_moves

TRACE_VERSION = 1


def _save(path: Path, trace: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(trace, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _planned_steps() -> list[tuple[int, int, Stroke]]:
    return [
        (stroke_index, point_index, stroke)
        for stroke_index, stroke in enumerate(build_strokes())
        for point_index in range(1, len(stroke.points))
    ]


def _near(left: list[float] | tuple[float, float], right: tuple[float, float]) -> bool:
    return len(left) == 2 and hypot(left[0] - right[0], left[1] - right[1]) < 0.001


def _check_record(record: dict[str, Any], stroke_index: int, point_index: int, move: Move) -> None:
    if (
        record.get("stroke_index") != stroke_index
        or record.get("point_index") != point_index
        or not _near(record.get("start", []), move.start)
        or not _near(record.get("end", []), move.end)
    ):
        raise ValueError("recorded move does not match the current guide")


def _advance_recorded(
    turtle: Turtle, record: dict[str, Any], stroke: Stroke, stroke_index: int, point_index: int
) -> None:
    moves = candidate_moves(stroke, point_index, turtle)
    choice = record.get("choice")
    if choice not in moves:
        raise ValueError("trace contains an unoffered move")
    move = moves[choice]
    _check_record(record, stroke_index, point_index, move)
    turtle.advance(move, stroke)


def replay_trace(path: Path) -> Turtle:
    trace = json.loads(Path(path).read_text(encoding="utf-8"))
    if trace.get("schema_version") != TRACE_VERSION or not isinstance(trace.get("steps"), list):
        raise ValueError("unsupported trace format")
    planned = _planned_steps()
    if len(trace["steps"]) > len(planned):
        raise ValueError("trace is longer than the drawing guide")
    turtle = Turtle()
    previous_stroke = -1
    for record, (stroke_index, point_index, stroke) in zip(
        trace["steps"], planned, strict=False
    ):
        if stroke_index != previous_stroke:
            turtle.reposition(stroke.points[0])
            previous_stroke = stroke_index
        _advance_recorded(turtle, record, stroke, stroke_index, point_index)
    if trace.get("complete") and len(trace["steps"]) != len(planned):
        raise ValueError("complete trace is missing moves")
    return turtle


def generate_trace(
    client: JevClient,
    path: Path,
    *,
    resume: bool = False,
    on_progress: Callable[[int, int, str], None] | None = None,
) -> dict[str, Any]:
    path = Path(path)
    if resume:
        trace = json.loads(path.read_text(encoding="utf-8"))
        replay_trace(path)
        if trace.get("model") != client.model:
            raise ValueError("trace model differs from the requested model")
    else:
        trace = {
            "schema_version": TRACE_VERSION,
            "model": client.model,
            "complete": False,
            "steps": [],
        }
    planned = _planned_steps()
    turtle = Turtle()
    previous_stroke = -1
    for step_number, (stroke_index, point_index, stroke) in enumerate(planned):
        if stroke_index != previous_stroke:
            turtle.reposition(stroke.points[0])
            previous_stroke = stroke_index
        if step_number < len(trace["steps"]):
            _advance_recorded(
                turtle, trace["steps"][step_number], stroke, stroke_index, point_index
            )
            continue
        moves = candidate_moves(stroke, point_index, turtle)
        state = {
            "goal": "Draw a pelican on a bicycle with a Logo turtle",
            "step": step_number + 1,
            "turtle": {
                "x": round(turtle.x, 2),
                "y": round(turtle.y, 2),
                "heading_degrees": round(turtle.heading, 2),
                "pen_down": True,
            },
            "recent_moves": [
                {
                    "start": record["start"],
                    "end": record["end"],
                    "turn_degrees": record["turn_degrees"],
                    "forward_pixels": record["forward_pixels"],
                    "choice": record["choice"],
                }
                for record in trace["steps"][-6:]
            ],
            "drawing_so_far": [
                [
                    round(record["start"][0]),
                    round(record["start"][1]),
                    round(record["end"][0]),
                    round(record["end"][1]),
                ]
                for record in trace["steps"]
            ],
        }
        # Jev selected the exact guide center on every trial move when it was offered.
        # Offer two equally safe offsets so its live choices visibly shape the line.
        criteria = {
            name: (
                f"{name}: turn {move.turn_degrees:+.1f} degrees, "
                f"forward {move.forward_pixels:.1f} pixels"
            )
            for name, move in moves.items()
            if name != "center"
        }
        question = "Which turtle move should come next to draw a pelican on a bicycle?"
        decision = client.choose(state, criteria, instructions=question)
        move = moves[decision.choice]
        turtle.advance(move, stroke)
        trace["steps"].append(
            {
                "stroke_index": stroke_index,
                "point_index": point_index,
                "part": stroke.part,
                "question": question,
                "options": criteria,
                "option_moves": {
                    name: {
                        "turn_degrees": move.turn_degrees,
                        "forward_pixels": move.forward_pixels,
                        "end": list(move.end),
                    }
                    for name, move in moves.items()
                    if name in criteria
                },
                "choice": decision.choice,
                "confidence": decision.confidence,
                "probabilities": decision.probabilities,
                "response_model": decision.model,
                "start": list(move.start),
                "end": list(move.end),
                "turn_degrees": move.turn_degrees,
                "forward_pixels": move.forward_pixels,
                "color": stroke.color,
                "width": stroke.width,
            }
        )
        _save(path, trace)
        if on_progress:
            on_progress(step_number + 1, len(planned), stroke.part)
    trace["complete"] = True
    _save(path, trace)
    return trace
