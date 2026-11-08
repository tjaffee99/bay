"""Map road segments (Overture roads_local / roads_region) on vanished sites -> road_segments.csv
(segment drawn on the site's last topo sheet = existed; otherwise not before the site's end)."""
import sys, csv, json, numpy as np, shapely
from shapely.geometry import shape
sys.path.insert(0,'.')
from segs import site_segments
from segdate import on_sheet
from roads_in import _load
SHEETS={  # site_id: (npy, cx, cy, half, res, sheet label)
 'bay_meadows':('cache/bm1993w.npy',-122.2971,37.5427,800,1.0,'USGS San Mateo 1:24k 1993 (1993 photos)'),
 'hp_cupertino':('cache/ap1991t8.npy',-122.0090,37.3345,800,1.0,'USGS Cupertino 1:24k 1991'),
 'tanforan':('cache/tf1956.npy',-122.4192,37.6356,700,1.0,'USGS San Francisco South 1:24k 1956'),
 'ford_milpitas':('cache/fm1979.npy',-121.8980,37.4158,700,1.0,'USGS Milpitas 1:24k 1980 photorevision (1979 photos)'),
 'marine_world':('cache/mw1980.npy',-122.2640,37.5300,700,1.0,'USGS San Mateo 1:24k 1980 photorevision (1978 photos)'),
 'frontier_village':('cache/fv1973.npy',-121.8240,37.2650,700,1.0,'USGS San Jose East 1:24k 1973 photorevision'),
}
fc=json.load(open('sites.geojson'))['features']
def zone_of(site_id, line):
    best=None
    for f in fc:
        p=f['properties']
        if p['site_id'] not in (site_id,'apple_park'): continue
        g=shape(f['geometry'])
        if g.intersects(line):
            L=g.intersection(line).length
            if best is None or L>best[0]: best=(L,p)
    return best[1] if best else None
rows=[]
geoms={}
for f in ['roads_local','roads_region']:
    d=_load(f); geoms.update(dict(zip(d.id,d.geometry)))
for sid,(npy,cx,cy,H,RES,label) in SHEETS.items():
    segs=site_segments(sid, part_filter=lambda p: p['site_id']==sid and p['year_end']<9999)
    if segs is None: continue
    img=np.load(npy)
    for r in segs.itertuples():
        cls=r._3
        if cls in ('motorway','trunk','motorway_link','trunk_link'): continue
        ln=geoms[r.id]
        fr=on_sheet(img,H,RES,ln,cx,cy,tol=4.0)
        z=zone_of(sid, ln)
        end=z['year_end'] if z else None
        if (fr>=0.85 and not (sid=='bay_meadows' and str(r.name).startswith('Park Place'))) or (sid=='hp_cupertino' and cls in ('secondary','tertiary')):
            act,nb,ev='keep','',f'drawn on the {label} ({fr:.0%} of its length)'
        else:
            nb=int(np.ceil(end)) if end else ''
            act='date'
            ev=f"not on the {label} ({fr:.0%}); lies on '{z['name'] if z else sid}' ground ({z['cover'] if z else ''}, {z['year_start'] if z else ''}-{end})"
            if sid=='bay_meadows' and z and z['year_end']<2000: nb=1999; ev+='; Bay Meadows Phase I (Franklin Templeton campus opened 2001)'
            elif sid=='bay_meadows': nb=2010; ev+='; Bay Meadows II streets: north streets already paved on the Oct 2010 orthophoto, residential blocks from Oct 2012'
            elif sid=='hp_cupertino': nb=2017
        rows.append(dict(segment_id=r.id,file=r.file,cls=cls,name=r.name if isinstance(r.name,str) else '',site_id=sid,inside_m=int(r.inside_m),
                         on_last_sheet=round(fr,2),action=act,not_before=nb,evidence=ev))
# Apple Park Way etc. inside today's campus (campus roads, 2017)
segs=site_segments('apple_park', part_filter=lambda p: p['surface']=='campus park')
for r in segs.itertuples():
    if any(x['segment_id']==r.id for x in rows): continue
    if r._3 in ('motorway','trunk','secondary','tertiary'): continue
    rows.append(dict(segment_id=r.id,file=r.file,cls=r._3,name=r.name if isinstance(r.name,str) else '',site_id='apple_park',inside_m=int(r.inside_m),
                     on_last_sheet='',action='date',not_before=2017,evidence='Apple Park campus road (opened 2017); the HP site had no through streets here (old Pruneridge Ave is in sites.geojson)'))
for x in rows:
    if x['name'].startswith('Apple Park Way'): x['not_before']=2017; x['action']='date'; x['evidence']='Apple Park Way: campus ring/perimeter road built with Apple Park (2014-17), not on the 1991 sheet'
with open('road_segments.csv','w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
import collections
print(len(rows), collections.Counter((x['site_id'],x['action']) for x in rows))
