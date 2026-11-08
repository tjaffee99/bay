import sys, json, numpy as np
sys.path.insert(0,'.')
import vt, geom, presence
from shapely.geometry import Polygon, box, mapping
from shapely import affinity
CX,CY=-122.0090,37.3345
feats={f['id']:Polygon(f['coords']) for f in json.load(open('cache/hp_feats.json'))}
def seg(i, ang=0, tol=1.5): 
    return geom.clean_rect(feats[i], ang, tol=tol, close=2.5)
B={}
# north: HP Cupertino site (Homestead / Wolfe), segmentation of the Oct 2010 orthophoto + hand reading
B['A']=box(-390,118,-303,220).union(box(-310,160,-300,227))
B['B']=box(-293,136,-198,210)
B['n220']=seg(220); B['n226']=seg(226); B['n245']=seg(245); B['n249']=feats[249].simplify(1.5)
B['n255']=seg(255); B['n263']=seg(263); B['n274']=seg(274); B['n262']=box(207,32,262,100)
B['n210']=seg(210); B['G1']=box(92,148,128,210); B['n248']=box(106,115,134,129)
# south: Pruneridge Ave office campus (hand-read corners, Oct 2010 orthophoto)
B['S1']=Polygon([(-202,-266),(-182,-249),(-157.5,-280),(-177.5,-300)])
B['S2']=Polygon([(-282,-385),(-208,-305),(-182,-328),(-256,-410)])
B['S3']=Polygon([(-80,-309),(-37.5,-332.5),(-82.5,-442.5),(-135,-415)])
B['S4']=Polygon([(35,-327.5),(85,-335),(102.5,-435),(57.5,-445)])
B['S5']=box(165,-327.5,237.5,-297.5)
B['S6']=box(185,-470,242.5,-382.5)
B['S7']=Polygon([(-225,-482.5),(-197.5,-447.5),(-112.5,-527.5),(-135,-562.5)])
B['S8']=Polygon([(-50,-552.5),(8,-592),(-35,-655),(-90,-615)])
B['S9']=Polygon([(57.5,-517.5),(105,-545),(70,-605),(65,-610),(37.5,-675),(-15,-625),(20,-580),(25,-575)])
B['S10']=box(157,-542,182,-527)
B['S11']=box(215,-647.5,252.5,-567.5)
B['S12']=box(180,-707.5,237.5,-650)
T='https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/GeoTIFF/CA/'
ed=[('1960','CA_Cupertino_289703_1961_24000_geo.tif',1960),('1968','CA_Cupertino_289705_1961_24000_geo.tif',1968),('1973','CA_Cupertino_289706_1961_24000_geo.tif',1973),('1979','CA_Cupertino_289707_1961_24000_geo.tif',1979),('1991','CA_Cupertino_289701_1991_24000_geo.tif',1991)]
H,RES=800,1.0
imgs={}
for k,f,y in ed:
    try: imgs[k]=np.load(f'cache/ap{k}t8.npy')
    except Exception:
        imgs[k]=vt.render_topo(T+f,CX,CY,H,RES); np.save(f'cache/ap{k}t8.npy',imgs[k])
out={}
for n,p in B.items():
    p=p.buffer(0)
    fr=[presence.ink_frac(imgs[k],H,RES,list(p.exterior.coords)) for k,_,_ in ed]
    out[n]=dict(coords=[[round(x,1),round(y,1)] for x,y in p.exterior.coords],ink=[round(f,2) for f in fr],area=round(p.area))
    print(n,round(p.area),[round(f,2) for f in fr])
json.dump(out,open('traced/hp_cupertino_2010.json','w'))
