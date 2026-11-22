# -*- coding: utf-8 -*-
"""Algoritmos de organización de los titulares de opnflash.com (aprobados por el usuario el 22/11/2026, 7:37 p. m.).

Reglas simples y públicas, sin popularidad, sin clics y sin juicio editorial. Se ejecuta después de traducir.py y antes de partir.py.
1. Repetidos: el mismo titular publicado dos veces por el mismo medio (o por sus ediciones con el mismo dominio) se deja una sola vez.
2. Misma noticia en varios medios: los titulares que cuentan el mismo hecho (comparados en inglés, original o traducción)
   reciben el mismo número de grupo «c». Solo se agrupan si son de al menos dos medios distintos y se publicaron con menos de 48 horas.
3. Temas en aumento: países y lugares que aparecen en los titulares de las últimas 24 horas mucho más que la media de los días
   anteriores de la captura → datos/tendencias.json.
4. Traducciones dudosas: «q» lleva «e» (español) o «n» (inglés) si esa traducción parece de mala calidad
   (deja muchas palabras sin traducir, o es mucho más corta o más larga que el original).
Uso: python3 herramientas/algoritmos.py .
"""
import json, os, re, sys, math, time, unicodedata, datetime as dt, collections

PUB = sys.argv[1] if len(sys.argv) > 1 else '.'
D = os.path.join(PUB, 'datos')
T0 = time.time()

VACIAS = set("""a an the of and or to in on at for with from by as is are was were be been being it its this that these those after before over under
into about than then but not no yes says said say will would can could may might has have had do does did new more most up out off just how why what who when
where which while amid against during via vs per de la el los las del y en con por para un una que se su al es lo como mas sobre tras ante entre
le les des du et dans pour sur par une est au aux il elle ils qui ne pas o e da do dos das em no na um uma por com ao
der die das und mit von zu im ist ein eine den dem nicht auf fur sich
first two three one year years day days week time live news video report update latest today world people""".split())

