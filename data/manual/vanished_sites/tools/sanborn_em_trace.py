"""Emeryville race track (New California Jockey Club) and Shell Mound Park buildings from the 1911 Sanborn map
(Oakland 1911-12 vol. 3 'including Emeryville', sheets 323-325). Sheet 325 is fitted to today's Park Ave crossings
(Holden, Horton, Hubbard, Halleck: similarity, the sheet is to scale); 324 is joined to 325 by the covered walk to
the grandstand drawn on both, 323 to 324 by two hydrants drawn on both (similarity, scale 1).
-> traced/emeryville_sanborn_1911.json (frame of the emeryville_racetrack site)."""
import json, numpy as np, shapely, cv2
from shapely.geometry import Polygon, shape, box
from rasterio import features
from PIL import Image
import sbref, sbseg
CX, CY = -122.2870, 37.8360
# 325 -> local: Park Ave centreline crossings (px on the 25 % image; local from Overture centrelines)
px325 = np.array([(1582, 240), (1582, 733), (1582, 1236), (1582, 1737)], float)
loc325 = np.array([(6.1, -554.8), (-90.7, -577.8), (-183.6, -603.0), (-282.8, -627.4)])
f325, s325, r325, res325 = sbref.fit_similarity(px325 * [1, -1], loc325)
def sim_px(src, dst, fixed_scale=None):
    """similarity between two pixel frames (y down) from 2 point pairs"""
    a, b = np.asarray(src, float), np.asarray(dst, float)
    va, vb = a[1] - a[0], b[1] - b[0]
    ang = np.arctan2(vb[1], vb[0]) - np.arctan2(va[1], va[0])
    sc = fixed_scale or np.hypot(*vb) / np.hypot(*va)
    R = sc * np.array([[np.cos(ang), -np.sin(ang)], [np.sin(ang), np.cos(ang)]])
    ca, cb = a.mean(0), b.mean(0)
    return lambda p: (np.asarray(p, float) - ca) @ R.T + cb
s324_325 = sim_px([(1356, 1157), (1398, 405)], [(140, 1478), (190, 718)])
s323_324 = sim_px([(1534, 463), (1570, 664)], [(153, 447), (191, 637)], fixed_scale=1.0)
T = {'0325': lambda p: f325(np.asarray(p, float) * [1, -1]),
     '0324': lambda p: f325(s324_325(p) * [1, -1]),
     '0323': lambda p: f325(s324_325(s323_324(p)) * [1, -1])}
def tp(sheet, g):
    return shapely.transform(g, lambda xy: T[sheet](xy))

