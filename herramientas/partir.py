"""Parte titulares.json para que cada versión del sitio descargue solo su idioma (usuario, 22/11/2026: aligerar el sitio).

Saca de cada titular las traducciones «e» (español) y «n» (inglés) y las guarda, en el mismo orden, en
datos/titulares-es.json y datos/titulares-en.json: {"generado": ..., "e": [...]} y {"generado": ..., "n": [...]}.
El sitio las vuelve a unir solo si «generado» coincide. Si este paso falla, titulares.json queda entero y el sitio sigue funcionando.
Uso: python3 herramientas/partir.py .
"""
import json, os, sys

PUB = sys.argv[1] if len(sys.argv) > 1 else '.'
D = os.path.join(PUB, 'datos')
ruta = os.path.join(D, 'titulares.json')
t = json.load(open(ruta, encoding='utf-8'))
T = t['titulares']
for k, nom in (('e', 'titulares-es.json'), ('n', 'titulares-en.json')):
    if not any(k in a for a in T):
        print(nom, 'sin cambios (titulares.json ya estaba partido o sin traducciones)'); continue
    L = [a.pop(k, None) for a in T]
    while L and L[-1] is None: L.pop()
    json.dump({'generado': t['generado'], k: L}, open(os.path.join(D, nom), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(nom, sum(1 for x in L if x), 'traducciones')
json.dump(t, open(ruta, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
