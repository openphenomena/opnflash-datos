# -*- coding: utf-8 -*-
"""Titulares de medios para opnflash.com.

Lee la lista aprobada por el usuario el 21/11/2026 (referencia/medios/fuentes-medios.json) y guarda
public/datos/titulares.json. De cada noticia solo se guarda: titular, medio, hora y enlace (y el lugar que nombra, ver lugar.py).
Nunca texto, fotos, vídeos ni logos. Uso:  python3 medios.py [carpeta public] [segundos máximos]
"""
import json, os, sys, re, time, html, datetime as dt, urllib.request, urllib.parse, xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from email.utils import parsedate_to_datetime
import lugar

AQUI = os.path.dirname(os.path.abspath(__file__))
PUB = sys.argv[1] if len(sys.argv) > 1 else os.path.join(AQUI, '..', 'public')
TOPE = float(sys.argv[2]) if len(sys.argv) > 2 else 150
LISTA = os.path.join(AQUI, '..', 'referencia', 'medios', 'fuentes-medios.json')
UA = {'User-Agent': 'Mozilla/5.0 (compatible; opnflash.com; titulares enlazados; +https://www.opnflash.com/acerca.html)',
      'Accept': 'application/rss+xml, application/atom+xml, application/xml, text/xml, */*'}
POR_MEDIO, HORAS, HORAS_SALA = 3, 72, 168
REG = {'General': 'general', 'Europa': 'europa', 'África': 'africa', 'América': 'america', 'Asia': 'asia', 'Oriente Medio': 'oriente'}
T0 = time.time()

def limpio(s):
    s = html.unescape(html.unescape(s or ''))
    s = re.sub(r'<[^>]+>', ' ', s)
    return ' '.join(s.split())

def fecha(s):
    if not s: return None
    s = s.strip()
    try: d = parsedate_to_datetime(s)
    except Exception:
        try: d = dt.datetime.fromisoformat(s.replace('Z', '+00:00'))
        except Exception:
            # fechas con día y mes en español («Mar, 17 Nov 2026 …», «17 dic 2026 …»)
            t = re.sub(r'^[^\d]*', '', s)
            for a, b in (('ene', 'Jan'), ('abr', 'Apr'), ('ago', 'Aug'), ('dic', 'Dec')): t = re.sub(r'\b%s\w*' % a, b, t, flags=re.I)
            try: d = parsedate_to_datetime(t)
            except Exception: return None
    if d.tzinfo is None: d = d.replace(tzinfo=dt.timezone.utc)
    return d.astimezone(dt.timezone.utc)

def local(tag): return tag.rsplit('}', 1)[-1].lower()

def leer(f):
    """Devuelve (índice, [(titular, enlace, fecha, resumen para ubicar)], error)."""
    i, feed = f
    if time.time() - T0 > TOPE: return i, [], 'sin tiempo'
    try:
        with urllib.request.urlopen(urllib.request.Request(feed['url'], headers=UA), timeout=12) as r:
            b = r.read(1_500_000)
        raiz = ET.fromstring(b)
    except Exception as e:
        return i, [], type(e).__name__
    google = 'news.google.com' in feed['url']
    out = []
    for it in raiz.iter():
        if local(it.tag) not in ('item', 'entry'): continue
        t = u = f_ = None; res = []
        for c in it:
            k = local(c.tag)
            if k == 'title' and t is None: t = limpio(''.join(c.itertext()))
            elif k == 'link' and not u: u = (c.get('href') if c.get('href') and c.get('rel', 'alternate') == 'alternate' else (c.text or '')).strip() or u
            elif k in ('pubdate', 'published', 'updated', 'date') and f_ is None: f_ = fecha(c.text)
            elif k in ('description', 'summary', 'category', 'subject') and len(res) < 6: res.append(limpio(''.join(c.itertext()) or c.get('term') or '')[:500])   # solo para ubicar el titular: no se guarda
        if not t or not u or not u.startswith('http'): continue
        if google: t = re.sub(r'\s+[-–|]\s+[^-–|]{2,60}$', '', t)
        if len(t) < 12: continue
        out.append((t[:240], u, f_, ' . '.join(x for x in res if x)))
        if len(out) >= 12: break
    return i, out, None

