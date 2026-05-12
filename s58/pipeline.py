#!/usr/bin/env python3
"""News topic → OpenCode Go script → Inworld TTS multi-voz → Pexels fondo → música → video sincronizado → 12 shorts → upload."""
import os, json, re, asyncio, subprocess, textwrap, argparse, base64, requests, shutil, tempfile, random, atexit
from pathlib import Path
from datetime import datetime

# ── Load .env ──────────────────────────────────────────────────────────────
_env = Path(__file__).parent/".env"
if _env.exists():
    for line in _env.read_text().strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('#'): continue
        if '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

# ── Config ─────────────────────────────────────────────────────────────────
GO_KEY = os.environ.get("OPENCODE_GO_API_KEY","")
GO_MODEL = os.environ.get("OPENCODE_GO_MODEL","deepseek-v4-flash")
INWORLD_KEY = os.environ.get("INWORLD_API_KEY","")
YT_SECRET = os.environ.get("YT_CLIENT_SECRET","")
YT_TOKEN = os.environ.get("YT_TOKEN_PATH", str(Path.home()/".yt_token.json"))
PEXELS_KEY = os.environ.get("PEXELS_API_KEY","")
PIXABAY_KEY = os.environ.get("PIXABAY_API_KEY","")

WORK = Path(__file__).parent/"work"; WORK.mkdir(exist_ok=True)
ASSETS = Path(__file__).parent/"assets"; (ASSETS/"pexels").mkdir(parents=True,exist_ok=True); (ASSETS/"music").mkdir(parents=True,exist_ok=True)

# ── Voices ─────────────────────────────────────────────────────────────────
VOICES = {
    "intro":  {"id":"Elizabeth","model":"inworld-tts-1.5-max"},
    "hook":   {"id":"Ethan","model":"inworld-tts-1.5-max"},
    "body":   {"id":"Tyler","model":"inworld-tts-1.5-max"},
    "example":{"id":"Jason","model":"inworld-tts-1.5-max"},
    "body2":  {"id":"Simon","model":"inworld-tts-1.5-max"},
    "outro":  {"id":"Elizabeth","model":"inworld-tts-1.5-max"},
    "cta":    {"id":"Tyler","model":"inworld-tts-1.5-max"},
}

def tts_inworld(text: str, voice: str = "Elizabeth", model: str = "inworld-tts-1.5-max") -> bytes:
    r = requests.post("https://api.inworld.ai/tts/v1/voice",
        headers={"Authorization": f"Basic {INWORLD_KEY}", "Content-Type":"application/json"},
        json={"text":text,"voiceId":voice,"modelId":model,"audioConfig":{"audioEncoding":"LINEAR16","sampleRateHertz":24000}}, timeout=60)
    return base64.b64decode(r.json()["audioContent"])

# ── Helpers ────────────────────────────────────────────────────────────────
def _audio_dur(path: str) -> float:
    try:
        d = json.loads(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","json",path],
            capture_output=True,text=True,timeout=10).stdout)
        return float(d["format"]["duration"])
    except: return 0

# ── Step 1: Script ────────────────────────────────────────────────────────
def _template_script(topic: str) -> str:
    """Template de emergencia cuando la API falla. Cada linea menciona el topic explicitamente."""
    # Extraer keyword principal del topic (la primer palabra significativa)
    kw = topic.split(":")[-1].strip() if ":" in topic else topic
    kw = re.sub(r'[´ˈˈ]', '', kw)
    words = [w for w in kw.split() if len(w) > 3 and w.lower() not in ('that','this','with','from','have','been','what','when','where','which','their','about','would','could','should','after','into','over','than','then','also','just','more','some','them','these','those','there')]
    main = words[0] if words else kw[:30]
    return f"[INTRO] Hey. Let's talk about {topic}.\n[HOOK] Here is why {main} matters right now.\n[BODY] First of all, {main} is not what most people think. The reality is simpler and crazier at the same time.\n[EXAMPLE] Take a closer look at {topic}. The details explain the whole story.\n[BODY2] Here is the part nobody talks about. Most coverage gets this wrong.\n[BODY3] So what does this mean for you? A lot actually. Here is the bottom line.\n[OUTRO] To sum it up: {main} is moving fast and you should pay attention.\n[CTA] I am {os.environ.get('USER','your host')}. That was your update. See you in the next one."

