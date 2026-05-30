"""Generate videos with: font96, single-screen, digit numbers, randomized assets, varied real content.

Errors are logged to error_log.txt for later review.
"""

import asyncio, sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from video_templator import GamingTemplate, TemplateConfig
import subprocess, json

BASE = '/home/vuos/code/p3/s72'
OUT = f'{BASE}/videos_demo/v2'
os.makedirs(OUT, exist_ok=True)
os.makedirs(f'{BASE}/logs', exist_ok=True)
ERR_LOG = f'{BASE}/logs/errors_renderv2.txt'

def log(msg: str):
    with open(ERR_LOG, 'a') as f:
        f.write(f'{msg}\n')

# ── Scripts with REAL data, digit numbers ────────────────
SCRIPTS = [
    {
        'name': 'modelos_2026',
        'script': (
            'Este 2026 ha sido un año histórico para la inteligencia artificial. '
            'OpenAI lanzó GPT-5 en febrero con una capacidad de razonamiento 10 veces superior a GPT-4. '
            'DeepSeek lanzó su modelo V3 y R1 compitiendo de frente con OpenAI. '
            'Anthropic lanzó Claude 4 con ventanas de contexto de 200 mil tokens. '
            'Google presentó Gemini 2.5 Pro con capacidades multimodales avanzadas. '
            'Meta lanzó Llama 4 de código abierto con 400 mil millones de parámetros. '
            'Mistral AI lanzó Mistral Large 2 compitiendo en la cima de los rankings. '
            'Nunca antes hubo tanta competencia y avance en tan poco tiempo.'
        ),
    },
    {
        'name': 'ipo_acciones',
        'script': (
            'El mercado de acciones de IA está en ebullición. '
            'CoreWeave, el proveedor de infraestructura cloud para IA, salió a bolsa en marzo 2025 valuado en 35 mil millones de dólares. '
            'SK Hynix duplicó sus ingresos en 2026 gracias a la memoria HBM para chips de IA. '
            'NVIDIA alcanzó una capitalización de 4 billones de dólares en mayo de 2026. '
            'Groq, el fabricante de chips LPU, planea su salida a bolsa para finales de 2026. '
            'El KOSPI de Corea subió un 100% impulsado por fabricantes de chips de IA. '
            'Empresas de infraestructura energética para centros de datos también se dispararon.'
        ),
    },
    {
        'name': 'open_source',
        'script': (
            'El ecosistema open source de IA está explosivo. '
            'Hugging Face superó el millón de modelos publicados en su plataforma. '
            'Stable Diffusion 4 lanzado con generación de video incluida. '
            'Llama 4 de Meta se ha descargado más de 300 millones de veces desde su lanzamiento. '
            'El framework LangChain alcanzó 100 mil estrellas en GitHub. '
            'El proyecto Olama para ejecutar modelos localmente creció un 500% en usuarios. '
            'Whisper de OpenAI sigue siendo el estándar de facto para transcripción open source. '
            'La comunidad open source está democratizando el acceso a la IA.'
        ),
    },
    {
        'name': 'cadena_suministro',
        'script': (
            'Hay empresas clave en la cadena de suministro de IA que pocos conocen. '
            'TSMC fabrica el 90% de los chips avanzados del mundo para inteligencia artificial. '
            'ASML tiene el monopolio de las máquinas de litografía ultravioleta extrema. '
            'Vertiv y Schneider Electric fabrican los sistemas de enfriamiento para centros de datos. '
            'Coherent fabrica los láseres necesarios para la litografía de chips de IA. '
            'Estas empresas son esenciales para toda la industria y nadie habla de ellas. '
            'Conocer la cadena de suministro permite entender dónde está el verdadero valor de la IA.'
        ),
    },
    {
        'name': 'startups_ia',
        'script': (
            'Las startups de IA están redefiniendo industrias enteras. '
            'Harvey AI, asistente legal con IA, alcanzó 3 mil millones de dólares de valuación. '
            'Synthesia, generación de video con avatares IA, llegó a 2 mil millones. '
            'Eleven Labs, clonación de voces con IA, alcanzó 100 millones de dólares en ingresos recurrentes. '
            'Perplexity AI, el buscador conversacional, superó los 15 millones de usuarios activos mensuales. '
            'Cognition Labs lanzó Devin, el primer ingeniero de software IA. '
            'Todas estas startups crecieron más de un 300% en el último año.'
        ),
    },
]

# Available assets
GAMEPLAYS = [
    f'{BASE}/assets/gameplay/bg1.mp4',
    f'{BASE}/assets/gameplay/bg2.mp4',
    f'{BASE}/assets/gameplay/bg3.mp4',
    f'{BASE}/assets/gameplay/primary.mp4',
]
MUSICS = [
    f'{BASE}/assets/audio/synthwave.mp3',
    f'{BASE}/assets/audio/music1.mp3',
    f'{BASE}/assets/audio/music2.mp3',
    f'{BASE}/assets/audio/music.mp3',
]

async def render_one(cfg, script_data):
    name = script_data['name']
    gp = random.choice(GAMEPLAYS)
    mu = random.choice(MUSICS)

    out = await cfg.render(
        script=script_data['script'],
        gameplay_primary=gp,
        output=f'{OUT}/{name}.mp4',
        bg_music=mu,
        subtitle_format='ass',
    )

    # Verify
    p = subprocess.run(['ffprobe','-v','quiet','-print_format','json','-show_format',out],
                       capture_output=True, text=True)
    info = json.loads(p.stdout)
    dur = float(info['format']['duration'])
    sz = int(info['format']['size'])/1024/1024
    print(f'  ✅ {name}.mp4  {dur:.0f}s  {sz:.0f}MB  bg={os.path.basename(gp)} music={os.path.basename(mu)}')
    return out

async def main():
    tpl_cfg = TemplateConfig(
        width=1080, height=1920,
        subtitle_font_size=96,
        subtitle_stroke_width=3.0,
        subtitle_margin_bottom=160,
        max_words_per_block=5,
        min_block_duration_ms=1500,
    )
    template = GamingTemplate(tpl_cfg)

    print(f'Rendering {len(SCRIPTS)} videos with randomized assets...\n')
    for i, sd in enumerate(SCRIPTS, 1):
        try:
            print(f'[{i}/{len(SCRIPTS)}] {sd["name"]}...')
            await render_one(template, sd)
        except Exception as e:
            msg = f'❌ {sd["name"]}: {e}'
            print(f'  {msg}')
            log(msg)

    print(f'\nDone! Files in {OUT}/')
    print(f'Errors logged to {ERR_LOG}')

if __name__ == '__main__':
    asyncio.run(main())
