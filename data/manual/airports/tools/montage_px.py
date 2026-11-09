"""python -I montage_px.py OUT.png PX PY HALFPX IMG[@label] ... [--cols 3]"""
import sys
from PIL import Image, ImageDraw
a=[s for s in sys.argv[1:] if not s.startswith('--')]; cols=int(next((s.split('=')[1] for s in sys.argv if s.startswith('--cols=')),3))
out=a[0]; px,py,h=map(int,a[1:4]); ps=[]
for spec in a[4:]:
    f,_,lab=spec.partition('@'); im=Image.open(f).crop((px-h,py-h,px+h,py+h)); ImageDraw.Draw(im).text((4,2*h-14),lab or f[-12:],fill=(255,0,0)); ps.append(im)
rows=(len(ps)+cols-1)//cols; o=Image.new('RGB',(cols*(2*h+3),rows*(2*h+3)))
for k,p in enumerate(ps): o.paste(p,((k%cols)*(2*h+3),(k//cols)*(2*h+3)))
o.save(out); print(out,o.size)
