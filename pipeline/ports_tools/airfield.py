"""NAS Alameda airfield pavement -> data/manual/airports_extra.geojson
Runways: OSM abandoned:aeroway=runway centrelines buffered to 200 ft (NAS Alameda 13/31 and 07/25 were
8,000 x 200 ft and 7,200 x 200 ft). Taxiways: OSM abandoned:aeroway=taxiway centrelines; their
paved width (and the aprons) from the orthophoto pavement (light, unsaturated pixels; Esri World
Imagery, viewed only), so wide WWII strips keep their real width."""
import sys, os, math, json
BASE=os.environ.get('PORTS_CACHE', os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','..','data','raw','ports'))
import numpy as np, requests
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from osmparse import load
import shapely
from shapely.geometry import LineString, Polygon, box, mapping, shape
from shapely.ops import unary_union
from shapely import affinity
import rasterio.features as rf
from affine import Affine
OUT=sys.argv[1]; NAME=sys.argv[2]
nodes,ntags,ways,rels=load(os.path.join(BASE,'alameda_point.osm'))
lat0=37.785; lon0=-122.318; k=111320*math.cos(math.radians(lat0))
def to_m(lon,lat): return ((lon-lon0)*k,(lat-lat0)*110574)
def to_ll(x,y): return (lon0+x/k, lat0+y/110574)
rw=[];tw=[];bld=[]
for i,(nds,tg) in ways.items():
    pts=[to_m(*nodes[n]) for n in nds if n in nodes]
    if tg.get('abandoned:aeroway')=='runway': rw.append(LineString(pts))
    elif tg.get('abandoned:aeroway')=='taxiway': tw.append(LineString(pts))
    elif 'building' in tg and len(pts)>3:
        p=Polygon(pts)
        if p.is_valid: bld.append(p.buffer(3))
# extend runway centrelines to the documented lengths (OSM traces stop short at the overruns)
def extend(l, L):
    a=np.array(l.coords[0]); b=np.array(l.coords[-1]); d=(b-a)/np.linalg.norm(b-a); m=(a+b)/2
    return LineString([m-d*L/2, m+d*L/2])
runway_lens=[]
RW=[]
for l in rw:
    L=l.length
    doc=8000*0.3048 if L>2250 else 7200*0.3048
    RW.append((extend(l,max(L,doc)) if abs(L-doc)<250 else l))
runways=unary_union([l.buffer(200*0.3048/2, cap_style='flat') for l in RW])
# airfield area: the field west of Monarch Street and the seaplane apron along the lagoon
area_ll=[box(-122.3335,37.7735,-122.30915,37.7942), box(-122.30915,37.77965,-122.2968,37.78135)]
area=unary_union([shapely.transform(g, lambda c: np.array([to_m(x,y) for x,y in c])) for g in area_ll])
# orthophoto pavement mask
z=16; res=2.0
x0,y0,x1,y1=area.bounds
W=int((x1-x0)/res); H=int((y1-y0)/res)
xs=x0+(np.arange(W)+0.5)*res; ys=y1-(np.arange(H)+0.5)*res
X,Y=np.meshgrid(xs,ys); lon=lon0+X/k; lat=lat0+Y/110574
n=256*2**z; px=(lon+180)/360*n; sn=np.sin(np.radians(lat)); py=(0.5-np.log((1+sn)/(1-sn))/(4*np.pi))*n
tx0,tx1=int(px.min()//256),int(px.max()//256); ty0,ty1=int(py.min()//256),int(py.max()//256)
mos=np.zeros(((ty1-ty0+1)*256,(tx1-tx0+1)*256,3),np.uint8)
TILES=os.path.join(BASE,'tiles'); os.makedirs(TILES,exist_ok=True)
S=requests.Session(); S.headers['User-Agent']='BayAreaThroughTime research'
for tx in range(tx0,tx1+1):
    for ty in range(ty0,ty1+1):
        fn=f'{TILES}/{z}_{tx}_{ty}.jpg'
        if not os.path.exists(fn):
            r=S.get(f'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{ty}/{tx}',timeout=30); open(fn,'wb').write(r.content)
        mos[(ty-ty0)*256:(ty-ty0+1)*256,(tx-tx0)*256:(tx-tx0+1)*256]=np.array(Image.open(fn).convert('RGB'))
img=mos[np.clip((py-ty0*256).astype(int),0,mos.shape[0]-1),np.clip((px-tx0*256).astype(int),0,mos.shape[1]-1)].astype(float)
mx=img.max(2); mn=img.min(2); sat=(mx-mn)/np.maximum(mx,1)
pave=(sat<0.16)&(mx>105)&(mx<245)
from scipy import ndimage as ndi
pave=ndi.binary_closing(pave,iterations=2); pave=ndi.binary_opening(pave,iterations=3)
tr=Affine(res,0,x0,0,-res,y1)
polys=[shape(g) for g,v in rf.shapes(pave.astype(np.uint8),mask=pave,transform=tr) if v==1]
mask=unary_union(polys).buffer(2).buffer(-2).intersection(area)
mask=mask.difference(unary_union(bld))
taxi_zone=unary_union([l.buffer(35) for l in tw])
taxiways=mask.intersection(taxi_zone).difference(runways)
aprons=mask.difference(runways).difference(taxi_zone)
feats=[]
def add(geom,kind,minarea):
    gs=[geom] if geom.geom_type=='Polygon' else list(getattr(geom,'geoms',[]))
    for g in gs:
        if g.geom_type!='Polygon' or g.area<minarea: continue
        g=g.simplify(2.5)
        if g.is_empty or g.area<minarea: continue
        if kind!='runway' and g.area/g.length<7: continue  # shoreline riprap slivers
        ext=[to_ll(x,y) for x,y in g.exterior.coords]
        holes=[[to_ll(x,y) for x,y in h.coords] for h in g.interiors if Polygon(h).area>400]
        feats.append({'type':'Feature','properties':{'airport':NAME,'kind':kind},
                      'geometry':{'type':'Polygon','coordinates':[[[round(a,7),round(b,7)] for a,b in ext]]+[[[round(a,7),round(b,7)] for a,b in h] for h in holes]}})
add(runways,'runway',1000); add(taxiways,'taxiway',800); add(aprons,'apron',4000)
fc={'type':'FeatureCollection','name':'airports_extra',
    'description':'Airfields missing from Overture (decommissioned). '+NAME+': runways = OSM abandoned runway centrelines (© OpenStreetMap contributors, ODbL) buffered to the documented 200 ft and extended to 8,000 / 7,200 ft; taxiways and aprons = pavement traced on the Esri World Imagery orthophoto (2026, viewed only) along the OSM abandoned taxiways and in front of the hangars.',
    'features':feats}
json.dump(fc,open(OUT,'w'))
import collections
print(collections.Counter(f['properties']['kind'] for f in feats), 'areas m2', {kd: round(sum(Polygon([to_m(*c) for c in f['geometry']['coordinates'][0]]).area for f in feats if f['properties']['kind']==kd)) for kd in ('runway','taxiway','apron')})
print('runway lengths', [round(l.length) for l in RW])
# debug overlay
from PIL import ImageDraw
dbg=Image.fromarray(img.astype(np.uint8)); d=ImageDraw.Draw(dbg)
col={'runway':(255,0,0),'taxiway':(255,255,0),'apron':(0,255,255)}
for f in feats:
    pts=[((to_m(*c)[0]-x0)/res,(y1-to_m(*c)[1])/res) for c in f['geometry']['coordinates'][0]]
    d.line(pts+[pts[0]],fill=col[f['properties']['kind']],width=2)
dbg.save(sys.argv[3])
