#!/usr/bin/env node
/**
 * Inworld AI TTS Generator — with emotional control
 * Usage: node tts-inworld.js <text> <output-file> [options]
 * 
 * Options:
 *   --voice <id>       Voice ID (default: Ashley)
 *   --model <id>       Model ID (default: inworld-tts-1.5-mini)
 *   --speed <0.5-1.5>  Speaking rate (default: 1.0)
 *   --temp <0-2>       Expressiveness temperature (default: 1.2)
 *   --mode <mode>      Delivery mode: STABLE, BALANCED, EXPRESSIVE (default: EXPRESSIVE)
 */

const { InworldTTS } = require('@inworld/tts');
const fs = require('fs');
const path = require('path');

// Parse args
const args = process.argv.slice(2);
const text = args[0];
const outputFile = args[1];

if (!text || !outputFile) {
  console.error('Usage: node tts-inworld.js <text> <output-file> [--voice V] [--speed N] [--temp N] [--mode M]');
  process.exit(1);
}

// Parse options
let voice = 'Ashley';
let model = 'inworld-tts-1.5-mini';
let speakingRate = 1.0;
let temperature = 1.2;
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

// Validate
if (!process.env.INWORLD_API_KEY) {
  console.error('ERROR: INWORLD_API_KEY not set');
  process.exit(1);
}

async function main() {
  console.log(`[Inworld TTS] Generating...`);
  console.log(`  Text:   "${text.substring(0, 60)}${text.length > 60 ? '...' : ''}"`);
  console.log(`  Voice:  ${voice}`);
  console.log(`  Model:  ${model}`);
  console.log(`  Speed:  ${speakingRate}`);
  console.log(`  Temp:   ${temperature}`);
  console.log(`  Mode:   ${deliveryMode}`);
  console.log(`  Output: ${outputFile}`);

  const tts = new InworldTTS({
    apiKey: process.env.INWORLD_API_KEY,
  });

  const audio = await tts.generate({
    text,
    voice,
    model,
    encoding: 'MP3',
    sampleRate: 24000,
    bitRate: 96000,
    speakingRate,
    temperature,
  });

  fs.writeFileSync(outputFile, Buffer.from(audio));
  console.log(`  Done:   ${(audio.length / 1024).toFixed(1)} KB written`);
}

main().catch(err => {
  console.error('Error:', err.message);
  process.exit(1);
});
