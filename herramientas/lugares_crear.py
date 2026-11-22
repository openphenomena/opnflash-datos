# -*- coding: utf-8 -*-
"""Crea herramientas/lugares.json a partir de Natural Earth (dominio público): países, estados y ciudades,
con sus nombres en varios idiomas, para ubicar titulares. Uso: python3 lugares_crear.py carpeta_con_geojson salida.json
Archivos: ne_50m_admin_0_countries, ne_10m_admin_1_states_provinces, ne_10m_populated_places (.geojson)."""
import json, sys, re, unicodedata, os, random
D, OUT = sys.argv[1], sys.argv[2]
def nz(s): return re.sub(r'\s+', ' ', re.sub(r"[^\w ]", ' ', ''.join(c for c in unicodedata.normalize('NFD', (s or '').lower()) if unicodedata.category(c) != 'Mn'))).strip()
LAT = ['ES', 'EN', 'PT', 'FR', 'DE', 'IT', 'NL', 'SV', 'PL', 'HU', 'TR', 'ID', 'VI', 'RU', 'UK', 'EL']
SIN = ['AR', 'FA', 'HE', 'UR', 'HI', 'BN', 'KO']      # sin mayúsculas, con espacios
CJK = ['ZH', 'JA', 'ZHT']                              # sin espacios
STOP = set(nz(x) for x in """Mobile|Nice|Reading|Bath|Orange|Normal|Union|Enterprise|Surprise|Independence|Liberal|Hope|Split|Bar|Male|Man|Of|Van|Batman|Sale|Hull|Bury|Deal|Mary|Mission|Columbia|Lincoln|Jackson|Victoria|Regina|George|Santiago|Rosario|Mercedes|Florencia|Carmen|Trinidad|Concepción|Pilar|Dolores|Soledad|Ángeles|León|Leon|Colón|Salto|David|Santa Ana|San Juan|San José|San Pedro|San Luis|San Fernando|San Miguel|San Carlos|Santa Cruz|Santa Fe|Santa María|Santa Rosa|La Paz|Charlotte|Austin|Madison|Jordan|Douglas|Hamilton|Nelson|Sofia|Florence|Phoenix|Columbus|Orlando|Savannah|Eugene|Marion|Troy|Kent|Lancaster|Goya|Morón|Mar|Bello|Sucre|Miranda|Bolívar|Guzmán|Hidalgo|Juárez|Lara|Santander|Nariño|Morelos|Guerrero|Colima|Amazonas|Washington|Distrito Federal|Central|Norte|Sur|Oriental|Occidental|Centro|Sud|Nord|West|East|North|South|Western|Eastern|Northern|Southern|Capital|Federal|Granada|Toledo|Trujillo|Linares|Mendoza|Luján|Belén|Jesús María|Libertad|Progreso|Esperanza|Unión|Paraíso|Reforma|Carolina|Bismarck|Lourdes|Guadalupe|Nancy|Marshall|Carson|Paterson|Jefferson|Franklin|Clinton|Monroe|Tyler|Chandler|Gilbert|Irving|Garland|Lewis|Henderson|Warren|Sterling|Roseville|Vista|Tempe|Mesa|Aurora|Concord|Hayward|Corona|Elizabeth|Ica|Ife|Ho|Po|Bo|Ed|Am|Ba|Zug|Most|Usa|Tula|Tena|Mao|Puno|Pau|Buy|Ur|Same|Along|Many|Hit|Hot|Sin|Best|Nome|Real|Media|Santos|Flores|Rivera|Salinas|Reyes|Cruz|Rojas|Vargas|Medina|Rio Branco|Vitória|Natal|Salvador|Palmas|São Luís|Imperatriz|Cascavel|Marília|Pasto|Neiva|Armenia|Pereira|Palmira|Valera|Coro|Guanare|San Cristóbal|San Felipe|Durango|Celaya|Morelia|Reynosa|Matamoros|Obregón|Madero|Zamora|Uruapan|Tepic|Campeche|Chetumal|Tampico|Georgia|Chad|Guinea|Niger|Mali|Togo|Turkey|Macedonia|Dominica|Jersey|Man|Polish|China Grove|Asia|Africa|Europa|Europe|America|Oceania|Summit|Enterprise|Opportunity|Success|Experiment|Bend|Fairfield|Springfield|Richmond|Newport|Kingston|Georgetown|Alexandria|Tripoli|Hyderabad|Santa Clara|San Marcos|Rey|Reina|Papa|Sol|Luna|Alba|Esteban|Federación|Presidente|General|Coronel|Doctor|Lima|Bolivar|Para|Pará|Ceará|Acre|Ilha|Rio|Río|Mérida|Córdoba|Cordoba|Merida|Victoria de Durango|Bristol|Lincoln|Preston|Derby|Worth|Buffalo|Eureka|Tacoma|Olympia|Helena|Pierre|Augusta|Dover|Salem|Hartford|Montgomery|Jackson|Cheyenne|Lansing|Tyler|Abilene|Odessa|Midland|Victoria|Laredo|Killeen|Sandy|Provo|Boulder|Greeley|Pueblo|Reno|Paradise|Sparks|Chico|Davis|Bakersfield""".split('|'))
OKADM = {'US', 'CA', 'MX', 'BR', 'AR', 'CO', 'VE', 'CL', 'ES', 'DE', 'FR', 'IT', 'GB', 'AU', 'IN', 'RU', 'UA', 'CN', 'EC', 'BO', 'PY', 'UY'}
P, N, S, C, CAP, PTS, AMB = [], {}, {}, {}, {}, {}, {}
def dentro(x, y, anillo):
    d = False; n = len(anillo); j = n - 1
    for i in range(n):
        xi, yi = anillo[i][:2]; xj, yj = anillo[j][:2]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi: d = not d
        j = i
    return d
