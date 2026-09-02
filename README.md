# dc-tts-cast

Local TTS in Docker — converts .txt files into ~20-minute mp3 episodes using Silero TTS on GPU.

## Requirements

- Docker with [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
- NVIDIA GPU
- `python3` on the host (used by `make run-resume` to read `tts_config.json`)

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

`make run-resume` uses the host's `python3` to read `input-host` from `tts_config.json` and re-mount the input directory, so it only works with a config written by `make run` (`make up` does not record host paths).

## Batch processing

Process N files at a time:

```bash
make run SPEAKER=baya SPEED=1.5 COUNT=100 INPUT_HOST=./input/my_book OUTPUT_HOST=./output/my_book_baya
```

Then resume to do the next batch:

```bash
make run-resume OUTPUT_HOST=./output/my_book_baya
```

To limit the run to files whose name contains a string, and set the album name used in ID3 tags and cover art:

```bash
make run MASK=chapter ALBUM="My Book" INPUT_HOST=./input/my_book OUTPUT_HOST=./output/my_book_baya
```

`run_star_wars.sh` is a committed one-off batch example: it loops over `../pybookworm/output/star_wars/*/`, calls `make run` (or `make run-resume` for partially converted books) per book, and aborts if the Docker daemon goes away. Paths are hard-coded.

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--speaker` | `xenia` | Voice: `aidar`, `baya`, `kseniya`, `xenia`, `eugene` |
| `--speed` | `1.0` | Playback speed (e.g. `1.5`) |
| `--duration` | `20` | Chunk duration in minutes |
| `--sample-rate` | `48000` | Audio quality: `8000`, `24000`, `48000` |
| `--skip-existing` | off | Skip files that already have mp3 output |
| `--count` | `0` | Process at most N files (0 = all remaining) |
| `--start` | `0` | Start from file N (0-based index in sorted list) |
| `--mask` | none | Only process files whose name contains this string (e.g. `chapter`) |
| `--album` | output dir name | Album name for ID3 tags and cover art (host output dir name when known, else the container's) |
| `--config` | auto | Path to JSON config (default: `<output>/tts_config.json`); CLI args override config values |
| `--input-host`, `--output-host` | none | Host-side paths, saved to the config so `make run-resume` can re-mount the input directory |

## Makefile targets

| Target | Description |
|--------|-------------|
| `make build` | Build the Docker image |
| `make up` | Build and run via docker compose with defaults (all `.txt` files from `./input` → `./output`) |
| `make run` | Run with options (`SPEAKER`, `SPEED`, `DURATION`, `SAMPLE_RATE`, `COUNT`, `MASK`, `ALBUM`, `INPUT_HOST`, `OUTPUT_HOST`) |
| `make run-resume` | Resume from saved config (only needs `OUTPUT_HOST`; needs host `python3`) |
| `make down` | Stop and remove containers |
| `make logs` | Show container logs |
| `make clean` | Remove generated output files (`rm -rf output/*/`) |
| `make format` | Format Python code with ruff |
| `make lint` | Lint Python code with ruff |
| `make help` | Show all targets |
