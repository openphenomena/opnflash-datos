# -*- coding: utf-8 -*-
"""Capas del modo Experto de opnflash.com con fuentes aprobadas por el usuario el 22/11/2026.

Guarda public/datos/capas.json. Cada capa lleva su fuente, su licencia y la hora de la consulta.
Una fuente que no responde deja su capa vacía (el sitio no la muestra y no avisa: regla 19); un solo intento por fuente (regla 16).
Uso:  python3 capas.py [carpeta public]
"""
import csv, io, json, os, re, sys, datetime as dt, urllib.request, urllib.parse

AQUI = os.path.dirname(os.path.abspath(__file__))
PUB = sys.argv[1] if len(sys.argv) > 1 else os.path.join(AQUI, '..', 'public')
UA = {'User-Agent': 'opnflash.com (+https://www.opnflash.com/acerca.html)', 'Accept': 'application/geo+json, application/json, text/csv, */*'}
AHORA = dt.datetime.now(dt.timezone.utc)
ISO = lambda d: d.strftime('%Y-%m-%dT%H:%M:%SZ')

def pedir(url, seg=40):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=seg) as r:
        return r.read()

def centro(geom):
    """Punto medio aproximado de un polígono o multipolígono GeoJSON."""
    if not geom: return None
    c = geom['coordinates']
    while c and isinstance(c[0][0], list): c = c[0]
    if not c: return None
    return [round(sum(p[0] for p in c) / len(c), 2), round(sum(p[1] for p in c) / len(c), 2)]

def incendios():
    """NASA FIRMS, archivo público de 24 h (MODIS), sin clave. Solo detecciones de confianza alta; las 1.200 de más potencia."""
    t = pedir('https://firms.modaps.eosdis.nasa.gov/data/active_fire/modis-c6.1/csv/MODIS_C6_1_Global_24h.csv', 90).decode('utf-8', 'replace')
    F = []
    for r in csv.DictReader(io.StringIO(t)):
        try:
            if int(r['confidence']) < 80: continue
            h = r['acq_time'].zfill(4)
            F.append([round(float(r['longitude']), 2), round(float(r['latitude']), 2), round(float(r['frp'])), r['acq_date'] + 'T' + h[:2] + ':' + h[2:] + ':00Z', r['daynight']])
        except Exception: continue
    F.sort(key=lambda x: -x[2])
    return {'fuente': 'NASA FIRMS / LANCE · MODIS', 'licencia': 'Datos de la NASA, de uso libre citando a NASA FIRMS', 'enlace': 'https://firms.modaps.eosdis.nasa.gov/', 'total': len(F), 'datos': F[:1200]}

EVENTOS = {'Tornado Warning': 'Aviso de tornado', 'Tornado Watch': 'Vigilancia de tornado', 'Flood Warning': 'Aviso de inundación', 'Flash Flood Warning': 'Aviso de crecida repentina', 'Flood Watch': 'Vigilancia de inundación',
           'Coastal Flood Warning': 'Aviso de inundación costera', 'Storm Warning': 'Aviso de tormenta (mar)', 'Storm Watch': 'Vigilancia de tormenta (mar)', 'Special Marine Warning': 'Aviso marítimo especial',
           'Freeze Warning': 'Aviso de helada', 'Freeze Watch': 'Vigilancia de helada', 'Heavy Freezing Spray Warning': 'Aviso de rocío helado intenso', 'High Wind Warning': 'Aviso de viento fuerte', 'High Wind Watch': 'Vigilancia de viento fuerte',
           'Hurricane Warning': 'Aviso de huracán', 'Hurricane Watch': 'Vigilancia de huracán', 'Tropical Storm Warning': 'Aviso de tormenta tropical', 'Severe Thunderstorm Warning': 'Aviso de tormenta eléctrica severa',
           'Severe Thunderstorm Watch': 'Vigilancia de tormenta eléctrica severa', 'Winter Storm Warning': 'Aviso de tormenta invernal', 'Winter Storm Watch': 'Vigilancia de tormenta invernal', 'Blizzard Warning': 'Aviso de ventisca',
           'Ice Storm Warning': 'Aviso de tormenta de hielo', 'Red Flag Warning': 'Aviso de riesgo extremo de incendio', 'Extreme Heat Warning': 'Aviso de calor extremo', 'Excessive Heat Warning': 'Aviso de calor excesivo',
           'Extreme Cold Warning': 'Aviso de frío extremo', 'Tsunami Warning': 'Aviso de tsunami', 'Storm Surge Warning': 'Aviso de marejada ciclónica', 'Dust Storm Warning': 'Aviso de tormenta de polvo', 'Avalanche Warning': 'Aviso de avalancha',
           'Hurricane Force Wind Warning': 'Aviso de viento huracanado', 'Gale Warning': 'Aviso de temporal', 'Lake Effect Snow Warning': 'Aviso de nevada por efecto lago', 'Wind Chill Warning': 'Aviso de sensación térmica extrema'}