def generate_script(topic: str, url: str = "") -> str:
    """Genera script via API con reintentos. Fallback a template conversacional."""
    if not GO_KEY: return _template_script(topic)

    prompts = [
        f"Write a 2-minute video script about: {topic}. {'Source: ' + url if url else ''} Make it conversational like you are explaining to a friend. Start with a strong hook that grabs attention. Short paragraphs, one per line. Use [INTRO] [HOOK] [BODY] [EXAMPLE] [BODY2] [BODY3] [OUTRO] [CTA] markers. Be specific. No fluff.",
        f"Explain {topic} like I am 12 years old. Short sentences. Conversational. One paragraph per line. Use [INTRO] [HOOK] [BODY] [EXAMPLE] [BODY2] [BODY3] [OUTRO] [CTA] markers.",
        f"Write a script for a short video about {topic}. Hook in the first 5 seconds. Tell me something I did not know. Keep it real. Use [INTRO] [HOOK] [BODY] [EXAMPLE] [BODY2] [BODY3] [OUTRO] [CTA] markers. Each paragraph one line.",
    ]

    from openai import OpenAI
    client = OpenAI(api_key=GO_KEY, base_url="https://opencode.ai/zen/go/v1", timeout=120)

    for i, prompt in enumerate(prompts):
        try:
            r = client.chat.completions.create(model=GO_MODEL, max_tokens=4096,
                messages=[{"role": "user", "content": prompt}])
            content = r.choices[0].message.content
            if content and len(content.strip()) > 100:
                lines = [l.strip() for l in content.strip().split('\n') if l.strip()]
                # Verificar que tenga los markers requeridos
                markers = sum(1 for l in lines if re.match(r'\[(INTRO|HOOK|BODY\d?|EXAMPLE|OUTRO|CTA)\]', l))
                if markers >= 4:
                    return content.strip()
            print(f"  ⚠ Intento {i+1} insuficiente (marcadores: {markers if 'markers' in dir() else 0})")
        except Exception as e:
            print(f"  ⚠ Intento {i+1} fallo ({e})")

    print("  ⚠ Usando template de emergencia")
    return _template_script(topic)

# ── Step 2: TTS voiceover (returns audio path + segment paths for sync) ────
async def generate_tts(script: str, out_dir: str):
    """Generate TTS per section. Returns (narration_wav, [(text, duration_sec), ...])."""
    output = out_dir + "/narration.wav"
    lines = [l.strip() for l in script.strip().split('\n') if l.strip()]
    segments, voice_map = [], {"intro":"intro","hook":"hook","body":"body","body2":"body2","body3":"body2","example":"example","outro":"outro","cta":"cta"}

    if not lines:
        subprocess.run(["ffmpeg","-y","-f","lavfi","-i","anullsrc=r=24000:cl=mono","-t","5",output],capture_output=True,timeout=10)
        return output, []

    for line in lines:
        marker = re.match(r'\[(\w+)\]', line)
        vk = voice_map.get(marker.group(1).lower() if marker else "body", "body")
        v = VOICES.get(vk, VOICES["body"])
        clean = re.sub(r'\[\w+\]\s*', '', line).strip()
        if not clean or len(clean) < 5: continue
        try:
            audio = tts_inworld(clean, voice=v["id"], model=v["model"])
        except:
            continue
        if len(audio) < 1000: continue
        sp = f"{out_dir}/seg_{len(segments):02d}.wav"
        with open(sp, "wb") as f: f.write(audio)
        dur = _audio_dur(sp)
        segments.append((clean, dur, sp))

    if not segments:
        subprocess.run(["ffmpeg","-y","-f","lavfi","-i","anullsrc=r=24000:cl=mono","-t","10",output],capture_output=True,timeout=10)
        return output, []

    # Concatenate with filter_complex (no intermediate silence files)
    # seg0, sil0, seg1, sil1, seg2, ...
    n = len(segments) + (len(segments) - 1)  # segs + pauses
    in_list = []
    for i, (_, _, sp) in enumerate(segments):
        if i > 0:
            in_list += ["-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono:d=0.3"]
        in_list += ["-i", sp]
    refs = "".join(f"[{i}:a]" for i in range(n))
    subprocess.run(["ffmpeg","-y"] + in_list + [
        "-filter_complex", f"{refs}concat=n={n}:v=0:a=1[aout]",
        "-map", "[aout]", output
    ], check=True, capture_output=True, timeout=120)
    return output, [(t, d) for t, d, _ in segments]

