"""Is each map road segment drawn on a topo sheet? (fraction of 5 m samples with road ink within tol m)"""
import sys, json, numpy as np, cv2, shapely
sys.path.insert(0,'.')
import vt
from segs import site_segments
from roads_in import _load
def on_sheet(img, H, RES, line_ll, cx, cy, tol=7.0, thresh=120):
    r,g,b=[img[:,:,i].astype(int) for i in range(3)]
    dark=((r<thresh)&(g<thresh)&(b<thresh)) | (((r-g)>38)&((b-g)>18)&(g<175))
    k=int(2*tol/RES)|1
    near=cv2.dilate(dark.astype(np.uint8),cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(k,k)))
    x,y=vt.ll2loc(*np.asarray(line_ll.coords).T,cx,cy)
    ln=shapely.LineString(np.column_stack([x,y]))
    n=max(2,int(ln.length/5)); pts=[ln.interpolate(t,normalized=True) for t in np.linspace(0,1,n)]
    hit=[]
    for p in pts:
        i=int((p.x+H)/RES); j=int((H-p.y)/RES)
        if 0<=i<img.shape[1] and 0<=j<img.shape[0]: hit.append(near[j,i])
    return float(np.mean(hit)) if hit else np.nan
if __name__=='__main__':
    sid, npys, cx, cy, H, RES = sys.argv[1], sys.argv[2].split(','), *map(float, sys.argv[3:7])
    segs=site_segments(sid)
    imgs={n:np.load(n) for n in npys}
    allr={}
    for f in ['roads_local','roads_region']:
        d=_load(f).set_index('id'); allr.update({i:g for i,g in zip(d.index,d.geometry) if i in set(segs.id)})
    out=[]
    for r in segs.itertuples():
        fr=[round(on_sheet(imgs[n],H,RES,allr[r.id],cx,cy),2) for n in npys]
        out.append(dict(id=r.id,cls=r._3,name=r.name,inside_m=r.inside_m,on=fr))
        print(r.id, r._3, r.name, r.inside_m, fr)
    json.dump(out,open(f'cache/segdate_{sid}.json','w'))
