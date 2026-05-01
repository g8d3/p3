FROM python:3.13-slim

WORKDIR /agent

# Install minimal deps
RUN pip install --no-cache-dir --timeout 60 \
    livekit-agents \
    livekit-plugins-silero \
    livekit-plugins-openai \
    livekit-plugins-deepgram \
    httpx

COPY *.py .

CMD ["python", "-u", "main.py", "start"]