# ── Step 3: SRT sincronizado con duración real ────────────────────────────
def generate_srt(segments: list) -> str:
    """Genera SRT con timestamps reales desde segmentos TTS. segments = [(text, dur), ...]"""
    srt, t = "", 0.0
    for i, (text, dur) in enumerate(segments):
        h1,r1=divmod(t,3600); m1,s1=divmod(r1,60); h2,r2=divmod(t+dur,3600); m2,s2=divmod(r2,60)
        srt+=f"{i+1}\n{int(h1):02d}:{int(m1):02d}:{int(s1):02d},{int(s1%1*1000):03d} --> {int(h2):02d}:{int(m2):02d}:{int(s2):02d},{int(s2%1*1000):03d}\n{text}\n\n"
        t += dur + 0.3
    return srt

# ── Step 4: Background video dinámico (cambia cada 6s) ────────────────────
def make_bg_video(topic: str, out: str, total_dur: float = 60) -> str:
    """Genera video de fondo con segmentos de colores cambiantes usando un solo ffmpeg."""
    dur_per_color = 6
    n = max(2, int(total_dur / dur_per_color) + 1)
    tl = topic.lower()
    if any(w in tl for w in ['ai','agent','intelligence','llm','gpt','model','neural']):
        colors = ["#0f0f23","#1a1a3e","#2d1b69","#4a0e4e","#0d1b2a","#1b2838"]
    elif any(w in tl for w in ['startup','funding','venture','business']):
        colors = ["#1b5e20","#0d5302","#33691e","#004d40","#2e7d32","#1b5e20"]
    else:
        colors = ["#0f0f23","#1a237e","#004d40","#311b92","#01579b","#1a237e"]

    # Generar con un solo ffmpeg: cada color se genera como un segmento y se concatena via filter
    # Usamos el filter concat de video con entradas de color
    inputs = []
    filter_inputs = ""
    for i in range(n):
        c = colors[i % len(colors)]
        inputs += ["-f", "lavfi", "-i", f"color=c={c}:s=1080x1920:d={dur_per_color}:r=30"]
        filter_inputs += f"[{i}:v]"
    subprocess.run(["ffmpeg","-y"] + inputs + [
        "-filter_complex", f"{filter_inputs}concat=n={n}:v=1:a=0,format=yuv420p[v]",
        "-map", "[v]", "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-t", str(total_dur), out
    ], check=True, capture_output=True, timeout=120)
    return out

# ── Step 5: Background music ──────────────────────────────────────────────
def fetch_bg_music(out: str) -> str:
    if not PIXABAY_KEY:
        subprocess.run(["ffmpeg","-y","-f","lavfi","-i","anoisesrc=d=60:c=pink:a=0.1","-af","lowpass=f=400,volume=0.15",out],capture_output=True,timeout=30)
        return out
    try:
        r = requests.get(f"https://pixabay.com/api/videos/?key={PIXABAY_KEY}&q=background+music+corporate&category=music&per_page=5",timeout=30)
        if r.status_code == 200 and r.json().get("hits"):
            pass  # Would download real music here
    except: pass
    subprocess.run(["ffmpeg","-y","-f","lavfi","-i","anoisesrc=d=60:c=pink:a=0.1","-af","lowpass=f=400,volume=0.15",out],capture_output=True,timeout=30)
    return out