def repartidos(geom, n, semilla):
    """n puntos al azar (siempre los mismos) dentro del polígono mayor: para repartir por el país o el estado los titulares que solo lo nombran."""
    if not geom: return []
    pols = [geom['coordinates']] if geom['type'] == 'Polygon' else geom['coordinates']
    def area(a): return abs(sum(a[i][0] * a[i - 1][1] - a[i - 1][0] * a[i][1] for i in range(len(a)))) / 2
    pol = max(pols, key=lambda q: area(q[0])); ext = pol[0]
    xs = [c[0] for c in ext]; ys = [c[1] for c in ext]; rnd = random.Random(semilla); out = []; k = 0
    while len(out) < n and k < n * 60:
        k += 1; x = rnd.uniform(min(xs), max(xs)); y = rnd.uniform(min(ys), max(ys))
        if dentro(x, y, ext) and not any(dentro(x, y, h) for h in pol[1:]): out.append([round(x, 2), round(y, 2)])
    return out
def nuevo(lon, lat, nom, k, a3, pop): P.append([round(lon, 2), round(lat, 2), nom, k, a3, int(pop)]); return len(P) - 1
def pon(T, k, i):
    if len(k) < 3 and T is not C: return
    if k in STOP and P[i][3] != 'p' and T is N: return
    if T is N and k in T and T[k] != i and P[T[k]][3] != 'p' and P[i][3] != 'p' and P[T[k]][4] != P[i][4]:
        L = AMB.setdefault(k, [T[k]])   # mismo nombre en países distintos (Valencia, Córdoba, Mérida…): se guardan todos
        if i not in L: L.append(i)
    if k in T and T[k] != i:
        a, b = P[T[k]], P[i]; orden = {'p': 3, 'c': 2, 'e': 1}
        if (orden[a[3]], a[5]) >= (orden[b[3]], b[5]) and not (a[3] == 'p' and False): return
    T[k] = i
def nombres(p, i, mayus=str.upper):
    g = lambda c: p.get('NAME_' + c) or p.get('name_' + c.lower())
    for c in (LAT if P[i][3] == 'p' else LAT[:6]):   # ciudades y estados: solo en seis idiomas, para no confundir palabras
        if g(c): pon(N, nz(g(c)), i)
    for c in SIN:
        if g(c): pon(S, nz(g(c)), i)
    for c in CJK:
        if g(c) and len(g(c)) >= 2: pon(C, g(c), i)
for f in json.load(open(os.path.join(D, 'adm0.geojson'), encoding='utf-8'))['features']:
    p = f['properties']
    i = nuevo(p['LABEL_X'], p['LABEL_Y'], p.get('NAME_ES') or p['NAME'], 'p', p['ADM0_A3'], p.get('POP_EST') or 0)
    nombres(p, i); pon(N, nz(p['NAME']), i); pon(N, nz(p.get('NAME_LONG')), i)
    PTS[i] = repartidos(f.get('geometry'), 48, p['ADM0_A3'])
