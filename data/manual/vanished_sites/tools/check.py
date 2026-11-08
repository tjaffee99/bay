"""python check.py NPY CX CY HALF RES SITE_ID out.png [year]"""
import sys, json, numpy as np
sys.path.insert(0,'.')
import vt
from PIL import Image, ImageDraw
from shapely.geometry import shape
a=sys.argv
img=np.load(a[1]); CX,CY,H,RES=map(float,a[2:6]); sid=a[6]; out=a[7]; yr=float(a[8]) if len(a)>8 else None
im=Image.fromarray(img).convert('RGB'); d=ImageDraw.Draw(im)
Pp=lambda x,y:((x+H)/RES,(H-y)/RES)
COL={'dirt_track':(200,120,40),'turf':(0,200,0),'grass':(120,255,120),'park':(0,160,0),'parking':(0,200,255),'water':(0,0,255),'industrial':(255,0,255),'urban':(255,128,0)}
base='..' if 'tools' in a[0] else '.'
for fn,col in [('sites.geojson',None),('buildings.geojson',(255,0,0))]:
    for f in json.load(open(fn))['features']:
        p=f['properties']
        if p['site_id']!=sid: continue
        y0=p.get('year_start',p.get('start_year')); y1=p.get('year_end',p.get('end_year'))
        if yr is not None and not (y0<=yr<y1): continue
        g=shape(f['geometry'])
        c=col or COL.get(p['cover'],(255,255,0))
        for pp in getattr(g,'geoms',[g]):
            for r in [pp.exterior,*pp.interiors]:
                x,y=vt.ll2loc(*np.asarray(r.coords).T,CX,CY)
                d.line([Pp(u,v) for u,v in zip(x,y)],fill=c,width=2)
im.save(out); print(out)
