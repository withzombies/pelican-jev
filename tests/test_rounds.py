from __future__ import annotations

import json
import subprocess
import sys

import pytest

from pelican_jev.jev import JevClient, PermanentJevError
from pelican_jev.proposer import CodexProposer
from pelican_jev.trace import generate_trace, replay_trace
from pelican_jev.video import render_final_frame


def _candidates(_state, _preview):
    return {"candidates": [
        {"id": "1", "label": "first", "commands": [
            "PENUP", "SETXY_200_200", "PENDOWN", "SETXY_250_200", "PENUP"
        ]},
        {"id": "2", "label": "second", "commands": [
            "PENUP", "SETXY_300_300", "PENDOWN", "SETXY_350_320", "PENUP"
        ]},
        {"id": "3", "label": "third", "commands": [
            "PENUP", "SETXY_400_400", "PENDOWN", "SETXY_450_440", "PENUP"
        ]},
    ]}


def _response(choice):
    return {"answers": {"move": {"type": "choice", "choice": choice, "confidence": 0.8}}}


def test_jev_selects_a_proposed_logo_batch_and_trace_replays_it(tmp_path) -> None:
    requests = []

    def transport(payload):
        requests.append(payload)
        return _response("2")

    path = tmp_path / "trace.json"
    trace = generate_trace(
        JevClient(transport=transport), path,
        proposer=CodexProposer(transport=_candidates), max_rounds=1,
    )
    assert trace["complete"] is True
    assert trace["rounds"][0]["choice"] == "2"
    assert [step["choice"] for step in trace["steps"]] == _candidates(None, None)[
        "candidates"
    ][1]["commands"]
    assert len(replay_trace(path).segments) == 1
    assert replay_trace(path).segments[0].end == (350, 320)
    assert render_final_frame(path).size == (1280, 720)
    assert set(requests[0]["questions"]["move"]["criteria"]) == {"1", "2", "3"}
    assert set(requests[0]["state"]) == {"goal", "canvas", "turtle", "drawing_so_far"}
    assert requests[0]["state"]["drawing_so_far"] == []


def test_round_trace_resumes_without_repeating_accepted_strokes(tmp_path) -> None:
    path = tmp_path / "trace.json"
    calls = 0

    def interrupted(_payload):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise PermanentJevError("stop")
        return _response("1")

    with pytest.raises(PermanentJevError):
        generate_trace(
            JevClient(transport=interrupted), path,
            proposer=CodexProposer(transport=_candidates), max_rounds=2,
        )
    partial = json.loads(path.read_text())
    assert len(partial["rounds"]) == 1
    resumed = generate_trace(
        JevClient(transport=lambda _payload: _response("3")), path,
        proposer=CodexProposer(transport=_candidates), max_rounds=2, resume=True,
    )
    assert len(resumed["rounds"]) == 2
    assert resumed["rounds"][0] == partial["rounds"][0]
    assert len(replay_trace(path).segments) == 2


def test_completed_trace_can_be_extended_with_more_jev_rounds(tmp_path) -> None:
    path = tmp_path / "trace.json"
    first = generate_trace(
        JevClient(transport=lambda _payload: _response("1")), path,
        proposer=CodexProposer(transport=_candidates), max_rounds=1,
    )
    extended = generate_trace(
        JevClient(transport=lambda _payload: _response("2")), path,
        proposer=CodexProposer(transport=_candidates), max_rounds=2, resume=True,
    )
    assert extended["complete"] is True
    assert len(extended["rounds"]) == 2
    assert extended["rounds"][0] == first["rounds"][0]


def test_trace_rejects_command_outside_jev_selected_batch(tmp_path) -> None:
    path = tmp_path / "trace.json"
    trace = generate_trace(
        JevClient(transport=lambda _payload: _response("1")), path,
        proposer=CodexProposer(transport=_candidates), max_rounds=1,
    )
    trace["steps"][3]["choice"] = "SETXY_600_600"
    path.write_text(json.dumps(trace))
    with pytest.raises(ValueError, match="selected proposal"):
        replay_trace(path)


def test_replay_cli_writes_h264_video_from_selected_stroke(tmp_path) -> None:
    path = tmp_path / "trace.json"
    generate_trace(
        JevClient(transport=lambda _payload: _response("2")), path,
        proposer=CodexProposer(transport=_candidates), max_rounds=1,
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
