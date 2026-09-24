"""Codex proposes generic Logo command batches; Jev decides which one runs."""

from __future__ import annotations

import json
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from .turtle import HEIGHT, WIDTH, Turtle

GOAL = "Draw a humorous pelican on a bicycle"
SCHEMA = {
    "type": "object",
    "properties": {
        "candidates": {
            "type": "array",
            "minItems": 3,
            "maxItems": 3,
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "label": {"type": "string"},
                    "commands": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["id", "label", "commands"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["candidates"],
    "additionalProperties": False,
}


class ProposalError(RuntimeError):
    """The proposer failed or returned unusable turtle commands."""


@dataclass(frozen=True)
class Proposal:
    id: str
    label: str
    commands: list[str]
    added_segments: list[list[float]]


Transport = Callable[[dict[str, Any], Path], dict[str, Any]]


def drawing_state(turtle: Turtle) -> dict[str, Any]:
    return {
        "goal": GOAL,
        "canvas": {
            "width": WIDTH, "height": HEIGHT, "origin": "top left",
            "positive_y": "down", "heading_zero": "right",
        },
        "turtle": {
            "x": round(turtle.x, 3),
            "y": round(turtle.y, 3),
            "heading_degrees_clockwise": round(turtle.heading, 3),
            "pen_down": turtle.pen_down,
        },
        "drawing_so_far": [
            [round(s.start[0], 2), round(s.start[1], 2),
             round(s.end[0], 2), round(s.end[1], 2)]
            for s in turtle.segments
        ],
    }


def _preview(turtle: Turtle, path: Path) -> None:
    canvas = Image.new("RGB", (WIDTH, HEIGHT), "#f8f4ea")
    draw = ImageDraw.Draw(canvas)
    for segment in turtle.segments:
        draw.line((segment.start, segment.end), fill="#172a3b", width=4)
    canvas.save(path)


class CodexProposer:
    def __init__(self, transport: Transport | None = None) -> None:
        self.transport = transport or self._codex

    @staticmethod
    def prompt(state: dict[str, Any]) -> str:
        return (
            "You propose three DIFFERENT short Logo command sequences for the next part of "
            "a recognizable, humorous line drawing. Another model will choose one. "
            "Use only the goal and CURRENT canvas state below; decide the composition yourself. "
            "The attached image shows the current canvas. Commands are PENUP, PENDOWN, "
            "SETXY_x_y (integer coordinates, x=24..936, y=24..696), FORWARD_n, BACK_n "
            "(n=10,20,40,80,120), LEFT_n, RIGHT_n (n=15,30,45,90,120). "
            "Each candidate must draw at least one visible line, contain 6-30 commands, "
            "and end PENUP. Draw additions that fit what is already on the canvas. "
            "Use brief candidate labels and return only the requested JSON.\n\n"
            f"Current state: {json.dumps(state, separators=(',', ':'))}"
        )

    def propose(self, turtle: Turtle) -> list[Proposal]:
        state = drawing_state(turtle)
        with tempfile.TemporaryDirectory(prefix="pelican-proposer-") as directory:
            preview = Path(directory) / "canvas.png"
            _preview(turtle, preview)
            raw = self.transport(state, preview)
        if not isinstance(raw, dict) or not isinstance(raw.get("candidates"), list):
            raise ProposalError("proposer returned no candidate list")
        rows = raw["candidates"]
        if len(rows) != 3 or {row.get("id") for row in rows if isinstance(row, dict)} != {
            "1", "2", "3"
        }:
            raise ProposalError("proposer must return three distinct candidate IDs")
        proposals = []
        for row in rows:
            label = row.get("label")
            commands = row.get("commands")
            if not isinstance(label, str) or not 1 <= len(label) <= 120:
                raise ProposalError("proposer returned an invalid label")
            if (not isinstance(commands, list) or not 2 <= len(commands) <= 30
                    or any(not isinstance(command, str) for command in commands)):
                raise ProposalError("proposer returned an invalid command list")
            simulated = replace(turtle, segments=list(turtle.segments))
            try:
                for command in commands:
                    simulated.execute(command)
            except ValueError as error:
                raise ProposalError(f"proposer returned an invalid command: {error}") from error
            if len(simulated.segments) == len(turtle.segments):
                raise ProposalError("candidate must draw at least one line")
            if simulated.pen_down:
                raise ProposalError("candidate must end with the pen up")
            added = [
                [*segment.start, *segment.end]
                for segment in simulated.segments[len(turtle.segments):]
            ]
            proposals.append(Proposal(row["id"], label, commands, added))
        return proposals

    @staticmethod
    def _codex(state: dict[str, Any], preview: Path) -> dict[str, Any]:
        directory = preview.parent
        schema_path = directory / "schema.json"
        response_path = directory / "response.json"
        schema_path.write_text(json.dumps(SCHEMA), encoding="utf-8")
        command = [
            "codex", "exec", "--ephemeral", "--skip-git-repo-check",
            "--sandbox", "read-only", "--ignore-user-config", "-C", str(directory),
            "--output-schema", str(schema_path), "-o", str(response_path),
            "-i", str(preview), "-",
        ]
        try:
            result = subprocess.run(command, input=CodexProposer.prompt(state), text=True,
                                    capture_output=True, timeout=180, check=False)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ProposalError(f"could not run Codex proposer: {error}") from error
        if result.returncode or not response_path.exists():
            raise ProposalError(f"Codex proposer failed (exit {result.returncode})")
        try:
            return json.loads(response_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ProposalError("Codex proposer returned invalid JSON") from error
