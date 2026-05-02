#!/usr/bin/env python3
"""Vibe Coding Server — WebSocket + STT + LLM + TTS + Code Gen"""

import asyncio, json, base64, os, re, logging, ssl, time
from pathlib import Path

import aiohttp
from aiohttp import web

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("vibe")

DEEPGRAM_KEY = os.environ["DEEPGRAM_API_KEY"]
ZAI_KEY = os.environ["ZAI_API_KEY"]
CHUTES_TOKEN = os.environ["CHUTES_API_TOKEN"]
PORT = int(os.environ.get("PORT", 8765))
WORKSPACE = "/tmp/opencode-workspace"

LANG_VOICES = {
    "en": "af_heart",
    "es": "ef_dora",
}

LANG_INSTRUCTIONS = {
    "en": "Respond in English.",
    "es": "Responde en español.",
}

def make_system_prompt(lang="en"):
    note = LANG_INSTRUCTIONS.get(lang, "Respond in English.")
    asr_note = {
        "en": 'Note: Speech recognition sometimes confuses similar-sounding words ("comment" vs "command", "there" vs "their"). Read the transcript in context, not literally.',
        "es": 'Nota: El reconocimiento de voz a veces confunde palabras que suenan similares. Lee el transcript en contexto, no literalmente.',
    }.get(lang, LANG_INSTRUCTIONS["en"])
    return f"""You are a vibe coding assistant. Help users build software through conversation.

When the user asks you to run a command or write code, output exactly:
[OPencode: <shell command>]
on its own line, then explain what you're doing.

The system will execute the command and return the output. After execution, summarize results.

Available: any shell command (bash, python, ls, mkdir, echo, etc.). For multi-line code, use semicolons or write a temp file with cat.

{asr_note}

{note}

Keep responses conversational and concise."""

convos = {}  # conn_id -> {"lang": str, "voice": str, "messages": [...]}

async def index(request):
    p = Path(__file__).parent / "index.html"
    return web.FileResponse(p) if p.exists() else web.Response(status=404)

async def ws_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    cid = id(ws)
    convos[cid] = {"lang": "en", "voice": "af_heart", "messages": []}
    msg_queue = asyncio.Queue()
    log.info("WS connect %d", cid)

    processing_task = None

    async def processor():
        nonlocal processing_task
        while True:
            item = await msg_queue.get()
            if item is None:
                break
            if item["type"] == "audio":
                processing_task = asyncio.create_task(process_audio(ws, cid, item["data"]))
            elif item["type"] == "text":
                processing_task = asyncio.create_task(process_text(ws, cid, item["text"]))
            try:
                await processing_task
            except asyncio.CancelledError:
                log.info("Interrupt[%d]: cancelled", cid)
            finally:
                processing_task = None

    proc_task = asyncio.create_task(processor())
    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                data = json.loads(msg.data)
                t = data.get("type")
                if t == "config":
                    lang = data.get("lang", "en")
                    convos[cid]["lang"] = lang
                    convos[cid]["voice"] = LANG_VOICES.get(lang, "af_heart")
                    convos[cid]["messages"] = [{"role": "system", "content": make_system_prompt(lang)}]
                    log.info("Config[%d]: lang=%s voice=%s", cid, lang, convos[cid]["voice"])
                elif t == "interrupt":
                    log.info("Interrupt[%d]: requested", cid)
                    if processing_task and not processing_task.done():
                        processing_task.cancel()
                    while not msg_queue.empty():
                        try:
                            msg_queue.get_nowait()
                        except asyncio.QueueEmpty:
                            break
                elif t == "audio":
                    if ws.closed:
                        break
                    msg_queue.put_nowait({"type": "audio", "data": data["data"]})
                    log.info("Audio queued[%d] lang=%s", cid, convos[cid]["lang"])
                elif t == "text":
                    if ws.closed or not data.get("text", "").strip():
                        break
                    msg_queue.put_nowait({"type": "text", "text": data["text"].strip()})
                    log.info("Text queued[%d]: %.60s", cid, data["text"].strip())
                elif t == "client_error":
                    log.error("CLIENT[%d] %s", cid, data.get("message", ""))
                    if s := data.get("stack"):
                        for line in s.split("\n"):
                            log.error("CLIENT[%d]   %s", cid, line)
            elif msg.type == web.WSMsgType.ERROR:
                log.error("WS error: %s", msg.data)
    except asyncio.CancelledError:
        pass
    finally:
        if not proc_task.done():
            msg_queue.put_nowait(None)
            await proc_task
        convos.pop(cid, None)
        log.info("WS disconnect %d", cid)
    return ws