A3 = {P[i][4]: i for i in range(len(P))}
ciudades = json.load(open(os.path.join(D, 'ne_10m_populated_places.geojson'), encoding='utf-8'))['features']
porNombre = {}
for f in sorted(ciudades, key=lambda f: -(f['properties']['POP_MAX'] or 0)):
    p = f['properties']; cap = p['FEATURECLA'].startswith('Admin-0 capital'); pop = p['POP_MAX'] or 0
    porNombre.setdefault(nz(p['NAME']), f)
    if pop < 50000 and not cap: continue
    lon, lat = f['geometry']['coordinates']
    i = nuevo(lon, lat, p.get('NAME_ES') or p['NAME'], 'c', p['ADM0_A3'], pop + (5_000_000 if cap else 0))
    if cap and p['ADM0_A3'] not in CAP: CAP[p['ADM0_A3']] = i
    nombres(p, i); pon(N, nz(p['NAME']), i); pon(N, nz(p.get('NAMEASCII')), i)
for f in json.load(open(os.path.join(D, 'ne_10m_admin_1_states_provinces.geojson'), encoding='utf-8'))['features']:
    p = f['properties']
    if p.get('iso_a2') not in OKADM or p.get('latitude') is None: continue
    i = nuevo(p['longitude'], p['latitude'], p.get('name_es') or p['name'], 'e', p['adm0_a3'], 1000)
    for c in ('name_es', 'name', 'name_en', 'name_pt'):
        if p.get(c): pon(N, nz(p[c]), i)
    PTS[i] = repartidos(f.get('geometry'), 14, p.get('name') or '')
# Alias: lugares que la prensa nombra de otra forma
ALIAS = {'D.C.': 'Washington, D.C.', 'Washington D.C.': 'Washington, D.C.', 'Washington DC': 'Washington, D.C.', 'Washington': 'Washington, D.C.', 'Casa Blanca': 'Washington, D.C.', 'White House': 'Washington, D.C.',
         'Pentágono': 'Washington, D.C.', 'Pentagon': 'Washington, D.C.', 'Capitolio': 'Washington, D.C.', 'Capitol Hill': 'Washington, D.C.', 'Kremlin': 'Moscow', 'Wall Street': 'New York', 'Manhattan': 'New York',
         'Brooklyn': 'New York', 'Hollywood': 'Los Angeles', 'Downing Street': 'London', 'Westminster': 'London', 'Elíseo': 'Paris', 'Miraflores': 'Caracas', 'Casa Rosada': 'Buenos Aires', 'Planalto': 'Brasília',
         'CDMX': 'Mexico City', 'Zócalo': 'Mexico City', 'Kiev': 'Kyiv', 'Bogotá': 'Bogota', 'Lima': 'Lima', 'Córdoba': 'Córdoba', 'Mérida': 'Mérida', 'La Paz': 'La Paz', 'Santiago de Chile': 'Santiago', 'Rio': 'Rio de Janeiro', 'Río de Janeiro': 'Rio de Janeiro'}
for a, t in ALIAS.items():
    f = porNombre.get(nz(t))
    if not f: print('alias sin ciudad:', a, t); continue
    p = f['properties']; lon, lat = f['geometry']['coordinates']
    N[nz(a)] = nuevo(lon, lat, p.get('NAME_ES') or p['NAME'], 'c', p['ADM0_A3'], 9_000_000)
