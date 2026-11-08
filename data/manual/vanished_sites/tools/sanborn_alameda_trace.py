"""Alameda west-end bath resorts from the Sanborn maps of Alameda (LOC sanborn00374: 1897 edition, and the 1948
edition), each sheet fitted by an affine transform to the corners of a block north of Central Ave (today's parcels).
-> traced/alameda_baths_sanborn.json (local metre frame cx/cy below)."""
import json, numpy as np, shapely, cv2
from shapely.geometry import Polygon, shape
from rasterio import features
from PIL import Image
import sbref, sbseg
CX, CY = -122.2800, 37.7700
BLOCK = {  # today's parcel blocks between Central and Taylor (NW, NE, SE, SW), local m
    'A': [(-520, 278), (-221, 269), (-224, 187), (-524, 196)],      # Fourth - Fifth
    'B': [(-202, 292), (41, 286), (35, 180), (-205, 187)],          # Fifth - Sixth
    'C': [(58, 261), (265, 255), (263, 173), (55, 179)],            # Sixth - Webster
}
SHEETS = {  # key: (image, block, px corners NW, NE, SE, SW)
    '1897_11': ('sb/00374_001_0011_25.jpg', 'A', [(99, 701), (1619, 710), (1612, 1132), (93, 1115)]),
    '1897_12': ('sb/00374_001_0012_25.jpg', 'B', [(238, 562), (1461, 563), (1461, 1100), (237, 1100)]),
    '1897_15': ('sb/00374_001_0015_25.jpg', 'C', [(300, 667), (1355, 668), (1352, 1096), (300, 1097)]),
    '1948_11': ('sb/00374_002_0011_25.jpg', 'A', [(117, 718), (1591, 722), (1591, 1138), (115, 1123)]),
    '1948_12': ('sb/00374_002_0012_25.jpg', 'B', [(222, 574), (1416, 575), (1416, 1101), (223, 1098)]),
    '1948_15': ('sb/00374_002_0015_25.jpg', 'C', [(306, 690), (1335, 690), (1336, 1118), (306, 1118)]),
}
TF = {}
for k, (img, b, px) in SHEETS.items():
    f, M, res = sbref.fit_affine(np.asarray(px, float) * [1, -1], np.asarray(BLOCK[b], float))
    TF[k] = (f, res)
def T(k, pts):
    return TF[k][0](np.asarray(pts, float) * [1, -1])
def tp(k, poly):
    return shapely.transform(poly, lambda xy: T(k, xy))

