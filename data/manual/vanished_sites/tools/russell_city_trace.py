"""Russell City (Hayward): town extent from the urban tint of USGS San Leandro 1:24k 1959 (1958 photos), building
positions from the building symbols of the 1947 edition, dated by presence on the Hayward 1:62,500 sheets
(1915 ed., 1914 survey; 1942 ed., 1939 photos) and checked for removal on the 1968 photorevision.
-> /home/user/bay/data/manual/vanished_sites/traced/russell_city_topo.json"""
import numpy as np, cv2, json, vt, blobs, shapely
from shapely.geometry import Polygon, shape, Point
from rasterio import features
G = 'https://prd-tnm.s3.amazonaws.com/StagedProducts/Maps/HistoricalTopo/GeoTIFF/CA/'
cx, cy = -122.1336, 37.6475; H = 900; R = 1.0
i47 = np.load('cache/rcS1947.npy'); i59 = np.load('cache/rcS1959.npy'); i68 = np.load('cache/rcS1968.npy')
r, g, b = [i59[:, :, k].astype(int) for k in range(3)]
pink = ((r > 200) & (g < 200) & (g > 120) & (b < 210) & (r - g > 35)).astype(np.uint8)
pink = cv2.morphologyEx(pink, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8)); pink = cv2.morphologyEx(pink, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
big = max([shape(gm) for gm, v in features.shapes(pink, mask=pink.astype(bool))], key=lambda p: p.area)
T = lambda p: shapely.transform(p, lambda xy: np.column_stack([-H + xy[:, 0] * R, H - xy[:, 1] * R]))
town = T(big).simplify(2).buffer(0)
bl = blobs.blobs(i47, H, R, poly_xy=list(town.buffer(40).exterior.coords), open_m=4.0, min_m2=40, thresh=135)
# 1:62,500 renders for dating (the early 15' sheets may be offset: aligned to the 1947 sheet's ink by cross-correlation)
def ink(img, thr=120):
    r, g, b = [img[:, :, k].astype(int) for k in range(3)]
    return ((r < thr) & (g < thr) & (b < thr)).astype(np.float32)
ref = ink(i47)
eds = {}
for nm, f in [('1914', 'CA_Hayward_297660_1915_62500_geo.tif'), ('1939', 'CA_Hayward_465728_1942_62500_geo.tif')]:
    im = vt.render_topo(G + f, cx, cy, H, R)
    a = ink(im)
    A = cv2.GaussianBlur(a, (0, 0), 6); B = cv2.GaussianBlur(ref, (0, 0), 6)
    c = np.fft.fftshift(np.fft.irfft2(np.fft.rfft2(A - A.mean()) * np.conj(np.fft.rfft2(B - B.mean())), s=A.shape))
    n = A.shape[0]; ms = 250; w = c[n // 2 - ms:n // 2 + ms + 1, n // 2 - ms:n // 2 + ms + 1]
    j, i = np.unravel_index(np.argmax(w), w.shape); dx, dy = (i - ms) * R, -(j - ms) * R
    print(nm, 'shift of the 1:62,500 ink vs 1947 (m)', dx, dy)
    eds[nm] = (a, dx, dy)
def near_ink(a, x, y, rad):
    i0, j0 = int((x + H) / R), int((H - y) / R); k = int(rad / R)
    return float(a[max(0, j0 - k):j0 + k + 1, max(0, i0 - k):i0 + k + 1].mean())
out = {'cx': cx, 'cy': cy, 'town1958': [[round(v, 1) for v in c] for c in town.exterior.coords], 'shifts': {k: [v[1], v[2]] for k, v in eds.items()}, 'buildings': []}
a68 = ink(i68)
for bb in bl:
    p = Polygon(bb['poly'])
    x, y = bb['cx'], bb['cy']
    pres = {k: near_ink(a, x + dx, y + dy, 12) for k, (a, dx, dy) in eds.items()}
    p68 = near_ink(a68, x, y, 5)
    out['buildings'].append({'cx': round(float(x), 1), 'cy': round(float(y), 1), 'area_sym': round(float(bb['area'])), 'fill': round(float(bb['fill']), 2), 'w': round(float(bb['w']), 1), 'l': round(float(bb['l']), 1),
                             'coords': [[round(float(v), 1) for v in c] for c in p.exterior.coords], 'ink1914': round(pres['1914'], 2), 'ink1939': round(pres['1939'], 2),
                             'ink1968': round(p68, 2), 'in_town': town.buffer(15).contains(Point(x, y))})
json.dump(out, open('/home/user/bay/data/manual/vanished_sites/traced/russell_city_topo.json', 'w'))
bs = out['buildings']
print(len(bs), 'in town', sum(b['in_town'] for b in bs))
for k in ('ink1914', 'ink1939', 'ink1968'):
    v = np.array([b[k] for b in bs]); print(k, np.percentile(v, [10, 25, 50, 75, 90]).round(2))
