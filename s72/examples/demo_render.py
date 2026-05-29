"""Demo: generate 3 videos using video-templator with real-world data.

Videos:
  1. AI News of the Week (May 27, 2026)
  2. How AI Is Reshaping the Job Market (Oliver Wyman CEO survey data)
  3. AI for Online Business — Concrete Numbers

Each uses: GamingTemplate (ReVid style) + edge-tts + ASS karaoke subs + ffmpeg.
"""

import asyncio
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from video_templator import GamingTemplate


SCRIPTS = {
    "ai_news_week": {
        "title": "IA Noticias de la Semana — 27 Mayo 2026",
        "script": (
            "Semana intensa en inteligencia artificial. "
            "YouTube anunció que etiquetará automáticamente los videos generados por IA. "
            "Según Simon Willison, Anthropic y OpenAI ya encontraron product market fit. "
            "DuckDuckGo vio un aumento del veintiocho por ciento en búsquedas tras el modo IA de Google. "
            "TechCrunch reporta que los CEOs de tecnología sufren de psicosis por la IA. "
            "Y el índice KOSPI de Corea del Sur subió un ciento por ciento en dos mil veintiséis impulsado por acciones de chips de IA. "
            "Fujitsu firmó una alianza estratégica con Anthropic. "
            "Todo esto pasó esta semana. "
            "La inteligencia artificial no se detiene."
        ),
        "voice": "es-MX-DaliaNeural",
    },
    "ai_job_market": {
        "title": "IA y el Mercado Laboral — Datos Concretos",
        "script": (
            "Un estudio global de Oliver Wyman revela datos impactantes. "
            "El cuarenta y tres por ciento de los CEOs planea reducir roles junior en los próximos dos años. "
            "El año pasado era solo el diecisiete por ciento. "
            "Los que contratan para posiciones intermedias pasaron del diez al treinta por ciento. "
            "Pero solo el veintisiete por ciento dice que la inversión en IA cumplió expectativas. "
            "El setenta y cuatro por ciento de los CEOs está congelando o reduciendo contrataciones. "
            "La IA está reemplazando tareas de empleados junior. "
            "Y las empresas aún no ven el retorno de inversión prometido. "
            "El mercado laboral está cambiando más rápido de lo que creemos."
        ),
        "voice": "es-MX-DaliaNeural",
    },
    "ai_online_business": {
        "title": "IA para Negocios Online — Números Reales",
        "script": (
            "La inteligencia artificial ya está transformando negocios online con cifras concretas. "
            "Empresas que usan chatbots con IA reportan aumento del treinta y cinco por ciento en conversión de ventas. "
            "La generación de contenido con IA reduce costos hasta un sesenta por ciento comparado con métodos tradicionales. "
            "Automatización de atención al cliente con IA reduce tiempos de respuesta de veinticuatro horas a solo segundos. "
            "El análisis predictivo de IA mejora la retención de clientes en un veinticinco por ciento. "
            "Pero ojo, solo el veintisiete por ciento de las empresas ven retorno positivo. "
            "La clave está en implementar con métricas claras y medir resultados. "
            "No se trata de reemplazar, sino de aumentar capacidades."
        ),
        "voice": "es-MX-DaliaNeural",
    },
}


async def render_video(
    key: str,
    data: dict,
    output_dir: str,
    bg_primary: str,
    bg_secondary: str = None,
    bg_music: str = None,
) -> dict:
    """Render one video and return metadata about the result."""
    output_path = os.path.join(output_dir, f"{key}.mp4")

    template = GamingTemplate()

    print(f"\n{'='*60}")
    print(f"Rendering: {data['title']}")
    print(f"  Output: {output_path}")
    print(f"{'='*60}")

    result = await template.render(
        script=data["script"],
        gameplay_primary=bg_primary,
        output=output_path,
        gameplay_secondary=bg_secondary,
        bg_music=bg_music,
        voice=data["voice"],
        subtitle_format="ass",
    )

    # Get file info
    info = {"key": key, "title": data["title"], "output": result}
    try:
        import subprocess

        probe = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                result,
            ],
            capture_output=True, text=True,
        )
        info["probe"] = json.loads(probe.stdout)
    except Exception as e:
        info["probe_error"] = str(e)

    return info


async def main():
    output_dir = "/tmp/video_demo"
    os.makedirs(output_dir, exist_ok=True)

    bg_primary = "/tmp/bg_primary.mp4"
    bg_secondary = "/tmp/bg_secondary.mp4"
    bg_music = "/tmp/bg_music.mp3"

    # Verify backgrounds exist
    for f in [bg_primary, bg_secondary, bg_music]:
        if not os.path.exists(f):
            print(f"ERROR: Missing background file: {f}")
            sys.exit(1)

    results = []
    for key, data in SCRIPTS.items():
        try:
            info = await render_video(
                key, data, output_dir,
                bg_primary=bg_primary,
                bg_secondary=bg_secondary,
                bg_music=bg_music,
            )
            results.append(info)
        except Exception as e:
            print(f"\n  FAILED: {e}")
            results.append({"key": key, "title": data["title"], "error": str(e)})

    # Print summary
    print(f"\n\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for r in results:
        status = "✅" if "probe" in r else "❌"
        size = ""
        duration = ""
        if "probe" in r:
            fmt = r["probe"].get("format", {})
            size_mb = int(fmt.get("size", 0)) / 1024 / 1024
            dur = float(fmt.get("duration", 0))
            size = f"{size_mb:.1f}MB"
            duration = f"{dur:.1f}s"
            # Show subtitle info
            for s in r["probe"].get("streams", []):
                if s["codec_type"] == "audio":
                    duration = f"{float(s.get('duration', 0)):.1f}s"

        print(f"  {status} {r['title']}")
        if size or duration:
            print(f"     File: {size} | Duration: {duration}")
        if "error" in r:
            print(f"     ERROR: {r['error']}")
        print()

    # Save metadata
    summary_path = os.path.join(output_dir, "_summary.json")
    with open(summary_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"Summary saved: {summary_path}")


if __name__ == "__main__":
    asyncio.run(main())
