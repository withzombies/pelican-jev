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
        {"part": "beak", "position": [2, 3]},
        {"left": "left turn", "right": "right turn"},
        instructions="Which move draws the beak?",
    )
    assert decision.choice == "right"
    assert decision.confidence == 0.82
    assert decision.probabilities == {"left": 0.1, "right": 0.9}
    assert requests == [
        {
            "state": {"part": "beak", "position": [2, 3]},
            "model": "jev-latest",
            "questions": {
                "move": {
                    "type": "choice",
                    "instructions": "Which move draws the beak?",
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


def test_live_drawing_offers_two_distinct_guided_moves(tmp_path) -> None:
    requests = []

    def transport(payload):
        requests.append(payload)
        raise PermanentJevError("stop after first request")

    with pytest.raises(PermanentJevError):
        generate_trace(JevClient(transport=transport), tmp_path / "decisions.json")
    criteria = requests[0]["questions"]["move"]["criteria"]
    assert set(criteria) == {"left", "right"}
    assert criteria["left"] != criteria["right"]


def test_jev_sees_the_goal_and_current_turtle_state_without_feature_hints(tmp_path) -> None:
    requests = []

    def transport(payload):
        requests.append(payload)
        if len(requests) == 3:
            raise PermanentJevError("stop after two moves")
        return {"answers": {"move": {"type": "choice", "choice": "right", "confidence": 0.7}}}

    with pytest.raises(PermanentJevError):
        generate_trace(JevClient(transport=transport), tmp_path / "decisions.json")
    first = requests[0]
    second = requests[1]
    assert first["state"]["goal"] == "Draw a pelican on a bicycle with a Logo turtle"
    assert set(first["state"]) == {"goal", "step", "turtle", "recent_moves", "drawing_so_far"}
    assert first["state"]["turtle"]["pen_down"] is True
    assert first["state"]["recent_moves"] == []
    assert first["state"]["drawing_so_far"] == []
    assert len(second["state"]["recent_moves"]) == 1
    assert len(second["state"]["drawing_so_far"]) == 1
    assert second["state"]["turtle"]["x"] != first["state"]["turtle"]["x"]
    assert first["questions"]["move"]["instructions"] == (
        "Which turtle move should come next to draw a pelican on a bicycle?"
    )


def test_trace_captures_each_question_and_jev_response(tmp_path) -> None:
    path = tmp_path / "decisions.json"
    requests = []
    response = {
        "answers": {
            "move": {
                "type": "choice",
                "choice": "right",
                "confidence": 0.73,
                "probabilities": {"left": 0.2, "right": 0.8},
            }
        }
    }
    def transport(payload):
        requests.append(payload)
        return response

    trace = generate_trace(JevClient(transport=transport), path)
    first = trace["steps"][0]
    assert first["question"] == "Which turtle move should come next to draw a pelican on a bicycle?"
    assert first["question"] == requests[0]["questions"]["move"]["instructions"]
    assert set(first["options"]) == {"left", "right"}
    assert first["options"] == requests[0]["questions"]["move"]["criteria"]
    assert set(first["option_moves"]) == {"left", "right"}
    assert first["option_moves"]["left"]["end"] != first["option_moves"]["right"]["end"]
    assert first["choice"] == "right"
    assert first["confidence"] == 0.73
    assert first["probabilities"] == {"left": 0.2, "right": 0.8}


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
                "answers": {"move": {"type": "choice", "choice": "left", "confidence": 0.8}}
            }
        ),
        path,
    )
    trace["steps"][0]["end"] = [9999, 9999]
    path.write_text(json.dumps(trace))
    with pytest.raises(ValueError, match="does not match"):
        replay_trace(path)
