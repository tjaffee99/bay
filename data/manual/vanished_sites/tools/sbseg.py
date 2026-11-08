"""Colour segmentation of Sanborn sheets -> building polygons (pixel coords)."""
import sys, json
import numpy as np, cv2
from PIL import Image, ImageDraw

def masks(a):
    r, g, b = [a[:, :, i].astype(int) for i in range(3)]
    yellow = (r > 105) & (g > 100) & (b < 0.62 * g) & ((r - b) > 55)
    blue = (b > r + 15) & (b > 70) & (g > r)
    pink = (r > g + 25) & (r > 120) & (b > g - 10)
    gray = (abs(r - g) < 12) & (abs(g - b) < 14) & (r > 95) & (r < 140)
    return {'yellow': yellow, 'blue': blue, 'pink': pink}

def comps(img_path, roi=None, min_area=60, open_k=3, close_k=5, kinds=('yellow', 'blue', 'pink')):
    a = np.asarray(Image.open(img_path).convert('RGB'))
    M = masks(a)
    out = []
    for kind in kinds:
        m = M[kind].astype(np.uint8)
        if roi is not None:
            rm = np.zeros_like(m); cv2.fillPoly(rm, [np.asarray(roi, np.int32)], 1); m &= rm
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (close_k, close_k)))
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (open_k, open_k)))
        cs, hier = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in cs:
            A = cv2.contourArea(c)
            if A < min_area: continue
            ap = cv2.approxPolyDP(c, 1.5, True)[:, 0, :]
            M_ = cv2.moments(c)
            out.append({'kind': kind, 'area_px': float(A), 'cx': M_['m10'] / M_['m00'], 'cy': M_['m01'] / M_['m00'], 'coords': ap.tolist()})
    return out

def overlay(img_path, cs, out, scale=1.0, crop=None):
    im = Image.open(img_path).convert('RGB')
    d = ImageDraw.Draw(im)
    for i, c in enumerate(cs):
        col = {'yellow': (255, 0, 0), 'blue': (0, 0, 255), 'pink': (0, 160, 0)}.get(c['kind'], (255, 0, 255))
        pts = [tuple(p) for p in c['coords']]
        if len(pts) > 2: d.line(pts + [pts[0]], fill=col, width=2)
        d.text((c['cx'] - 6, c['cy'] - 6), str(i), fill=(255, 0, 255))
    if crop: im = im.crop(crop)
    if scale != 1: im = im.resize((int(im.size[0] * scale), int(im.size[1] * scale)))
    im.save(out)

if __name__ == '__main__':
    p = sys.argv[1]
    cs = comps(p)
    json.dump(cs, open(sys.argv[2], 'w'))
    overlay(p, cs, sys.argv[3])
    print(len(cs))
