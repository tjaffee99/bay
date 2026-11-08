import sys,json,numpy as np,cv2
sys.path.insert(0,'.')
import presence
from shapely.geometry import Polygon
from PIL import Image, ImageDraw
H,RES=1100,1.0
img=np.load('cache/oab1959.npy'); img46=np.load('cache/oab1946.npy')
m=np.load('cache/fisc_mask.npy')
d=json.load(open('traced/oakland_nsc_topo.json')); nsc=Polygon(d['nsc'])
# grid angle from the good warehouses of the previous pass (mod 90)
angs=[]
for o in d['warehouses1959']:
    e=np.array(o['coords']); v=e[1]-e[0]
    angs.append(np.degrees(np.arctan2(v[1],v[0]))%90)
angs=np.array(angs); a0=np.median(angs); print('grid angle (deg, mod 90)',round(a0,1), np.percentile(angs,[25,75]).round(1))
t=np.radians(a0); ux,uy=np.cos(t),np.sin(t); vx,vy=-uy,ux
def intervals(vals, L, frac, minw):
    lo,hi=np.floor(vals.min()),np.ceil(vals.max())
    bins=np.arange(lo,hi+2); h,_=np.histogram(vals,bins)
    occ=h>frac*L
    out=[];k=0
    while k<len(occ):
        if occ[k]:
            k0=k
            while k<len(occ) and occ[k]: k+=1
            if bins[k]-bins[k0]>=minw: out.append((bins[k0],bins[k]))
        k+=1
    return out
n,lab,st,_=cv2.connectedComponentsWithStats(m,8)
out=[]
for i in range(1,n):
    if st[i,cv2.CC_STAT_AREA]<600: continue
    ys,xs=np.nonzero(lab==i); X=-H+xs+.5; Y=H-ys-.5
    u=X*ux+Y*uy; v=X*vx+Y*vy
    for v0,v1 in intervals(v, u.max()-u.min(), 0.3, 12):
        s=(v>=v0)&(v<v1)
        for u0,u1 in intervals(u[s], v1-v0, 0.3, 12):
            s2=s&(u>=u0)&(u<u1)
            if s2.sum()<400: continue
            # trim to the pixel extent
            uu,vv=u[s2],v[s2]
            a,b_=np.percentile(uu,[1,99]); c,e=np.percentile(vv,[1,99])
            poly=[(a*ux+c*vx,a*uy+c*vy),(b_*ux+c*vx,b_*uy+c*vy),(b_*ux+e*vx,b_*uy+e*vy),(a*ux+e*vx,a*uy+e*vy)]
            P=Polygon(poly)
            dims=sorted([b_-a,e-c])
            fill=s2.sum()/max(P.area,1)
            if not nsc.contains(P.centroid) or P.area<900 or dims[0]<14 or dims[1]<35 or fill<0.6: continue
            out.append(dict(coords=[[round(x,1),round(y,1)] for x,y in poly],w=round(dims[0],1),l=round(dims[1],1),area=round(P.area),fill=round(fill,2),
                            ink1946=round(presence.ink_frac(img46,H,RES,poly,purple=False),2)))
im=Image.fromarray(img); dr=ImageDraw.Draw(im)
for o in out:
    dr.line([(x+H,H-y) for x,y in o['coords']+[o['coords'][0]]],fill=(255,0,0) if o['ink1946']>0.2 else (0,0,255),width=3)
im.resize((1100,1100)).save('out/fisc6.png')
d['warehouses1959']=out; d['grid_angle_deg']=round(float(a0),2); json.dump(d,open('traced/oakland_nsc_topo.json','w'))
print(len(out), sum(o['area'] for o in out))
