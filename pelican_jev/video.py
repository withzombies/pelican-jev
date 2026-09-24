"""Render recorded turtle strokes and Jev decisions into an H.264 video."""

from __future__ import annotations

import json
import os
import subprocess
import textwrap
from math import atan2, cos, degrees, radians, sin
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from .guide import Point
from .trace import replay_trace
from .turtle import Segment

WIDTH = 1280
HEIGHT = 720
CANVAS_WIDTH = 960
FPS = 30
PEN_UP_FRAMES = 8
PAPER = "#f8f4ea"
NAVY = "#172a3b"
ORANGE = "#f4a563"
TURTLE_GREEN = "#79c963"


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default(size=size)


def _draw_segment(image: Image.Image, segment: Segment, fraction: float = 1) -> None:
    end = (
        segment.start[0] + (segment.end[0] - segment.start[0]) * fraction,
        segment.start[1] + (segment.end[1] - segment.start[1]) * fraction,
    )
    radius = segment.width / 2
    draw = ImageDraw.Draw(image)
    draw.line((segment.start, end), fill=segment.color, width=segment.width)
    for point in (segment.start, end):
        draw.ellipse(
            (point[0] - radius, point[1] - radius, point[0] + radius, point[1] + radius),
            fill=segment.color,
        )


def _draw_turtle(image: Image.Image, position: Point, heading: float, pen_down: bool) -> None:
    """Keep a small turtle visibly attached to the moving pen tip."""
    x, y = position
    angle = radians(heading)
    forward = (cos(angle), sin(angle))
    side = (-forward[1], forward[0])
    draw = ImageDraw.Draw(image)
    for length in (-8, 8):
        for across in (-11, 11):
            foot = (x + forward[0] * length + side[0] * across,
                    y + forward[1] * length + side[1] * across)
            draw.ellipse((foot[0] - 4, foot[1] - 4, foot[0] + 4, foot[1] + 4), fill="#4d9c55")
    draw.ellipse((x - 14, y - 14, x + 14, y + 14), fill=TURTLE_GREEN, outline="#24644d", width=3)
    head = (x + forward[0] * 19, y + forward[1] * 19)
    draw.ellipse((head[0] - 7, head[1] - 7, head[0] + 7, head[1] + 7), fill="#4d9c55")
    eye = (head[0] + side[0] * 3, head[1] + side[1] * 3)
    draw.ellipse((eye[0] - 2, eye[1] - 2, eye[0] + 2, eye[1] + 2), fill=NAVY)
    if pen_down:
        pen = (x - side[0] * 10, y - side[1] * 10)
        draw.ellipse((pen[0] - 3, pen[1] - 3, pen[0] + 3, pen[1] + 3), fill="#e86b3b")


def _compose(
    canvas: Image.Image,
    record: dict[str, Any] | None,
    step: int,
    total: int,
    turtle_position: Point,
    turtle_heading: float,
    pen_down: bool,
) -> Image.Image:
    frame = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
    frame.paste(canvas, (0, 0))
    _draw_turtle(frame, turtle_position, turtle_heading, pen_down)
    draw = ImageDraw.Draw(frame)
    draw.text((72, 48), "A PELICAN ON A BICYCLE", fill=NAVY, font=_font(22))
    draw.text((73, 84), "drawn one turtle move at a time", fill="#65717a", font=_font(15))
    draw.rectangle((CANVAS_WIDTH, 0, WIDTH, HEIGHT), fill=NAVY)
    draw.text((994, 48), "LOGO / TURTLEDRAW", fill=ORANGE, font=_font(22))
    draw.text((995, 86), "JEV CHOOSES EACH STROKE", fill="#a8b9c7", font=_font(12))
    draw.line((994, 123, 1246, 123), fill="#476174", width=2)
    draw.text((994, 147), "DRAWING", fill="#a8b9c7", font=_font(13))
    part = record["part"].replace("_", " ").upper() if record else "READY"
    draw.text((994, 173), part, fill="#ffffff", font=_font(23))
    if pen_down:
        draw.text((994, 228), "QUESTION SENT TO JEV", fill="#a8b9c7", font=_font(13))
        question = record.get("question", "Which guided turtle move draws this part next?")
        option_moves = record.get("option_moves", {})
    else:
        draw.text((994, 228), "PEN-UP TRANSIT", fill="#a8b9c7", font=_font(13))
        question = "The turtle moves to the next path without drawing a line."
        option_moves = {}
    for line_index, line in enumerate(textwrap.wrap(question, width=33)[:4]):
        draw.text((994, 254 + line_index * 19), line, fill="#ffffff", font=_font(14))
    draw.text((994, 345), "OPTIONS", fill="#a8b9c7", font=_font(13))
    if option_moves:
        for index, name in enumerate(("left", "right")):
            option = option_moves[name]
            label = (
                f"{name.upper():5}  TURN {option['turn_degrees']:+.1f}°  "
                f"FD {option['forward_pixels']:.1f}"
            )
            draw.text((994, 369 + index * 25), label, fill="#c8d5df", font=_font(13))
    else:
        draw.text((994, 369), "LEFT  /  RIGHT", fill="#c8d5df", font=_font(13))
    draw.line((994, 414, 1246, 414), fill="#476174", width=2)
    draw.text((994, 432), "JEV RESPONSE", fill="#a8b9c7", font=_font(13))
    choice = record["choice"].upper() if pen_down and record else "TRAVEL"
    draw.text((994, 453), choice, fill=ORANGE, font=_font(31))
    if pen_down:
        confidence = f"{record['confidence']:.0%} confidence"
        probabilities = record.get("probabilities", {})
        left = probabilities.get("left")
        right = probabilities.get("right")
        distribution = (
            f"P(LEFT) {left:.0%}  /  P(RIGHT) {right:.0%}"
            if left is not None and right is not None else "Probability details unavailable"
        )
    else:
        confidence = "Pen lifted"
        distribution = "Travel is not a Jev choice"
    draw.text((994, 497), confidence, fill="#ffffff", font=_font(17))
    draw.text((994, 526), distribution, fill="#c8d5df", font=_font(13))
    draw.text((994, 573), "LOGO COMMANDS", fill="#a8b9c7", font=_font(13))
    if pen_down:
        turn = record["turn_degrees"]
        turn_command = "RIGHT" if turn >= 0 else "LEFT"
        commands = (
            f"PENDOWN / {turn_command} {abs(turn):.1f}°",
            f"FORWARD {record['forward_pixels']:.1f}",
        )
    else:
        commands = ("PENUP", "MOVE TO NEXT PATH")
    for index, command in enumerate(commands):
        draw.text((994, 596 + index * 23), command, fill=TURTLE_GREEN, font=_font(16))
    draw.text((994, 652), f"STEP  {step:03d} / {total:03d}", fill="#ffffff", font=_font(15))
    draw.rectangle((994, 685, 1246, 693), fill="#476174")
    if total:
        draw.rectangle((994, 685, 994 + round(252 * step / total), 693), fill=ORANGE)
    return frame


