"""Oaks Park (Oakland Base Ball Association grounds), Emeryville, from the Sanborn map Oakland 1911-Oct 1950 vol. 3
sheet 317 ('from plans Feb 1913'), fitted by an affine transform to four street crossings (water-main crossings on the
sheet; today's centrelines, Watts St extended north of Park Ave to 45th St). Stands / bleachers hand-traced (px).
-> traced/oaks_park_sanborn.json (frame of the emeryville_racetrack site)."""
import json, numpy as np, shapely
from shapely.geometry import Polygon
import sbref
CX, CY = -122.2870, 37.8360
px = np.array([(1545, 208), (1548, 1230), (480, 215), (478, 1230)], float)
loc = np.array([(589.1, -404.4), (387.7, -457.5), (530.2, -197.3), (335.0, -250.0)])
f, M, res = sbref.fit_affine(px * [1, -1], loc)
T = lambda pts: f(np.asarray(pts, float) * [1, -1])
P = lambda pts: [[round(v, 2) for v in c] for c in T(pts)]
out = {'cx': CX, 'cy': CY, 'fit_residual_m': res.round(2).tolist(), 'parts': [
    {'name': 'Oaks Park grounds (Oakland Base Ball Association)', 'kind': 'grounds', 'coords': P([(815, 470), (1495, 470), (1495, 1195), (815, 1195)])},
    {'name': 'Oaks Park grandstand (roofed, wood)', 'kind': 'grandstand', 'height_m': 12, 'coords': P([(820, 560), (860, 480), (1155, 480), (1155, 562), (900, 562), (900, 900), (820, 900)])},
    {'name': 'Oaks Park bleachers (first-base side, San Pablo Ave)', 'kind': 'bleachers', 'height_m': 6, 'coords': P([(1160, 485), (1430, 485), (1480, 560), (1480, 640), (1400, 600), (1160, 560)])},
    {'name': 'Oaks Park bleachers (left field)', 'kind': 'bleachers', 'height_m': 6, 'coords': P([(818, 905), (900, 885), (965, 1185), (900, 1195)])},
    {'name': 'Oaks Park bleachers (Watts St)', 'kind': 'bleachers', 'height_m': 6, 'coords': P([(940, 1115), (1370, 1105), (1370, 1195), (960, 1195)])},
    {'name': 'Oaks Park bleachers (Park Ave corner)', 'kind': 'bleachers', 'height_m': 6, 'coords': P([(1370, 1105), (1450, 1030), (1490, 1010), (1490, 1180), (1370, 1195)])},
]}
json.dump(out, open('/home/user/bay/data/manual/vanished_sites/traced/oaks_park_sanborn.json', 'w'))
print(res.round(2), [round(Polygon(p['coords']).area) for p in out['parts']])