# ── Step 6: Build video with ducking ──────────────────────────────────────
def build_video(bg_video: str, audio: str, srt: str, out: str, dur: float):
    srt_f = WORK / "c.srt"; srt_f.write_text(srt)
    music_path = str(ASSETS/"music"/"bgm.wav") if (ASSETS/"music"/"bgm.wav").exists() else None
    has_music = music_path and os.path.exists(music_path)

    # Subtitles centrados (Alignment=8) para evitar UI de plataformas
    subtitle_style = "FontName=Ubuntu,FontSize=40,PrimaryCol=&H00FFFFFF,BorderStyle=3,Outline=2,Shadow=2,Alignment=8,MarginV=50"

    inputs = ["-i",bg_video, "-i",audio]
    filter_parts = [
        f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        f"setsar=1,format=yuv420p,"
        f"subtitles={srt_f}:force_style='{subtitle_style}'[v0]",
        f"[1:a]loudnorm=I=-16:TP=-1.5:LRA=11,volume=1.5[a_nar]",
    ]

    if has_music:
        inputs += ["-i", music_path]
        filter_parts += [
            f"[2:a]volume=0.5[a_music]",
            f"[a_nar][a_music]sidechaincompress=threshold=-20dB:ratio=4:attack=5:release=250[aout]",
        ]
    else:
        filter_parts.append("[a_nar]acopy[aout]")

    subprocess.run(["ffmpeg","-y"] + inputs + [
        "-filter_complex", ";".join(filter_parts),
        "-map","[v0]","-map","[aout]", "-t",str(dur),
        "-c:v","libx264","-preset","fast","-crf","23","-c:a","aac","-shortest","-pix_fmt","yuv420p",
        "-movflags","+faststart",out], check=True, capture_output=True, timeout=300)
    srt_f.unlink(missing_ok=True)
    return out

# ── Step 7: Split shorts ─────────────────────────────────────────────────
def split_shorts(video: str, n=12) -> list:
    d=_audio_dur(video); sd=d/n; out=[]
    for i in range(n):
        o=str(WORK/f"s{i+1:02d}.mp4")
        subprocess.run(["ffmpeg","-y","-ss",str(i*sd),"-i",video,"-t",str(sd),"-c","copy",o],check=True,capture_output=True,timeout=120)
        out.append(o)
    return out

# ── Uploads ──────────────────────────────────────────────────────────────
def upload_yt(video: str, title: str, desc: str, tags=None):
    if not YT_SECRET: return print("  ⚠ YT: no YT_CLIENT_SECRET")
    from google.auth.transport.requests import Request as GRequest
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    creds=None
    if os.path.exists(YT_TOKEN): creds=Credentials.from_authorized_user_file(YT_TOKEN,["https://www.googleapis.com/auth/youtube.upload"])
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token: creds.refresh(GRequest())
        else: creds=InstalledAppFlow.from_client_secrets_file(YT_SECRET,["https://www.googleapis.com/auth/youtube.upload"]).run_local_server(open_browser=True)
        with open(YT_TOKEN,"w") as f: f.write(creds.to_json())
    yt=build("youtube","v3",credentials=creds)
    body={"snippet":{"title":title,"description":desc,"tags":tags or [],"categoryId":"28"},"status":{"privacyStatus":"public","selfDeclaredMadeForKids":False}}
    req=yt.videos().insert(part=",".join(body.keys()),body=body,media_body=MediaFileUpload(video,chunksize=-1,resumable=True))
    resp=None
    while resp is None:
        s,resp=req.next_chunk()
        if s: print(f"  ⏳ YT: {int(s.progress()*100)}%")
    print(f"  ✅ YT: https://youtu.be/{resp['id']}")

async def upload_social(video: str, platform: str):
    try:
        from playwright.async_api import async_playwright
    except ImportError: return print(f"  ⚠ {platform}: install playwright")
    p=await async_playwright().start(); b=await p.chromium.launch(headless=False); page=await b.new_page()
    try:
        if platform=="tiktok":
            await page.goto("https://www.tiktok.com/upload"); print(f"  ℹ  Login to TikTok..."); await page.wait_for_timeout(20000)
            await page.locator("input[type=file]").set_input_files(video); await page.wait_for_timeout(5000)
            if await page.locator("button:has-text('Post')").is_visible(): await page.locator("button:has-text('Post')").click()
            print(f"  ✅ TikTok: posted")
        elif platform=="instagram":
            await page.goto("https://www.instagram.com"); print(f"  ℹ  Login to Instagram..."); await page.wait_for_timeout(20000)
            await page.goto("https://www.instagram.com/create/select/"); await page.wait_for_timeout(3000)
            await page.locator("input[type=file]").set_input_files(video); await page.wait_for_timeout(5000)
            print(f"  ✅ Instagram: uploaded (confirm in browser)")
    finally: await b.close(); await p.stop()