# buildings to keep: (sheet, px, py, site_id, name, height, storeys, use)
KEEP = [
    ('1897_11', 769, 1427, 'sandy_beach_baths', 'Sandy Beach Baths dressing rooms and platform', 4, 1, 'other'),
    ('1897_11', 933, 1562, 'alameda_baths', 'Alameda Baths dressing rooms and platform (pier)', 4, 1, 'other'),
    ('1897_11', 997, 1459, 'alameda_baths', 'Alameda Baths office', 4, 1, 'office'),
    ('1897_11', 1016, 1550, 'sunny_cove_baths', 'Sunny Cove Baths dressing rooms', 4, 1, 'other'),
    ('1897_11', 1165, 1509, 'sunny_cove_baths', 'Sunny Cove Baths cabin', 3.5, 1, 'other'),
    ('1897_11', 1242, 1489, 'sunny_cove_baths', 'Sunny Cove Baths cabins', 3.5, 1, 'other'),
    ('1897_11', 1266, 1524, 'sunny_cove_baths', 'Sunny Cove Baths cabin', 3.5, 1, 'other'),
    ('1897_11', 1312, 1598, 'green_arbor_baths', 'Green Arbor Baths dressing rooms (platform)', 4, 1, 'other'),
    ('1897_11', 1389, 1545, 'green_arbor_baths', 'Green Arbor Baths dressing rooms', 4, 1, 'other'),
    ('1897_11', 1464, 1530, 'green_arbor_baths', 'Green Arbor Baths outbuilding', 3, 1, 'other'),
    ('1897_11', 1544, 1516, 'green_arbor_baths', 'Green Arbor Baths kitchen and storage', 4, 1, 'other'),
    ('1897_12', 1423, 1311, 'cottage_baths', 'The Cottage Baths (tub baths)', 5, 1, 'hall'),
    ('1897_12', 1390, 1396, 'cottage_baths', 'The Cottage Baths dressing rooms', 3.5, 1, 'other'),
    ('1897_12', 1456, 1390, 'cottage_baths', 'The Cottage Baths dressing rooms and boiler', 3.5, 1, 'other'),
    ('1897_15', 324, 1572, 'terrace_baths', 'The Terrace Baths (dressing rooms, laundry, suit room, glass-roofed swimming tank)', 6, 1, 'hall'),
    ('1897_15', 640, 1479, 'terrace_baths', 'The Terrace Baths dressing rooms and boat house', 4, 1, 'other'),
    ('1897_15', 266, 1443, 'terrace_baths', 'The Terrace Baths hot-water heater house', 3.5, 1, 'other'),
    ('1897_15', 269, 1859, 'terrace_baths', 'The Terrace Baths diving shelter', 4, 1, 'other'),
    ('1897_15', 715, 1924, 'terrace_baths', 'The Terrace Baths platform shelter', 3.5, 1, 'other'),
    ('1897_15', 1586, 1374, 'neptune_gardens', 'Neptune Gardens pavilion (dancing, skating, theatre)', 12, 1, 'hall'),
    ('1897_15', 991, 1353, 'neptune_gardens', 'Neptune Gardens house', 9, 2, 'dwelling'),
    ('1897_15', 899, 1261, 'neptune_gardens', 'Neptune Gardens shed', 4, 1, 'other'),
    ('1897_15', 1011, 1479, 'neptune_gardens', 'Neptune Gardens shed', 4, 1, 'other'),
    ('1897_15', 1109, 1481, 'neptune_gardens', 'Neptune Gardens shed', 3.5, 1, 'other'),
    ('1897_15', 853, 1339, 'neptune_gardens', 'Neptune Gardens windmill and tank house', 9, 1, 'other'),
    ('1897_15', 932, 1309, 'neptune_gardens', 'Neptune Gardens summer house', 4, 1, 'other'),
    ('1897_15', 947, 1276, 'neptune_gardens', 'Neptune Gardens summer house', 4, 1, 'other'),
    ('1897_15', 1023, 1283, 'neptune_gardens', 'Neptune Gardens summer house', 4, 1, 'other'),
    ('1897_15', 1064, 1318, 'neptune_gardens', 'Neptune Gardens summer house', 4, 1, 'other'),
    ('1897_15', 1054, 1395, 'neptune_gardens', 'Neptune Gardens summer house', 4, 1, 'other'),
    ('1948_11', 1081, 1511, 'sunny_cove_baths', 'Sunny Cove Baths lunch room, dressing rooms and tank platform', 5, 1, 'hall'),
    ('1948_11', 1030, 1698, 'sunny_cove_baths', 'Sunny Cove Baths dressing rooms', 3.5, 1, 'other'),
    ('1948_11', 1294, 1542, 'sunny_cove_baths', 'Sunny Cove Baths dressing rooms', 3.5, 1, 'other'),
    ('1948_11', 1279, 1604, 'sunny_cove_baths', 'Sunny Cove Baths dressing rooms', 3.5, 1, 'other'),
    ('1948_11', 1283, 1669, 'sunny_cove_baths', 'Sunny Cove Baths dressing rooms', 3.5, 1, 'other'),
    ('1948_11', 1264, 1602, 'sunny_cove_baths', 'Sunny Cove Baths dressing rooms', 3.5, 1, 'other'),
    ('1948_11', 1268, 1672, 'sunny_cove_baths', 'Sunny Cove Baths dressing rooms', 3.5, 1, 'other'),
    ('1948_11', 1271, 1732, 'sunny_cove_baths', 'Sunny Cove Baths dressing rooms', 3.5, 1, 'other'),
    ('1948_11', 1298, 1694, 'sunny_cove_baths', 'Sunny Cove Baths dressing rooms', 3.5, 1, 'other'),
    ('1948_12', 1053, 1466, 'cottage_baths', 'Cottage Baths dressing rooms (west)', 3.5, 1, 'other'),
    ('1948_12', 1053, 1623, 'cottage_baths', 'Cottage Baths dressing rooms (west)', 3.5, 1, 'other'),
    ('1948_12', 1104, 1706, 'cottage_baths', 'Cottage Baths canoe house, filters and dressing rooms', 4, 1, 'other'),
    ('1948_12', 1089, 1734, 'cottage_baths', 'Cottage Baths outbuilding', 3.5, 1, 'other'),
    ('1948_12', 1073, 1356, 'cottage_baths', 'Cottage Baths dressing rooms', 3.5, 1, 'other'),
    ('1948_12', 1089, 1359, 'cottage_baths', 'Cottage Baths dressing rooms', 3.5, 1, 'other'),
    ('1948_12', 1108, 1355, 'cottage_baths', 'Cottage Baths dressing rooms', 3.5, 1, 'other'),
    ('1948_12', 1136, 1359, 'cottage_baths', 'Cottage Baths suit room', 3.5, 1, 'other'),
    ('1948_12', 1240, 1317, 'cottage_baths', 'Cottage Baths office and store', 5, 1, 'hall'),
    ('1948_12', 1273, 1405, 'cottage_baths', 'Cottage Baths dressing rooms', 3.5, 1, 'other'),
    ('1948_12', 1274, 1351, 'cottage_baths', 'Cottage Baths dressing rooms', 3.5, 1, 'other'),
    ('1948_12', 1296, 1388, 'cottage_baths', 'Cottage Baths dressing rooms', 3.5, 1, 'other'),
    ('1948_12', 1297, 1370, 'cottage_baths', 'Cottage Baths dressing rooms', 3.5, 1, 'other'),
    ('1948_12', 1312, 1351, 'cottage_baths', 'Cottage Baths dressing rooms', 3.5, 1, 'other'),
    ('1948_12', 1312, 1405, 'cottage_baths', 'Cottage Baths dressing rooms', 3.5, 1, 'other'),
    ('1948_12', 1336, 1926, 'cottage_baths', 'Cottage Baths club house', 5, 1, 'hall'),
    ('1948_15', 493, 1342, 'neptune_court', 'Neptune Court (bungalow court, 39 units)', 6, 1, 'dwelling'),
    ('1948_15', 377, 1498, 'neptune_court', 'Neptune Court garages', 3.5, 1, 'other'),
    ('1948_15', 445, 1497, 'neptune_court', 'Neptune Court garages', 3.5, 1, 'other'),
    ('1948_15', 557, 1497, 'neptune_court', 'Neptune Court garages', 3.5, 1, 'other'),
    ('1948_15', 638, 1497, 'neptune_court', 'Neptune Court garages', 3.5, 1, 'other'),
]
WATER = [  # (sheet, site_id, name, px polygon)
    ('1897_11', 'green_arbor_baths', 'Green Arbor Baths open swimming tank', [(1328, 1653), (1390, 1653), (1390, 1818), (1328, 1818)]),
    ('1897_15', 'terrace_baths', 'The Terrace Baths enclosed swimming tank (bay water inside a planked platform)',
     [(370, 1497), (700, 1497), (718, 1515), (718, 1930), (700, 1945), (355, 1945), (330, 1925), (310, 1900), (310, 1700), (370, 1700)]),
    ('1948_11', 'sunny_cove_baths', 'Sunny Cove Baths concrete swimming tank', [(1060, 1638), (1180, 1638), (1180, 1830), (1060, 1830)]),
    ('1948_12', 'cottage_baths', 'Cottage Baths swimming tank', [(1088, 1462), (1195, 1462), (1195, 1650), (1088, 1650)]),
]
out = {'cx': CX, 'cy': CY, 'fit_residual_m': {k: v[1].round(2).tolist() for k, v in TF.items()}, 'buildings': [], 'water': [], 'shore_1897': None}
cache = {}
for k, (img, b, px) in SHEETS.items():
    a = np.asarray(Image.open(img).convert('RGB'))
    m = sbseg.masks(a)['yellow'].astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))
    cache[k] = [shape(g).simplify(1.2) for g, v in features.shapes(m, mask=m.astype(bool)) if shape(g).area >= 40]
