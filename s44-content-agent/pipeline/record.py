"""
Screen Recording Module
Uses Playwright to record browser-based software interactions.
Can also output Testreel-compatible JSON configs for polished recordings.
"""

import json
import subprocess
import tempfile as _tempfile
import os
from pathlib import Path

TMP = Path(__file__).parent.parent / "tmp"
TMP.mkdir(parents=True, exist_ok=True)
def tmpdir(**kw):
    if "dir" not in kw: kw["dir"] = str(TMP)
    return _tempfile.mkdtemp(**kw)
def tmpfile(**kw):
    if "dir" not in kw: kw["dir"] = str(TMP)
    return _tempfile.mktemp(**kw)


# Testreel-compatible step templates
RECORDING_ACTIONS = {
    "click": {"action": "click", "selector": None},
    "type": {"action": "type", "selector": None, "text": None},
    "fill": {"action": "fill", "selector": None, "text": None},
    "scroll": {"action": "scroll", "x": 0, "y": 300},
    "hover": {"action": "hover", "selector": None},
    "wait": {"action": "wait", "ms": 1500},
    "screenshot": {"action": "screenshot"},
    "navigate": {"action": "navigate", "url": None},
    "zoom": {"action": "zoom", "selector": None},
    "waitForNetwork": {"action": "waitForNetwork"},
}


def create_testreel_config(url: str, steps: list,
                           output_format: str = "mp4",
                           viewport: dict = None,
                           chrome: bool = True,
                           background: bool = True) -> dict:
    """
    Create a Testreel-compatible recording configuration.
    
    steps: list of dicts with keys matching RECORDING_ACTIONS
    """
    if viewport is None:
        viewport = {"width": 1280, "height": 720}

    config = {
        "url": url,
        "viewport": viewport,
        "outputSize": viewport,
        "outputFormat": output_format,
        "cursor": {"enabled": True, "style": "pointer", "ripple": True},
        "chrome": {"enabled": chrome, "url": True},
        "background": {
            "enabled": background,
            "gradient": {"from": "#1e1b4b", "to": "#4c1d95"},
            "padding": 40,
            "borderRadius": 12,
        },
        "steps": steps,
    }

    return config


def generate_recording_steps_from_script(script_data: list) -> list:
    """
    Convert a high-level script description into Testreel steps.
    script_data is a list of dicts like:
      {"action": "navigate", "url": "..."}
      {"action": "click", "selector": "...", "wait": 1000}
      {"action": "type", "selector": "...", "text": "..."}
      {"action": "scroll"}
    """
    supported = {
        "click": lambda s: {
            "action": "click",
            "selector": s.get("selector", "body"),
            "pauseAfter": s.get("wait", 800),
            **(s.get("zoom", False) and {"zoom": True} or {})
        },
        "type": lambda s: {
            "action": "type",
            "selector": s.get("selector", "input"),
            "text": s.get("text", ""),
            "pauseAfter": s.get("wait", 500),
        },
        "fill": lambda s: {
            "action": "fill",
            "selector": s.get("selector", "input"),
            "text": s.get("text", ""),
            "pauseAfter": s.get("wait", 500),
        },
        "navigate": lambda s: {
            "action": "navigate",
            "url": s.get("url", ""),
            "pauseAfter": s.get("wait", 2000),
        },
        "scroll": lambda s: {
            "action": "scroll",
            "selector": s.get("selector", "body"),
            "x": s.get("x", 0),
            "y": s.get("y", 400),
            "pauseAfter": s.get("wait", 500),
        },
        "hover": lambda s: {
            "action": "hover",
            "selector": s.get("selector", "body"),
            "pauseAfter": s.get("wait", 800),
        },
        "wait": lambda s: {
            "action": "wait",
            "ms": s.get("ms", 2000),
        },
        "screenshot": lambda s: {
            "action": "screenshot",
            "pauseAfter": 200,
        },
        "zoom": lambda s: {
            "action": "zoom",
            "selector": s.get("selector", "body"),
        },
    }

    steps = []
    for step in script_data:
        action = step.get("action", "wait")
        handler = supported.get(action)
        if handler:
            steps.append(handler(step))

    return steps