def nz(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn')

def palabras(s):
    return [w for w in re.findall(r"[a-z0-9]+", nz(s)) if len(w) > 2 and w not in VACIAS and not w.isdigit()]

def fecha(a):
    try: return dt.datetime.strptime(a['f'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=dt.timezone.utc).timestamp()
    except Exception: return 0

def main():
    ruta = os.path.join(D, 'titulares.json')
    d = json.load(open(ruta, encoding='utf-8')); M = d['medios']; T = d['titulares']
    # Si titulares.json ya estaba partido (se ejecutó partir.py), se vuelven a unir las traducciones para poder comparar.
    for k, nom in (('e', 'titulares-es.json'), ('n', 'titulares-en.json')):
        if any(k in a for a in T): continue
        try:
            p = json.load(open(os.path.join(D, nom), encoding='utf-8'))
            if p.get('generado') == d.get('generado'):
                for a, x in zip(T, p.get(k, [])):
                    if x: a[k] = x
        except Exception: pass

    # 1. Repetidos dentro del mismo medio o dominio
    vistos = set(); out = []; quitados = 0
    for a in sorted(T, key=fecha):
        m = M[a['m']]; clave = ((m.get('s') or m['n']).lower(), ' '.join(palabras(a['t'])) or nz(a['t']))
        if clave in vistos: quitados += 1; continue
        vistos.add(clave); out.append(a)
    orden = {id(a): i for i, a in enumerate(T)}
    T = sorted(out, key=lambda a: orden[id(a)]); d['titulares'] = T

    # 2. Misma noticia: palabras del titular en inglés (original si el medio escribe en inglés; si no, su traducción «n»)
    # Titulares de plantilla (fichas de cotización, informes periódicos) no son un mismo hecho aunque se parezcan
    PLANTILLA = re.compile(r'stock price,? news,? quote|price today|\bcot\b.*report|weekly (news|recap|roundup)|newsletter|podcast|live updates?', re.I)
    N = len(T); W = []
    for a in T:
        txt = a['t'] if M[a['m']]['i'] == 'en' else (a.get('n') or '')
        W.append(set() if PLANTILLA.search(txt) or PLANTILLA.search(a['t']) else set(palabras(txt)))
    df = collections.Counter(w for s in W for w in s)
    idf = {w: math.log(N / (1 + c)) for w, c in df.items()}
    raras = {w for w, c in df.items() if 2 <= c <= max(60, N // 25)}   # palabras que distinguen un hecho (ni únicas ni comunes)
    idx = collections.defaultdict(list)
    for i, s in enumerate(W):
        for w in s & raras: idx[w].append(i)
    F = [fecha(a) for a in T]
    padre = list(range(N))
    def raiz(i):
        while padre[i] != i: padre[i] = padre[padre[i]]; i = padre[i]
        return i
    pares = collections.Counter()
    for w, L in idx.items():
        if len(L) > 160: continue
        for x in range(len(L)):
            for y in range(x + 1, len(L)): pares[(L[x], L[y])] += 1
    unidos = 0
    for (i, j), comunes in pares.items():
        if comunes < 2 or abs(F[i] - F[j]) > 48 * 3600 or T[i]['m'] == T[j]['m']: continue
        a, b = W[i], W[j]
        inter = sum(idf[w] for w in a & b); union = sum(idf[w] for w in a | b) or 1
        if inter / union >= 0.36 and len(a & b) >= 3 or inter / union >= 0.55 and len(a & b) >= 2:
            ri, rj = raiz(i), raiz(j)
            if ri != rj: padre[ri] = rj; unidos += 1
    grupos = collections.defaultdict(list)
    for i in range(N): grupos[raiz(i)].append(i)
    for a in T: a.pop('c', None)
    ng = 0
    for g in sorted(grupos.values(), key=len, reverse=True):
        medios = {T[i]['m'] for i in g}
        if len(medios) < 2 or len(g) > 80: continue   # un grupo enorme sería un tema general, no un mismo hecho
        ng += 1
        for i in g: T[i]['c'] = ng

    # 3. Temas en aumento: países y lugares nombrados (lugar.py), últimas 24 h frente a la media diaria de los días anteriores
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import lugar
        ahora = max(F) if F else time.time(); ini = min(F) if F else ahora
        dias_prev = max(1.0, (ahora - 86400 - ini) / 86400)
        hoy = collections.Counter(); antes = collections.Counter(); ej = collections.defaultdict(set)
        for a, f in zip(T, F):
            txt = a['t'] if M[a['m']]['i'] in ('en', 'es') else (a.get('n') or a.get('e') or '')
            if not txt: continue
            try: i = lugar.buscar(txt)
            except Exception: i = None
            if i is None: continue
            p = lugar.P[i]
            nombre = p[2]
            (hoy if f >= ahora - 86400 else antes)[nombre] += 1
            if f >= ahora - 86400: ej[nombre].add(M[a['m']]['n'])
        # Los feeds guardan pocos días, así que hay menos titulares antiguos: se compara la proporción, no la cuenta
        t24 = sum(1 for f in F if f >= ahora - 86400) or 1; tant = (len(F) - t24) or 1
        ten = []
        for nombre, n in hoy.items():
            media = antes[nombre] / dias_prev
            x = (n / t24) / max(antes[nombre] / tant, 1.5 / tant)
            if n >= 12 and x >= 2 and len(ej[nombre]) >= 4: ten.append({'lugar': nombre, 'n24': n, 'media': round(media, 1), 'x': round(x, 1), 'medios': len(ej[nombre])})
        ten.sort(key=lambda t: (-t['x'], -t['n24']))
        json.dump({'generado': d.get('generado'), 'nota': 'Lugares nombrados en los titulares de las últimas 24 horas, comparados con su media diaria en los días anteriores de la captura. Cuenta automática, sin valoración.',
                   'datos': ten[:8]}, open(os.path.join(D, 'tendencias.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
        print('temas en aumento', len(ten), [(t['lugar'], t['x']) for t in ten[:5]])
    except Exception as e:
        print('AVISO tendencias', type(e).__name__, str(e)[:100])

    # 4. Traducciones dudosas
    dud = collections.Counter()
    for a in T:
        q = ''
        o = palabras(a['t'])
        for k in ('e', 'n'):
            tr = a.get(k)
            if not tr: continue
            p = palabras(tr)
            iguales = len(set(o) & set(p)) / max(1, len(set(o)))
            r = len(tr) / max(1, len(a['t']))
            if (len(o) >= 4 and iguales > 0.5) or r < 0.45 or r > 2.2: q += k; dud[k] += 1
        if q: a['q'] = q
        else: a.pop('q', None)

    json.dump(d, open(ruta, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print('repetidos quitados', quitados, '· grupos de una misma noticia', ng, 'con', sum(1 for a in T if 'c' in a), 'titulares',
          '· traducciones dudosas', dict(dud), '· seg', round(time.time() - T0, 1))

if __name__ == '__main__':
    main()
