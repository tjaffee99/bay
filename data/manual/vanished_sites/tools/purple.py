import numpy as np, cv2, shapely
from shapely.geometry import Polygon
def purple_mask(img):
    r,g,b=[img[:,:,i].astype(int) for i in range(3)]
    return (((r-g)>38)&((b-g)>18)&(g<175)).astype(np.uint8)
def areas(img,H,RES,zone_xy,dot_close=9,min_m2=2000,solid=False,open_px=5,min_solid=60):
    m=purple_mask(img)
    zm=np.zeros_like(m); pts=np.array([[(x+H)/RES,(H-y)/RES] for x,y in zone_xy],np.int32); cv2.fillPoly(zm,[pts],1); m&=zm
    if solid:
        m=cv2.morphologyEx(m,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(open_px,open_px)))
        mina=min_solid
    else:
        m=cv2.morphologyEx(m,cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(dot_close,dot_close)))
        m=cv2.morphologyEx(m,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(5,5)))
        mina=min_m2
    cs,_=cv2.findContours(m,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    out=[]
    for c in cs:
        if cv2.contourArea(c)*RES*RES<mina: continue
        c=cv2.approxPolyDP(c,1.5/RES,True)[:,0,:]
        if len(c)<3: continue
        out.append(Polygon([(-H+(px+.5)*RES,H-(py+.5)*RES) for px,py in c]).buffer(0))
    return out
