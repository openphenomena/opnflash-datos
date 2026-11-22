# -*- coding: utf-8 -*-
"""Señales de vídeo en directo para opnflash.com.

Para cada canal aprobado mira su página pública de YouTube y anota el vídeo que está emitiendo ahora.
Así el sitio abre siempre la señal vigente y, si una no está en directo, pasa a otra
(en los pódcast y programas, a los últimos vídeos del canal).
Guarda public/datos/directos.json. No descarga ni copia vídeo: solo el identificador del directo.
Uso:  python3 directos.py [carpeta public]
"""
import json, os, re, sys, datetime as dt, urllib.request
from concurrent.futures import ThreadPoolExecutor

AQUI = os.path.dirname(os.path.abspath(__file__))
PUB = sys.argv[1] if len(sys.argv) > 1 else os.path.join(AQUI, '..', 'public')
H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36',
     'Accept-Language': 'es-ES,es;q=0.9', 'Cookie': 'SOCS=CAI; CONSENT=YES+1'}

# Lista aprobada por el usuario: referencia/medios/canales-youtube.json
CANALES = json.load(open(os.path.join(AQUI, '..', 'referencia', 'medios', 'canales-youtube.json'), encoding='utf-8'))['canales']

def mirar(cid):
    """Devuelve (vídeo en directo o None, se puede insertar). Un solo intento: si falla, se anota y se sigue."""
    try:
        with urllib.request.urlopen(urllib.request.Request('https://www.youtube.com/channel/%s/live' % cid, headers=H), timeout=20) as r:
            p = r.read().decode('utf-8', 'replace')
    except Exception as e:
        print('AVISO directo', cid, type(e).__name__)
        return 'error', False
    m = re.search(r'"videoDetails":\{"videoId":"([\w-]{11})"', p)
    vivo = '"isLive":true' in p or '"isLiveNow":true' in p
    return (m.group(1) if m and vivo else None), '"playableInEmbed":true' in p

def main():
    ruta = os.path.join(PUB, 'datos', 'directos.json')
    try:
        ant = json.load(open(ruta, encoding='utf-8'))
    except Exception:
        ant = {}
    antes = {c['id']: c for c in ant.get('canales', [])}
    with ThreadPoolExecutor(8) as ex:
        vistos = list(ex.map(lambda c: mirar(c['id']), CANALES))
    out = []
    for c, (v, ins) in zip(CANALES, vistos):
        if v == 'error':  # la página no respondió: se conserva lo último que se sabía
            a = antes.get(c['id'], {})
            v, ins = a.get('v'), a.get('ins', False)
        out.append({**c, 'v': v, 'ins': bool(v and ins)})
    print('canales', len(out), 'en directo', sum(1 for c in out if c['v']), 'insertables', sum(1 for c in out if c['ins']))
    # La fecha solo cambia si cambia alguna señal: así el archivo no se sube en cada ejecución.
    if ant.get('canales') == out:
        print('Sin cambios'); return
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    json.dump({'generado': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'canales': out},
              open(ruta, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))

if __name__ == '__main__':
    main()
