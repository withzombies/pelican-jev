from __future__ import annotations

import json

import pytest
from PIL import Image

from pelican_jev.proposer import CodexProposer, ProposalError
from pelican_jev.turtle import Turtle


def candidates():
    return {"candidates": [
        {"id": "1", "label": "first sketch", "commands": [
            "SETXY_200_200", "PENDOWN", "SETXY_250_200", "PENUP"
        ]},
        {"id": "2", "label": "second sketch", "commands": [
            "SETXY_300_300", "PENDOWN", "SETXY_350_300", "PENUP"
        ]},
        {"id": "3", "label": "third sketch", "commands": [
            "SETXY_400_400", "PENDOWN", "SETXY_450_400", "PENUP"
        ]},
    ]}


def test_proposer_sees_current_canvas_and_returns_valid_logo_batches() -> None:
    captured = {}

    def transport(state, preview):
        captured["state"] = state
        captured["preview"] = Image.open(preview).copy()
        return candidates()

    proposals = CodexProposer(transport=transport).propose(Turtle())
    assert len(proposals) == 3
    assert proposals[0].commands[1] == "PENDOWN"
    assert proposals[0].added_segments == [[200, 200, 250, 200]]
    assert captured["state"]["goal"] == "Draw a humorous pelican on a bicycle"
    assert set(captured["state"]) == {"goal", "canvas", "turtle", "drawing_so_far"}
    assert captured["preview"].size == (960, 720)
    prompt = CodexProposer.prompt(captured["state"])
    assert all(word not in prompt.lower() for word in ("wheel", "spoke", "beak", "pouch"))


def test_proposer_rejects_invalid_or_empty_candidate() -> None:
    bad = candidates()
    bad["candidates"][1]["commands"] = ["SETXY_9999_300", "PENDOWN"]
    with pytest.raises(ProposalError, match="invalid"):
        CodexProposer(transport=lambda _state, _preview: bad).propose(Turtle())
    empty = candidates()
    empty["candidates"][2]["commands"] = ["PENUP", "SETXY_450_400"]
    with pytest.raises(ProposalError, match="draw"):
        CodexProposer(transport=lambda _state, _preview: empty).propose(Turtle())


def test_proposer_never_sends_previous_attempts() -> None:
    seen = []

    def transport(state, _preview):
        seen.append(json.dumps(state))
        return candidates()

    turtle = Turtle()
    CodexProposer(transport=transport).propose(turtle)
    turtle.execute("PENDOWN")
    turtle.execute("SETXY_600_400")
    turtle.execute("PENUP")
    CodexProposer(transport=transport).propose(turtle)
    assert "previous" not in " ".join(seen).lower()
    assert "SETXY" not in " ".join(seen)
    assert len(json.loads(seen[1])["drawing_so_far"]) == 1