def _load_completed(path: Path) -> tuple[list[dict[str, Any]], list[Segment]]:
    path = Path(path)
    trace = json.loads(path.read_text(encoding="utf-8"))
    if not trace.get("complete"):
        raise ValueError("finish the Jev trace before rendering a video")
    turtle = replay_trace(path)
    return trace["steps"], turtle.segments


def render_final_frame(trace_path: Path) -> Image.Image:
    records, segments = _load_completed(trace_path)
    canvas = Image.new("RGB", (CANVAS_WIDTH, HEIGHT), PAPER)
    for segment in segments:
        _draw_segment(canvas, segment)
    last = segments[-1]
    heading = degrees(atan2(last.end[1] - last.start[1], last.end[0] - last.start[0]))
    return _compose(canvas, records[-1], len(records), len(records), last.end, heading, True)


def render_video(
    trace_path: Path,
    output_path: Path,
    *,
    frames_per_step: int = 5,
    hold_seconds: float = 2,
) -> Path:
    if frames_per_step < 1 or hold_seconds < 0:
        raise ValueError("frames_per_step must be positive and hold_seconds nonnegative")
    records, segments = _load_completed(trace_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(".tmp.mp4")
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-pixel_format", "rgb24", "-video_size", f"{WIDTH}x{HEIGHT}",
        "-framerate", str(FPS), "-i", "pipe:0", "-an", "-c:v", "libx264",
        "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(temporary),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    canvas = Image.new("RGB", (CANVAS_WIDTH, HEIGHT), PAPER)
    try:
        assert process.stdin is not None
        previous_end: Point | None = None
        previous_stroke = -1
        for step, (record, segment) in enumerate(zip(records, segments, strict=True), start=1):
            if previous_end is not None and record["stroke_index"] != previous_stroke:
                travel_heading = degrees(
                    atan2(segment.start[1] - previous_end[1], segment.start[0] - previous_end[0])
                )
                for frame_index in range(1, PEN_UP_FRAMES + 1):
                    fraction = frame_index / PEN_UP_FRAMES
                    travel_position = (
                        previous_end[0] + (segment.start[0] - previous_end[0]) * fraction,
                        previous_end[1] + (segment.start[1] - previous_end[1]) * fraction,
                    )
                    process.stdin.write(
                        _compose(
                            canvas, record, step - 1, len(records),
                            travel_position, travel_heading, False,
                        ).tobytes()
                    )
            heading = degrees(
                atan2(segment.end[1] - segment.start[1], segment.end[0] - segment.start[0])
            )
            for frame_index in range(1, frames_per_step + 1):
                fraction = frame_index / frames_per_step
                partial = canvas.copy()
                _draw_segment(partial, segment, fraction)
                position = (
                    segment.start[0] + (segment.end[0] - segment.start[0]) * fraction,
                    segment.start[1] + (segment.end[1] - segment.start[1]) * fraction,
                )
                process.stdin.write(
                    _compose(partial, record, step, len(records), position, heading, True).tobytes()
                )
            _draw_segment(canvas, segment)
            previous_end = segment.end
            previous_stroke = record["stroke_index"]
        last = segments[-1]
        ending = _compose(canvas, records[-1], len(records), len(records), last.end, heading, True)
        for _ in range(round(hold_seconds * FPS)):
            process.stdin.write(ending.tobytes())
        process.stdin.close()
        assert process.stderr is not None
        error = process.stderr.read().decode("utf-8", "replace")
        result = process.wait()
        if result:
            raise RuntimeError(f"FFmpeg failed: {error.strip()}")
        os.replace(temporary, output_path)
        return output_path
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        temporary.unlink(missing_ok=True)
