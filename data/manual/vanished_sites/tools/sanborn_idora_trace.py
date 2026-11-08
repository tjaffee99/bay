"""Idora Park, Oakland: buildings and rides from the 1911 Sanborn sheet (Oakland vol. 3, sheet 293),
fitted to today's block (parcel union) by an affine transform of the four block corners.
-> traced/idora_park_1911.json (local metre frame of the site, cx/cy below)."""
import json, numpy as np, shapely, cv2
from shapely.geometry import Polygon, LineString, shape, mapping
from rasterio import features
from PIL import Image
import sbref, sbseg
CX, CY = -122.2633, 37.8423
IMG = 'sb/00727_007_0293_25.jpg'
PX = np.array([(173.3, 1304), (1270, 1552), (1585, 63), (184, 159)], float)       # SW, SE, NE, NW block corners (px, 25 % image)
LOC = np.array([(-107.7, -107.6), (117.7, -132.4), (151.7, 174.7), (-131.8, 120.1)])  # today's parcel-block corners (m)
F, M, RES = sbref.fit_affine(PX * [1, -1], LOC)
def T(pts):
    p = np.asarray(pts, float) * [1, -1]
    return F(p)
def tp(poly):
    return shapely.transform(poly, lambda xy: T(xy))

a = np.asarray(Image.open(IMG).convert('RGB'))
MS = sbseg.masks(a)
roi = np.zeros(a.shape[:2], np.uint8); cv2.fillPoly(roi, [PX.astype(np.int32)], 1)
LABELS = [  # (px, py, name, height m, storeys, use, material)
    (850, 135, 'Idora Park warehouse', 5, 1, 'other', 'wood frame'),
    (955, 180, 'Idora Park restaurant', 7, 1, 'hall', 'wood frame'),
    (1222, 126, 'Idora Park band stand', 6, 1, 'other', 'wood frame'),
    (1435, 300, "Shooting the Rapids, the 'Tickler' and concessions", 10, 2, 'hall', 'wood frame'),
    (831, 231, 'Moving pictures theatre', 6, 1, 'hall', 'wood frame'),
    (805, 421, 'concession booths (ball game, photo, restaurant, shooting gallery)', 4.5, 1, 'other', 'wood frame'),
    (693, 535, 'Idora Park shop / ride platform', 4, 1, 'other', 'wood frame'),
    (669, 610, 'Mountain Slide (canvas covered)', 8, 1, 'other', 'wood frame'),
    (588, 665, 'concession booth', 4, 1, 'other', 'wood frame'),
    (727, 683, 'Idora Park concrete building', 4, 1, 'other', 'concrete'),
    (944, 740, 'Idora Park theatre (opera house: stage, balcony)', 13, 2, 'hall', 'wood frame'),
    (944, 492, 'Social Whirl (ride)', 6, 1, 'other', 'wood frame'),
    (1134, 552, 'figure-eight roller coaster station', 6, 1, 'other', 'wood frame'),
    (1431, 507, 'Idora Park monkey house', 5, 1, 'other', 'wood frame'),
    (1238, 1187, 'Idora Park merry-go-round', 8, 1, 'hall', 'wood frame'),
    (900, 1150, 'Idora Park roller skating rink', 11, 1, 'hall', 'wood frame'),
    (388, 1132, 'Idora Park electric shop / paint shop', 5, 1, 'other', 'wood frame'),
    (361, 866, 'The Prairie Schooner (ride)', 5, 1, 'other', 'wood frame'),
    (217, 919, 'Idora Park ice cream factory and warehouses', 6, 1, 'factory', 'wood frame'),
    (1409, 854, 'Idora Park main entrance (Telegraph Ave)', 8, 2, 'hall', 'wood frame'),
    (1067, 1448, 'Scenic Railway station', 7, 1, 'hall', 'wood frame'),
    (184, 749, 'Idora Park Shattuck Ave entrance', 5, 1, 'other', 'wood frame'),
    (1120, 973, 'Idora Park cement store', 3, 1, 'other', 'concrete'),
    (343, 1308, 'Idora Park shed', 4, 1, 'other', 'wood frame'),
]
out = {'cx': CX, 'cy': CY, 'fit_residual_m': RES.round(2).tolist(), 'buildings': [], 'rides': [], 'ground': []}
for kind in ('yellow', 'blue'):
    m = (MS[kind] & roi.astype(bool)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))
    for g, v in features.shapes(m, mask=m.astype(bool)):
        p = shape(g)
        if p.area < 60:
            continue
        r = p.minimum_rotated_rectangle
        e = np.asarray(r.exterior.coords)
        dims = sorted([np.hypot(*(e[1] - e[0])), np.hypot(*(e[2] - e[1]))])
        if dims[0] < 9 and p.area < 600:          # coaster / platform hatch stripes, not buildings
            continue
        p = p.simplify(1.2)
        L = [l for l in LABELS if p.buffer(4).contains(shapely.Point(l[0], l[1]))]
        if L:
            l = L[0]; name, h, st, use, mat = l[2], l[3], l[4], l[5], l[6]
        else:
            name, h, st, use, mat = 'Idora Park concession / ride building', 4.5, 1, 'other', 'wood frame'
        q = tp(p)
        out['buildings'].append({'name': name, 'height_m': h, 'storeys': st, 'use': use, 'material': mat,
                                 'colour': kind, 'area_m2': round(q.area, 1), 'coords': [list(map(lambda v: round(v, 2), c)) for c in q.exterior.coords],
                                 'holes': [[list(map(lambda v: round(v, 2), c)) for c in h_.coords] for h_ in q.interiors if Polygon(h_).area > 200]})
