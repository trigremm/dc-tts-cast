# dc-tts-cast

Local TTS in Docker — converts .txt files into ~20-minute mp3 episodes using Silero TTS on GPU.

## Requirements

- Docker with [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
- NVIDIA GPU

## Quick start

```bash
make build
```

Put `.txt` files into an input directory (e.g. `input/my_book/`), then run:

```bash
make run SPEAKER=baya SPEED=1.5 INPUT_HOST=./input/my_book OUTPUT_HOST=./output/my_book_baya
```

Output: `output/my_book_baya/<filename>.mp3`

## Resume

First run saves `tts_config.json` in the output directory with all settings. To continue where you left off:

```bash
make run-resume OUTPUT_HOST=./output/my_book_baya
```

This reads the config, skips already-converted files, and processes the rest.

## Batch processing

Process N files at a time:

```bash
make run SPEAKER=baya SPEED=1.5 COUNT=100 INPUT_HOST=./input/my_book OUTPUT_HOST=./output/my_book_baya
```

Then resume to do the next batch:

```bash
make run-resume OUTPUT_HOST=./output/my_book_baya
```

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--speaker` | `xenia` | Voice: `aidar`, `baya`, `kseniya`, `xenia`, `eugene` |
| `--speed` | `1.0` | Playback speed (e.g. `1.5`) |
| `--duration` | `20` | Chunk duration in minutes |
| `--sample-rate` | `48000` | Audio quality: `8000`, `24000`, `48000` |
| `--skip-existing` | off | Skip files that already have mp3 output |
| `--count` | `0` | Process at most N files (0 = all) |
| `--start` | `0` | Start from file N (0-based index) |
| `--config` | auto | Path to JSON config (default: `<output>/tts_config.json`) |

## Makefile targets

| Target | Description |
|--------|-------------|
| `make build` | Build the Docker image |
| `make run` | Run with options (`SPEAKER`, `SPEED`, `COUNT`, `INPUT_HOST`, `OUTPUT_HOST`) |
| `make run-resume` | Resume from saved config (only needs `OUTPUT_HOST`) |
| `make help` | Show all targets |
