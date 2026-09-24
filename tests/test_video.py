from __future__ import annotations

import json
import os
import subprocess
import sys

from PIL import ImageChops

from pelican_jev.jev import JevClient
from pelican_jev.trace import generate_trace
from pelican_jev.video import render_final_frame


def _trace_for_choice(tmp_path, choice):
    path = tmp_path / f"{choice}.json"
    response = {"answers": {"move": {"type": "choice", "choice": choice, "confidence": 0.75}}}
    generate_trace(JevClient(transport=lambda _: response), path)
    return path


def test_final_frame_reflects_jev_choices(tmp_path) -> None:
    left = render_final_frame(_trace_for_choice(tmp_path, "left"))
    right = render_final_frame(_trace_for_choice(tmp_path, "right"))
    assert left.size == (1280, 720)
    assert ImageChops.difference(left, right).getbbox() is not None


def test_final_frame_has_a_visible_turtle_at_the_last_position(tmp_path) -> None:
    trace = _trace_for_choice(tmp_path, "left")
    last_end = json.loads(trace.read_text())["steps"][-1]["end"]
    frame = render_final_frame(trace)
    red, green, blue = frame.getpixel((round(last_end[0]), round(last_end[1])))
    assert green > red * 1.2
    assert green > blue * 1.2


def test_replay_cli_writes_h264_mp4_without_a_key(tmp_path) -> None:
    trace = _trace_for_choice(tmp_path, "left")
    output = tmp_path / "pelican_on_bicycle.mp4"
    env = dict(os.environ)
    env.pop("TYPESAFE_API_KEY", None)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pelican_jev",
            "replay",
            "--trace",
            str(trace),
            "--output",
            str(output),
            "--frames-per-step",
            "1",
            "--hold-seconds",
            "0",
        ],
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=codec_name,width,height,r_frame_rate,nb_frames",
            "-of",
            "json",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    stream = json.loads(probe.stdout)["streams"][0]
    assert stream["codec_name"] == "h264"
    assert (stream["width"], stream["height"], stream["r_frame_rate"]) == (1280, 720, "30/1")
    assert int(stream["nb_frames"]) > len(json.loads(trace.read_text())["steps"])
    assert output.stat().st_size > 0