# hand-traced rides (px on the 25 % image)
f8 = [(1140, 530), (1120, 500), (1090, 450), (1060, 400), (1030, 350), (1015, 317), (975, 305), (935, 315), (922, 340), (925, 370), (945, 395),
      (980, 410), (1015, 428), (1040, 440), (1070, 452), (1095, 465), (1110, 485), (1112, 510), (1100, 535), (1080, 550), (1045, 552), (1018, 535),
      (1008, 505), (1010, 470), (1018, 440), (1025, 410), (1030, 380), (1030, 350)]
f8l = LineString(T(f8))
out['rides'].append({'name': 'figure-eight roller coaster (track)', 'height_m': 8, 'coords': [list(c) for c in f8l.buffer(2.0, cap_style=2, join_style=2).exterior.coords],
                     'note': 'dashed track outline with hatching on the 1911 sheet ("incline start"); centreline hand-traced, track width 4 m; height estimated'})
sr = [(368, 1262), (380, 1238), (410, 1232), (440, 1240), (560, 1262), (760, 1300), (900, 1340), (1010, 1370), (1060, 1385), (1060, 1450),
      (870, 1445), (700, 1405), (560, 1375), (480, 1355), (420, 1335), (380, 1310), (366, 1285)]
out['rides'].append({'name': 'Scenic Railway (trestle)', 'height_m': 3, 'coords': [list(c) for c in T(sr)],
                     'note': 'trestle loop "elevated 3 ft" between the dashed outer lines on the 1911 sheet; hand-traced'})
outer = [(186.7, 500), (190.8, 400), (220, 308), (278, 242), (378, 204), (503, 196), (628, 187.5), (737, 200), (787, 242), (803, 317), (787, 400),
         (753, 467), (703, 525), (637, 583), (545, 642), (420, 625), (295, 575), (220, 525)]
inner = [(228, 400), (253, 317), (303, 267), (387, 242), (503, 237.5), (637, 229), (703, 242), (737, 317), (728, 400), (703, 467), (637, 542),
         (545, 583), (445, 587.5), (337, 550), (253, 500), (228, 442)]
out['ground'].append({'name': 'Auto Race Course (electric cars)', 'cover': 'dirt_track', 'outer': [list(c) for c in T(outer)], 'inner': [list(c) for c in T(inner)],
                      'note': 'track between the two curves of the 1911 sheet, hand-traced'})
amph = [(1033, 114), (1121, 105), (1180, 135), (1277, 186), (1296, 205), (1284, 380), (1178, 355), (1084, 311), (1035, 265), (1060, 240), (1037, 208)]
out['ground'].append({'name': 'Amphitheatre (open-air seating and platform)', 'cover': 'parking', 'outer': [list(c) for c in T(amph)], 'inner': None,
                      'note': 'dashed outline on the 1911 sheet (uncoloured = open air), hand-traced'})
out['ground'].append({'name': 'Idora Park grounds', 'cover': 'park', 'outer': LOC.tolist(), 'inner': None,
                      'note': 'the park block (56th-58th St, Telegraph-Shattuck), corners from today\'s parcels; 16.8 acres (documented 17.5)'})
json.dump(out, open('/home/user/bay/data/manual/vanished_sites/traced/idora_park_1911.json', 'w'), indent=None)
print('fit residual', RES.round(2), 'buildings', len(out['buildings']))
for b in out['buildings']:
    print(round(b['area_m2']), b['colour'], b['name'], 'holes', len(b['holes']))
