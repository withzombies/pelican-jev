# Context

The workspace began empty and without a Git repository. Python 3.11, Pillow, pytest, Ruff, FFmpeg with libx264, and `TYPESAFE_API_KEY` are available. Jev's official API accepts `state`, `model`, and named `choice` questions; answers contain a selected choice and confidence. Jev does not generate free-form turtle commands.

The drawing guide uses 236 visible moves, making the default video about 48 seconds including turtle travel and its final hold. A synthetic trace has been rendered and inspected: the frame clearly shows both bicycle wheels, its frame, and the pelican's head, long beak, pouch, body, wing, and feet at the pedals. The first live run chose center for all 236 moves; the live choice set now offers left and right offsets, and the video shows the exact question, options, answer, probabilities, and Logo commands. The larger turtle moves visibly along strokes and with its pen up between paths.

The user's later correction simplified the Jev prompt: the API question now asks which next turtle move helps draw a pelican on a bicycle. State contains only that goal, step number, current turtle pose, recent moves, and all drawn line segments. Feature names and guide targets remain internal to the renderer and are not sent to Jev. The earlier left/right live run was stopped before its video encoded; the final live run must use this new request shape.

Final live run: 236 Jev answers (125 left, 111 right), each with both probabilities, recorded in `output/decisions.json`. `output/pelican_on_bicycle.mp4` is 48 seconds, 1280×720, 30 fps, H.264/yuv420p, and 1,219,241 bytes. Inspected a pen-up transit frame, an in-progress drawing frame, and the finished frame. The file is below X's standard 140-second and 512-MB upload limits.
