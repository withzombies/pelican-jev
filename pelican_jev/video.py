"""Animate the exact Jev-selected Logo commands into a shareable MP4."""

from __future__ import annotations

import json
import os
import subprocess
import textwrap
from math import cos, radians, sin
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from .trace import replay_trace
from .turtle import HEIGHT, WIDTH, Point

VIDEO_WIDTH = 1280
FPS = 30
PAPER = "#f8f4ea"
NAVY = "#172a3b"
ORANGE = "#f4a563"
GREEN = "#79c963"


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default(size=size)


def _line(canvas: Image.Image, start: Point, end: Point) -> None:
    draw = ImageDraw.Draw(canvas)
    draw.line((start, end), fill=NAVY, width=4)
    for x, y in (start, end):
        draw.ellipse((x - 2, y - 2, x + 2, y + 2), fill=NAVY)


def _draw_turtle(frame: Image.Image, x: float, y: float, heading: float,
                 pen_down: bool) -> None:
    direction = (cos(radians(heading)), sin(radians(heading)))
    side = (-direction[1], direction[0])
    draw = ImageDraw.Draw(frame)
    for along in (-12, 12):
        for across in (-16, 16):
            fx = x + direction[0] * along + side[0] * across
            fy = y + direction[1] * along + side[1] * across
            draw.ellipse((fx - 6, fy - 6, fx + 6, fy + 6), fill="#4d9c55")
    draw.ellipse((x - 21, y - 21, x + 21, y + 21), fill=GREEN, outline="#24644d", width=3)
    hx, hy = x + direction[0] * 28, y + direction[1] * 28
    draw.ellipse((hx - 10, hy - 10, hx + 10, hy + 10), fill="#4d9c55")
    ex, ey = hx + side[0] * 4, hy + side[1] * 4
    draw.ellipse((ex - 2, ey - 2, ex + 2, ey + 2), fill=NAVY)
    if pen_down:
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill="#e86b3b")


def _compose(canvas: Image.Image, record: dict[str, Any] | None, step: int, total: int,
             x: float, y: float, heading: float, pen_down: bool) -> Image.Image:
    frame = Image.new("RGB", (VIDEO_WIDTH, HEIGHT), PAPER)
    frame.paste(canvas, (0, 0))
    _draw_turtle(frame, x, y, heading, pen_down)
    draw = ImageDraw.Draw(frame)
    draw.text((72, 48), "GOAL: PELICAN ON A BICYCLE", fill=NAVY, font=_font(22))
    draw.text((73, 84), "Jev directs a Logo turtle", fill="#65717a", font=_font(15))
    draw.rectangle((WIDTH, 0, VIDEO_WIDTH, HEIGHT), fill=NAVY)
    draw.text((994, 48), "LOGO / TURTLEDRAW", fill=ORANGE, font=_font(22))
    draw.text((995, 86), "JEV CHOOSES EVERY COMMAND", fill="#a8b9c7", font=_font(12))
    draw.line((994, 123, 1246, 123), fill="#476174", width=2)
    draw.text((994, 148), "CURRENT STATE", fill="#a8b9c7", font=_font(13))
    draw.text((994, 174), f"X {x:.0f}  Y {y:.0f}", fill="#ffffff", font=_font(18))
    draw.text((994, 203), f"HEADING {heading:.0f}°   PEN {'DOWN' if pen_down else 'UP'}",
              fill="#ffffff", font=_font(14))
    draw.text((994, 248), "QUESTION SENT TO JEV", fill="#a8b9c7", font=_font(13))
    question = record["question"] if record else "What Logo command should come next?"
    for index, line in enumerate(textwrap.wrap(question, width=33)[:4]):
        draw.text((994, 275 + index * 20), line, fill="#ffffff", font=_font(14))
    draw.text((994, 379), "AVAILABLE COMMANDS", fill="#a8b9c7", font=_font(13))
    options = record["options"] if record else {}
    families = ["PENUP / PENDOWN", "FORWARD / BACK", "LEFT / RIGHT", "DONE"]
    for index, label in enumerate(families):
        draw.text((994, 403 + index * 22), label, fill="#c8d5df", font=_font(13))
    draw.line((994, 506, 1246, 506), fill="#476174", width=2)
    draw.text((994, 524), "JEV RESPONSE / LOGO", fill="#a8b9c7", font=_font(13))
    choice = record["choice"] if record else "READY"
    draw.text((994, 549), choice.replace("_", " "), fill=ORANGE, font=_font(27))
    if record:
        confidence = f"{record['confidence']:.0%} confidence · {len(options)} options"
        draw.text((994, 591), confidence, fill="#ffffff", font=_font(15))
    draw.text((994, 654), f"COMMAND {step:03d} / {total:03d}", fill="#ffffff", font=_font(15))
    draw.rectangle((994, 685, 1246, 693), fill="#476174")
    if total:
        draw.rectangle((994, 685, 994 + round(252 * step / total), 693), fill=ORANGE)
    return frame


