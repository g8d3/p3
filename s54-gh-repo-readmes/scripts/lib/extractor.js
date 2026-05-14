// extractor.js — Run via: agent-browser eval "$(cat scripts/lib/extractor.js)"
// Returns JSON array: [{name, description, topics, stars, language, updated}, ...]
// Scoped to <main> to avoid sidebar headings.

(function() {
  const results = [];
  const main = document.querySelector('main');
  if (!main) return JSON.stringify({error: 'no main element'});
  const repoHeadings = Array.from(main.querySelectorAll('h3')).filter(h => {
    const a = h.querySelector('a');
    return a && a.textContent.trim().includes('/');
  });
  for (const h of repoHeadings) {
    const a = h.querySelector('a');
    const name = a.textContent.trim();
    let el = h.nextElementSibling;
    let description = '', topics = '', stars = '', language = '', updated = '';
    while (el) {
      const cls = el.className || '';
      const txt = el.textContent.trim();
      if (cls.includes('Content-module__Content__') && !description)
        description = txt;
      else if (cls.includes('TokenList-module__tokenList__'))
        topics = Array.from(el.querySelectorAll('a')).map(x => x.textContent.trim()).filter(Boolean).join('; ');
      else if (cls.includes('Footer-module__footer__')) {
        const parts = txt.split('\u00b7').map(s => s.trim()).filter(Boolean);
        for (const p of parts) {
          if (p.match(/^\d+\.?\d*k?$/)) { stars = stars || p; }
          else if (p.match(/^(Updated|about|a )/i) || p.match(/(ago|hour|minute|second|day|week|month|year)$/i)) updated = updated || p;
          else language = language || p;
        }
      }
      else if ((el.tagName === 'BUTTON' || el.tagName === 'button') && (txt.includes('Star') || txt.includes('Unstar') || txt.includes('Sponsor'))) break;
      else if (el.tagName === 'H3' || el.tagName === 'h3') break;
      el = el.nextElementSibling;
    }
    results.push({name, description: description.replace(/\\n/g,' ').replace(/\\s+/g,' ').trim(), topics, stars, language, updated});
  }
  return JSON.stringify(results);
})()
