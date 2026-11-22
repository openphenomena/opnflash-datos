# -*- coding: utf-8 -*-
"""Ubicación de titulares para opnflash.com.

Estrategia, por orden:
  1. el lugar que nombra el titular (ciudad, estado o país; en el idioma original);
  2. el lugar que nombra el resumen del feed (se lee solo para ubicar: no se guarda ni se muestra);
  3. la sede del medio (tabla referencia/medios/sedes-medios.json, país en el nombre o dominio nacional);
  4. si no hay nada de lo anterior, el titular no lleva punto en el mapa.
Diccionario: lugares.json (Natural Earth, dominio público; lo crea lugares_crear.py).
Uso suelto, para reubicar un titulares.json ya capturado:  python3 lugar.py public/datos/titulares.json
"""
import json, os, re, sys, unicodedata, zlib
AQUI = os.path.dirname(os.path.abspath(__file__))
L = json.load(open(os.path.join(AQUI, 'lugares.json'), encoding='utf-8'))
P, N, S, C, G = L['p'], L['n'], L['s'], L['c'], L['g']
try: SEDES = json.load(open(os.path.join(AQUI, '..', 'referencia', 'medios', 'sedes-medios.json'), encoding='utf-8'))['sedes']
except Exception: SEDES = {}
TLD = {'es': 'ESP', 'mx': 'MEX', 'ar': 'ARG', 'cl': 'CHL', 've': 'VEN', 'ec': 'ECU', 'uy': 'URY', 'py': 'PRY', 'bo': 'BOL', 'cr': 'CRI', 'pa': 'PAN', 'do': 'DOM', 'gt': 'GTM', 'hn': 'HND', 'sv': 'SLV', 'ni': 'NIC',
       'cu': 'CUB', 'br': 'BRA', 'ca': 'CAN', 'us': 'USA', 'gov': 'USA', 'fr': 'FRA', 'de': 'DEU', 'it': 'ITA', 'pt': 'PRT', 'uk': 'GBR', 'ie': 'IRL', 'nl': 'NLD', 'be': 'BEL', 'ch': 'CHE', 'at': 'AUT', 'se': 'SWE', 'no': 'NOR',
       'dk': 'DNK', 'fi': 'FIN', 'is': 'ISL', 'pl': 'POL', 'cz': 'CZE', 'sk': 'SVK', 'hu': 'HUN', 'ro': 'ROU', 'bg': 'BGR', 'gr': 'GRC', 'hr': 'HRV', 'si': 'SVN', 'rs': 'SRB', 'ba': 'BIH', 'al': 'ALB', 'md': 'MDA', 'ua': 'UKR',
       'ru': 'RUS', 'lt': 'LTU', 'lv': 'LVA', 'ee': 'EST', 'lu': 'LUX', 'ad': 'AND', 'tr': 'TUR', 'il': 'ISR', 'ir': 'IRN', 'ps': 'PSX', 'om': 'OMN', 'ly': 'LBY', 'ge': 'GEO', 'az': 'AZE', 'uz': 'UZB', 'kg': 'KGZ', 'tj': 'TJK',
       'mn': 'MNG', 'kr': 'KOR', 'jp': 'JPN', 'cn': 'CHN', 'tw': 'TWN', 'vn': 'VNM', 'lk': 'LKA', 'sg': 'SGP', 'in': 'IND', 'pk': 'PAK', 'au': 'AUS', 'nz': 'NZL', 'pg': 'PNG', 'fj': 'FJI', 'za': 'ZAF', 'cv': 'CPV', 'sn': 'SEN',
       'mg': 'MDG', 'tz': 'TZA', 'rw': 'RWA', 'na': 'NAM', 'zw': 'ZWE', 'ug': 'UGA', 'cd': 'COD', 'st': 'STP', 'ke': 'KEN', 'ng': 'NGA', 'gh': 'GHA', 'et': 'ETH', 'eg': 'EGY', 'ma': 'MAR', 'bb': 'BRB', 'pe': 'PER', 'co': 'COL',
       'kz': 'KAZ', 'am': 'ARM', 'by': 'BLR', 'mk': 'MKD', 'me': 'MNE', 'cy': 'CYP', 'mt': 'MLT', 'sm': 'SMR', 'li': 'LIE', 'jo': 'JOR', 'lb': 'LBN', 'sa': 'SAU', 'ae': 'ARE', 'qa': 'QAT', 'kw': 'KWT', 'bh': 'BHR', 'iq': 'IRQ',
       'sy': 'SYR', 'dz': 'DZA', 'tn': 'TUN', 'th': 'THA', 'my': 'MYS', 'id': 'IDN', 'ph': 'PHL', 'bd': 'BGD', 'np': 'NPL', 'kh': 'KHM', 'la': 'LAO', 'mm': 'MMR', 'bt': 'BTN', 'mv': 'MDV', 'af': 'AFG', 'tt': 'TTO', 'jm': 'JAM',
       'ht': 'HTI', 'gy': 'GUY', 'sr': 'SUR', 'bz': 'BLZ', 'bs': 'BHS'}
