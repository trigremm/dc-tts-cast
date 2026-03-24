#!/usr/bin/env python3
"""Convert .txt files to ~20-minute audio episodes using Silero TTS (GPU)."""

import argparse
import json
import logging
import re
import subprocess
import sys
from pathlib import Path

import num2words
import torch
import torchaudio

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

SPEAKERS = ["aidar", "baya", "kseniya", "xenia", "eugene"]
MAX_CHARS = 900  # Silero per-call character limit


def numbers_to_words(text: str, lang: str = "ru") -> str:
    """Replace numbers with their word equivalents."""
    def replace_number(match):
        num_str = match.group(0)
        try:
            if "." in num_str or "," in num_str:
                num = float(num_str.replace(",", "."))
            else:
                num = int(num_str)
            return num2words.num2words(num, lang=lang)
        except (ValueError, OverflowError):
            return num_str

    return re.sub(r"\d+[.,]?\d*", replace_number, text)


def split_into_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    text = numbers_to_words(text)
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

    output_dir.mkdir(parents=True, exist_ok=True)
    stem = txt_path.stem

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
                mp3_name = f"{stem}_{chunk_num:03d}.mp3"
                mp3_path = output_dir / mp3_name
                save_chunk_as_mp3(combined, sample_rate, mp3_path, speed)
                minutes = chunk_samples / sample_rate / 60 / speed
                log.info(f"  Saved {mp3_name} ({minutes:.1f} min)")
                chunk_num += 1
                chunk_parts = []
                chunk_samples = 0

        if (i + 1) % 50 == 0:
            log.info(f"  Progress: {i + 1}/{total} sentences")

    if chunk_parts:
        combined = torch.cat(chunk_parts)
        # Single chunk: use stem directly; multi-chunk: append number
        if chunk_num == 1:
            mp3_name = f"{stem}.mp3"
        else:
            mp3_name = f"{stem}_{chunk_num:03d}.mp3"
        mp3_path = output_dir / mp3_name
        save_chunk_as_mp3(combined, sample_rate, mp3_path, speed)
        minutes = chunk_samples / sample_rate / 60 / speed
        log.info(f"  Saved {mp3_name} ({minutes:.1f} min)")

    log.info(f"Done: {txt_path.name} → {chunk_num} file(s)")


def has_output(txt_path: Path, output_dir: Path) -> bool:
    """Check if an mp3 already exists for this input file."""
    stem = txt_path.stem
    # Single-chunk output or first multi-chunk
    if (output_dir / f"{stem}.mp3").exists():
        return True
    if (output_dir / f"{stem}_001.mp3").exists():
        return True
    return False


def load_config(config_path: Path) -> dict:
    """Load project config from JSON file."""
    with open(config_path) as f:
        return json.load(f)


def save_config(config_path: Path, cfg: dict):
    """Save project config to JSON file."""
    with open(config_path, "w") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    log.info(f"Config saved: {config_path}")


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
    parser.add_argument(
        "--skip-existing", action="store_true",
        help="skip files that already have mp3 output",
    )
    parser.add_argument(
        "--start", type=int, default=0,
        help="start from file N (0-based index in sorted list)",
    )
    parser.add_argument(
        "--count", type=int, default=0,
        help="process at most N files (0 = all remaining)",
    )
    parser.add_argument(
        "--config", default=None,
        help="path to JSON config file (overrides CLI defaults)",
    )
    parser.add_argument(
        "--input-host", default=None,
        help="host-side input path (saved to config for resume)",
    )
    parser.add_argument(
        "--output-host", default=None,
        help="host-side output path (saved to config for resume)",
    )
    args = parser.parse_args()

    output_dir = Path(args.output)
    config_path = args.config or str(output_dir / "tts_config.json")
    config_path = Path(config_path)

    # Load existing config — CLI args override config values
    if config_path.exists():
        log.info(f"Loading config: {config_path}")
        cfg = load_config(config_path)
        for key, val in cfg.items():
            attr = key.replace("-", "_")
            cli_default = parser.get_default(attr)
            current = getattr(args, attr, None)
            if current == cli_default and val is not None:
                setattr(args, attr, val)

    input_dir = Path(args.input)
    output_dir = Path(args.output)

    # Save config to output dir so next run auto-resumes
    output_dir.mkdir(parents=True, exist_ok=True)
    save_config(config_path, {
        "input": str(args.input),
        "output": str(args.output),
        "speaker": args.speaker,
        "sample-rate": args.sample_rate,
        "duration": args.duration,
        "speed": args.speed,
        "skip-existing": True,
        "start": 0,
        "count": 0,
        "input-host": args.input_host,
        "output-host": args.output_host,
    })

    txt_files = sorted(input_dir.glob("*.txt"))
    if not txt_files:
        log.error(f"No .txt files in {input_dir}")
        sys.exit(1)

    total_available = len(txt_files)

    # Apply range
    if args.start > 0:
        txt_files = txt_files[args.start:]
    if args.count > 0:
        txt_files = txt_files[:args.count]

    # Skip existing
    if args.skip_existing:
        before = len(txt_files)
        txt_files = [f for f in txt_files if not has_output(f, output_dir)]
        skipped = before - len(txt_files)
        if skipped:
            log.info(f"Skipped {skipped} files with existing output")

    if not txt_files:
        log.info("Nothing to process — all files already converted")
        return

    log.info(
        f"Files: {len(txt_files)}/{total_available}, speaker: {args.speaker}, "
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

    for idx, txt_file in enumerate(txt_files):
        log.info(f"[{idx + 1}/{len(txt_files)}]")
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
