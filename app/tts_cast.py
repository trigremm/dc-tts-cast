#!/usr/bin/env python3
"""Convert .txt files to ~20-minute audio episodes using Silero TTS (GPU)."""

import argparse
import logging
import re
import subprocess
import sys
from pathlib import Path

import torch
import torchaudio

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

SPEAKERS = ["aidar", "baya", "kseniya", "xenia", "eugene"]
MAX_CHARS = 900  # Silero per-call character limit


def split_into_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    parts = re.split(r'(?<=[.!?…»"])\s+', text)
    return [p.strip() for p in parts if p.strip()]


def split_long_text(text: str, max_len: int = MAX_CHARS) -> list[str]:
    if len(text) <= max_len:
        return [text]

    chunks = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break
        split_at = -1
        for sep in [". ", ", ", "; ", " — ", " - ", " "]:
            idx = text.rfind(sep, 0, max_len)
            if idx > 0:
                split_at = idx + len(sep)
                break
        if split_at <= 0:
            split_at = max_len
        chunks.append(text[:split_at].strip())
        text = text[split_at:].strip()
    return chunks


def save_chunk_as_mp3(
    audio: torch.Tensor, sample_rate: int, output_path: Path, speed: float = 1.0
):
    wav_path = output_path.with_suffix(".wav")
    torchaudio.save(str(wav_path), audio.unsqueeze(0), sample_rate)
    cmd = ["ffmpeg", "-y", "-i", str(wav_path)]
    if speed != 1.0:
        cmd += ["-filter:a", f"atempo={speed}"]
    cmd += ["-b:a", "192k", str(output_path)]
    subprocess.run(cmd, check=True, capture_output=True)
    wav_path.unlink()


def process_file(
    txt_path: Path,
    output_dir: Path,
    model,
    speaker: str,
    sample_rate: int,
    chunk_minutes: int,
    device: torch.device,
    speed: float = 1.0,
):
    log.info(f"Processing: {txt_path.name}")

    text = txt_path.read_text(encoding="utf-8")
    sentences = split_into_sentences(text)

    if not sentences:
        log.warning(f"No text in {txt_path.name}, skipping")
        return

    book_dir = output_dir / txt_path.stem
    book_dir.mkdir(parents=True, exist_ok=True)

    target_samples = int(chunk_minutes * 60 * sample_rate * speed)
    silence = torch.zeros(int(0.3 * sample_rate))  # 300ms pause between sentences

    chunk_parts: list[torch.Tensor] = []
    chunk_samples = 0
    chunk_num = 1
    total = len(sentences)

    for i, sentence in enumerate(sentences):
        parts = split_long_text(sentence)

        for part in parts:
            try:
                audio = model.apply_tts(
                    text=part, speaker=speaker, sample_rate=sample_rate
                )
                if device.type == "cuda":
                    audio = audio.cpu()
            except Exception as e:
                log.warning(f"TTS failed for: {part[:60]}... — {e}")
                continue

            chunk_parts.append(audio)
            chunk_parts.append(silence)
            chunk_samples += len(audio) + len(silence)

            if chunk_samples >= target_samples:
                combined = torch.cat(chunk_parts)
                mp3_path = book_dir / f"{chunk_num:03d}.mp3"
                save_chunk_as_mp3(combined, sample_rate, mp3_path, speed)
                minutes = chunk_samples / sample_rate / 60 / speed
                log.info(f"  Saved {mp3_path.name} ({minutes:.1f} min)")
                chunk_num += 1
                chunk_parts = []
                chunk_samples = 0

        if (i + 1) % 50 == 0:
            log.info(f"  Progress: {i + 1}/{total} sentences")

    if chunk_parts:
        combined = torch.cat(chunk_parts)
        mp3_path = book_dir / f"{chunk_num:03d}.mp3"
        save_chunk_as_mp3(combined, sample_rate, mp3_path)
        minutes = chunk_samples / sample_rate / 60
        log.info(f"  Saved {mp3_path.name} ({minutes:.1f} min)")

    log.info(f"Done: {txt_path.name} → {chunk_num} file(s)")


def main():
    parser = argparse.ArgumentParser(description="txt → mp3 episodes via Silero TTS")
    parser.add_argument("--input", default="/data/input")
    parser.add_argument("--output", default="/data/output")
    parser.add_argument("--speaker", default="xenia", choices=SPEAKERS)
    parser.add_argument(
        "--sample-rate", type=int, default=48000, choices=[8000, 24000, 48000]
    )
    parser.add_argument(
        "--duration", type=int, default=20, help="chunk duration in minutes"
    )
    parser.add_argument(
        "--speed", type=float, default=1.0, help="playback speed (e.g. 1.5)"
    )
    args = parser.parse_args()

    input_dir = Path(args.input)
    output_dir = Path(args.output)

    txt_files = sorted(input_dir.glob("*.txt"))
    if not txt_files:
        log.error(f"No .txt files in {input_dir}")
        sys.exit(1)

    log.info(
        f"Files: {len(txt_files)}, speaker: {args.speaker}, "
        f"chunk: {args.duration} min, speed: {args.speed}x"
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    log.info(f"Device: {device}")

    model, _ = torch.hub.load(
        repo_or_dir="snakers4/silero-models",
        model="silero_tts",
        language="ru",
        speaker="v4_ru",
    )
    model.to(device)
    log.info("Model loaded")

    for txt_file in txt_files:
        process_file(
            txt_file,
            output_dir,
            model,
            args.speaker,
            args.sample_rate,
            args.duration,
            device,
            args.speed,
        )

    log.info("All done!")


if __name__ == "__main__":
    main()
