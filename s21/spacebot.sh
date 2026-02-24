docker run -d \
  --name spacebot \
  -v spacebot-data:/data \
  -p 19898:19898 \
  ghcr.io/spacedriveapp/spacebot:slim
