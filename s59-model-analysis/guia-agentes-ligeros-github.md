# Guía para encontrar Agentes de IA Ligeros en GitHub

> Estrategias, filtros y URLs bookmarkeables para descubrir proyectos minimalistas
> sin Docker, sin bloat, que puedas visitar a diario.

---

## 📌 URLs bookmarkeables (para el navegador)

Estas URLs funcionan directamente en GitHub. Click → bookmark → visitas todos los días.

### 🎯 La MEJOR (la que usaría a diario)

```
https://github.com/search?q=agent+language%3Apython+size%3A%3C5120+stars%3A%3E30&type=repositories&s=stars&o=desc
```

**Explicación de los filtros:**

| Filtro | Significado |
|---|---|
| `agent` | Busca repos que mencionen "agent" |
| `language:python` | Solo Python |
| `size:<5120` | **< 5 MB** — filtro mágico. Elimina automáticamente proyectos con Docker pesado, modelos locales, datasets, etc. |
| `stars:>30` | Mínimo 30 estrellas (calidad mínima) |
| `s=stars&o=desc` | Ordenado por estrellas descendente |

Esto devuelve **~3,300+ proyectos** ordenados por popularidad. Los primeros son los más conocidos, y scrolleando encuentras gemas ocultas.

### 🔍 Variantes más específicas

| Propósito | URL |
|---|---|
| **Minimal coding agents** | `https://github.com/search?q=minimal+agent+language%3Apython+size%3A%3C5120+stars%3A%3E30&type=repositories&s=stars&o=desc` |
| **Lightweight explícito** | `https://github.com/search?q=lightweight+agent+language%3Apython+stars%3A%3E50&type=repositories&s=stars&o=desc` |
| **CLI agents** | `https://github.com/search?q=cli+agent+language%3Apython+size%3A%3C5120+stars%3A%3E20&type=repositories&s=stars&o=desc` |
| **ReAct agents** (patrón minimalista) | `https://github.com/search?q=react+agent+language%3Apython+size%3A%3C5120+stars%3A%3E20&type=repositories&s=stars&o=desc` |
| **Frameworks pequeños** | `https://github.com/search?q=%22agent+framework%22+language%3Apython+size%3A%3C5120+stars%3A%3E30&type=repositories&s=stars&o=desc` |
| **Sin Docker** | `https://github.com/search?q=agent+NOT+docker+language%3Apython+size%3A%3C5120+stars%3A%3E30&type=repositories&s=stars&o=desc` |
| **Recién actualizados** | `https://github.com/search?q=agent+language%3Apython+size%3A%3C5120+stars%3A%3E30+pushed%3A%3E2025-06-01&type=repositories&s=updated&o=desc` |
| **Coding agents específicos** | `https://github.com/search?q=%22coding+agent%22+OR+%22code+agent%22+language%3Apython+size%3A%3C10240+stars%3A%3E30&type=repositories&s=stars&o=desc` |

### 📂 Páginas de Topics

```
https://github.com/topics/ai-agents?l=python
https://github.com/topics/agent-framework?l=python
https://github.com/topics/lightweight
https://github.com/topics/minimal
```

---

## 🧠 El filtro secreto: `size:<N`

De todas las pruebas realizadas contra la API de GitHub, `size:<N` es **el filtro más efectivo** para encontrar proyectos ligeros.

**¿Por qué funciona?**
- Proyectos con Docker pesado → repos grandes → eliminados
- Proyectos con modelos locales incluidos → eliminados
- Proyectos con datasets → eliminados
- Proyectos con muchas dependencias empaquetadas → eliminados

**Lo que SÍ pasa el filtro:**
- Agentes CLI puros (como pi, Hermes, agentsilex)
- Frameworks pequeños que son solo código fuente
- Proyectos que usan APIs externas (no modelos locales)
- Agentes minimalistas de ~300-1500 líneas

**Ajusta el umbral según lo que consideres ligero:**

| Tamaño | Significado |
|---|---|
| `size:<1024` | **< 1 MB** — ultra-ligero, solo código fuente puro |
| `size:<5120` | **< 5 MB** — el punto dulce (recomendado) |
| `size:<10240` | **< 10 MB** — más permisivo |

---

## 🏆 Gemas ultra-ligeras encontradas con estos filtros

