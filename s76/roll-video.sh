#!/bin/bash
# Continuous fMP4 writer. Writes directly to current.mp4 using fragmented MP4.
# The file grows continuously; MSE fetches new fragments via Range requests.
mkdir -p /tmp/video-cache

while true; do
  # Remove old file so MSE detects discontinuity
  rm -f /tmp/video-cache/current.mp4

  ffmpeg -y -loglevel warning \
    -f lavfi -i "color=c=#1a1a2e:s=1280x720:r=30,format=yuv420p" \
    -f lavfi -i "gradients=s=1280x720:r=30:c0=#ff6b6b:c1=#4ecdc4:c2=#45b7d1:c3=#96ceb4:rate=20" \
    -f lavfi -i "aevalsrc='sin(110*2*PI*t)*0.3 + sin(165*2*PI*t)*0.2 + sin(220*2*PI*t)*0.15',aecho=0.8:0.7:40:0.5" \
    -filter_complex "[0:v]drawtext=text='%{localtime}':fontcolor=white:fontsize=72:x=(w-text_w)/2:y=20:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf[v0];[1:v]drawtext=text='s76 live':fontcolor=black:fontsize=36:x=20:y=h-th-30:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf[v1];[v0][v1]overlay=format=auto,format=yuv420p" \
    -c:v libx264 -preset veryfast -b:v 2000k \
    -c:a aac -b:a 96k \
    -movflags empty_moov+frag_keyframe \
    -f mp4 \
    "/tmp/video-cache/current.mp4"

  echo "[roll-video] ffmpeg exited, restarting..."
  sleep 1
done