PAIS = {p[4]: i for i, p in enumerate(P) if p[3] == 'p'}
CAPITAL = L['cap']
PTS = L.get('pts', {})
CJK = re.compile(r'[぀-ヿ一-鿿]')
def nz(s): return re.sub(r'\s+', ' ', re.sub(r"[^\w ]", ' ', ''.join(c for c in unicodedata.normalize('NFD', (s or '').lower()) if unicodedata.category(c) != 'Mn'))).strip()
ORDEN = {'c': 3, 'e': 2, 'p': 1}

AMB = L.get('amb', {})
GEORGIA_EEUU = next((i for i, p in enumerate(P) if p[3] == 'e' and p[4] == 'USA' and p[2] == 'Georgia'), None)

def buscar(texto, a3=None, paises=None):
    """Devuelve el índice del lugar más concreto que nombra el texto, o None.

    Reglas para los nombres repetidos en varios países (Valencia, Córdoba, Mérida, Santiago, Georgia…):
      1. si el texto nombra también un país (o `paises` trae los ya nombrados en el titular), gana el lugar de ese país;
      2. si no, gana el lugar del país del medio (`a3`);
      3. si no, solo se acepta el mayor cuando es al menos cinco veces más grande que el segundo;
      4. si sigue la duda, ese nombre no se usa: es mejor no ubicar que ubicar mal.
    """
    if not texto: return None
    # Escrituras de la India y del sudeste asiático: al separar palabras se cortan en los signos vocálicos y los trozos coinciden con nombres de ciudades (titular nepalí sobre Irán ubicado en Coro). En esos alfabetos no se buscan lugares.
    texto = re.sub(r"[\u0900-\u0DFF\u0E00-\u0FFF\u1000-\u109F\u1780-\u17FF]+", ' ', texto)
    texto = re.sub(r"\b(Texas Instruments|New York Times|Wall Street Journal|Washington Post|New York Post|Los Angeles Times|Boston Globe|Miami Herald|Real Madrid|Atlético de Madrid|Bayern Munich|Paris Saint-Germain|Inter Miami|Manchester (United|City)|Santiago Bernabéu)\b", ' ', texto)
    texto = re.sub(r"\bEE\.?\s?UU\.?|\bU\.S\.(A\.)?|\bUSA\b|\bUS\b(?!\$)", ' Estados Unidos ', texto)
    texto = re.sub(r"\bU\.K\.|\bUK\b", ' Reino Unido ', texto)
    texto = re.sub(r"[’']s\b", '', texto)
    M = []   # (posición, índice, clave)
    if CJK.search(texto):
        for nom, i in C.items():
            k = texto.find(nom)
            if k >= 0: M.append((k, i, None))
    pal = [(m.group(0), m.start()) for m in re.finditer(r"[^\W\d_]+(?:[.'’-][^\W\d_]+)*\.?", texto)]
    n = len(pal); i = 0
    while i < n:
        hecho = False
        for k in (4, 3, 2, 1):
            if i + k > n: continue
            trozo = ' '.join(w for w, _ in pal[i:i + k]); clave = nz(trozo)
            if not clave: continue
            w0 = pal[i][0]
            if clave in S: M.append((pal[i][1], S[clave], None)); hecho = True
            elif w0[0].isupper() or not w0[0].isalpha():
                if clave in N:
                    j = N[clave]; p = P[j]
                    if k == 1 and p[3] == 'c' and p[5] < 100_000 and clave not in AMB: continue   # ciudades pequeñas de una sola palabra: demasiado ambiguas
                    M.append((pal[i][1], j, clave)); hecho = True
            if not hecho and k == 1 and clave in G: M.append((pal[i][1], G[clave], None)); hecho = True
            if hecho: i += k; break
        if not hecho: i += 1
    nombrados = set(paises or ()) | {P[j][4] for _, j, _ in M if P[j][3] == 'p'}
    mejor = None
    for pos, j, clave in M:
        if clave in AMB:
            cand = AMB[clave]
            de = [c for c in cand if P[c][4] in nombrados] or ([c for c in cand if P[c][4] == a3] if a3 else [])
            if de: j = max(de, key=lambda c: P[c][5])
            else:
                o = sorted(cand, key=lambda c: -P[c][5])
                if P[o[0]][5] >= 5 * max(1, P[o[1]][5]) and P[o[0]][3] == 'c': j = o[0]
                else: continue
        if P[j][4] == 'GEO' and P[j][3] == 'p' and a3 in ('USA', 'CAN') and GEORGIA_EEUU is not None: j = GEORGIA_EEUU   # en un medio de EE. UU., «Georgia» es el estado
        c = (ORDEN[P[j][3]], -pos, j)
        if mejor is None or c > mejor: mejor = c
    return mejor[2] if mejor else None

