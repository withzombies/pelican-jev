from __future__ import annotations

import json
import subprocess
import sys

import pytest

from pelican_jev.jev import InvalidJevResponse, JevClient, PermanentJevError, TemporaryJevError
from pelican_jev.trace import generate_trace, replay_trace
from pelican_jev.turtle import Turtle, available_commands
from pelican_jev.video import render_final_frame


def response(choice: str) -> dict:
    return {"answers": {"move": {"type": "choice", "choice": choice, "confidence": 0.8}}}


def test_jev_client_retries_transient_failure() -> None:
    calls = 0
    delays = []

    def transport(_payload):
        nonlocal calls
        calls += 1
        if calls < 3:
            raise TemporaryJevError("busy")
        return response("PENDOWN")

    decision = JevClient(transport=transport, sleep=delays.append).choose(
        {}, {"PENDOWN": "Lower the pen"}
    )
    assert decision.choice == "PENDOWN"
    assert calls == 3
    assert delays == [0.5, 1.0]


def test_jev_client_rejects_unoffered_command() -> None:
    client = JevClient(transport=lambda _: response("TELEPORT"))
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


def test_commands_are_generic_and_bounded() -> None:
    commands = available_commands(Turtle())
    assert {"PENUP", "PENDOWN", "FORWARD_40", "BACK_20", "LEFT_90", "RIGHT_90"} <= set(commands)
    forbidden = ("wheel", "spoke", "beak", "frame", "pouch")
    assert all(term not in json.dumps(commands).lower() for term in forbidden)


def test_jev_receives_only_goal_state_and_generic_commands(tmp_path) -> None:
    requests = []

    def transport(payload):
        requests.append(payload)
        if len(requests) == 4:
            raise PermanentJevError("stop")
        return response(["PENDOWN", "FORWARD_40", "PENUP"][len(requests) - 1])

    path = tmp_path / "trace.json"
    with pytest.raises(PermanentJevError):
        generate_trace(JevClient(transport=transport), path, max_steps=8)
    assert len(requests) == 4
    assert all(
        set(request["state"]) == {"goal", "canvas", "turtle", "drawing_so_far"}
        for request in requests
    )
    assert requests[0]["state"]["drawing_so_far"] == []
    assert requests[0]["state"]["turtle"]["pen_down"] is False
    assert requests[1]["state"]["turtle"]["pen_down"] is True
    assert len(requests[2]["state"]["drawing_so_far"]) == 1
    sent = json.dumps(requests).lower()
    assert "pelican on a bicycle" in sent
    forbidden = ("wheel", "spoke", "beak", "pouch", "guide", "waypoint")
    assert all(term not in sent for term in forbidden)
    assert [step["choice"] for step in json.loads(path.read_text())["steps"]] == [
        "PENDOWN", "FORWARD_40", "PENUP"
    ]


def test_trace_replays_exact_jev_commands_and_rejects_tampering(tmp_path) -> None:
    sequence = iter(["PENDOWN", "FORWARD_40", "RIGHT_90", "FORWARD_40", "PENUP", "DONE"])
    path = tmp_path / "trace.json"
    trace = generate_trace(
        JevClient(transport=lambda _: response(next(sequence))), path, max_steps=10
    )
    assert trace["complete"] is True
    assert [s["choice"] for s in trace["steps"]] == [
        "PENDOWN", "FORWARD_40", "RIGHT_90", "FORWARD_40", "PENUP", "DONE"
    ]
    assert len(replay_trace(path).segments) == 2
    assert render_final_frame(path).size == (1280, 720)
    trace["steps"][1]["end"] = [9999, 9999]
    path.write_text(json.dumps(trace))
    with pytest.raises(ValueError, match="does not match"):
        replay_trace(path)


def test_resume_and_mp4(tmp_path) -> None:
    path = tmp_path / "trace.json"
    calls = 0

    def interrupted(_):
        nonlocal calls
        calls += 1
        if calls == 3:
            raise PermanentJevError("stop")
        return response(["PENDOWN", "FORWARD_40"][calls - 1])

    with pytest.raises(PermanentJevError):
        generate_trace(JevClient(transport=interrupted), path, max_steps=5)
    sequence = iter(["RIGHT_90", "FORWARD_40", "DONE"])
    generate_trace(
        JevClient(transport=lambda _: response(next(sequence))), path, max_steps=5, resume=True
    )
    output = tmp_path / "video.mp4"
    subprocess.run(
        [sys.executable, "-m", "pelican_jev", "replay", "--trace", str(path),
         "--output", str(output), "--frames-per-step", "1", "--hold-seconds", "0"],
        check=True, capture_output=True, text=True,
    )
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=codec_name,width,height", "-of", "json", str(output)],
        check=True, capture_output=True, text=True,
    )
    assert json.loads(probe.stdout)["streams"][0] == {
        "codec_name": "h264", "width": 1280, "height": 720
    }
