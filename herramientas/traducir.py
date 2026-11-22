# -*- coding: utf-8 -*-
"""Traducción gratuita de titulares al español para opnflash.com (aprobada por el usuario el 22/11/2026: «que no cueste nada»).

Usa los modelos libres de Argos Translate (con CTranslate2 y SentencePiece) en la propia máquina del robot, sin enviar los titulares a ningún servicio.
Añade a cada titular que no está en español el campo «e» (su traducción) en public/datos/titulares.json.
Versión en inglés del sitio (usuario, 22/11): añade también el campo «n» (traducción al inglés) a cada titular que no está en inglés;
en los idiomas que pasan por el inglés se aprovecha ese paso intermedio, y el español se traduce con el modelo español→inglés.
Guarda lo ya traducido en public/datos/traducciones.json para no repetirlo: en cada ejecución solo se traduce lo nuevo.
El inglés va directo al español; los demás idiomas pasan por el inglés. Tiene un tope de tiempo: lo que no entra se traduce en la siguiente ejecución.
Uso:  python3 traducir.py [carpeta public] [segundos máximos para el español] [segundos máximos para el inglés]
"""
import json, os, re, sys, time, html

PUB = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'public')
TOPE = float(sys.argv[2]) if len(sys.argv) > 2 else 240
TOPE_EN = float(sys.argv[3]) if len(sys.argv) > 3 else 180
T0 = time.time()
# Idiomas por orden de cuántos titulares traen. Solo se instalan los modelos de los que haya titulares pendientes.
IDIOMAS = ['en', 'fr', 'pt', 'de', 'ar', 'ru', 'el', 'nl', 'pl', 'hu', 'it', 'ro', 'sv', 'tr', 'uk', 'zh', 'ja', 'ko', 'fa', 'he', 'hi', 'id', 'cs', 'sk', 'sl', 'sq', 'lt', 'th', 'vi']
MAX_MODELOS_NUEVOS = 4   # por ejecución, para no alargarla: cada modelo pesa unos 100 MB

def igual(a, b): n = lambda t: re.sub(r'[\W_]+', ' ', t.lower()).strip(); return n(a) == n(b)

# El modelo inglés→español a veces devuelve el texto en inglés sin traducir, sobre todo con titulares en «Title Case».
# Si pasa, se reintenta con el titular en minúsculas (salvo siglas y la primera letra); si sigue igual, no se da por traducido.
EN = set('a an the of and to in is for with on after over from by says new its as at be are was will has have this that who what how why'.split())
ES = set('de la el en y los las del que por con para un una se su al es lo como más tras sobre'.split())
def parece_ingles(t):
    w = re.findall(r"[a-záéíóúñü']+", t.lower())
    return sum(x in EN for x in w) + sum(len(x) > 5 and x.endswith('ing') for x in w) >= 2 and not any(x in ES for x in w)
EN_FUERTE = set('the of and to for with on after from by says its are has have this that who what how why'.split())
def en_ingles(t):
    """Titular que ya viene en inglés aunque el medio esté anotado en otro idioma (ediciones en inglés): se traduce desde el inglés.
    Si se pasara por el modelo del idioma anotado, el resultado sale roto («cu cu cu…»)."""
    w = re.findall(r"[^\W\d_]+", t.lower())   # palabras enteras con sus tildes: «był» no cuenta como «by»
    return sum(x in EN_FUERTE for x in w) >= 2 and parece_ingles(t)
def latino(t):
    """Una traducción al español tiene que estar casi toda en alfabeto latino."""
    l = [c for c in t if c.isalpha()]
    return bool(l) and sum('a' <= c.lower() <= 'z' or c in 'áéíóúñüàèìòùç' for c in l) / len(l) >= 0.85
def terminos(orig, trad):
    """Términos que el traductor libre pierde: si el original dice «superinteligente» o «superinteligencia» y la traducción no, se repone."""
    if trad and re.search(r'super[\s-]?intell?ig', orig, re.I) and not re.search(r'super[\s-]?intelig', trad, re.I):
        for rx, por in ((r'\b(i)nteligencia artificial\b', None), (r'\bIA\b', 'IA superinteligente'), (r'\b(i)nteligencia\b', None)):
            n = re.sub(rx, (lambda m: ('S' if m.group(1) == 'I' else 's') + 'uper' + m.group(0).lower()) if por is None else por, trad, count=1, flags=0 if por else re.I)
            if n != trad: return n
    return trad