def punto(i, modo, clave=''):
    """Una ciudad va en su sitio. Un país o un estado no es un punto: el titular se reparte dentro de él (siempre en el mismo sitio para el mismo titular)."""
    p = P[i]; q = PTS.get(str(i))
    if p[3] != 'c' and q:
        x, y = q[zlib.crc32(clave.encode('utf-8')) % len(q)]
        return [x, y, p[2], modo]
    return [p[0], p[1], p[2], modo]

def por_sede(h, clave):
    """Titular sin lugar propio: se reparte por el país donde tiene su sede el medio."""
    i = PAIS.get(h[3]) if len(h) > 3 else None
    return punto(i, 'm', clave) if i is not None else [h[0], h[1], h[2], 'm']

def ubicar(titulo, resumen=None, a3=None):
    """[lon, lat, nombre, 't'] si lo nombra el titular; 'r' si lo nombra el resumen; None si no. a3: país del medio, para deshacer nombres repetidos."""
    i = buscar(titulo, a3)
    if i is not None and P[i][3] != 'p': return punto(i, 't', titulo)
    j = buscar(resumen, a3, [P[i][4]] if i is not None else None) if resumen else None
    if j is not None and (i is None or (P[j][3] != 'p' and P[j][4] == P[i][4])): return punto(j, 'r' if i is None else 't', titulo)
    return punto(i, 't', titulo) if i is not None else None

def sede(medio):
    """Sede del medio: [lon, lat, nombre] o None. medio = {'n': nombre, 's': dominio, 'r': región}."""
    def de(txt):
        i = buscar(txt)
        if i is None: i = N.get(nz(txt))
        if i is None: return None
        if P[i][3] == 'p' and P[i][4] in CAPITAL: i = CAPITAL[P[i][4]]
        return P[i][:3] + [P[i][4]]
    n = medio['n']
    if n in SEDES: return de(SEDES[n]) if SEDES[n] else None
    m = re.search(r'\s[—–]\s(.+)$', n)
    if m: return de(m.group(1))
    if medio.get('r') == 'general': return None
    t = (medio.get('s') or '').split('.')[-1]
    if t in TLD and TLD[t] in CAPITAL: return P[CAPITAL[TLD[t]]][:3] + [TLD[t]]
    return de(n)

if __name__ == '__main__':
    f = sys.argv[1]; d = json.load(open(f, encoding='utf-8'))
    for m in d['medios']:
        h = sede(m)
        if h: m['h'] = h
        else: m.pop('h', None)
    for a in d['titulares']:
        h_ = d['medios'][a['m']].get('h'); g = ubicar(a['t'], None, h_[3] if h_ and len(h_) > 3 else None) or ('h' in d['medios'][a['m']] and por_sede(d['medios'][a['m']]['h'], a['t']))
        if g: a['g'] = g
        else: a.pop('g', None)
    json.dump(d, open(f, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    T = d['titulares']; print('titulares', len(T), 'con lugar propio', sum(1 for a in T if 'g' in a), 'con sede del medio', sum(1 for a in T if 'g' not in a and 'h' in d['medios'][a['m']]), 'medios con sede', sum(1 for m in d['medios'] if 'h' in m))
