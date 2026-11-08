"""Shift of a topo render against today's roads: python align.py NPY CX CY HALF RES [maxshift]"""
import sys, numpy as np, cv2, shapely.wkb
sys.path.insert(0,'.')
import vt
def align(img, cx, cy, H, RES, maxs=300, region=None):
    n=img.shape[0]
    rr=np.zeros((n,n),np.uint8)
    for rid,cls,g in vt.roads_local(cx,cy,H):
        if cls in ('motorway','trunk','footway','service','path'): continue
        ln=shapely.wkb.loads(bytes(g))
        x,y=vt.ll2loc(*np.asarray(ln.coords).T,cx,cy)
        pts=np.array([[(a+H)/RES,(H-b)/RES] for a,b in zip(x,y)],np.int32)
        cv2.polylines(rr,[pts],False,1,max(1,int(6/RES)))
    r,g,b=[img[:,:,i].astype(int) for i in range(3)]
    ink=((r<150)&(g<150)&(b<150)).astype(np.float32)
    ink=cv2.GaussianBlur(ink,(0,0),3/RES); rrf=cv2.GaussianBlur(rr.astype(np.float32),(0,0),3/RES)
    if region is not None:
        m=np.zeros((n,n),np.float32); x0,x1,y0,y1=region
        m[int((H-y1)/RES):int((H-y0)/RES), int((x0+H)/RES):int((x1+H)/RES)]=1
        ink*=m
    ms=int(maxs/RES)
    res=cv2.matchTemplate(np.pad(rrf,ms), ink[ms:-ms,ms:-ms] if False else ink, cv2.TM_CCORR_NORMED) if False else None
    # brute force via FFT correlation
    F=np.fft.rfft2(ink-ink.mean()); G=np.fft.rfft2(rrf-rrf.mean())
    c=np.fft.irfft2(F*np.conj(G), s=ink.shape)
    c=np.fft.fftshift(c)
    ctr=n//2
    win=c[ctr-ms:ctr+ms+1, ctr-ms:ctr+ms+1]
    j,i=np.unravel_index(np.argmax(win),win.shape)
    dy_px, dx_px = j-ms, i-ms     # ink is shifted by (dx,dy) px relative to roads
    return dx_px*RES, -dy_px*RES, float(win.max()/np.abs(win).mean())
if __name__=='__main__':
    a=sys.argv; img=np.load(a[1]); cx,cy,H,RES=map(float,a[2:6]); ms=float(a[6]) if len(a)>6 else 300
    reg=tuple(map(float,a[7].split(','))) if len(a)>7 else None
    print('map - modern shift (m): dx=%.1f dy=%.1f peak=%.1f'%align(img,cx,cy,H,RES,ms,reg))
