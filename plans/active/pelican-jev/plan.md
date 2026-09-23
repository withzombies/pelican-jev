# Jev pelican bicycle

Build a Python Logo-style turtle project that draws a recognizable pelican riding a bicycle. Live Jev chooses every visible pen-down move from bounded options. Save a key-free trace and render the same run to an MP4 with a decision overlay.

Acceptance: `python -m pelican_jev draw` creates `output/pelican_on_bicycle.mp4` and a JSON trace using `TYPESAFE_API_KEY`; replay of that trace needs no API key and produces the same drawing; tests, compilation, and Ruff pass. The final video is 1280×720, 30 fps, H.264, with no audio.

Sources: [TypeSafe API](https://api.typesafe.ai/docs), [minimal Jev client](https://github.com/Foadsf/jev-for-engineers/blob/main/jev.py), [browser agent](https://github.com/TypeSafeAI/typesafe-playground/blob/main/lib/agentLoop.ts), [router client](https://github.com/TypeSafeAI/typesafe-router/blob/main/lib/jevClient.ts), [Pillow](https://pillow.readthedocs.io/en/latest/reference/ImageDraw.html), [FFmpeg](https://ffmpeg.org/ffmpeg-formats.html).
