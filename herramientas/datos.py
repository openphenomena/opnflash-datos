#!/usr/bin/env python3
"""opnflash.com — recoge las fuentes aprobadas y escribe public/datos/portada.json (todo en español).

Fuentes aprobadas por el usuario (ESTADO.md, 21/11 19:05): USGS, GDACS, NASA EONET, GDELT, NOAA SWPC, CelesTrak,
Cloudflare Radar (solo gráficos insertables), Copernicus EMS (citando; aún no integrado), GWIS/EFFIS (aún no integrado),
NOAA NHC, arXiv, SINC, Global Voices en Español, Noticias ONU (no se usa hasta fijar cómo se la informa).
Descartadas: NASA FIRMS, UCDP.
Uso: python3 herramientas/datos.py [carpeta-public]
"""
import json, os, sys, time, re, math, datetime as dt, urllib.request, urllib.parse, xml.etree.ElementTree as ET

AQUI = os.path.dirname(os.path.abspath(__file__))
PUB = sys.argv[1] if len(sys.argv) > 1 else os.path.join(AQUI, '..', 'public')
UA = {'User-Agent': 'opnflash.com (datos publicos; contacto en el sitio)'}

def get(url, tries=2, wait=5, raw=False):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                b = r.read()
                return b if raw else json.loads(b)
        except Exception as e:
            err = e
            time.sleep(wait)
    print('AVISO', url, err); return None

def ahora(): return dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

# --- nombres de países en español (Natural Earth, dominio público) ---
NE = json.load(open(os.path.join(AQUI, 'ne_paises.json'), encoding='utf-8'))  # iso3 -> nombre ES

PUNTOS = {'N': 'N', 'S': 'S', 'E': 'E', 'W': 'O', 'NE': 'NE', 'NW': 'NO', 'SE': 'SE', 'SW': 'SO',
          'NNE': 'NNE', 'NNW': 'NNO', 'SSE': 'SSE', 'SSW': 'SSO', 'ENE': 'ENE', 'ESE': 'ESE', 'WNW': 'ONO', 'WSW': 'OSO'}
def lugar_es(p):
    if not p: return ''
    m = re.match(r'^(\d+)\s*km\s+([NSEW]{1,3})\s+of\s+(.*)$', p)
    if m: return f'A {m.group(1)} km al {PUNTOS.get(m.group(2), m.group(2))} de {m.group(3)}'
    return p.replace(' region', ', región').replace('south of the', 'al sur de').replace('off the coast of', 'frente a la costa de')

def terremotos():
    d = get('https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_week.geojson')
    if not d: return None
    out = []
    for f in d['features']:
        p = f['properties']; lon, lat, prof = f['geometry']['coordinates']
        out.append({'mag': round(p['mag'] or 0, 1), 'lugar': lugar_es(p.get('place')), 'hora': p['time'], 'lat': lat, 'lon': lon,
                    'prof': round(prof or 0), 'tsunami': bool(p.get('tsunami')), 'url': p.get('url')})
    out.sort(key=lambda x: -x['hora'])
    return {'fuente': 'USGS · Servicio Geológico de EE. UU.', 'licencia': 'Dominio público', 'enlace': 'https://earthquake.usgs.gov/',
            'actualizado': ahora(), 'datos': out}

TIPO_GDACS = {'EQ': 'Terremoto', 'TC': 'Ciclón tropical', 'FL': 'Inundación', 'VO': 'Volcán', 'DR': 'Sequía', 'WF': 'Incendio forestal', 'TS': 'Tsunami'}
NIVEL = {'Green': 'verde', 'Orange': 'naranja', 'Red': 'roja'}
def alertas():
    d = get('https://www.gdacs.org/gdacsapi/api/events/geteventlist/EVENTS4APP')
    if not d: return None
    out = []
    for f in d['features']:
        p = f['properties']; g = f['geometry']
        if g.get('type') != 'Point': continue
        paises = [NE.get(a.get('iso3'), a.get('countryname')) for a in p.get('affectedcountries') or []]
        sev = (p.get('severitydata') or {})
        out.append({'nombre': p.get('name'), 'tipo': TIPO_GDACS.get(p['eventtype'], p['eventtype']), 'codigo': p['eventtype'], 'nivel': NIVEL.get(p['alertlevel'], p['alertlevel']),
                    'paises': [x for x in paises if x], 'desde': p.get('fromdate'), 'hasta': p.get('todate'),
                    'gravedad': sev.get('severity'), 'unidad': sev.get('severityunit'),
                    'lat': g['coordinates'][1], 'lon': g['coordinates'][0], 'url': (p.get('url') or {}).get('report')})
    orden = {'roja': 0, 'naranja': 1, 'verde': 2}
    out.sort(key=lambda x: (orden.get(x['nivel'], 3), x['desde'] or ''), reverse=False)
    return {'fuente': 'GDACS · Naciones Unidas y Comisión Europea', 'licencia': 'Reutilización autorizada citando la fuente (© Unión Europea)',
            'enlace': 'https://www.gdacs.org/', 'actualizado': ahora(), 'datos': out}

