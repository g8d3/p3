# p3 — Folder Index

| Folder | Description |
|--------|-------------|
| `s1-funding-rate-scraper` | CLI tool that fetches and normalizes funding rates from multiple decentralized perpetual DEX exchanges (Hyperliquid, dYdX, GMX, etc.) |
| `s2-bizbot-agent` | BizBot — autonomous business agent MVP that scouts business ideas from Reddit/X, generates digital products (ebooks/PDFs) via OpenAI, and auto-markets them on X using Playwright browser automation |
| `s3-nocode-ai-platform` | No-code AI development platform with a React frontend (visual editor, database designer, workflow builder) and Express/Apollo GraphQL backend for drag-and-drop app creation powered by AI |
| `s4-browser-automation` | Playwright-based browser automation scripts (CDP mode) including an X/Twitter home feed scraper, a Bitwarden popout automation, and a CDP codegen helper |
| `s5-english-learning-mvp` | English Learning MVP — a platform where teachers assign AI roles for students to chat with, with AI-powered progress tracking via a React frontend and Express/SQLite backend |
| `s6-cdp-playground` | CDP Master Playground — a React + Vite app that provides a visual IDE for connecting to Chrome DevTools Protocol (CDP) targets, executing commands, and inspecting browser pages |
| `s7-ai-web-scraper` | AI-powered web scraper platform with a Bun/TypeScript backend, PocketBase database, Puppeteer CDP browser automation, and OpenAI integration for AI-assisted scraping with scheduling and data sink export |
| `s8-github-topic-scraper` | Simple Playwright-based GitHub topic scraper utility that connects to a running Chrome via CDP and scrapes GitHub repository lists from topic pages into a CSV file |
| `s9-tax-filing-agent` | Brainstorming documents exploring a multi-agent AI system for automated IRS tax form filing using specialized LLM agents (researcher, drafter, auditor, orchestrator) |
| `s10-contract-security` | Flask web app for smart contract security that provides endpoints for retrieving security datasets, auditing Solidity code via the MythX API, and a placeholder for real-time contract monitoring |
| `s11-contract-security-app` | Full-stack web application (Express/TypeScript backend + React frontend) for smart contract security automation including dataset aggregation, contract auditing, and real-time protection monitoring |
| `s12-contract-exploit-dataset` | CSV dataset cataloging unified smart contract exploits (primarily reentrancy vulnerabilities) sourced from multiple analysis tools and academic studies across thousands of contract addresses |
| `s13-scratch` | Empty directory |
| `s14-llc-tax-filing` | Python/Node.js system for managing LLC tax profiles and transactions, automatically downloading IRS templates and filling PDF forms (5472 and 1120-F) with CLI/interactive menu and PDF verification |
| `s15-api-benchmarks` | GLM API performance benchmarking/monitoring toolkit plus research docs on copy-trading platforms and Hyperliquid trader analysis, including shell scripts, Python metrics collection, and quantitative trader evaluation |
| `s16-trader-perf-analysis` | Architecture design document for a Hyperliquid Trader Performance Analysis Tool — planned full-stack web app (FastAPI + React + PostgreSQL/Redis) computing quantitative trading metrics (Sharpe, Sortino, VaR, etc.) |
| `s17-terminal-ai-chat` | Terminal-based AI chat application with curses TUI, CRUD for providers/models/agents/tools, SQLite persistence, and support for OpenAI, Anthropic, Ollama, and local models |
| `s18-autonomous-agent` | Autonomous economic agent that explores, creates value, and earns money, with a Textual TUI, AI-driven task execution, browser automation, and self-evolution capabilities |
| `s19-ai-skills-marketplace` | Next.js marketplace (with Prisma/PostgreSQL) for AI agents and humans to publish, share, buy, and sell AI agent skills, featuring Polar.sh, x402, and ERC-8004 payment integrations |
| `s20-content-orchestrator` | Novaisabuilder Agent — a Node.js autonomous content orchestration agent for social media and content creation, using Express, SQLite, OpenAI, cron scheduling, and browser automation |
| `s21-spacebot-agent` | Nova Builds / Spacebot — an autonomous AI agent project that scrapes X.com likes/bookmarks, stores knowledge in a graph database (GraphQLite), produces content/code, and runs a Spacebot Docker service |
| `s22-mcp-server-config` | MCP Super Assistant Proxy — a Claude MCP (Model Context Protocol) server configuration running Chrome DevTools and shell MCP servers via npx |
| `s23-zai-api-tests` | Simple curl-based shell scripts for testing the Z.ai (Zhipu AI) coding/chat API with GLM models (streaming completions) |
| `s24-video-content-factory` | AI Content Factory — a Python automated content creation pipeline with topic generation, screen recording, video processing, TTS (text-to-speech), and social media uploading |
| `s25-tutorial-video-recorder` | Playwright-based browser automation scripts that record AI tutorial videos by navigating websites and overlaying styled subtitle captions |
| `s26-video-generator` | Autonomous video generator that uses TTS (Inworld/OpenAI/ElevenLabs) to create narrated videos with slides and uploads them to YouTube, with Privy/Capsule wallet integration |
| `s28-bittensor-subnet-analyzer` | Bittensor subnet rotation strategy analyzer that fetches on-chain subnet data, computes weighted signals (yield, momentum, volume, price trend, age), and generates staking rebalance recommendations with SQLite history tracking |
| `s29-bittensor-subnet-trader` | Bittensor subnet trader (refactored version) that fetches data from both the Bittensor chain and taostats.io API, computes multi-timeframe signals, ranks subnets, and generates stake/unstake orders |
| `s30-opencode-config` | Minimal OpenCode workspace configuration file (just sets a GLM-4.5-Air model) |
| `s31-cdp-browser-scripts` | Browser automation shell scripts using `agent-browser` CLI over Chrome DevTools Protocol for filling web forms, taking screenshots, and providing an interactive browser REPL |
| `s32-cdp-node-toolkit` | Node.js CDP (Chrome DevTools Protocol) toolset for automating AI service API key creation across providers (with browser/LLM fallback), Google SSO login automation, and app logout (clearing cookies/storage) |
| `s33-evm-wallet-generator` | CLI tool written in Zig for generating EVM (Ethereum) wallets with BIP-39 mnemonics, HD derivation, EIP-55 addresses, and AES-256-GCM encryption — zero external dependencies |
| `s34-eth-wallet-utility` | Node.js (ethers.js) utility for creating Ethereum wallets and checking balances, configurable via environment variables for raw/encrypted JSON output |
| `s35-content-automation` | Self-hostable Python content automation platform that gathers data from RSS/GitHub/Reddit/NewsAPI, generates articles using OpenAI/Anthropic LLMs, and posts to Twitter/Facebook/LinkedIn/Instagram with a FastAPI web dashboard |
| `s36-twitter-poster` | Automated X (Twitter) posting scripts using Puppeteer + Chrome DevTools Protocol (CDP) — posts single tweets and threads with media attachments via an existing browser session (no API keys needed) |
| `s37-skills-manager` | Simple Python CLI skills manager for OpenCode/Claude/Agents — lists, enables, and disables skill files (`SKILL.md` / `SKILL.md.disabled`) in global and project-local directories |
| `s38-sfx-downloader` | Sound effect downloader scripts (Python + Node.js) that use Chrome DevTools Protocol (CDP) to automate downloading sound effects from Pixabay |
| `s39-trading-bot` | Mega Alpha trading system — an institutional-grade multi-signal combination trading bot for perpetual DEXes (Hyperliquid) implementing the Fundamental Law of Active Management (IR = IC × √N) with 12+ signals, empirical Kelly sizing, and comprehensive risk management |
| `s40-trading-backtester` | Streamlit web dashboard (Hyperliquid Trading Game) that lets users compare grid trading vs. take-profit/stop-loss (TP/SL) trading strategies using the Nautilus Trader backtesting engine |
| `s41-dex-volume-fetcher` | Python CLI tool that fetches and caches real-time trading volume data for all assets (perpetual and spot) from the Hyperliquid DEX exchange, outputs CSVs with hourly/daily volume in USD |
| `s42-vrp-monitor` | Live terminal dashboard that monitors the Volatility Risk Premium (VRP) across BTC, ETH, and SOL by fetching Implied Volatility from Deribit and Realized Volatility from Hyperliquid |
| `s43-crypto-strategy-lab` | Crypto trading strategy research toolkit: MAE/MFE (Maximum Adverse/Favorable Excursion) analyzer for RSI-based signals + comprehensive strategy design blueprints for DEXes (GMX, dYdX, Uniswap V3, Deribit) |
| `s44-content-agent` | Content Agent — autonomous AI-powered content creation pipeline that researches tools, writes review scripts, records screen demos via Playwright, generates TTS voiceover narration, and assembles polished videos with ffmpeg |
| `s45-openmontage` | OpenMontage — open-source, AI-orchestrated video production platform that turns an AI coding assistant into a full video production studio, handling research, scripting, asset generation, and Remotion-based composition |
| `s46-ai-content-scheduler` | Autonomous AI content system that uses opencode agents to generate written posts, narrates them via TTS, reviews quality through a multi-model council, and monitors system health — all cron-driven |
| `s47-vibe-coding-livekit` | Vibe Coding — voice-controlled AI coding assistant using Deepgram STT, choice of LLM providers, code generation via OpenCode CLI, and Kokoro TTS, with a Python LiveKit agent and React/Vite web client |
| `s48-vibe-coding-ws` | Vibe Coding (WebSocket variant) — Python WebSocket server + single-page vanilla HTML/JS frontend where users speak or type ideas, processed through Deepgram STT → z.ai GLM-4.5 LLM → Kokoro TTS |
| `s49-scratch` | Empty placeholder directory |
