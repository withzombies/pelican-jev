# Jev pelican bicycle

Build a Python Logo-style turtle project that draws a recognizable, humorous pelican on a bicycle. A generative sketch proposer sees the goal and current canvas and offers three short Logo command sequences each round. Jev selects a sequence; the turtle executes exactly its pen and movement commands. There are no hard-coded feature instructions or drawing guide. Save proposals, decisions, and executed commands in a key-free trace and render the same run to an MP4 that clearly labels both model roles.

Acceptance: `python -m pelican_jev draw` creates `output/pelican_on_bicycle.mp4` and a JSON trace using `TYPESAFE_API_KEY`; replay of that trace needs no API key and produces the same drawing; tests, compilation, and Ruff pass. The final video is 1280×720, 30 fps, H.264, with no audio.

Sources: [TypeSafe API](https://api.typesafe.ai/docs), [minimal Jev client](https://github.com/Foadsf/jev-for-engineers/blob/main/jev.py), [browser agent](https://github.com/TypeSafeAI/typesafe-playground/blob/main/lib/agentLoop.ts), [router client](https://github.com/TypeSafeAI/typesafe-router/blob/main/lib/jevClient.ts), [Pillow](https://pillow.readthedocs.io/en/latest/reference/ImageDraw.html), [FFmpeg](https://ffmpeg.org/ffmpeg-formats.html).