def main():
    feeds = json.load(open(LISTA, encoding='utf-8'))['feeds']
    ahora = dt.datetime.now(dt.timezone.utc)
    medios, idx = [], {}
    for f in feeds:
        if f['medio'] not in idx:
            idx[f['medio']] = len(medios)
            p = urllib.parse.urlparse(f['url'])
            sitio = p.netloc
            if 'news.google.com' in sitio:
                m = re.search(r'site(?:%3A|:)([^+%&\s]+)', f['url']); sitio = m.group(1) if m else ''
            medios.append({'n': f['medio'], 'i': f['idioma'], 'r': REG.get((f.get('region') or ['General'])[0], 'general'), 's': re.sub(r'^(www|feeds?|rss)\.', '', sitio), 'ok': 0})
        mm = medios[idx[f['medio']]]
        if f.get('principal'): mm['pr'] = 1                         # sale también en modo Simple
        if f.get('sala'): mm['k'] = f['sala']                      # tema en la Sala de control
        if f.get('max'): mm['_max'] = max(mm.get('_max', 0), f['max'])   # titulares por captura (por defecto, POR_MEDIO)
    res, err = {}, {}
    with ThreadPoolExecutor(96) as ex:
        for fu in as_completed([ex.submit(leer, x) for x in enumerate(feeds)]):
            i, items, e = fu.result()
            if e: err[e] = err.get(e, 0) + 1
            res[i] = items
    for m in medios:
        h = lugar.sede(m)
        if h: m['h'] = h
    tit, vistos = [], set()
    por = {}
    for i, f in enumerate(feeds):
        m = idx[f['medio']]
        for t, u, d, rs in res.get(i, []):
            horas = HORAS_SALA if f.get('max') else HORAS      # los medios especializados publican menos: se mira una semana
            if d is None or d > ahora + dt.timedelta(minutes=30) or (ahora - d).total_seconds() > horas * 3600: continue
            por.setdefault(m, []).append((d, t, u, rs))
    for m, L in por.items():
        L.sort(reverse=True); n = 0
        for d, t, u, rs in L:
            k = t.lower()
            if not re.match(r'(?i)^https?://', u or ''): continue   # solo enlaces web normales (nunca javascript: ni data:)
            if k in vistos or u in vistos: continue
            vistos.add(k); vistos.add(u)
            a = {'m': m, 't': t, 'u': u, 'f': d.strftime('%Y-%m-%dT%H:%M:%SZ')}
            h_ = medios[m].get('h'); g = lugar.ubicar(t, rs, h_[3] if h_ and len(h_) > 3 else None) or ('h' in medios[m] and lugar.por_sede(medios[m]['h'], t))
            if g: a['g'] = g
            tit.append(a); n += 1
            if n >= medios[m].get('_max', POR_MEDIO): break
        medios[m]['ok'] = n
    for m in medios: m.pop('_max', None)
    tit.sort(key=lambda a: a['f'], reverse=True)
    sal = {'generado': ahora.strftime('%Y-%m-%dT%H:%M:%SZ'),
           'nota': 'Solo titular, medio, hora y enlace. Los derechos de cada noticia pertenecen a su medio.',
           'medios': medios, 'titulares': tit}
    os.makedirs(os.path.join(PUB, 'datos'), exist_ok=True)
    json.dump(sal, open(os.path.join(PUB, 'datos', 'titulares.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print('ubicados por titular', sum(1 for a in tit if a.get('g', [0, 0, 0, ''])[3] == 't'), 'por resumen', sum(1 for a in tit if a.get('g', [0, 0, 0, ''])[3] == 'r'), 'por sede del medio', sum(1 for a in tit if a.get('g', [0, 0, 0, ''])[3] == 'm'), 'sin lugar', sum(1 for a in tit if 'g' not in a))
    print('feeds', len(feeds), 'medios', len(medios), 'con titulares', sum(1 for m in medios if m['ok']), 'titulares', len(tit), 'seg', round(time.time() - T0))
    print('errores', sorted(err.items(), key=lambda a: -a[1])[:12])

if __name__ == '__main__':
    main()