OTROS = [('Princeton', -74.66, 40.35, 'Princeton', 'USA'), ('Harvard', -71.12, 42.37, 'Cambridge (Massachusetts)', 'USA'), ('Stanford', -122.17, 37.43, 'Stanford', 'USA'), ('Silicon Valley', -122.04, 37.37, 'Silicon Valley', 'USA'),
         ('Yale', -72.92, 41.31, 'New Haven', 'USA'), ('Oxford', -1.26, 51.75, 'Oxford', 'GBR'), ('Davos', 9.84, 46.8, 'Davos', 'CHE'), ('Gaza', 34.45, 31.5, 'Gaza', 'PSX'), ('Franja de Gaza', 34.4, 31.45, 'Franja de Gaza', 'PSX'),
         ('Cisjordania', 35.25, 32.0, 'Cisjordania', 'PSX'), ('West Bank', 35.25, 32.0, 'Cisjordania', 'PSX'), ('Crimea', 34.1, 45.0, 'Crimea', 'UKR'), ('Donbás', 38.0, 48.3, 'Donbás', 'UKR'), ('Donbass', 38.0, 48.3, 'Donbás', 'UKR'),
         ('Mar-a-Lago', -80.04, 26.68, 'Palm Beach', 'USA'), ('Guantánamo', -75.2, 20.14, 'Guantánamo', 'CUB'), ('Esequibo', -59.0, 5.0, 'Esequibo', 'GUY'), ('Darién', -77.5, 8.0, 'Darién', 'PAN'),
         ('Ormuz', 56.4, 26.6, 'Estrecho de Ormuz', 'IRN'), ('Hormuz', 56.4, 26.6, 'Estrecho de Ormuz', 'IRN'), ('Zaporiyia', 35.14, 47.84, 'Zaporiyia', 'UKR'), ('Zaporizhzhia', 35.14, 47.84, 'Zaporiyia', 'UKR'),
         ('Jersón', 32.6, 46.64, 'Jersón', 'UKR'), ('Rafah', 34.25, 31.29, 'Rafah', 'PSX'), ('Cachemira', 75.0, 34.0, 'Cachemira', 'IND'), ('Kashmir', 75.0, 34.0, 'Cachemira', 'IND'), ('Tíbet', 91.1, 29.65, 'Tíbet', 'CHN'),
         ('Patagonia', -69.0, -45.0, 'Patagonia', 'ARG'), ('Amazonía', -62.0, -4.0, 'Amazonía', 'BRA'), ('Amazônia', -62.0, -4.0, 'Amazonía', 'BRA'), ('Canal de Panamá', -79.7, 9.1, 'Canal de Panamá', 'PAN'),
         ('Panama Canal', -79.7, 9.1, 'Canal de Panamá', 'PAN'), ('Taiwán', 121.0, 23.7, 'Taiwán', 'TWN'), ('Hong Kong', 114.17, 22.3, 'Hong Kong', 'HKG'), ('Tierra del Fuego', -68.3, -54.3, 'Tierra del Fuego', 'ARG'),
         ('Catatumbo', -72.8, 8.6, 'Catatumbo', 'COL'), ('Essequibo', -59.0, 5.0, 'Esequibo', 'GUY'), ('Malvinas', -59.0, -51.75, 'Islas Malvinas', 'FLK'), ('Vaca Muerta', -69.2, -38.2, 'Vaca Muerta', 'ARG')]
for nom, lon, lat, lab, a3 in OTROS: N[nz(nom)] = nuevo(lon, lat, lab, 'c', a3, 8_000_000)
# Gentilicios (español, inglés y portugués) de los países que más salen
GENT = {'VEN': 'venezolano venezolana venezolanos venezolanas venezuelan venezuelans', 'ARG': 'argentino argentina argentinos argentinas argentine argentinian', 'COL': 'colombiano colombiana colombianos colombianas colombian colombians',
        'MEX': 'mexicano mexicana mexicanos mexicanas mexican mexicans', 'CHL': 'chileno chilena chilenos chilenas chilean', 'PER': 'peruano peruana peruanos peruanas peruvian', 'BRA': 'brasileño brasileña brasileños brasileñas brazilian brazilians brasileiro brasileira brasileiros',
        'CUB': 'cubano cubana cubanos cubanas cuban cubans', 'USA': 'estadounidense estadounidenses', 'RUS': 'ruso rusa rusos rusas russian russians', 'UKR': 'ucraniano ucraniana ucranianos ucranianas ukrainian ukrainians',
        'ISR': 'israelí israelíes israeli israelis', 'IRN': 'iraní iraníes iranian iranians', 'CHN': 'chino china chinos chinas chinese', 'ESP': 'español española españoles españolas spanish', 'FRA': 'francés francesa franceses french',
        'DEU': 'alemán alemana alemanes german germans', 'GBR': 'británico británica británicos british', 'ECU': 'ecuatoriano ecuatoriana ecuatorianos ecuadorian', 'BOL': 'boliviano boliviana bolivianos bolivian', 'URY': 'uruguayo uruguaya uruguayos uruguayan',
        'PRY': 'paraguayo paraguaya paraguayos paraguayan', 'NIC': 'nicaragüense nicaragüenses nicaraguan', 'CAN': 'canadiense canadienses canadian canadians', 'IND': 'indio india indios indian', 'JPN': 'japonés japonesa japoneses japanese',
        'TUR': 'turco turca turcos turkish', 'PSX': 'palestino palestina palestinos palestinas palestinian palestinians', 'SYR': 'sirio siria sirios syrian', 'LBN': 'libanés libanesa libaneses lebanese', 'HTI': 'haitiano haitiana haitianos haitian haitians'}
G = {}
for a3, s in GENT.items():
    for w in s.split():
        if a3 in A3 and nz(w) not in N: G[nz(w)] = A3[a3]
json.dump({'p': P, 'n': N, 's': S, 'c': C, 'g': G, 'cap': CAP, 'amb': AMB, 'pts': {str(k): v for k, v in PTS.items() if v}}, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('lugares', len(P), 'nombres', len(N), len(S), len(C), 'gentilicios', len(G), 'bytes', os.path.getsize(OUT))