for sheet, x, y, sid, name, h, st, use in KEEP:
    pt = shapely.Point(x, y)
    cands = [p for p in cache[sheet] if Polygon(p.exterior).distance(pt) < (6 if sheet != "1948_15" else 2)] or [p for p in cache[sheet] if p.distance(pt) < 45]
    if not cands:
        print('MISSING', sheet, x, y, name); continue
    p = min(cands, key=lambda p: Polygon(p.exterior).distance(pt) - 1e-7 * p.area)
    q = tp(sheet, Polygon(p.exterior, [h for h in p.interiors if Polygon(h).area > 400]))
    out['buildings'].append({'sheet': sheet, 'site_id': sid, 'name': name, 'height_m': h, 'storeys': st, 'use': use,
                             'area_m2': round(q.area, 1), 'coords': [[round(v, 2) for v in c] for c in q.exterior.coords],
                             'holes': [[[round(v, 2) for v in c] for c in h.coords] for h in q.interiors]})
for sheet, sid, name, poly in WATER:
    q = Polygon(T(sheet, poly))
    out['water'].append({'sheet': sheet, 'site_id': sid, 'name': name, 'area_m2': round(q.area, 1), 'coords': [[round(v, 2) for v in c] for c in q.exterior.coords]})
json.dump(out, open('/home/user/bay/data/manual/vanished_sites/traced/alameda_baths_sanborn.json', 'w'))
print(json.dumps(out['fit_residual_m']))
import collections
print(collections.Counter(b['site_id'] for b in out['buildings']))
for w in out['water']: print(w['name'], w['area_m2'])
