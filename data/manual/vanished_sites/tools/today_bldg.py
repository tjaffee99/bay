"""python today_bldg.py NPY CX CY HALF RES out.png : overlay today's Overture footprints (region5 + SF) on a render"""
import sys, numpy as np, duckdb, shapely.wkb
sys.path.insert(0,'.')
import vt
from PIL import Image, ImageDraw
a=sys.argv; img=np.load(a[1]); CX,CY,H,RES=map(float,a[2:6])
dl=H/vt.kfac(CY)*1.1; dd=H/110574*1.1
con=duckdb.connect(); con.execute('LOAD spatial')
rows=[]
for f in ['region5_building','building']:
    q=f"select id, ST_AsWKB(geometry) g from read_parquet('/home/user/bay/data/raw/overture/2026-10-21.0/{f}.parquet') where ST_XMin(geometry)<{CX+dl} and ST_XMax(geometry)>{CX-dl} and ST_YMin(geometry)<{CY+dd} and ST_YMax(geometry)>{CY-dd}"
    try: rows+=con.execute(q).fetchall()
    except Exception as e: print(e)
im=Image.fromarray(img); d=ImageDraw.Draw(im)
P=lambda x,y:((x+H)/RES,(H-y)/RES)
for _,g in rows:
    gg=shapely.wkb.loads(bytes(g))
    for p in getattr(gg,'geoms',[gg]):
        x,y=vt.ll2loc(*np.asarray(p.exterior.coords).T,CX,CY)
        d.line([P(u,v) for u,v in zip(x,y)],fill=(0,170,0),width=2)
for v in range(-int(H)//100*100,int(H)+1,100):
    d.line([P(v,-H),P(v,H)],fill=(0,160,255),width=1); d.line([P(-H,v),P(H,v)],fill=(0,160,255),width=1)
    d.text((P(v,H)[0]+2,2),str(v),fill=(0,0,200)); d.text((2,P(-H,v)[1]+2),str(v),fill=(0,0,200))
im.save(a[6]); print(len(rows),'buildings')
