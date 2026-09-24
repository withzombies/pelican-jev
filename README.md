# Jev turtle: a pelican on a bicycle

Jev from TypeSafe AI chooses each visible Logo-style turtle advance from two distinct bounded moves. It sees the overall goal, the turtle's current pose, recent moves, and the drawing so far; the question does not name the current feature or a target point. A fixed guide keeps the pelican and bicycle recognizable. An animated turtle follows each stroke and travels with its pen up between paths. The program saves every live decision in a JSON trace and turns that exact run into a video with the question asked, both offered moves, Jev's answer and probabilities, and the resulting Logo commands.

## Run

Use Python 3.11+, Pillow 10.4+, and FFmpeg with `libx264`. Install the project and test tools with `uv sync --extra dev`, or use an environment where they are already available. Set `TYPESAFE_API_KEY` in your environment; the program never writes it to the trace or video.

```sh
python3.11 -m pelican_jev draw
```

The command writes `output/decisions.json` and `output/pelican_on_bicycle.mp4`. If a live run stops because of a network or API problem, continue its saved decisions with:

```sh
python3.11 -m pelican_jev draw --resume
```

Replay a completed trace without a key or extra Jev calls:

```sh
python3.11 -m pelican_jev replay
```

The default video is a 1280×720, 30 fps H.264 MP4 suitable for attaching to an X post. Each drawn move gets five animation frames; the turtle visibly travels between paths with its pen up, and the final drawing holds for two seconds. Use `--trace`, `--output`, `--frames-per-step`, and `--hold-seconds` to change file locations or pacing. The default duration is well below [X's standard 140-second limit](https://help.x.com/en/using-x/x-videos).

## Verify

```sh
python3.11 -m compileall -q pelican_jev tests
python3.11 -m pytest -q
python3.11 -m ruff check .
```

The API request shape follows [TypeSafe's official schema](https://api.typesafe.ai/docs). The decision loop draws on three implementations studied before coding: the [minimal Python Jev client](https://github.com/Foadsf/jev-for-engineers/blob/main/jev.py), [TypeSafe browser agent](https://github.com/TypeSafeAI/typesafe-playground/blob/main/lib/agentLoop.ts), and [TypeSafe router client](https://github.com/TypeSafeAI/typesafe-router/blob/main/lib/jevClient.ts). Rendering uses [Pillow](https://pillow.readthedocs.io/en/latest/reference/ImageDraw.html) and [FFmpeg](https://ffmpeg.org/ffmpeg-formats.html).
