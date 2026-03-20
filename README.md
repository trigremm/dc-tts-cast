# dc-tts-cast

Local TTS in Docker — converts .txt files into ~20-minute mp3 episodes using Silero TTS on GPU.

## Requirements

- Docker with [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
- NVIDIA GPU

## Usage

1. Put `.txt` files into `input/`
2. Run:

```bash
docker compose up --build
```

3. Get mp3 files from `output/<book_name>/001.mp3, 002.mp3, ...`

## Options

Pass via `docker-compose.yml` → `command:` or override:

```bash
docker compose run tts --speaker aidar --duration 30
```

| Flag | Default | Description |
|------|---------|-------------|
| `--speaker` | `xenia` | Voice: `aidar`, `baya`, `kseniya`, `xenia`, `eugene` |
| `--duration` | `20` | Chunk duration in minutes |
| `--sample-rate` | `48000` | Audio quality: `8000`, `24000`, `48000` |
