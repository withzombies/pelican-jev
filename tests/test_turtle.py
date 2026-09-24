from __future__ import annotations

import json

import pytest

from pelican_jev.jev import InvalidJevResponse, JevClient, TemporaryJevError
from pelican_jev.turtle import Turtle, available_commands


def _response(choice: str) -> dict:
    return {"answers": {"move": {"type": "choice", "choice": choice, "confidence": 0.8}}}


def test_jev_client_retries_transient_failure() -> None:
    calls = 0
    delays = []

    def transport(_payload):
        nonlocal calls
        calls += 1
        if calls < 3:
            raise TemporaryJevError("busy")
        return _response("PENDOWN")

    decision = JevClient(transport=transport, sleep=delays.append).choose(
        {}, {"PENDOWN": "Lower the pen"}
    )
    assert decision.choice == "PENDOWN"
    assert calls == 3
    assert delays == [0.5, 1.0]


def test_jev_client_rejects_unoffered_choice() -> None:
    client = JevClient(transport=lambda _: _response("TELEPORT"))
    with pytest.raises(InvalidJevResponse, match="unoffered"):
        client.choose({}, {"PENDOWN": "Lower the pen"})


def test_turtle_executes_pen_and_motion_commands() -> None:
    turtle = Turtle()
    start = (turtle.x, turtle.y)
    turtle.execute("FORWARD_40")
    assert turtle.segments == []
    turtle.execute("PENDOWN")
    turtle.execute("RIGHT_90")
    turtle.execute("FORWARD_40")
    assert len(turtle.segments) == 1
    assert turtle.segments[0].start == (start[0] + 40, start[1])
    turtle.execute("PENUP")
    turtle.execute("BACK_20")
    assert len(turtle.segments) == 1


def test_turtle_setxy_draws_only_with_pen_down_and_rejects_off_canvas() -> None:
    turtle = Turtle()
    turtle.execute("SETXY_300_300")
    assert turtle.segments == []
    turtle.execute("PENDOWN")
    turtle.execute("SETXY_320_330")
    assert turtle.segments[-1].start == (300, 300)
    assert turtle.segments[-1].end == (320, 330)
    with pytest.raises(ValueError, match="unavailable"):
        turtle.execute("SETXY_9999_300")


def test_commands_are_generic_and_bounded() -> None:
    commands = available_commands(Turtle())
    assert {"PENUP", "PENDOWN", "FORWARD_40", "BACK_20", "LEFT_90", "RIGHT_90"} <= set(commands)
    forbidden = ("wheel", "spoke", "beak", "frame", "pouch")
    assert all(term not in json.dumps(commands).lower() for term in forbidden)
