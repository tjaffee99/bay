"""python crop.py NPY CX CY HALF RES x0 x1 y0 y1 out.png [grid] [overlay.json]"""
import sys, json, numpy as np
from PIL import Image, ImageDraw
a=sys.argv
img=np.load(a[1]); H=float(a[4]); res=float(a[5])
x0,x1,y0,y1=map(float,a[6:10]); out=a[10]; grid=float(a[11]) if len(a)>11 else 10
i0=int((x0+H)/res); i1=int((x1+H)/res); j0=int((H-y1)/res); j1=int((H-y0)/res)
im=Image.fromarray(img[j0:j1,i0:i1].copy()); d=ImageDraw.Draw(im)
P=lambda x,y:((x+H)/res-i0,(H-y)/res-j0)
g=grid
for v in np.arange(np.floor(min(x0,y0)/g)*g, max(x1,y1)+g, g):
    major = abs(v/50-round(v/50))<1e-6
    c=(255,255,0) if major else (0,140,255)
    if x0<=v<=x1: d.line([P(v,y0),P(v,y1)],fill=c,width=1)
    if y0<=v<=y1: d.line([P(x0,v),P(x1,v)],fill=c,width=1)
    if major:
        if x0<=v<=x1: d.text((P(v,y1)[0]+2,2),str(int(v)),fill=(255,255,0))
        if y0<=v<=y1: d.text((2,P(x0,v)[1]+2),str(int(v)),fill=(255,255,0))
if len(a)>12:
    for f in json.load(open(a[12])):
        d.line([P(*p) for p in f['coords']],fill=(255,0,0),width=2)
        cx=np.mean([p[0] for p in f['coords']]); cy=np.mean([p[1] for p in f['coords']])
        d.text(P(cx,cy),str(f['id']),fill=(255,80,80))
im.save(out); print(out, im.size)