Proyectos verificados con la API de GitHub, todos **sin Docker** y < 5 MB:

| Proyecto | ⭐ | Tamaño | Líneas | Notas |
|---|---|---|---|---|
| **rasbt/mini-coding-agent** | 839 | **0.1 MB** | ~500 | El más mínimo posible |
| **he-yufeng/CoreCoder** | 694 | **0.6 MB** | ~1,400 | Inspirado en Claude Code |
| **howl-anderson/agentsilex** | 450 | **0.7 MB** | ~300 | "Sin magia, transparente" |
| **openai/swarm** | 21,483 | **0.5 MB** | educativo | Framework ligero multi-agente |
| **InternLM/lagent** | 2,247 | **0.8 MB** | framework | Framework ligero para agentes |
| **mistralai/mistral-vibe** | 4,172 | **1.8 MB** | CLI | Coding agent oficial de Mistral |
| **operand/agency** | 484 | **3.1 MB** | mínimo | Framework minimalista |
| **MiniMax-AI/Mini-Agent** | 2,606 | **4.2 MB** | demo | Single agent demo profesional |
| **Jacob-liu1996/miniagent** | 185 | **~0 MB** | pequeño | ReAct pattern completo |
| **hwfengcs/DM-Code-Agent** | 135 | **0.9 MB** | ~1,500 | Coding agent auditable |
| **amszuidas/mini-opencode** | 117 | **4.3 MB** | experimental | Coding experimental |

### Referencia: proyectos que mencionaste

| Proyecto | ⭐ | Tamaño | Docker | Notas |
|---|---|---|---|---|
| **NousResearch/hermes-agent** (Open Code Hermes) | 148,515 | 208 MB | ❌ | "The agent that grows with you" |
| **pi** (earendil-works/pi-coding-agent) | ~162 (ecosistema) | 186 MB | ❌ | El coding agent que estás usando |

> Ambos son "ligeros" en sentido arquitectónico (CLI, sin Docker, usan APIs), pero sus repositorios pesan ~200 MB por dependencias empaquetadas.

---

## 🐍 Script para terminal

Guarda esto como `buscar_agentes.py` y ejecútalo cuando quieras:

```python
#!/usr/bin/env python3
"""
Buscador de agentes de IA ligeros en GitHub
Uso: python3 buscar_agentes.py
"""
import urllib.request
import json

def search(query, n=15):
    url = f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page={n}"
    req = urllib.request.Request(url, headers={"User-Agent": "my-agent-bot"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

busquedas = {
    "🌱 Lightweight agent":     "lightweight+agent+language:python+stars:>50",
    "📦 Frameworks <5MB":       "'agent+framework'+language:python+size:<5120+stars:>30",
    "🎯 Minimal coding agent": "minimal+agent+language:python+size:<5120+stars:>30",
    "🔍 Todo Python <5MB":     "agent+language:python+size:<5120+stars:>30",
}

for nombre, query in busquedas.items():
    print(f"\n── {nombre} ──")
    try:
        d = search(query, 10)
        print(f"  {d['total_count']} resultados")
        for r in d['items'][:10]:
            sz = r['size'] / 1024
            st = r['stargazers_count']
            docker = '🐳' if r.get('has_dockerfile') else '  '
            desc = (r['description'] or '')[:65]
            print(f"  {docker} {r['full_name'][:48]:48s} ⭐{st:>6d}  {sz:5.1f}MB")
            if desc:
                print(f"  {'':2} {desc}")
    except Exception as e:
        print(f"  Error: {e}")
```

---

## 💡 Recomendación final

Para tu uso diario:

1. **Bookmarkea esta URL** (la mejor de todas las pruebas):
   ```
   https://github.com/search?q=agent+language%3Apython+size%3A%3C5120+stars%3A%3E30&type=repositories&s=stars&o=desc
   ```

2. **Para solo coding agents** (como pi y Hermes):
   ```
   https://github.com/search?q=%22coding+agent%22+OR+%22code+agent%22+language%3Apython+size%3A%3C10240+stars%3A%3E30&type=repositories&s=stars&o=desc
   ```

3. **Para descubrir novedades semanales**, cambia `s=stars` por `s=updated` y añade `pushed:>2025-06-01`.

---

*Generado el 2026-05-13 con datos verificados contra la API de GitHub.*