KEEP = {  # sheet: [(px, py, site, name, height, storeys, use, clip)]  clip: 'top'/'bottom' split of grandstand+walk
 '0324': [(1192, 391, 'ncjc', 'New California Jockey Club grandstand, betting ring and paddock', 15, 2, 'grandstand', ('lt', 560)),
          (1192, 391, 'ncjc', 'covered walk to the grandstand', 4, 1, 'other', ('ge', 560)),
          (365, 393, 'ncjc', 'race track stable (barn E)', 5, 1, 'other', None), (687, 440, 'ncjc', 'private stand and stable (R, Q)', 5, 1, 'other', None),
          (395, 594, 'ncjc', 'race track stable (barn D)', 5, 1, 'other', None), (617, 599, 'ncjc', 'stable outbuilding (T)', 4, 1, 'other', None),
          (810, 709, 'ncjc', 'race track stable (barn B)', 5, 1, 'other', None), (438, 791, 'ncjc', 'race track stable (barn C)', 5, 1, 'other', None),
          (747, 916, 'ncjc', 'race track stable (barn H)', 5, 1, 'other', None),
          (196, 1000, 'ncjc', 'stable hands\' rooms (M)', 4, 1, 'dwelling', None), (323, 1023, 'ncjc', 'stable hands\' rooms (N)', 4, 1, 'dwelling', None),
          (737, 1082, 'ncjc', 'stable hands\' rooms (O)', 4, 1, 'dwelling', None), (882, 1104, 'ncjc', 'stable hands\' rooms (P)', 4, 1, 'dwelling', None),
          (254, 905, 'ncjc', 'hose house', 3.5, 1, 'other', None), (449, 962, 'ncjc', 'oil house (S)', 3.5, 1, 'other', None),
          (1198, 1195, 'ncjc', 'race track station waiting platform (Southern Pacific)', 4, 1, 'other', None),
          (633, 1369, 'shellmound', 'Shell Mound Park dining room, bars and bowling alley', 6, 1, 'hall', None),
          (300, 1589, 'shellmound', 'Shell Mound Park dance pavilion (with stage)', 10, 1, 'hall', None),
          (1090, 1620, 'shellmound', 'Shell Mound Park grandstand (around its athletic / racing track)', 8, 1, 'grandstand', None),
          (603, 1699, 'shellmound', 'Shell Mound Park merry-go-round', 7, 1, 'hall', None),
          (213, 1489, 'shellmound', 'Shell Mound Park confectionery', 4, 1, 'other', None), (114, 1549, 'shellmound', 'Shell Mound Park band stand', 5, 1, 'other', None),
          (54, 1492, 'shellmound', 'Shell Mound Park band stand', 5, 1, 'other', None), (102, 1639, 'shellmound', 'Shell Mound Park pavilion (octagon)', 5, 1, 'other', None),
          (140, 1672, 'shellmound', 'Shell Mound Park bar and photo gallery', 4, 1, 'other', None),
          (198, 1753, 'shellmound', 'Shell Mound Park shooting gallery', 4, 1, 'other', None),
          (855, 1863, 'shellmound', 'Shell Mound Park building (south fence)', 5, 1, 'other', None),
          (972, 1862, 'shellmound', 'Shell Mound Park building (south fence)', 5, 1, 'other', None),
          (406, 1625, 'shellmound', 'Shell Mound Park booth', 3, 1, 'other', None), (459, 1611, 'shellmound', 'Shell Mound Park booth', 3, 1, 'other', None),
          (628, 1624, 'shellmound', 'Shell Mound Park booth', 3, 1, 'other', None), (460, 1725, 'shellmound', 'Shell Mound Park booth', 3, 1, 'other', None),
          (640, 1761, 'shellmound', 'Shell Mound Park booth', 3, 1, 'other', None)],
 '0325': [(1219, 485, 'ncjc', 'New California Jockey Club stalls (quadrangle)', 4.5, 1, 'other', None),
          (396, 377, 'ncjc', 'New California Jockey Club club house', 8, 2, 'hall', None),
          (164, 725, 'ncjc', 'New California Jockey Club grandstand (south end)', 15, 2, 'grandstand', ('lt', 700)),
          (164, 725, 'ncjc', 'covered walk to the grandstand', 4, 1, 'other', ('ge', 700)),
          (664, 882, 'ncjc', 'Burns & Waterhouse private racing barn', 4.5, 1, 'other', None),
          (1028, 881, 'ncjc', 'private racing barn', 4.5, 1, 'other', None),
          (896, 843, 'ncjc', 'race track dwelling', 6, 2, 'dwelling', None),
          (939, 1313, 'ncjc', 'race track stalls along the fence (Z)', 4, 1, 'other', None),
          (849, 1195, 'ncjc', 'stable shed (X)', 3.5, 1, 'other', None), (848, 1263, 'ncjc', 'stable shed (Y)', 3.5, 1, 'other', None),
          (212, 1541, 'ncjc', 'race track station waiting platform (Southern Pacific)', 4, 1, 'other', None)],
 '0323': [(1414, 496, 'ncjc', 'race track stable (barn H)', 5, 1, 'other', None), (1455, 697, 'ncjc', 'race track stable (barn G)', 5, 1, 'other', None),
          (1498, 898, 'ncjc', 'race track stable (barn F)', 5, 1, 'other', None), (684, 559, 'ncjc', 'race track stable (barn K)', 5, 1, 'other', None),
          (1015, 587, 'ncjc', 'race track stable (barn J)', 5, 1, 'other', None), (1120, 773, 'ncjc', 'race track stable (barn I)', 5, 1, 'other', None),
          (906, 792, 'ncjc', 'race track restaurant (Q)', 4, 1, 'hall', None), (1229, 912, 'ncjc', 'race track warehouse (L)', 4.5, 1, 'warehouse', None),
          (774, 508, 'ncjc', 'stable hands\' rooms (R, V)', 4, 1, 'dwelling', None), (886, 990, 'ncjc', 'race track station waiting shed', 4, 1, 'other', None),
          (1319, 962, 'ncjc', 'stable outbuilding (W)', 3.5, 1, 'other', None), (1349, 979, 'ncjc', 'stable outbuilding', 3.5, 1, 'other', None),
          (1227, 1364, 'shellmound', 'Shell Mound Park octagonal dance pavilion on the shell mound (with bar)', 12, 1, 'hall', None)],
}
out = {'cx': CX, 'cy': CY, 'fit': {'325_sim_residual_m': res325.round(2).tolist(), 'scale_m_per_px': round(float(s325), 4), 'rotation_deg': round(float(r325), 2)},
       'buildings': [], 'ground': []}
