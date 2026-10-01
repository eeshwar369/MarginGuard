"""Mux real browser video with the local system-voice narration, preserving action timing."""

import json
import os
import shutil
import subprocess
import wave
from pathlib import Path


def durations():
    segments = json.loads(Path("scripts/demo-narration.json").read_text(encoding="utf-8"))
    for segment in segments:
        with wave.open(str(Path("artifacts/audio") / (segment["id"] + ".wav"))) as stream:
            segment["duration"] = stream.getnframes() / stream.getframerate()
    Path("artifacts/audio/durations.json").write_text(json.dumps(segments), encoding="utf-8")
    print("Narration duration:", round(sum(s["duration"] for s in segments)), "seconds")


def render():
    timeline = json.loads(Path("artifacts/video/timings.json").read_text(encoding="utf-8"))
    cached_encoder = Path("artifacts/encoder-path.txt")
    encoder = os.environ.get("FFMPEG_BIN") or shutil.which("ffmpeg")
    if not encoder and cached_encoder.exists():
        encoder = cached_encoder.read_text().strip()
    if not encoder:
        raise SystemExit("Install FFmpeg or set FFMPEG_BIN to the encoder executable.")
    output = Path("../deliverables/MarginGuard_Product_Demo.mp4").resolve()
    args = [encoder, "-y", "-i", timeline["source"]]
    filters, labels = [], []
    for index, segment in enumerate(timeline["segments"], start=1):
        args += ["-i", str(Path("artifacts/audio") / (segment["id"] + ".wav"))]
        filters.append(f"[{index}:a]adelay={segment['start_ms']}|{segment['start_ms']}[a{index}]")
        labels.append(f"[a{index}]")
    filters.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0:dropout_transition=0[audio]")
    args += [
        "-filter_complex",
        ";".join(filters),
        "-map",
        "0:v",
        "-map",
        "[audio]",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "22",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        "-shortest",
        str(output),
    ]
    subprocess.run(args, check=True)
    print(output)


if __name__ == "__main__":
    import sys

    durations() if "--durations" in sys.argv else render()
