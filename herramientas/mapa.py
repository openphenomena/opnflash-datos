# Genera public/mapa.svg (equirectangular 2000x1000, Natural Earth 50m, dominio público)
import json,sys
g=json.load(open(sys.argv[1]))
W,H=2000,1000
def P(lon,lat): return (lon+180)/360*W,(90-lat)/180*H
def ring(r):
    pts=[];last=None
    for lon,lat in r:
        x,y=P(lon,lat); q=(round(x,1),round(y,1))
        if last and abs(q[0]-last[0])+abs(q[1]-last[1])<0.9: continue
        pts.append(q);last=q
    if len(pts)<3: return ''
    return 'M'+'L'.join(f'{x:g},{y:g}' for x,y in pts)+'Z'
out=[]
for f in g['features']:
    geo=f['geometry'];polys=geo['coordinates'] if geo['type']=='MultiPolygon' else [geo['coordinates']]
    d=''.join(ring(r) for p in polys for r in p)
    if d: out.append(f'<path d="{d}"><title>{f["properties"].get("NAME_ES") or f["properties"]["NAME"]}</title></path>')
open('public/mapa.svg','w').write(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}"><g class="tierra">'+''.join(out)+'</g></svg>')