def _load_completed(path: Path) -> list[dict[str, Any]]:
    trace = json.loads(Path(path).read_text(encoding="utf-8"))
    if not trace.get("complete"):
        raise ValueError("finish the Jev trace before rendering a video")
    replay_trace(path)
    return trace["steps"]


def _pose(record: dict[str, Any], fraction: float) -> tuple[float, float, float, bool]:
    start, end = record["start"], record["end"]
    choice = record["choice"]
    x = start["x"] + (end["x"] - start["x"]) * fraction
    y = start["y"] + (end["y"] - start["y"]) * fraction
    if choice.startswith("LEFT_"):
        heading = (start["heading_degrees_clockwise"] - int(choice.split("_")[1]) * fraction) % 360
    elif choice.startswith("RIGHT_"):
        heading = (start["heading_degrees_clockwise"] + int(choice.split("_")[1]) * fraction) % 360
    else:
        heading = start["heading_degrees_clockwise"]
    pen_down = end["pen_down"] if fraction == 1 else start["pen_down"]
    return x, y, heading, pen_down


def render_final_frame(trace_path: Path) -> Image.Image:
    records = _load_completed(trace_path)
    canvas = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
    for record in records:
        if record["start"]["pen_down"] and record["choice"].startswith(("FORWARD_", "BACK_")):
            start, end = record["start"], record["end"]
            _line(canvas, (start["x"], start["y"]), (end["x"], end["y"]))
    if records:
        x, y, heading, pen_down = _pose(records[-1], 1)
        return _compose(canvas, records[-1], len(records), len(records),
                        x, y, heading, pen_down)
    return _compose(canvas, None, 0, 0, WIDTH / 2, HEIGHT / 2, 0, False)


def render_video(trace_path: Path, output_path: Path, *, frames_per_step: int = 5,
                 hold_seconds: float = 2) -> Path:
    if frames_per_step < 1 or hold_seconds < 0:
        raise ValueError("frames_per_step must be positive and hold_seconds nonnegative")
    records = _load_completed(trace_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(".tmp.mp4")
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo",
        "-pixel_format", "rgb24", "-video_size", f"{VIDEO_WIDTH}x{HEIGHT}",
        "-framerate", str(FPS), "-i", "pipe:0", "-an", "-c:v", "libx264",
        "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(temporary),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    canvas = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
    try:
        assert process.stdin is not None
        for step, record in enumerate(records, start=1):
            start, end = record["start"], record["end"]
            draws = start["pen_down"] and record["choice"].startswith(("FORWARD_", "BACK_"))
            for frame_index in range(1, frames_per_step + 1):
                fraction = frame_index / frames_per_step
                partial = canvas.copy()
                x, y, heading, pen_down = _pose(record, fraction)
                if draws:
                    _line(partial, (start["x"], start["y"]), (x, y))
                process.stdin.write(_compose(partial, record, step, len(records),
                                             x, y, heading, pen_down).tobytes())
            if draws:
                _line(canvas, (start["x"], start["y"]), (end["x"], end["y"]))
        ending = render_final_frame(trace_path)
        for _ in range(round(hold_seconds * FPS)):
            process.stdin.write(ending.tobytes())
        process.stdin.close()
        assert process.stderr is not None
        error = process.stderr.read().decode("utf-8", "replace")
        if process.wait():
            raise RuntimeError(f"FFmpeg failed: {error.strip()}")
        os.replace(temporary, output_path)
        return output_path
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        temporary.unlink(missing_ok=True)
