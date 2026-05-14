#!/usr/bin/env node
/**
 * Inworld AI TTS Generator — Spanish voices verified
 * Usage: node tts-inworld.js <text> <output-file> [options]
 * 
 * Spanish voices: Rafael, Sofia, Mateo, Miguel, Diego, Lupita
 * TESTED: Rafael (v5.1) ✓
 */
const { InworldTTS } = require('@inworld/tts');
const fs = require('fs');
const path = require('path');

const args = process.argv.slice(2);
const text = args[0];
const outputFile = args[1];

if (!text || !outputFile) {
  console.error('Usage: tts-inworld.js <text> <output> [--voice V] [--speed N] [--temp N] [--mode M]');
  process.exit(1);
}

let voice = 'Rafael';
let model = 'inworld-tts-1.5-mini';
let speakingRate = 1.0;
let temperature = 1.5;
let deliveryMode = 'EXPRESSIVE';

for (let i = 2; i < args.length; i++) {
  switch (args[i]) {
    case '--voice': voice = args[++i]; break;
    case '--model': model = args[++i]; break;
    case '--speed': speakingRate = parseFloat(args[++i]); break;
    case '--temp':  temperature = parseFloat(args[++i]); break;
    case '--mode':  deliveryMode = args[++i]; break;
  }
}

if (!process.env.INWORLD_API_KEY) {
  console.error('ERROR: INWORLD_API_KEY not set');
  process.exit(1);
}

async function main() {
  // Validate voice supports Spanish
  const resp = await fetch('https://api.inworld.ai/tts/v1/voices', {
    headers: { 'Authorization': `Basic ${process.env.INWORLD_API_KEY}` }
  });
  const voices = await resp.json();
  const voiceList = Array.isArray(voices) ? voices : voices.voices || [];
  const found = voiceList.find(v => v.voiceId === voice || v.name === voice);
  if (found && !found.languages.includes('es')) {
    console.error(`WARNING: Voice '${voice}' may not support Spanish. Available Spanish voices: Rafael, Sofia, Mateo, Miguel, Diego, Lupita, Camila, Mauricio`);
  }

  const tts = new InworldTTS({ apiKey: process.env.INWORLD_API_KEY });
  const audio = await tts.generate({
    text, voice, model,
    encoding: 'MP3', sampleRate: 24000, bitRate: 96000,
    speakingRate, temperature,
  });
  fs.writeFileSync(outputFile, Buffer.from(audio));
  console.log(`TTS OK: ${(audio.length / 1024).toFixed(1)} KB -> ${outputFile}`);
}

main().catch(err => { console.error('TTS Error:', err.message); process.exit(1); });