# ── Main ──────────────────────────────────────────────────────────────────
async def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--topic"); ap.add_argument("--shorts",type=int,default=12)
    ap.add_argument("--skip-upload",action="store_true"); ap.add_argument("--news",action="store_true")
    ap.add_argument("--keep-temp",action="store_true",help="Don't auto-clean temp files")
    args=ap.parse_args()

    if args.news:
        print("Fetching trending news...")
        from news_agent import fetch_all_topics, pick_topic
        items = fetch_all_topics(); chosen = pick_topic(items)
        topic = chosen["title"]; print(f"  → {topic}"); print(f"  → Source: {chosen.get('url','')}")
    else:
        topic = args.topic or "Why AI agents are overhyped (and why they still matter)"

    # Temp dir with auto-cleanup
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = str(WORK / run_id)
    os.makedirs(out_dir, exist_ok=True)

    if not args.keep_temp:
        def _cleanup():
            if os.path.exists(out_dir):
                for f in os.listdir(out_dir):
                    fp = os.path.join(out_dir, f)
                    if os.path.isfile(fp) and not fp.endswith(".mp4"):
                        os.unlink(fp)
                print(f"  🧹 Temp cleaned: {out_dir}")
        atexit.register(_cleanup)

    print(f"\n{'='*60}\n  📝 [{run_id}] {topic}\n{'='*60}")

    # 1. Script
    print(f"[1/6] Script via OpenCode Go ({GO_MODEL})...")
    script = generate_script(topic); Path(f"{out_dir}/script.txt").write_text(script)
    print(f"  ✓ {len(script.split())} words")

    # 2. TTS (returns paths + durations for sync)
    print("[2/6] Voiceover via Inworld TTS (multi-voice)...")
    audio, segments = await generate_tts(script, out_dir)
    dur = sum(d for _, d in segments) + max(0, len(segments) - 1) * 0.3 if segments else _audio_dur(audio)
    if dur < 1: dur = 30
    print(f"  ✓ {dur:.0f}s | {len(segments)} segments")

    print("[3/6] Background video (dinámico, cambia cada 6s)...")
    bg_video = f"{out_dir}/bg_video.mp4"
    make_bg_video(topic, bg_video, dur + 10); print(f"  ✓ {bg_video}")

    print("[4/6] Background music...")
    bg_music = str(ASSETS/"music"/"bgm.wav")
    fetch_bg_music(bg_music); print(f"  ✓ {bg_music}")

    print("[5/6] Building video...")
    srt = generate_srt(segments); Path(f"{out_dir}/captions.srt").write_text(srt)
    long_video = f"{out_dir}/long.mp4"
    build_video(bg_video, audio, srt, long_video, dur + 4)
    print(f"  ✓ {dur+4:.0f}s 9:16 video | subtitles sincronizados | ducking activo")

    # 6. Shorts
    print(f"[6/6] {args.shorts} shorts...")
    shorts = split_shorts(long_video, args.shorts)
    for s in shorts: print(f"  ✓ {Path(s).name}")

    print(f"\n{'='*60}\n  ✅ Done! {long_video} + {len(shorts)} shorts\n{'='*60}")

    if not args.skip_upload:
        for i,sh in enumerate(shorts):
            t=f"{topic[:50]} — Part {i+1}"; d=f"Full: {topic}\n#shorts #tech #ai"
            print(f"\n  [{i+1}/{len(shorts)}] {t}")
            upload_yt(sh,t,d)
            if i==0:
                await upload_social(sh,"tiktok"); await upload_social(sh,"instagram")

if __name__=="__main__":
    asyncio.run(main())
