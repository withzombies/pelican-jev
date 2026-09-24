# Jev Logo turtle: a pelican on a bicycle

This project makes a short, shareable video of a Logo turtle drawing a humorous pelican on a bicycle. A Codex sketch proposer sees only that goal and the current canvas, then offers three short sequences of ordinary Logo commands. Jev chooses one sequence and the turtle executes its `PENUP`, `PENDOWN`, and movement commands. The loop repeats from the updated canvas. No bicycle or pelican parts are hard-coded in the project prompt or geometry.

The two model roles are explicit in the video: **Codex proposes; Jev chooses**. Jev's [typed API](https://api.typesafe.ai/openapi.json) chooses among supplied candidates rather than generating arbitrary command text. Every proposal, Jev choice, and executed command is saved in the trace for inspection and key-free replay.

## Run

Install Python 3.11+, Pillow, FFmpeg with `libx264`, and the [Codex CLI](https://learn.chatgpt.com/docs/non-interactive-mode). Sign in to Codex CLI and set `TYPESAFE_API_KEY` in your environment. Install Python dependencies with `uv sync --extra dev`, or use an environment where they are already available.

```sh
python3.11 -m pelican_jev draw
```

The command writes `output/decisions.json` and `output/pelican_on_bicycle.mp4`. The default is ten proposal/choice rounds; use `--max-rounds` to change it. If a model call interrupts a run, continue from the last completed round. You can also extend a completed drawing by resuming with a larger round budget:

```sh
python3.11 -m pelican_jev draw --resume
```

Replay a completed trace without either model:

```sh
python3.11 -m pelican_jev replay
```

The video is 1280×720, 30 fps, H.264/yuv420p. Use `--trace`, `--output`, `--frames-per-step`, and `--hold-seconds` to adjust paths or pacing. The CLI uses [Codex noninteractive mode](https://learn.chatgpt.com/docs/non-interactive-mode) with a JSON output schema and a read-only sandbox. It passes the current canvas image to the proposer; the project validates all commands and canvas bounds before sending candidates to Jev.

## Verify

```sh
python3.11 -m compileall -q pelican_jev tests
python3.11 -m pytest -q
python3.11 -m ruff check .
```

The proposal-and-choice loop follows the same division of work as the [TypeSafe community Jev harness](https://github.com/TypeSafeAI/jev-harness) and its [candidate-ranking examples](https://github.com/TypeSafeAI/typesafe-playground/blob/main/docs/document-extraction.md).
