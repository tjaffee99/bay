import numpy as np, cv2
def hatch_mask(img, thresh=175, win=9, dens=0.28, open_px=9, zone_xy=None, H=None):
    r,g,b=[img[:,:,i].astype(int) for i in range(3)]
    d=((r<thresh)&(g<thresh)&(b<thresh)&(np.abs(r-b)<50)).astype(np.float32)
    den=cv2.blur(d,(win,win))
    m=(den>dens).astype(np.uint8)
    solid=cv2.blur(d,(5,5))>0.9          # solid black fills
    m[solid]=1
    if zone_xy is not None:
        zm=np.zeros_like(m); cv2.fillPoly(zm,[np.array([[x+H,H-y] for x,y in zone_xy],np.int32)],1); m&=zm
    m=cv2.morphologyEx(m,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_RECT,(open_px,open_px)))
    return m