CA = {'warning': 'Aviso', 'watch': 'Vigilancia', 'advisory': 'Advertencia', 'statement': 'Boletín'}
CA_EV = {'special weather': 'meteorológico especial', 'wind': 'de viento', 'rainfall': 'de lluvia', 'snowfall': 'de nevada', 'winter storm': 'de tormenta invernal', 'blizzard': 'de ventisca', 'freezing rain': 'de lluvia engelante',
         'fog': 'de niebla', 'extreme cold': 'de frío extremo', 'heat': 'de calor', 'tornado': 'de tornado', 'severe thunderstorm': 'de tormenta eléctrica severa', 'hurricane': 'de huracán', 'tropical storm': 'de tormenta tropical',
         'storm surge': 'de marejada ciclónica', 'snow squall': 'de chubasco de nieve', 'arctic outflow': 'de aire ártico', 'blowing snow': 'de ventisca baja', 'freezing drizzle': 'de llovizna engelante', 'air quality': 'de calidad del aire',
         'frost': 'de helada', 'flash freeze': 'de congelación repentina', 'coastal flooding': 'de inundación costera', 'weather': 'meteorológico'}

def meteo():
    """Avisos graves y extremos de NOAA NWS (EE. UU., dominio público) y avisos de Environment and Climate Change Canada."""
    out = []; fuentes = []
    try:
        d = json.loads(pedir('https://api.weather.gov/alerts/active?status=actual&severity=Extreme,Severe'))
        for f in d.get('features', []):
            p = f['properties']; c = centro(f.get('geometry'))
            if not c: continue
            out.append({'lon': c[0], 'lat': c[1], 'pais': 'EE. UU.', 'tipo': EVENTOS.get(p['event'], p['event']), 'es': p['event'] in EVENTOS, 'nivel': 'extremo' if p.get('severity') == 'Extreme' else 'grave',
                        'zona': (p.get('areaDesc') or '')[:120], 'desde': p.get('effective'), 'hasta': p.get('expires') or p.get('ends'), 'emisor': p.get('senderName') or 'NWS', 'url': 'https://www.weather.gov/'})
        fuentes.append('NOAA NWS')
    except Exception as e: print('AVISO meteo NWS', type(e).__name__)
    try:
        d = json.loads(pedir('https://api.weather.gc.ca/collections/weather-alerts/items?f=json&limit=500'))
        visto = set()
        for f in d.get('features', []):
            p = f['properties']
            if p.get('status_en') == 'ended' or p.get('alert_type') not in ('warning', 'watch'): continue
            c = centro(f.get('geometry')); k = (p.get('alert_name_en'), p.get('feature_name_en'))
            if not c or k in visto: continue
            visto.add(k); ev = (p.get('alert_short_name_en') or '').lower()
            out.append({'lon': c[0], 'lat': c[1], 'pais': 'Canadá', 'tipo': CA.get(p['alert_type'], 'Aviso') + ' ' + CA_EV.get(ev, '· ' + (p.get('alert_name_en') or '')), 'es': ev in CA_EV, 'nivel': 'grave' if p['alert_type'] == 'warning' else 'vigilancia',
                        'zona': (p.get('feature_name_fr') or p.get('feature_name_en') or '')[:120] + (', ' + p['province'] if p.get('province') else ''), 'desde': p.get('validity_datetime') or p.get('publication_datetime'),
                        'hasta': p.get('event_end_datetime') or p.get('expiration_datetime'), 'emisor': 'Environment and Climate Change Canada', 'url': 'https://weather.gc.ca/warnings/index_e.html'})
        fuentes.append('Environment and Climate Change Canada')
    except Exception as e: print('AVISO meteo Canadá', type(e).__name__)
    if not fuentes: raise RuntimeError('sin fuentes')
    return {'fuente': ' · '.join(fuentes), 'licencia': 'NOAA NWS: dominio público · Fuente: Environment and Climate Change Canada (licencia de sus servidores de datos)', 'enlace': 'https://www.weather.gov/alerts', 'datos': out[:600]}

def radiacion():
    """Safecast (CC0): sensores fijos con lectura en los últimos 14 días. Tubo LND 7318: 334 cuentas por minuto ≈ 1 µSv/h."""
    d = json.loads(pedir('https://tt.safecast.org/devices?template=%7B%22device%22:null,%22when_captured%22:null,%22loc_lat%22:null,%22loc_lon%22:null,%22lnd_7318u%22:null%7D', 60))
    out = []
    for x in d:
        try:
            c = x.get('lnd_7318u'); t = dt.datetime.fromisoformat(x['when_captured'].replace('Z', '+00:00'))
            if not c or (AHORA - t).days > 14 or x.get('loc_lat') is None: continue
            out.append([round(x['loc_lon'], 2), round(x['loc_lat'], 2), round(c / 334, 3), ISO(t)])
        except Exception: continue
    return {'fuente': 'Safecast', 'licencia': 'CC0 (dominio público)', 'enlace': 'https://safecast.org/', 'datos': out}

