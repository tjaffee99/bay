import numpy as np, cv2
def ink_mask(img, purple=True):
    r,g,b=[img[:,:,i].astype(int) for i in range(3)]
    dark=(r<120)&(g<120)&(b<120)
    m=dark
    if purple:
        pur=((r-g)>38)&((b-g)>18)&(g<175)   # photorevision magenta/purple
        m=m|pur
    return m
def ink_frac(img, H, RES, poly_xy, buf_px=0, purple=True):
    m=ink_mask(img,purple).astype(np.uint8)
    pm=np.zeros(m.shape,np.uint8)
    pts=np.array([[(x+H)/RES,(H-y)/RES] for x,y in poly_xy],np.int32)
    cv2.fillPoly(pm,[pts],1)
    if buf_px: pm=cv2.dilate(pm,np.ones((2*buf_px+1,2*buf_px+1),np.uint8))
    n=pm.sum()
    return float((m&pm).sum())/max(n,1)
