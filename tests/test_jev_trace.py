from __future__ import annotations

import json

import pytest

from pelican_jev.jev import InvalidJevResponse, JevClient, PermanentJevError, TemporaryJevError
from pelican_jev.trace import generate_trace, replay_trace


def test_jev_client_sends_one_choice_question() -> None:
    requests = []

    def transport(payload):
        requests.append(payload)
        return {
            "model": "jev-1.13.0",
            "answers": {
                "move": {
                    "type": "choice",
                    "choice": "right",
                    "confidence": 0.82,
                    "probabilities": {"left": 0.1, "right": 0.9},
                }
            },
        }

    decision = JevClient(transport=transport).choose(
        {"part": "beak", "position": [2, 3]}, {"left": "left turn", "right": "right turn"}
    )
    assert decision.choice == "right"
    assert decision.confidence == 0.82
    assert requests == [
        {
            "state": {"part": "beak", "position": [2, 3]},
            "model": "jev-latest",
            "questions": {
                "move": {
                    "type": "choice",
                    "instructions": (
                        "Choose the next Logo turtle move that keeps the current part smooth "
                        "and recognizable. Favor a natural contour and vary choices when useful."
                    ),
                    "criteria": {"left": "left turn", "right": "right turn"},
                }
            },
        }
    ]


def test_jev_client_retries_transient_failure() -> None:
    calls = 0
    delays = []

    def transport(_payload):
        nonlocal calls
        calls += 1
        if calls < 3:
            raise TemporaryJevError("busy")
        return {"answers": {"move": {"type": "choice", "choice": "center", "confidence": 0.7}}}

    decision = JevClient(transport=transport, sleep=delays.append).choose({}, {"center": "center"})
    assert decision.choice == "center"
    assert calls == 3
    assert delays == [0.5, 1.0]


def test_jev_client_rejects_unoffered_choice() -> None:
    response = {"answers": {"move": {"type": "choice", "choice": "teleport", "confidence": 1}}}
    client = JevClient(transport=lambda _: response)
    with pytest.raises(InvalidJevResponse, match="unoffered"):
        client.choose({}, {"left": "left"})


def test_trace_can_resume_and_replay_without_an_api_call(tmp_path) -> None:
    trace_path = tmp_path / "decisions.json"
    calls = 0

    def interrupted_transport(_payload):
        nonlocal calls
        calls += 1
        if calls == 4:
            raise PermanentJevError("stop")
        return {"answers": {"move": {"type": "choice", "choice": "left", "confidence": 0.9}}}

    with pytest.raises(PermanentJevError):
        generate_trace(JevClient(transport=interrupted_transport), trace_path)
    partial = json.loads(trace_path.read_text())
    assert len(partial["steps"]) == 3
    assert partial["complete"] is False

    resumed_calls = 0

    def resumed_transport(_payload):
        nonlocal resumed_calls
        resumed_calls += 1
        return {"answers": {"move": {"type": "choice", "choice": "right", "confidence": 0.6}}}

    complete = generate_trace(JevClient(transport=resumed_transport), trace_path, resume=True)
    assert complete["complete"] is True
    assert complete["steps"][:3] == partial["steps"]
    assert resumed_calls == len(complete["steps"]) - 3
    turtle = replay_trace(trace_path)
    assert len(turtle.segments) == len(complete["steps"])
    assert "TYPESAFE_API_KEY" not in trace_path.read_text()


def test_trace_rejects_changed_move(tmp_path) -> None:
    path = tmp_path / "decisions.json"
    trace = generate_trace(
        JevClient(
            transport=lambda _: {
                "answers": {"move": {"type": "choice", "choice": "center", "confidence": 0.8}}
            }
        ),
        path,
    )
    trace["steps"][0]["end"] = [9999, 9999]
    path.write_text(json.dumps(trace))
    with pytest.raises(ValueError, match="does not match"):
        replay_trace(path)