CAT_EONET = {'wildfires': 'Incendio', 'volcanoes': 'Volcán', 'severeStorms': 'Tormenta', 'seaLakeIce': 'Hielo marino', 'floods': 'Inundación',
             'dustHaze': 'Polvo y bruma', 'earthquakes': 'Terremoto', 'landslides': 'Deslizamiento', 'snow': 'Nieve', 'drought': 'Sequía',
             'tempExtremes': 'Temperatura extrema', 'waterColor': 'Color del agua', 'manmade': 'Origen humano'}
def eventos():
    d = get('https://eonet.gsfc.nasa.gov/api/v3/events?status=open&limit=300&days=30')
    if not d: return None
    out = []
    for e in d['events']:
        g = e['geometry'][-1]
        if g.get('type') != 'Point': continue
        cat = e['categories'][0]['id']
        out.append({'titulo': e['title'], 'categoria': CAT_EONET.get(cat, cat), 'codigo': cat, 'fecha': g['date'],
                    'lat': g['coordinates'][1], 'lon': g['coordinates'][0], 'url': (e.get('sources') or [{}])[0].get('url')})
    return {'fuente': 'NASA EONET · Observatorio de eventos naturales', 'licencia': 'Dominio público', 'enlace': 'https://eonet.gsfc.nasa.gov/',
            'actualizado': ahora(), 'datos': out}

def clima_espacial():
    kp = get('https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json')
    if not kp: return None
    serie = [{'hora': r['time_tag'], 'kp': float(r['Kp'])} for r in kp][-24:]
    k = serie[-1]['kp']
    escala = 'G0 · sin tormenta' if k < 5 else ('G1 · menor' if k < 6 else 'G2 · moderada' if k < 7 else 'G3 · fuerte' if k < 8 else 'G4 · severa' if k < 9 else 'G5 · extrema')
    return {'fuente': 'NOAA SWPC · Centro de Predicción del Clima Espacial', 'licencia': 'Datos abiertos de EE. UU. (sin respaldo de NOAA)',
            'enlace': 'https://www.swpc.noaa.gov/', 'actualizado': ahora(), 'datos': {'kp': k, 'escala': escala, 'serie': serie}}

def ciclones():
    d = get('https://www.nhc.noaa.gov/CurrentStorms.json')
    if d is None: return None
    out = [{'nombre': s.get('name'), 'tipo': s.get('classification'), 'viento_kt': s.get('intensity'), 'presion': s.get('pressure'),
            'lat': s.get('latitudeNumeric'), 'lon': s.get('longitudeNumeric'), 'url': (s.get('publicAdvisory') or {}).get('url')}
           for s in d.get('activeStorms', [])]
    return {'fuente': 'NOAA NHC · Centro Nacional de Huracanes', 'licencia': 'Dominio público', 'enlace': 'https://www.nhc.noaa.gov/',
            'actualizado': ahora(), 'datos': out}

def tiangong():
    """Estación espacial china (CSS, Tianhe). Solo los elementos orbitales: la posición se calcula en el navegador."""
    d = get('https://celestrak.org/NORAD/elements/gp.php?CATNR=48274&FORMAT=TLE', raw=True)
    if not d: return None
    return {'fuente': 'CelesTrak · elementos orbitales', 'licencia': 'Datos públicos', 'enlace': 'https://celestrak.org/', 'actualizado': ahora(), 'datos': {'tle': d.decode().strip().splitlines()}}

