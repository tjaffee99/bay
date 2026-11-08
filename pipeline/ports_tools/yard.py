"""yard.py: container stacks from the Esri orthophoto (viewed only) in a terminal's wharf frame.
python yard.py <name> lonA latA lonB latB <osm polygon ids,comma> nmin out.json [--z 18]
Frame: s along A->B (m), n to the LEFT of A->B (inland). Cells: 40 ft container columns
(bay pitch 12.8 m along s, row pitch 2.8 m along n). A cell is a stack where >= 45 % of its
pixels look like painted container steel (saturated colour or bright white), not grey paving."""
import sys, os, math, json, argparse
BASE=os.environ.get('PORTS_CACHE', os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','..','data','raw','ports'))
import numpy as np, requests
from PIL import Image
from shapely.geometry import Polygon, Point
from shapely import contains_xy
ap=argparse.ArgumentParser()
ap.add_argument('name'); 
for k in ('la','pa','lb','pb'): ap.add_argument(k,type=float)
ap.add_argument('polys'); ap.add_argument('nmin',type=float); ap.add_argument('out')
ap.add_argument('--z',type=int,default=18); ap.add_argument('--res',type=float,default=0.4)
ap.add_argument('--debug'); ap.add_argument('--osm',default=os.path.join(BASE,'oak_port_w.osm'))
a=ap.parse_args()
TILES=os.path.join(BASE,'tiles'); os.makedirs(TILES,exist_ok=True)
P=json.load(open(os.path.join(BASE,'port_polys.json')))
polys=[v for k,v in P.items() if k.split(':')[0] in a.polys.split(',')]
lat0=a.pa; k=111320*math.cos(math.radians(lat0))
B=((a.lb-a.la)*k,(a.pb-a.pa)*110574); L=math.hypot(*B); u=np.array([B[0]/L,B[1]/L]); nv=np.array([-u[1],u[0]])
def to_sn(lon,lat):
    x=(lon-a.la)*k; y=(lat-a.pa)*110574; return x*u[0]+y*u[1], x*nv[0]+y*nv[1]
sn_polys=[Polygon([to_sn(*p) for p in poly]) for poly in polys]
from shapely.ops import unary_union
area=unary_union(sn_polys).buffer(0)
s0,n0,s1,n1=area.bounds; n0=max(n0,a.nmin)
W=int((s1-s0)/a.res)+1; H=int((n1-n0)/a.res)+1
ss=s0+np.arange(W)*a.res; nn=n0+np.arange(H)*a.res
S,N=np.meshgrid(ss,nn)
X=S*u[0]+N*nv[0]; Y=S*u[1]+N*nv[1]
lon=a.la+X/k; lat=a.pa+Y/110574
z=a.z; n=256*2**z; px=(lon+180)/360*n; sn=np.sin(np.radians(lat)); py=(0.5-np.log((1+sn)/(1-sn))/(4*np.pi))*n
tx0,tx1=int(px.min()//256),int(px.max()//256); ty0,ty1=int(py.min()//256),int(py.max()//256)
mos=np.zeros(((ty1-ty0+1)*256,(tx1-tx0+1)*256,3),np.uint8)
Sx=requests.Session(); Sx.headers['User-Agent']='BayAreaThroughTime research'
for tx in range(tx0,tx1+1):
    for ty in range(ty0,ty1+1):
        fn=f'{TILES}/{z}_{tx}_{ty}.jpg'
        if not os.path.exists(fn):
            r=Sx.get(f'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{ty}/{tx}',timeout=30); open(fn,'wb').write(r.content)
        try: t=np.array(Image.open(fn).convert('RGB'))
        except Exception: continue
        mos[(ty-ty0)*256:(ty-ty0+1)*256,(tx-tx0)*256:(tx-tx0+1)*256]=t
ix=np.clip((px-tx0*256).astype(int),0,mos.shape[1]-1); iy=np.clip((py-ty0*256).astype(int),0,mos.shape[0]-1)
img=mos[iy,ix].astype(np.float32)  # H x W x 3, row 0 = n0
mx=img.max(2); mn=img.min(2); sat=(mx-mn)/np.maximum(mx,1)
inside=contains_xy(area,S,N)
cont=((sat>0.28)&(mx>70)) | (mn>205)
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from osmparse import load as osmload
_nodes,_nt,_ways,_r=osmload(a.osm)
bl=[]
for _i,(_nds,_tg) in _ways.items():
    if 'building' in _tg and len(_nds)>3:
        try: bl.append(Polygon([to_sn(*_nodes[q]) for q in _nds]).buffer(2.0))
        except Exception: pass
bld=unary_union([g for g in bl if g.is_valid and g.intersects(area)]) if bl else None
if bld is not None and not bld.is_empty: inside&=~contains_xy(bld,S,N)
cont&=inside
# integral image
I=np.zeros((H+1,W+1)); I[1:,1:]=np.cumsum(np.cumsum(cont,0),1)
Iin=np.zeros((H+1,W+1)); Iin[1:,1:]=np.cumsum(np.cumsum(inside,0),1)
IR=[np.zeros((H+1,W+1)) for _ in range(3)]
for c in range(3): IR[c][1:,1:]=np.cumsum(np.cumsum(img[:,:,c]*cont,0),1)
def boxsum(I,r0,c0,r1,c1): return I[r1,c1]-I[r0,c1]-I[r1,c0]+I[r0,c0]
PB,PR=12.8,2.8; CL,CW=12.19,2.44
cells={}
# phase per 120 x 60 m tile
TS,TN=64.0,32.0
for ts in np.arange(s0,s1,TS):
    for tn in np.arange(n0,n1,TN):
        best=None
        for (PB,PR,CL,CW) in ((12.8,2.8,12.19,2.44),(2.8,12.8,2.44,12.19)):
          for ps in np.arange(0,PB,PB/8):
            for pn in np.arange(0,PR,PR/4):
                res=[]
                i0=int(math.floor((ts-ps-s0)/PB)); 
                for bi in range(int(TS/PB)+2):
                    cs=s0+ps+(i0+bi)*PB
                    if cs<ts or cs>=ts+TS: continue
                    for ri in range(int(TN/PR)+1):
                        cn=tn+pn+ri*PR
                        if cn>=tn+TN or cn+CW>n1: continue
                        c0=int((cs-s0)/a.res); c1=int((cs+CL-s0)/a.res); r0=int((cn-n0)/a.res); r1=int((cn+CW-n0)/a.res)
                        if c0<0 or r0<0 or c1>W or r1>H: continue
                        tot=(c1-c0)*(r1-r0); fin=boxsum(Iin,r0,c0,r1,c1)/tot
                        if fin<0.9: continue
                        f=boxsum(I,r0,c0,r1,c1)/tot
                        res.append((cs,cn,f,r0,c0,r1,c1,CL>CW))
                if not res: continue
                score=sum(max(f-0.5,0)*2+max(0.5-f,0) for _,_,f,*_ in res)
                if best is None or score>best[0]: best=(score,res)
        if not best: continue
        for cs,cn,f,r0,c0,r1,c1,al in best[1]:
            if f>=0.45:
                cnt=boxsum(I,r0,c0,r1,c1)
                rgb=[boxsum(IR[c],r0,c0,r1,c1)/max(cnt,1) for c in range(3)]
                cells[(round(cs,1),round(cn,1),int(al))]=rgb
# drop isolated cells (trucks): need a neighbour within one bay along s or one row across n
keys=list(cells)
from scipy.spatial import cKDTree
keep=[]
for al in (0,1):
    ks=[q for q in keys if q[2]==al]
    if not ks: continue
    sc=np.array([1/2.8,1/12.8]) if al==0 else np.array([1/12.8,1/2.8])
    pts=np.array([q[:2] for q in ks])*sc
    T=cKDTree(pts)
    for q,p in zip(ks,pts):
        if len(T.query_ball_point(p,1.25))-1>=1: keep.append((q,cells[q]))
out={'name':a.name,'A':[a.la,a.pa],'B':[a.lb,a.pb],'cells':[[p[0],p[1],p[2],[round(v) for v in rgb]] for p,rgb in keep]}
json.dump(out,open(a.out,'w'))
print(a.name,'cells',len(cells),'kept',len(keep),'area m2',round(area.area))
if a.debug:
    from PIL import ImageDraw
    im=Image.fromarray(np.flipud(img.astype(np.uint8)))
    d=ImageDraw.Draw(im)
    for p,rgb in keep:
        cs,cn,al=p
        CL,CW=(12.19,2.44) if al else (2.44,12.19)
        x0=(cs-s0)/a.res; x1=(cs+CL-s0)/a.res; y0=H-(cn+CW-n0)/a.res; y1=H-(cn-n0)/a.res
        d.rectangle([x0,y0,x1,y1],outline=(255,0,255))
    im.save(a.debug)