import lugar   # diccionario de lugares (Natural Earth) que ya usa la captura de titulares

def pais_iso3(a3):
    i = lugar.PAIS.get(a3)
    return lugar.P[i] if i is not None else None

def pais_nombre(nombre):
    i = lugar.N.get(lugar.nz(nombre))
    return lugar.P[i] if i is not None and lugar.P[i][3] == 'p' else None

def wikidata(consulta):
    q = urllib.request.Request('https://query.wikidata.org/sparql?' + urllib.parse.urlencode({'query': consulta}), headers={'User-Agent': UA['User-Agent'], 'Accept': 'text/csv'})
    with urllib.request.urlopen(q, timeout=90) as resp: t = resp.read().decode('utf-8', 'replace')
    out = []; vistos = set()
    for r in csv.DictReader(io.StringIO(t)):
        m = re.match(r'Point\(([-\d.]+) ([-\d.]+)\)', r.get('c') or '')
        if not m or r['i'] in vistos or re.fullmatch(r'Q\d+', r.get('iLabel') or ''): continue
        vistos.add(r['i']); out.append([round(float(m.group(1)), 2), round(float(m.group(2)), 2), r['iLabel'][:80], (r.get('pLabel') or '')[:40], r['i'].rsplit('/', 1)[-1]])
    return out
WD = 'SELECT ?i ?iLabel ?c ?pLabel WHERE { %s ?i wdt:P625 ?c. OPTIONAL{?i wdt:P17 ?p} SERVICE wikibase:label { bd:serviceParam wikibase:language "es,en". } }'

def bases():
    """Bases aéreas y navales militares con coordenadas en Wikidata (CC0)."""
    d = wikidata(WD % 'VALUES ?t { wd:Q695850 wd:Q1324633 } ?i wdt:P31 ?t.')
    return {'fuente': 'Wikidata', 'licencia': 'CC0 (dominio público)', 'enlace': 'https://www.wikidata.org/', 'datos': d}

def puertos():
    """Puertos espaciales con coordenadas en Wikidata (CC0)."""
    d = wikidata(WD % '?i wdt:P31/wdt:P279* wd:Q194188.')
    return {'fuente': 'Wikidata', 'licencia': 'CC0 (dominio público)', 'enlace': 'https://www.wikidata.org/', 'datos': d}

