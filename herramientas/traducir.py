# -*- coding: utf-8 -*-
"""Traducción gratuita de titulares al español para opnflash.com (aprobada por el usuario el 22/11/2026: «que no cueste nada»).

Usa los modelos libres de Argos Translate (con CTranslate2 y SentencePiece) en la propia máquina del robot, sin enviar los titulares a ningún servicio.
Añade a cada titular que no está en español el campo «e» (su traducción) en public/datos/titulares.json.
Guarda lo ya traducido en public/datos/traducciones.json para no repetirlo: en cada ejecución solo se traduce lo nuevo.
El inglés va directo al español; los demás idiomas pasan por el inglés. Tiene un tope de tiempo: lo que no entra se traduce en la siguiente ejecución.
Uso:  python3 traducir.py [carpeta public] [segundos máximos]
"""
import json, os, re, sys, time

PUB = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'public')
TOPE = float(sys.argv[2]) if len(sys.argv) > 2 else 240
T0 = time.time()
# Idiomas por orden de cuántos titulares traen. Solo se instalan los modelos de los que haya titulares pendientes.
IDIOMAS = ['en', 'fr', 'pt', 'de', 'ar', 'ru', 'el', 'nl', 'pl', 'hu', 'it', 'ro', 'sv', 'tr', 'uk', 'zh', 'ja', 'ko', 'fa', 'he', 'hi', 'id', 'cs', 'sk', 'sl', 'sq', 'lt', 'th', 'vi']
MAX_MODELOS_NUEVOS = 4   # por ejecución, para no alargarla: cada modelo pesa unos 100 MB

def igual(a, b): n = lambda t: re.sub(r'[\W_]+', ' ', t.lower()).strip(); return n(a) == n(b)

def main():
    ruta = os.path.join(PUB, 'datos', 'titulares.json'); rc = os.path.join(PUB, 'datos', 'traducciones.json')
    d = json.load(open(ruta, encoding='utf-8')); M = d['medios']
    try: cache = json.load(open(rc, encoding='utf-8')).get('t', {})
    except Exception: cache = {}
    pend = {}
    for a in d['titulares']:
        idi = M[a['m']]['i']
        if idi == 'es': continue
        if a['t'] in cache: a['e'] = cache[a['t']]
        elif idi in IDIOMAS: pend.setdefault(idi, []).append(a)
    hechos = 0
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
                    if os.path.exists(os.path.join(c, 'sentencepiece.model')) and os.path.isdir(os.path.join(c, 'model')): out[(md['from_code'], md['to_code'])] = c
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
                c = inst[par]; sp = sentencepiece.SentencePieceProcessor(); sp.load(os.path.join(c, 'sentencepiece.model'))
                motores[par] = (ctranslate2.Translator(os.path.join(c, 'model'), device='cpu', inter_threads=1, intra_threads=2), sp)
            return motores[par]
        def pasar(textos, par):
            tr, sp = motor(par)
            res = tr.translate_batch([sp.encode(t, out_type=str) for t in textos], beam_size=2, max_batch_size=32, max_decoding_length=160, replace_unknowns=True)
            return [''.join(r.hypotheses[0]).replace('\u2581', ' ').strip() for r in res]
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
                    for par in pares: T = pasar(T, par)
                except Exception as e: print('AVISO traducir tanda', idi, type(e).__name__, str(e)[:80]); break
                for a, t in zip(tanda, T):
                    t = ' '.join((t or '').split())
                    if t and not igual(t, a['t']): a['e'] = cache[a['t']] = t[:260]; hechos += 1
                    else: cache[a['t']] = ''          # no se pudo: no se reintenta en cada ejecución
    except Exception as e:
        print('AVISO traducir', type(e).__name__, str(e)[:120])
    vivos = {a['t'] for a in d['titulares']}
    cache = {k: v for k, v in cache.items() if k in vivos}
    for a in d['titulares']:
        if not a.get('e'): a.pop('e', None)
    json.dump(d, open(ruta, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    json.dump({'nota': 'Traducciones automáticas ya hechas (Argos Translate), para no repetirlas.', 't': cache}, open(rc, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    falta = sum(1 for a in d['titulares'] if M[a['m']]['i'] != 'es' and 'e' not in a)
    print('traducidos ahora', hechos, '· con traducción', sum(1 for a in d['titulares'] if 'e' in a), '· pendientes', falta, '· seg', round(time.time() - T0))

if __name__ == '__main__':
    main()