for sheet, items in KEEP.items():
    a = np.asarray(Image.open(f'sb/00727_007_{sheet}_25.jpg').convert('RGB'))
    m = (sbseg.masks(a)['yellow'] | sbseg.masks(a)['pink']).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))
    polys = [shape(g).simplify(1.2) for g, v in features.shapes(m, mask=m.astype(bool)) if shape(g).area >= 50]
    for x, y, site, name, h, st, use, clip in items:
        pt = shapely.Point(x, y)
        c = [p for p in polys if Polygon(p.exterior).distance(pt) < 4] or [p for p in polys if p.distance(pt) < 12]
        if not c:
            print('MISSING', sheet, x, y, name); continue
        p = min(c, key=lambda p: Polygon(p.exterior).distance(pt) - 1e-7 * p.area)
        p = Polygon(p.exterior, [h_ for h_ in p.interiors if Polygon(h_).area > 300])
        if clip:
            op, yc = clip
            p = p.intersection(box(-1e4, -1e4, 1e4, yc) if op == 'lt' else box(-1e4, yc, 1e4, 1e4))
            p = max(getattr(p, 'geoms', [p]), key=lambda g: g.area)
        q = tp(sheet, p)
        out['buildings'].append({'sheet': sheet, 'site': site, 'name': name, 'height_m': h, 'storeys': st, 'use': use, 'area_m2': round(q.area, 1),
                                 'coords': [[round(v, 2) for v in cc] for cc in q.exterior.coords],
                                 'holes': [[[round(v, 2) for v in cc] for cc in hh.coords] for hh in q.interiors]})
# ground: Shell Mound Park grounds (fence lines of sheets 323/324, hand-read px) and the mound
smp = [(1100, 1205), (1590, 1205), (1590, 1960)]   # 323: west part (from the walk-over to the bay fence)
mound_bottom = shapely.Point(1235, 1360).buffer(150)    # 323: 'bottom line of mound' circle, r ~ 150 px
out['ground'].append({'site': 'shellmound', 'name': 'shell mound (bottom line of the mound)', 'cover': 'park',
                      'coords': [list(c) for c in tp('0323', mound_bottom).exterior.coords]})
park324 = Polygon([(20, 1330), (1180, 1500), (1080, 1980), (20, 1950)])
park323 = Polygon([(1090, 1215), (1600, 1290), (1600, 1990), (1180, 1980), (1050, 1700)])
g = shapely.union_all([tp('0324', park324), tp('0323', park323)]).buffer(2).buffer(-2)
out['ground'].append({'site': 'shellmound', 'name': 'Shell Mound Park grounds', 'cover': 'park', 'coords': [list(c) for c in g.exterior.coords]})
json.dump(out, open('/home/user/bay/data/manual/vanished_sites/traced/emeryville_sanborn_1911.json', 'w'))
print(out['fit'])
import collections
print(collections.Counter(b['site'] for b in out['buildings']), round(sum(b['area_m2'] for b in out['buildings'])))
