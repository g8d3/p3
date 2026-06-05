#!/bin/bash
# comunicador: watches ~/.j/bus/buf/in/ and forwards content to tmux main:4

DIR="/home/vuos/.j/bus/buf/in"
mkdir -p "$DIR"

while true; do
  file=$(inotifywait -q -e create,moved_to --format "%f" "$DIR")
  cat "$DIR/$file" | tmux load-buffer -
  tmux paste-buffer -t main:4 -d
  tmux send-keys -t main:4 Enter
  rm -f "$DIR/$file"
done
