"""Generate all video variations for comparison."""

import asyncio, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from video_templator import GamingTemplate, TemplateConfig

BASE = '/home/vuos/code/p3/s72'
OUT = f'{BASE}/videos_demo'

SCRIPTS = {
    'news': (
        'Semana intensa en inteligencia artificial. '
        'YouTube anunció que etiquetará automáticamente los videos generados por IA. '
        'Según Simon Willison, Anthropic y OpenAI ya encontraron product market fit. '
        'DuckDuckGo vio un aumento del veintiocho por ciento en búsquedas. '
        'TechCrunch reporta que los CEOs de tecnología sufren de psicosis por la IA. '
        'El índice KOSPI de Corea del Sur subió un ciento por ciento en dos mil veintiséis. '
        'Fujitsu firmó una alianza estratégica con Anthropic. '
        'Trump nombró a Pam Bondi para el panel de IA de la Casa Blanca.'
    ),
    'jobs': (
        'Un estudio global de Oliver Wyman revela datos impactantes. '
        'El cuarenta y tres por ciento de los CEOs planea reducir roles junior. '
        'El año pasado era solo el diecisiete por ciento. '
        'Las contrataciones para posiciones intermedias pasaron del diez al treinta por ciento. '
        'Pero solo el veintisiete por ciento dice que la inversión en IA cumplió expectativas. '
        'El setenta y cuatro por ciento de los CEOs está congelando o reduciendo contrataciones. '
        'La inteligencia artificial está reemplazando tareas de empleados junior.'
    ),
    'business': (
        'Chatbots con inteligencia artificial aumentan la conversión de ventas un treinta y cinco por ciento. '
        'La generación de contenido con IA reduce costos hasta un sesenta por ciento. '
        'La atención al cliente automatizada baja de veinticuatro horas a solo segundos. '
        'El análisis predictivo mejora la retención de clientes en un veinticinco por ciento. '
        'Pero solo el veintisiete por ciento de las empresas ven retorno positivo. '
        'La clave está en implementar con métricas claras y objetivos medibles.'
    ),
}

CONFIGS = [
    # (name_suffix, font_size, max_words, voice, music)
    ('_font96', 96, 5, 'es-MX-DaliaNeural', 'synthwave.mp3'),
    ('_font144', 144, 4, 'es-MX-DaliaNeural', 'synthwave.mp3'),
    ('_font192', 192, 3, 'es-MX-DaliaNeural', 'synthwave.mp3'),
    ('_voice_alvaro', 96, 5, 'es-ES-AlvaroNeural', 'synthwave.mp3'),
    ('_music_default', 96, 5, 'es-MX-DaliaNeural', 'music.mp3'),
]

async def render(topic, script, suffix, font_size, max_words, voice, music_file):
    cfg = TemplateConfig(
        width=1080, height=1920,
        subtitle_font_size=font_size,
        subtitle_stroke_width=max(3.0, font_size / 30),
        subtitle_margin_bottom=160,
        max_words_per_block=max_words,
        min_block_duration_ms=1500,
    )
    tmpl = GamingTemplate(cfg)
    out = await tmpl.render(
        script=script,
        gameplay_primary=f'{BASE}/assets/gameplay/primary.mp4',
        output=f'{OUT}/{topic}{suffix}.mp4',
        gameplay_secondary=f'{BASE}/assets/gameplay/secondary.mp4',
        bg_music=f'{BASE}/assets/audio/{music_file}',
        voice=voice,
        subtitle_format='ass',
    )
    # Get duration
    import subprocess, json
    p = json.loads(subprocess.check_output(['ffprobe','-v','quiet','-print_format','json','-show_format',out]))
    dur = float(p['format']['duration'])
    print(f'  ✅ {topic}{suffix}.mp4  ({dur:.0f}s, font={font_size}, voice={voice.split("-")[1]})')
    return out

async def main():
    print('Rendering variations...\n')
    for topic, script in SCRIPTS.items():
        for suffix, fsize, mw, voice, music in CONFIGS:
            try:
                await render(topic, script, suffix, fsize, mw, voice, music)
            except Exception as e:
                print(f'  ❌ {topic}{suffix}: {e}')
        print()

    print('\nDone! Files in videos_demo/:')
    for f in sorted(os.listdir(OUT)):
        if f.endswith('.mp4'):
            sz = os.path.getsize(f'{OUT}/{f}') / 1024 / 1024
            print(f'  {f:45s} {sz:.1f}MB')

if __name__ == '__main__':
    asyncio.run(main())
