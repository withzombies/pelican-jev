"""Command-line entry point for live drawing and offline replay."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .jev import JevClient, JevError
from .trace import generate_trace
from .video import render_video


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Jev draws a pelican riding a bicycle")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("draw", "replay"):
        command = commands.add_parser(name)
        command.add_argument("--trace", type=Path, default=Path("output/decisions.json"))
        command.add_argument("--output", type=Path, default=Path("output/pelican_on_bicycle.mp4"))
        command.add_argument("--frames-per-step", type=int, default=5)
        command.add_argument("--hold-seconds", type=float, default=2)
        if name == "draw":
            command.add_argument("--resume", action="store_true")
            command.add_argument("--max-steps", type=int, default=180)
    options = parser.parse_args(argv)
    try:
        if options.command == "draw":
            def progress(step: int, total: int, choice: str) -> None:
                if step == 1 or step % 10 == 0 or step == total:
                    print(f"Jev command {step}/{total}: {choice}", flush=True)

            generate_trace(JevClient(), options.trace, resume=options.resume,
                           max_steps=options.max_steps, on_progress=progress)
        output = render_video(
            options.trace,
            options.output,
            frames_per_step=options.frames_per_step,
            hold_seconds=options.hold_seconds,
        )
    except (JevError, ValueError, FileNotFoundError, RuntimeError) as error:
        parser.exit(1, f"Error: {error}\n")
    print(f"Video: {output}")
    print(f"Trace: {options.trace}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