def record_with_playwright(config_path: str, output_dir: str = None) -> str:
    """
    Execute a Testreel recording from a config file.
    Returns path to the output video file.
    """
    if output_dir is None:
        output_dir = tmpdir(prefix="recording_")

    cmd = [
        "npx", "testreel", config_path,
        "--output", output_dir,
        "--quiet",
    ]

    result = subprocess.run(cmd, capture_output=True, timeout=120)
    if result.returncode != 0:
        stderr = result.stderr.decode()[:1000]
        raise RuntimeError(f"Recording failed: {stderr}")

    # Find the output video
    out_dir = Path(output_dir)
    videos = list(out_dir.glob("*.mp4")) + list(out_dir.glob("*.webm"))
    if videos:
        return str(videos[0])

    return output_dir


def record_simple_playwright(url: str, steps: list,
                              output_path: str = "/tmp/recording.mp4") -> str:
    """
    Simple Playwright recording without Testreel dependency.
    Uses a standalone Playwright script.
    """
    script_content = f"""
const {{ chromium }} = require('playwright');

(async () => {{
    const browser = await chromium.launch({{ headless: true }});
    const context = await browser.newContext({{
        viewport: {{ width: 1280, height: 720 }},
        recordVideo: {{ dir: '{output_path}.temp', size: {{ width: 1280, height: 720 }} }}
    }});
    const page = await context.newPage();
    
    await page.goto('{url}', {{ waitUntil: 'networkidle' }});
    
    {generate_playwright_steps(steps)}
    
    await context.close();
    await browser.close();
    
    // Rename the recorded video
    const fs = require('fs');
    const videos = fs.readdirSync('{output_path}.temp');
    if (videos.length > 0) {{
        fs.renameSync(
            `${{'{output_path}'}.temp}}/${{videos[0]}}`,
            '{output_path}'
        );
    }}
}})();
"""
    script_file = tmpfile(suffix=".js")
    with open(script_file, "w") as f:
        f.write(script_content)

    result = subprocess.run([
        "npx", "playwright", "test", "--browser", "chromium", script_file
    ], capture_output=True, timeout=60)

    # Fallback: try Node directly
    if result.returncode != 0:
        result = subprocess.run(["node", script_file], capture_output=True, timeout=60)

    return output_path


def generate_playwright_steps(steps: list) -> str:
    """Generate Playwright API calls from step descriptions."""
    code_lines = []
    for step in steps:
        action = step.get("action", "wait")
        if action == "click":
            code_lines.append(f"await page.click('{step.get('selector', 'body')}');")
            code_lines.append(f"await page.waitForTimeout({step.get('pauseAfter', 500)});")
        elif action == "type":
            code_lines.append(f"await page.click('{step.get('selector', 'input')}');")
            code_lines.append(f"await page.fill('{step.get('selector', 'input')}', '{step.get('text', '')}');")
            code_lines.append(f"await page.waitForTimeout({step.get('pauseAfter', 500)});")
        elif action == "scroll":
            code_lines.append(f"await page.evaluate(() => window.scrollBy(0, {step.get('y', 300)}));")
            code_lines.append(f"await page.waitForTimeout({step.get('pauseAfter', 500)});")
        elif action == "wait":
            code_lines.append(f"await page.waitForTimeout({step.get('ms', 2000)});")
        elif action == "navigate":
            code_lines.append(f"await page.goto('{step.get('url', 'about:blank')}', {{ waitUntil: 'networkidle' }});")
        elif action == "screenshot":
            code_lines.append(f"await page.screenshot({{ path: '{step.get('name', 'screenshot')}.png' }});")
        elif action == "hover":
            code_lines.append(f"await page.hover('{step.get('selector', 'body')}');")
            code_lines.append(f"await page.waitForTimeout({step.get('pauseAfter', 500)});")

    return "\n    ".join(code_lines)


if __name__ == "__main__":
    # Test - this won't run without a URL but shows the API
    config = create_testreel_config("https://example.com", [
        {"action": "wait", "ms": 1000},
        {"action": "screenshot"},
    ])
    print(json.dumps(config, indent=2))