def degenerada(t, orig=''):
    """El modelo a veces entra en bucle («cu cu cu cu…») o se inventa un texto mucho más largo que el original: no se da por traducido."""
    w = re.findall(r"\w+", (t or '').lower())
    if not w: return False
    if re.search(r'\b(\w+)(\W+\1\b){3,}', t.lower()): return True          # la misma palabra cuatro veces seguidas
    if len(w) >= 8 and len(set(w)) / len(w) < 0.5: return True                 # la mitad o más son repeticiones
    return bool(orig) and len(t) > 2.2 * len(orig) + 20                        # mucho más largo que el original

def limpiar_en(t):
    """Palabras que el traductor libre pone mal en inglés y resultan ofensivas («perrita» → «bitch»): se cambian por la neutra."""
    return re.sub(r'\b([Bb])itch(es)?\b', lambda m: ('D' if m.group(1) == 'B' else 'd') + 'og' + ('s' if m.group(2) else ''), t)

def frase(t):
    return ' '.join(x if (i == 0 or x.isupper() or any(c.isdigit() for c in x)) else x.lower() for i, x in enumerate(t.split()))

def main():
    ruta = os.path.join(PUB, 'datos', 'titulares.json'); rc = os.path.join(PUB, 'datos', 'traducciones.json')
    d = json.load(open(ruta, encoding='utf-8')); M = d['medios']
    try: _c = json.load(open(rc, encoding='utf-8'))
    except Exception: _c = {}
    cache = _c.get('t', {}); cache_n = _c.get('n', {})
    if _c.get('v', 1) < 2:   # versión 2 (22/11): los titulares con «&» se traducían mal; se rehacen una vez
        cache = {k: v for k, v in cache.items() if '&' not in k}
    # Traducciones guardadas que se quedaron en inglés: se vuelven a hacer con la corrección de abajo.
    malas = [k for k, v in cache.items() if v and (parece_ingles(v) or not latino(v) or degenerada(v, k) or re.search(r'&(amp|quot|gt|lt|#\d+);', v))]
    for k in malas: del cache[k]
    if malas: print('traducciones en inglés que se rehacen', len(malas))
    malas_n = [k for k, v in cache_n.items() if v and degenerada(v, k)]
    for k in malas_n: del cache_n[k]
    if malas_n: print('traducciones al inglés en bucle que se rehacen', len(malas_n))
    if _c.get('v', 1) < 3:   # versión 3 (22/11): titulares en inglés de medios anotados en otro idioma salían rotos; se rehacen una vez
        for a in d['titulares']:
            if M[a['m']]['i'] not in ('en', 'es') and en_ingles(a['t']): cache.pop(a['t'], None)
    pend = {}; pend_n = {}
    for a in d['titulares']:
        idi = M[a['m']]['i']
        if idi not in ('en', 'es') and en_ingles(a['t']): idi = 'en'
        if idi != 'en':
            if a['t'] in cache_n: a['n'] = cache_n[a['t']] = limpiar_en(cache_n[a['t']])
            elif (idi in IDIOMAS or idi == 'es') and not parece_ingles(a['t']): pend_n.setdefault(idi, []).append(a)   # medio mal anotado que ya escribe en inglés: se deja tal cual
        if idi == 'es': continue
        if a['t'] in cache: a['e'] = cache[a['t']] = terminos(a['t'], cache[a['t']])
        elif idi in IDIOMAS: pend.setdefault(idi, []).append(a)
    hechos = 0; vivos_ax = set()
    try:
        # Motor ligero: los mismos modelos libres de Argos Translate, usados directamente con CTranslate2 y SentencePiece.
        # Así no hace falta instalar el paquete completo (que arrastra dependencias de varios gigas y alargaba cada ejecución).
        import ctranslate2, sentencepiece, urllib.request, zipfile, io, glob
        BASE = os.path.expanduser('~/.local/share/argos-translate/packages'); os.makedirs(BASE, exist_ok=True)
        def instalados():
            out = {}
            for m in glob.glob(os.path.join(BASE, '*', 'metadata.json')):
                try:
                    md = json.load(open(m, encoding='utf-8')); c = os.path.dirname(m)
                    # Dos formatos de modelo: SentencePiece (los antiguos) y BPE con Moses (los de la versión 1.9, la mayoría).
                    if os.path.isdir(os.path.join(c, 'model')) and any(os.path.exists(os.path.join(c, f)) for f in ('sentencepiece.model', 'bpe.model')): out[(md['from_code'], md['to_code'])] = c
                except Exception: pass
            return out
        inst = instalados(); idx = []; motores = {}
        def asegurar(par, cupo):
            if par in inst: return True
            if cupo[0] <= 0: return False
            if not idx:
                with urllib.request.urlopen('https://raw.githubusercontent.com/argosopentech/argospm-index/main/index.json', timeout=30) as r: idx.extend(json.load(r))
            p = next((p for p in idx if (p.get('from_code'), p.get('to_code')) == par), None)
            url = p and next((u for u in p.get('links', []) if u.startswith('https://')), None)
            if not url: return False
            cupo[0] -= 1
            req = urllib.request.Request(url, headers={'User-Agent': 'opnflash.com (+https://www.opnflash.com/acerca.html)'})
            with urllib.request.urlopen(req, timeout=120) as r: zipfile.ZipFile(io.BytesIO(r.read())).extractall(BASE)
            inst.clear(); inst.update(instalados()); print('modelo instalado', par, par in inst); return par in inst
        def motor(par):
            if par not in motores:
                c = inst[par]; tr = ctranslate2.Translator(os.path.join(c, 'model'), device='cpu', inter_threads=1, intra_threads=2)
                if os.path.exists(os.path.join(c, 'sentencepiece.model')):
                    sp = sentencepiece.SentencePieceProcessor(); sp.load(os.path.join(c, 'sentencepiece.model'))
                    motores[par] = (tr, lambda t: sp.encode(t, out_type=str), lambda h: ''.join(h).replace('\u2581', ' ').strip())
                else:
                    import codecs
                    from subword_nmt.apply_bpe import BPE
                    from sacremoses import MosesTokenizer, MosesDetokenizer
                    bpe = BPE(codecs.open(os.path.join(c, 'bpe.model'), encoding='utf-8')); mt = MosesTokenizer(lang=par[0]); md = MosesDetokenizer(lang=par[1])
                    motores[par] = (tr, lambda t: bpe.process_line(mt.tokenize(t, return_str=True, escape=False)).split(),
                                    lambda h: md.detokenize(' '.join(h).replace('@@ ', '').split()))
            return motores[par]
        def pasar(textos, par):
            tr, cod, dec = motor(par)
            # «&» confunde a los modelos (devuelven &quot; o >): se cambia por la conjunción antes de traducir
            textos = [re.sub(r'\s*&\s*', ' and ' if par[0] == 'en' else ' ', t) for t in textos]
            res = tr.translate_batch([cod(t) for t in textos], beam_size=2, max_batch_size=32, max_decoding_length=160, replace_unknowns=True, no_repeat_ngram_size=4, repetition_penalty=1.1)
            return [dec(r.hypotheses[0]) for r in res]
        cupo = [MAX_MODELOS_NUEVOS]
        for idi in sorted(pend, key=lambda k: (IDIOMAS.index(k) > 0, -len(pend[k]))):
            if time.time() - T0 > TOPE: break
            pares = [('en', 'es')] if idi == 'en' else ([(idi, 'es')] if (idi, 'es') in inst else [(idi, 'en'), ('en', 'es')])
            try:
                if not all(asegurar(p, cupo) for p in pares): continue
            except Exception as e: print('AVISO traducir modelo', idi, type(e).__name__); continue
            L = sorted(pend[idi], key=lambda x: x['f'], reverse=True)
            for k in range(0, len(L), 64):
                if time.time() - T0 > TOPE: break
                tanda = L[k:k + 64]
                try:
                    T = [a['t'] for a in tanda]
                    for par in pares:
                        U = pasar(T, par)
                        if par[1] == 'en':   # paso intermedio al inglés: sirve también para la versión en inglés del sitio
                            for a, u in zip(tanda, U):
                                u = ' '.join(html.unescape(html.unescape(u or '')).split())
                                if u and latino(u) and not igual(u, a['t']) and not degenerada(u, a['t']) and 'n' not in a: a['n'] = cache_n[a['t']] = limpiar_en(u[:260])
                        if par == ('en', 'es'):
                            mal = [i for i, (x, y) in enumerate(zip(T, U)) if igual(x, y) or parece_ingles(y)]
                            if mal:
                                R = pasar([frase(T[i]) for i in mal], par)
                                for i, r in zip(mal, R): U[i] = '' if (igual(T[i], r) or parece_ingles(r)) else r
                        T = U
                except Exception as e: print('AVISO traducir tanda', idi, type(e).__name__, str(e)[:80]); break
                for a, t in zip(tanda, T):
                    t = ' '.join(html.unescape(html.unescape(t or '')).split())
                    if t and (not latino(t) or degenerada(t, a['t'])): t = ''   # salió en otro alfabeto o con basura: no se da por traducido
                    if t and not igual(t, a['t']): a['e'] = cache[a['t']] = terminos(a['t'], t[:260]); hechos += 1
                    else: cache[a['t']] = ''          # no se pudo: no se reintenta en cada ejecución
        # Títulos de arXiv (en inglés) al español, campo «e» en portada.json
        try:
            rp = os.path.join(PUB, 'datos', 'portada.json'); por = json.load(open(rp, encoding='utf-8'))
            AX = (por.get('ciencia') or {}).get('datos') or []
            for x in AX:
                if x.get('titulo') in cache and cache[x['titulo']]: x['e'] = cache[x['titulo']]
            falta = [x for x in AX if x.get('titulo') and 'e' not in x]
            if falta and asegurar(('en', 'es'), cupo):
                U = pasar([x['titulo'] for x in falta], ('en', 'es'))
                for x, u in zip(falta, U):
                    u = ' '.join(html.unescape(html.unescape(u or '')).split())
                    if u and latino(u) and not igual(u, x['titulo']) and not parece_ingles(u) and not degenerada(u, x['titulo']): x['e'] = cache[x['titulo']] = u[:260]
            vivos_ax.update(x['titulo'] for x in AX if x.get('titulo'))
            json.dump(por, open(rp, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
        except Exception as e: print('AVISO traducir arXiv', type(e).__name__, str(e)[:80])
        # Segunda vuelta: al inglés, lo que no salió del paso intermedio (español y los idiomas con modelo directo al español).
        T1 = time.time(); hechos_n = 0; cupo_n = [2]
        for idi in sorted(pend_n, key=lambda k: -len(pend_n[k])):
            if time.time() - T1 > TOPE_EN: break
            L = sorted([a for a in pend_n[idi] if 'n' not in a and a['t'] not in cache_n], key=lambda x: x['f'], reverse=True)
            if not L: continue
            par = (idi, 'en')
            try:
                if not asegurar(par, cupo_n): continue
            except Exception as e: print('AVISO traducir modelo', par, type(e).__name__); continue
            for k in range(0, len(L), 64):
                if time.time() - T1 > TOPE_EN: break
                tanda = L[k:k + 64]
                try: U = pasar([a['t'] for a in tanda], par)
                except Exception as e: print('AVISO traducir tanda', par, type(e).__name__, str(e)[:80]); break
                for a, u in zip(tanda, U):
                    u = ' '.join(html.unescape(html.unescape(u or '')).split())
                    if u and latino(u) and not igual(u, a['t']) and not degenerada(u, a['t']): a['n'] = cache_n[a['t']] = limpiar_en(u[:260]); hechos_n += 1
                    else: cache_n[a['t']] = ''
        print('al inglés ahora', hechos_n, '· seg', round(time.time() - T1))
    except Exception as e:
        print('AVISO traducir', type(e).__name__, str(e)[:120])
    vivos = {a['t'] for a in d['titulares']} | vivos_ax
    cache = {k: v for k, v in cache.items() if k in vivos}; cache_n = {k: v for k, v in cache_n.items() if k in vivos}
    for a in d['titulares']:
        if not a.get('e'): a.pop('e', None)
        if not a.get('n'): a.pop('n', None)
    json.dump(d, open(ruta, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    json.dump({'nota': 'Traducciones automáticas ya hechas (Argos Translate), para no repetirlas.', 'v': 3, 't': cache, 'n': cache_n}, open(rc, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    falta = sum(1 for a in d['titulares'] if M[a['m']]['i'] != 'es' and 'e' not in a)
    falta_n = sum(1 for a in d['titulares'] if M[a['m']]['i'] != 'en' and 'n' not in a)
    print('traducidos ahora', hechos, '· en inglés', sum(1 for a in d['titulares'] if 'n' in a), '· pendientes al inglés', falta_n, '· con traducción', sum(1 for a in d['titulares'] if 'e' in a), '· pendientes', falta, '· seg', round(time.time() - T0))

if __name__ == '__main__':
    main()
