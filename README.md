# Jev Logo turtle: pelican on a bicycle

Jev chooses every Logo command from a blank 960×720 canvas. The request tells Jev only the overall goal, its current position and heading, whether the pen is down, the lines on the current canvas, and the available commands. No previous commands or attempts are sent. There are no feature labels, target points, or planned strokes. The command set includes `PENUP`, `PENDOWN`, `FORWARD`, `BACK`, `LEFT`, `RIGHT`, and `DONE`; movement distances and turn angles are bounded choices because [Jev's API returns typed choices](https://api.typesafe.ai/docs), not arbitrary command text.

The program stores each Jev decision in `output/decisions.json` and animates those exact commands, including the large moving turtle, pen changes, question, and response, in `output/pelican_on_bicycle.mp4`. The video is a 1280×720, 30 fps H.264 MP4. The included live run drew a horizontal line and then mostly turned in place; it is an honest unguided attempt, not a recognizable pelican or bicycle.

## Run

Use Python 3.11+, Pillow, and FFmpeg with `libx264`. Install dependencies with `uv sync --extra dev`, or use an environment where they are already available. Set `TYPESAFE_API_KEY` in your environment. The key is never written to the trace or video.

```sh
python3.11 -m pelican_jev draw
```

The default decision budget is 180 commands. Jev may finish sooner by selecting `DONE`; otherwise the run stops at the budget. To change it, use `--max-steps 240`. If a network or API problem interrupts the run, resume with the same budget:

```sh
python3.11 -m pelican_jev draw --resume
```

Replay a completed trace without a key or more Jev calls:

```sh
python3.11 -m pelican_jev replay
```

Use `--trace`, `--output`, `--frames-per-step`, and `--hold-seconds` to change locations or pacing. The default 180-command video lasts about 32 seconds, within [X's standard video length limit](https://help.x.com/en/using-x/x-videos).

## Verify

```sh
python3.11 -m compileall -q pelican_jev tests
python3.11 -m pytest -q
python3.11 -m ruff check .
```

The choice loop follows [TypeSafe's browser agent](https://github.com/TypeSafeAI/typesafe-playground/blob/main/docs/jev-browser-agent.md), which observes current state and asks Jev to select from a bounded action set. The API request shape follows [TypeSafe's schema](https://api.typesafe.ai/docs).