async def process_audio(ws, cid, b64):
    """Voice input: STT then shared LLM+TTS pipeline."""
    if ws.closed:
        return
    if not convos[cid]["messages"]:
        convos[cid]["lang"] = "en"
        convos[cid]["voice"] = LANG_VOICES["en"]
        convos[cid]["messages"] = [{"role": "system", "content": make_system_prompt("en")}]

    try:
        t1 = time.monotonic()
        transcript = await stt(base64.b64decode(b64), convos[cid]["lang"])
        if not transcript.strip():
            log.info("STT[%d]: empty (%.1fs)", cid, time.monotonic() - t1)
            return
        await ws.send_json({"type": "transcript", "text": transcript})
        log.info("STT[%d]: %.60s (%.1fs)", cid, transcript, time.monotonic() - t1)
        convos[cid]["messages"].append({"role": "user", "content": transcript})
        await process_transcript(ws, cid, transcript)
    except Exception as e:
        log.error("STT[%d] error: %s", cid, e)
        if not ws.closed:
            try:
                await ws.send_json({"type": "error", "message": str(e)[:200]})
            except Exception:
                pass


async def process_text(ws, cid, text):
    """Text input: use text directly as transcript, then shared LLM+TTS pipeline."""
    if ws.closed or not text.strip():
        return
    if not convos[cid]["messages"]:
        convos[cid]["lang"] = "en"
        convos[cid]["voice"] = LANG_VOICES["en"]
        convos[cid]["messages"] = [{"role": "system", "content": make_system_prompt("en")}]

    await ws.send_json({"type": "transcript", "text": text})
    log.info("Text[%d]: %.60s", cid, text)
    convos[cid]["messages"].append({"role": "user", "content": text})
    await process_transcript(ws, cid, text)


async def process_transcript(ws, cid, transcript):
    """Shared pipeline: LLM stream + concurrent TTS + command execution."""
    t0 = time.monotonic()
    if ws.closed:
        return

    tts_queue = None
    tts_task = None
    voice = convos[cid]["voice"]
    full = ""
    buf = ""

    try:
        tts_queue = asyncio.Queue()

        async def tts_worker():
            while True:
                sent = await tts_queue.get()
                if sent is None:
                    break
                if ws.closed:
                    continue
                try:
                    wav = await asyncio.wait_for(tts(sent, voice), timeout=30)
                    if wav and not ws.closed:
                        await ws.send_json({"type": "audio_chunk", "data": base64.b64encode(wav).decode(), "format": "wav"})
                except asyncio.TimeoutError:
                    log.warning("TTS[%d] timeout for: %.40s", cid, sent)
                except Exception as e:
                    log.warning("TTS[%d] error: %s", cid, e)
            if not ws.closed:
                try:
                    await ws.send_json({"type": "audio_end"})
                except Exception:
                    pass

        tts_task = asyncio.create_task(tts_worker())

        t2 = time.monotonic()
        chunk_count = 0
        async for chunk in llm(convos[cid]["messages"]):
            if ws.closed:
                break
            full += chunk
            buf += chunk
            chunk_count += 1
            await ws.send_json({"type": "response_chunk", "text": chunk})
            while True:
                m = re.search(r"^(.+?[.!?])\s*", buf)
                if not m:
                    break
                await tts_queue.put(m.group(1))
                buf = buf[m.end():]

        if ws.closed:
            return

        if buf.strip():
            await tts_queue.put(buf.strip())

        log.info("LLM[%d]: %d chunks, %d chars (%.1fs)", cid, chunk_count, len(full), time.monotonic() - t2)
        log.info("RESP[%d]: %.200s", cid, full.strip().replace("\n", " "))

        # Check for command execution
        oc = re.search(r"\[OPencode:\s*(.+?)\]", full)
        if oc:
            task = oc.group(1).strip()
            log.info("Run[%d]: %s", cid, task[:120])
            await ws.send_json({"type": "thinking", "text": f"Running: {task[:60]}..."})
            t3 = time.monotonic()
            result = await run_command(ws, cid, task)
            log.info("Run[%d]: done (%.1fs)", cid, time.monotonic() - t3)
            if not ws.closed:
                await ws.send_json({"type": "code", "code": result[:2000], "summary": task[:200]})

        convos[cid]["messages"].append({"role": "assistant", "content": full})

    except Exception as e:
        log.error("PIPELINE[%d] error: %s", cid, e)
        if not ws.closed:
            try:
                await ws.send_json({"type": "error", "message": str(e)[:200]})
            except Exception:
                pass
    finally:
        if tts_task is not None:
            try:
                await tts_queue.put(None)
                await tts_task
            except (Exception, asyncio.CancelledError):
                pass

    log.info("TOTAL[%d]: %.1fs", cid, time.monotonic() - t0)