def iss():
    d = get('https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=TLE', raw=True)
    if not d: return None
    l = d.decode().strip().splitlines()
    try:
        from sgp4.api import Satrec, jday
    except ImportError:
        return {'fuente': 'CelesTrak', 'licencia': 'Datos públicos', 'enlace': 'https://celestrak.org/', 'actualizado': ahora(), 'datos': {'tle': l}}
    s = Satrec.twoline2rv(l[1], l[2]); t = dt.datetime.now(dt.timezone.utc)
    jd, fr = jday(t.year, t.month, t.day, t.hour, t.minute, t.second)
    e, r, v = s.sgp4(jd, fr)
    # TEME -> lat/lon aproximados (sin nutación; suficiente para el mapa)
    gmst = (280.46061837 + 360.98564736629 * (jd + fr - 2451545.0)) % 360
    lon = (math.degrees(math.atan2(r[1], r[0])) - gmst + 540) % 360 - 180
    lat = math.degrees(math.atan2(r[2], math.hypot(r[0], r[1])))
    alt = math.sqrt(sum(x * x for x in r)) - 6371
    return {'fuente': 'CelesTrak · elementos orbitales', 'licencia': 'Datos públicos', 'enlace': 'https://celestrak.org/', 'actualizado': ahora(),
            'datos': {'lat': round(lat, 2), 'lon': round(lon, 2), 'alt_km': round(alt), 'tle': l}}

def ciencia():
    out = []
    # «astro-ph» a secas solo encuentra artículos antiguos (desde 2009 se usan subcategorías): se piden todas.
    for cat, nombre in [('cat:cs.AI', 'Inteligencia artificial'), ('+OR+'.join('cat:astro-ph.' + s for s in ('CO', 'EP', 'GA', 'HE', 'IM', 'SR')), 'Astronomía')]:
        b = get(f'https://export.arxiv.org/api/query?search_query={cat}&sortBy=submittedDate&sortOrder=descending&max_results=6', raw=True)
        if not b: continue
        ns = {'a': 'http://www.w3.org/2005/Atom'}
        for en in ET.fromstring(b).findall('a:entry', ns):
            out.append({'tema': nombre, 'titulo': ' '.join(en.find('a:title', ns).text.split()),
                        'autores': [a.find('a:name', ns).text for a in en.findall('a:author', ns)][:3],
                        'fecha': en.find('a:published', ns).text, 'url': en.find('a:id', ns).text})
        time.sleep(3)
    return {'fuente': 'arXiv · Universidad Cornell', 'licencia': 'Metadatos libres; cada artículo tiene su propia licencia (solo se enlaza)',
            'enlace': 'https://arxiv.org/', 'actualizado': ahora(), 'datos': out}

def noticias():
    q = urllib.parse.quote('sourcelang:spanish (conflicto OR ataque OR bombardeo OR terremoto OR inteligencia artificial OR satélite)')
    d = get(f'https://api.gdeltproject.org/api/v2/doc/doc?query={q}&mode=artlist&format=json&maxrecords=25&sort=datedesc', tries=3, wait=12)
    datos = []
    if d:
        for a in d.get('articles', []):
            datos.append({'titulo': a.get('title'), 'medio': a.get('domain'), 'pais': a.get('sourcecountry'), 'fecha': a.get('seendate'), 'url': a.get('url')})
    return {'fuente': 'GDELT Project', 'licencia': 'Uso libre citando y enlazando a gdeltproject.org',
            'nota': 'Detección automática de noticias publicadas por medios: no es una fuente primaria.',
            'enlace': 'https://www.gdeltproject.org/', 'actualizado': ahora(), 'datos': datos}

