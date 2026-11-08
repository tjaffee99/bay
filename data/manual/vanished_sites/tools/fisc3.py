import sys,json,numpy as np,cv2
sys.path.insert(0,'.')
from PIL import Image, ImageDraw
H,RES=1100,1.0
img=np.load('cache/oab1959.npy')
r,g,b=[img[:,:,i].astype(int) for i in range(3)]
d=(((r+g+b)/3)<175).astype(np.uint8)
k1=np.eye(5,dtype=np.uint8); k2=np.fliplr(k1).copy()
o1=cv2.morphologyEx(d,cv2.MORPH_OPEN,k1).astype(np.float32); o2=cv2.morphologyEx(d,cv2.MORPH_OPEN,k2).astype(np.float32)
# remove long straight lines (rails/streets drawn diagonally): runs longer than 40 px
long1=cv2.morphologyEx(d,cv2.MORPH_OPEN,np.eye(41,dtype=np.uint8)).astype(np.float32)
long2=cv2.morphologyEx(d,cv2.MORPH_OPEN,np.fliplr(np.eye(41,dtype=np.uint8)).copy()).astype(np.float32)
o1=np.clip(o1-long1,0,1); o2=np.clip(o2-long2,0,1)
D1=cv2.blur(o1,(9,9)); D2=cv2.blur(o2,(9,9))
X=np.minimum(D1,D2)
m=(X>0.06).astype(np.uint8)
zone=[(-1060,470),(-200,520),(420,440),(920,-150),(920,-830),(-1060,-830)]
zm=np.zeros_like(m); cv2.fillPoly(zm,[np.array([[x+H,H-y] for x,y in zone],np.int32)],1); m&=zm
m=cv2.morphologyEx(m,cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_RECT,(3,3)))
m=cv2.morphologyEx(m,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_RECT,(9,9)))
np.save('cache/fisc_mask.npy',m)
n,lab,st,_=cv2.connectedComponentsWithStats(m,8)
out=[]
im=Image.fromarray(img); dr=ImageDraw.Draw(im)
for i in range(1,n):
    if st[i,cv2.CC_STAT_AREA]<500: continue
    comp=(lab==i).astype(np.uint8)
    cs,_=cv2.findContours(comp,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    c=max(cs,key=cv2.contourArea); a=cv2.contourArea(c)
    (cx,cy),(w,h),ang=cv2.minAreaRect(c); fill=a/max(w*h,1)
    box=cv2.boxPoints(((cx,cy),(w,h),ang))
    col=(255,0,0) if fill>0.8 else (0,0,255)
    dr.line([tuple(p) for p in box]+[tuple(box[0])],fill=col,width=3)
    out.append(dict(coords=[[round(float(-H+px+.5),1),round(float(H-py-.5),1)] for px,py in box],area=round(float(a)),w=round(float(min(w,h)),1),l=round(float(max(w,h)),1),fill=round(float(fill),2),cx=round(float(-H+cx)),cy=round(float(H-cy))))
im.resize((1100,1100)).save('out/fisc_blobs3.png')
json.dump(out,open('cache/fisc_blobs3.json','w'))
print(len(out), sum(o['fill']>0.8 for o in out))
