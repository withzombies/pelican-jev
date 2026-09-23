"""Render recorded turtle strokes and Jev decisions into an H.264 video."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from .trace import replay_trace
from .turtle import Segment

WIDTH = 1280
HEIGHT = 720
CANVAS_WIDTH = 960
FPS = 30
PAPER = "#f8f4ea"
NAVY = "#172a3b"
ORANGE = "#f4a563"


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


def _compose(
    canvas: Image.Image, record: dict[str, Any] | None, step: int, total: int
) -> Image.Image:
    frame = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
    frame.paste(canvas, (0, 0))
    draw = ImageDraw.Draw(frame)
    draw.text((72, 48), "A PELICAN ON A BICYCLE", fill=NAVY, font=_font(22))
    draw.text((73, 84), "drawn one turtle move at a time", fill="#65717a", font=_font(15))
    draw.rectangle((CANVAS_WIDTH, 0, WIDTH, HEIGHT), fill=NAVY)
    draw.text((994, 48), "JEV  /  TURTLE", fill=ORANGE, font=_font(24))
    draw.text((995, 86), "LIVE DECISION TRACE", fill="#a8b9c7", font=_font(13))
    draw.line((994, 123, 1246, 123), fill="#476174", width=2)
    draw.text((994, 157), "DRAWING", fill="#a8b9c7", font=_font(14))
    part = record["part"].replace("_", " ").upper() if record else "READY"
    draw.text((994, 188), part, fill="#ffffff", font=_font(24))
    draw.text((994, 260), "MOVE", fill="#a8b9c7", font=_font(14))
    choice = record["choice"].upper() if record else "—"
    draw.text((994, 289), choice, fill=ORANGE, font=_font(37))
    confidence = f"{record['confidence']:.0%}" if record else "—"
    draw.text((994, 374), "JEV CONFIDENCE", fill="#a8b9c7", font=_font(14))
    draw.text((994, 402), confidence, fill="#ffffff", font=_font(29))
    if record:
        draw.text(
            (994, 460),
            f"TURN  {record['turn_degrees']:+.1f}°",
            fill="#c8d5df",
            font=_font(17),
        )
        draw.text(
            (994, 490),
            f"FORWARD  {record['forward_pixels']:.1f} px",
            fill="#c8d5df",
            font=_font(17),
        )
    draw.text((994, 583), f"STEP  {step:03d} / {total:03d}", fill="#ffffff", font=_font(16))
    draw.rectangle((994, 618, 1246, 626), fill="#476174")
    if total:
        draw.rectangle((994, 618, 994 + round(252 * step / total), 626), fill=ORANGE)
    draw.text((994, 656), "TypeSafe AI  /  Logo turtle", fill="#a8b9c7", font=_font(13))
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
    return _compose(canvas, records[-1] if records else None, len(records), len(records))


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
        for step, (record, segment) in enumerate(zip(records, segments, strict=True), start=1):
            for frame_index in range(1, frames_per_step + 1):
                partial = canvas.copy()
                _draw_segment(partial, segment, frame_index / frames_per_step)
                process.stdin.write(_compose(partial, record, step, len(records)).tobytes())
            _draw_segment(canvas, segment)
        ending = _compose(canvas, records[-1] if records else None, len(records), len(records))
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