EEUU = {'AL': 'Alabama', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California', 'CO': 'Colorado', 'GA': 'Georgia, United States', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'MD': 'Maryland',
        'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri', 'NE': 'Nebraska', 'NV': 'Nevada', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma',
        'OR': 'Oregon', 'PA': 'Pennsylvania', 'SC': 'South Carolina', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VA': 'Virginia', 'WA': 'Washington State', 'WI': 'Wisconsin', 'WY': 'Wyoming'}

def centros_ia():
    """Centros de datos de IA de Epoch AI (CC BY). El archivo da la dirección, no las coordenadas: se ubican en su ciudad o estado."""
    t = pedir('https://epoch.ai/data/data_centers/data_centers.csv', 60).decode('utf-8-sig', 'replace'); out = []
    limpio = lambda x: re.sub(r'\s*#\w+', '', x or '').strip()
    for r in csv.DictReader(io.StringIO(t)):
        dire = r.get('Address') or ''; m = re.search(r',\s*([A-Z]{2})\s+\d{5}', dire)
        g = lugar.ubicar(dire)
        if (not g or g[2] in ('Estados Unidos',)) and m and m.group(1) in EEUU: g = lugar.ubicar(EEUU[m.group(1)]) or g
        g = g or lugar.ubicar(r.get('Country') or '')
        if not g: continue
        try: mw = round(float(r.get('Current power (MW)') or 0))
        except Exception: mw = 0
        out.append([g[0], g[1], r['Name'][:60], limpio(r.get('Owner'))[:60], limpio(r.get('Users'))[:90], mw, g[2]])
    return {'fuente': 'Epoch AI · AI data centers', 'licencia': 'CC BY', 'enlace': 'https://epoch.ai/data/data-centers', 'datos': out}

def desplazados():
    """ACNUR: personas refugiadas, solicitantes de asilo y desplazadas internas por país de origen (cifras anuales)."""
    out = []; año = AHORA.year
    for y in (año, año - 1):
        d = json.loads(pedir('https://api.unhcr.org/population/v1/population/?limit=400&year=%d&coo_all=true' % y, 60)).get('items', [])
        n = lambda v: int(v) if str(v).lstrip('-').isdigit() else 0
        for x in d:
            p = pais_iso3(x.get('coo_iso') or ''); tot = n(x.get('refugees')) + n(x.get('asylum_seekers')) + n(x.get('idps'))
            if p and tot >= 10000: out.append([p[0], p[1], p[2], n(x.get('refugees')), n(x.get('asylum_seekers')), n(x.get('idps')), y])
        if out: break
    return {'fuente': 'UNHCR Refugee Population Statistics Database', 'licencia': 'CC BY 4.0', 'enlace': 'https://www.unhcr.org/refugee-statistics/', 'datos': out}

def economia():
    """Banco Mundial: producto interior bruto por país (dólares corrientes), último año con dato. Las 60 mayores economías."""
    out = {}
    for y in (AHORA.year - 1, AHORA.year - 2):
        d = json.loads(pedir('https://api.worldbank.org/v2/country/all/indicator/NY.GDP.MKTP.CD?format=json&date=%d&per_page=400' % y, 60))
        for x in (d[1] or []) if len(d) > 1 else []:
            p = pais_iso3(x.get('countryiso3code') or '')
            if p and x.get('value') and p[2] not in out: out[p[2]] = [p[0], p[1], p[2], round(x['value'] / 1e9), y]
        if len(out) > 100: break
    return {'fuente': 'Banco Mundial · indicador NY.GDP.MKTP.CD', 'licencia': 'CC BY 4.0', 'enlace': 'https://data.worldbank.org/indicator/NY.GDP.MKTP.CD', 'datos': sorted(out.values(), key=lambda a: -a[3])[:60]}

def sanciones():
    """OFAC (Tesoro de EE. UU., dominio público): personas y entidades de la lista SDN, contadas por el país de su dirección."""
    t = pedir('https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/ADD.CSV', 120).decode('utf-8', 'replace'); C = {}
    for r in csv.reader(io.StringIO(t)):
        if len(r) > 4 and r[4].strip() not in ('', '-0-'): C.setdefault(r[4].strip(), set()).add(r[0])
    out = []
    for nom, S_ in C.items():
        p = pais_nombre(nom)
        if p and len(S_) >= 5: out.append([p[0], p[1], p[2], len(S_)])
    return {'fuente': 'OFAC · lista SDN (Tesoro de EE. UU.)', 'licencia': 'Dominio público', 'enlace': 'https://sanctionssearch.ofac.treas.gov/', 'datos': sorted(out, key=lambda a: -a[3])}

def ciber():
    """CISA (EE. UU., dominio público): las 25 vulnerabilidades añadidas más recientemente al catálogo de las que se explotan de verdad (KEV). No tiene lugar: va en un panel."""
    d = json.loads(pedir('https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json', 90))
    V = sorted(d.get('vulnerabilities', []), key=lambda v: v.get('dateAdded', ''), reverse=True)[:25]
    return {'fuente': 'CISA · catálogo KEV', 'licencia': 'Dominio público', 'enlace': 'https://www.cisa.gov/known-exploited-vulnerabilities-catalog', 'total': d.get('count'),
            'datos': [[v['cveID'], (v.get('vendorProject') or '')[:40], (v.get('product') or '')[:60], (v.get('vulnerabilityName') or '')[:140], v.get('dateAdded'), v.get('knownRansomwareCampaignUse') == 'Known'] for v in V]}

FIJAS = ('bases', 'puertos', 'centros_ia', 'desplazados', 'economia', 'sanciones')   # cambian poco: si la fuente falla, se conserva lo último

def main():
    ruta = os.path.join(PUB, 'datos', 'capas.json')
    try: ant = json.load(open(ruta, encoding='utf-8'))
    except Exception: ant = {}
    sal = {'generado': ISO(AHORA)}
    for nombre, fn in (('incendios', incendios), ('meteo', meteo), ('radiacion', radiacion), ('bases', bases), ('puertos', puertos), ('centros_ia', centros_ia), ('desplazados', desplazados), ('economia', economia), ('sanciones', sanciones), ('ciber', ciber)):
        try:
            c = fn()
            if not c['datos']: raise RuntimeError('sin datos')
            c['actualizado'] = ISO(AHORA); sal[nombre] = c; print(nombre, len(c['datos']))
        except Exception as e:
            print('AVISO', nombre, type(e).__name__, str(e)[:80])
            if nombre in ant and (nombre in FIJAS or (AHORA - dt.datetime.fromisoformat(ant[nombre]['actualizado'].replace('Z', '+00:00'))).total_seconds() < 86400): sal[nombre] = ant[nombre]   # se conserva lo último, un día como mucho
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    json.dump(sal, open(ruta, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))

if __name__ == '__main__':
    main()