def _rss(url, medio, n=12):
    b = get(url, raw=True)
    if not b: return []
    from email.utils import parsedate_to_datetime
    dc = '{http://purl.org/dc/elements/1.1/}creator'
    out = []
    for it in ET.fromstring(b).iter('item'):
        try: f = parsedate_to_datetime(it.findtext('pubDate')).astimezone(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        except Exception: f = None
        out.append({'medio': medio, 'titulo': ' '.join((it.findtext('title') or '').split()), 'url': (it.findtext('link') or '').strip(),
                    'fecha': f, 'autor': (it.findtext(dc) or it.findtext('author') or medio).strip(), 'tema': (it.findtext('category') or '').strip()})
        if len(out) >= n: break
    return out

def _comision(n=12):
    """Comisión Europea: solo los comunicados que existen en español (CC BY 4.0)."""
    out = []
    for pg in (1, 2):
        d = get(f'https://ec.europa.eu/commission/presscorner/api/search?language=es&pagesize=50&pagenumber={pg}&documenttype=1')
        for x in (d or {}).get('docuLanguageListResources', []):
            if x.get('languageCode') == 'ES':
                out.append({'medio': 'Comisión Europea', 'titulo': ' '.join(x['title'].split()), 'fecha': x['eventDate'] + 'T12:00:00Z',
                            'url': 'https://ec.europa.eu/commission/presscorner/detail/es/' + x['refCode'].lower().replace('/', '_'),
                            'autor': 'Comisión Europea', 'tema': x['docutype']['description']})
        if len(out) >= n: break
    return out[:n]

def noticias_es():
    """Fuentes aprobadas el 21/11 19:03: SINC (CC BY 4.0, solo lo producido por SINC) y Global Voices en Español
    (CC BY 3.0: enlace a la nota, nombre del autor y enlace a la licencia; sin fotos ni multimedia de terceros).
    Solo se muestran título, autor, fecha y enlace. Noticias ONU queda fuera hasta fijar cómo se la informa."""
    datos = _rss('https://www.agenciasinc.es/feed/Noticias', 'SINC') + _rss('https://es.globalvoices.org/feed/', 'Global Voices')
    datos += _rss('https://ciencia.nasa.gov/feed/', 'NASA en español') + _comision()
    datos.sort(key=lambda a: a['fecha'] or '', reverse=True)
    return {'fuente': 'SINC · Global Voices · Comisión Europea · NASA en español', 'licencia': 'Cada fuente con su licencia',
            'licencias': {'SINC': {'nombre': 'CC BY 4.0', 'url': 'https://creativecommons.org/licenses/by/4.0/deed.es', 'web': 'https://www.agenciasinc.es/'},
                          'Global Voices': {'nombre': 'CC BY 3.0', 'url': 'https://creativecommons.org/licenses/by/3.0/deed.es', 'web': 'https://es.globalvoices.org/'},
                          'Comisión Europea': {'nombre': 'CC BY 4.0', 'url': 'https://creativecommons.org/licenses/by/4.0/deed.es', 'web': 'https://ec.europa.eu/commission/presscorner/home/es'},
                          'NASA en español': {'nombre': 'Material de la NASA', 'url': 'https://www.nasa.gov/nasa-brand-center/images-and-media/', 'web': 'https://ciencia.nasa.gov/'}},
            'enlace': 'https://www.agenciasinc.es/', 'actualizado': ahora(), 'datos': datos}

def main():
    os.makedirs(os.path.join(PUB, 'datos'), exist_ok=True)
    portada = {'generado': ahora()}
    try: antes = json.load(open(os.path.join(PUB, 'datos', 'portada.json'), encoding='utf-8'))
    except Exception: antes = {}
    for k, fn in [('terremotos', terremotos), ('alertas', alertas), ('eventos', eventos), ('clima_espacial', clima_espacial),
                  ('ciclones', ciclones), ('iss', iss), ('tiangong', tiangong), ('ciencia', ciencia), ('noticias', noticias), ('noticias_es', noticias_es)]:
        r = fn()
        # Si una fuente de noticias falla en esta pasada (GDELT responde a menudo «429 Too Many Requests» a GitHub), se conserva lo de la anterior
        if k in ('ciencia', 'noticias', 'noticias_es') and r and not r.get('datos') and (antes.get(k) or {}).get('datos'):
            r = antes[k]; print('AVISO', k, 'sin datos en esta pasada: se conserva la anterior')
        portada[k] = r
        print(k, 'sin datos' if not r else (len(r['datos']) if isinstance(r['datos'], list) else 'ok'))
    json.dump(portada, open(os.path.join(PUB, 'datos', 'portada.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))

if __name__ == '__main__':
    main()
