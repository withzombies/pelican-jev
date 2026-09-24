# Context

Python 3.11, Pillow, pytest, Ruff, FFmpeg with libx264, and `TYPESAFE_API_KEY` are available. Jev's API accepts a `state` and typed `choice` questions. It does not generate arbitrary text commands, so the turtle exposes generic bounded Logo commands and Jev selects the sequence and parameters. The request includes only the goal, canvas and turtle state, and line segments drawn so far. It does not include previous commands, previous attempts, art feature labels, or waypoints.

The earlier implementation contained a fixed drawing guide and produced a recognizable 48-second MP4, but it did not give Jev artistic control. The user's correction removes that guide entirely. The new trace format is version 2 and replays each pen, turn, and travel command. The prior guided MP4 remains as a historical artifact until a full unguided run is inspected.

A first live 40-command pilot selected `PENDOWN`, repeated `FORWARD_20` many times, made a few right turns, and selected `DONE`. Its drawing was a long line and small shape, not a recognizable pelican or bicycle. This is evidence of a capability limit in the completely unguided Jev loop; do not describe that result as successful artwork or add hidden geometry to conceal it.

The final run sent no recent commands or previous attempts to Jev. Its 180 responses comprised 16 `FORWARD_20` moves, one `PENDOWN`, 82 `RIGHT_90` turns, and 81 `LEFT_90` turns. It hit the command budget and drew a horizontal line. The exact run is in `output/decisions.json`; `output/pelican_on_bicycle.mp4` is 32 seconds, 1280×720, 30 fps, H.264/yuv420p, 592,521 bytes. Its final frame was inspected. The earlier recognizable guided video is retained only as `output/pelican_on_bicycle_guided_reference.mp4`.