async def stt(audio_bytes, lang="en"):
    params = {"model": "nova-3"}
    if lang != "en":
        params["language"] = lang
    hdrs = {"Authorization": f"Token {DEEPGRAM_KEY}", "Content-Type": "audio/webm"}
    async with aiohttp.ClientSession() as s:
        async with s.post("https://api.deepgram.com/v1/listen", headers=hdrs, params=params, data=audio_bytes) as r:
            if r.status != 200:
                raise RuntimeError(f"Deepgram {r.status}: {(await r.text())[:200]}")
            j = await r.json()
            return j.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0].get("transcript", "")

async def llm(messages):
    hdrs = {"Authorization": f"Bearer {ZAI_KEY}", "Content-Type": "application/json"}
    body = {"model": "glm-4.5-air", "messages": messages, "stream": True, "max_tokens": 4096}
    async with aiohttp.ClientSession() as s:
        async with s.post("https://api.z.ai/api/coding/paas/v4/chat/completions", headers=hdrs, json=body) as r:
            if r.status != 200:
                raise RuntimeError(f"z.ai {r.status}: {(await r.text())[:200]}")
            async for line in r.content:
                line = line.decode("utf-8", errors="ignore").strip()
                if line.startswith("data: "):
                    d = line[6:].strip()
                    if d == "[DONE]":
                        break
                    try:
                        delta = json.loads(d).get("choices", [{}])[0].get("delta", {})
                        if c := delta.get("content"):
                            yield c
                    except json.JSONDecodeError:
                        pass

async def run_command(ws, cid, task):
    """Execute a task as a shell command. Returns stdout+stderr output."""
    os.makedirs(WORKSPACE, exist_ok=True)
    # Try to run it as a shell command directly
    try:
        proc = await asyncio.create_subprocess_exec(
            "sh", "-c", task,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT, cwd=WORKSPACE
        )

        async def progress_reporter():
            messages = ["Running...", "Still working...", "Almost done..."]
            idx = 0
            while True:
                await asyncio.sleep(10)
                if proc.returncode is not None:
                    break
                if not ws.closed:
                    try:
                        await ws.send_json({"type": "thinking", "text": messages[idx % len(messages)]})
                    except Exception:
                        pass
                    idx += 1

        reporter = asyncio.create_task(progress_reporter())
        try:
            out, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
        finally:
            reporter.cancel()

        result = out.decode(errors="replace").strip()
        return result or "Done (no output)"
    except asyncio.TimeoutError:
        return "Command timed out after 30s"
    except FileNotFoundError:
        return "Error: shell not found"
    except Exception as e:
        return f"Error: {e}"

async def tts(text, voice="af_heart"):
    hdrs = {"Authorization": f"Bearer {CHUTES_TOKEN}", "Content-Type": "application/json"}
    body = {"text": text, "speed": 1, "voice": voice}
    async with aiohttp.ClientSession() as s:
        async with s.post("https://chutes-kokoro.chutes.ai/speak", headers=hdrs, json=body) as r:
            if r.status != 200:
                raise RuntimeError(f"Kokoro {r.status}: {(await r.text())[:200]}")
            return await r.read()

def make_app():
    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/ws", ws_handler)
    return app

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=PORT)
    p.add_argument("--ssl", action="store_true")
    p.add_argument("--cert", default="/tmp/cert.pem")
    p.add_argument("--key", default="/tmp/key.pem")
    args = p.parse_args()
    ctx = None
    if args.ssl:
        ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ctx.load_cert_chain(args.cert, args.key)
    web.run_app(make_app(), host="0.0.0.0", port=args.port, ssl_context=ctx)
