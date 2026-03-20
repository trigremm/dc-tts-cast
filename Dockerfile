FROM pytorch/pytorch:2.2.0-cuda12.1-cudnn8-runtime

RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir torchaudio

# Pre-download Silero TTS model
RUN python -c "import torch; torch.hub.load('snakers4/silero-models', model='silero_tts', language='ru', speaker='v4_ru')"

COPY app/ .

ENTRYPOINT ["python", "tts_cast.py"]
