"""Writer for the viewer's compact columnar binary format ("BAYT").

Layout: b"BAYT" | uint32 header_len | JSON header (space-padded to 8) | columns,
each 8-byte aligned. See viewer/src/data/columnar.ts for the reader.
Everything is gzip-compressed (the viewer decompresses with DecompressionStream).

Column names ending in "|shuffle" are byte-shuffled before writing: all first
bytes of every element, then all second bytes, ... (as in Blosc/HDF5). Small
integers (delta-coded coordinates, counts) then gzip far better. The reader
un-shuffles and strips the suffix.
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path

import numpy as np

DTYPES = {np.float32: "f32", np.float64: "f64", np.uint32: "u32", np.int32: "i32",
          np.uint16: "u16", np.int16: "i16", np.uint8: "u8"}


def write_columnar(path: Path, columns: dict[str, np.ndarray], origin=(0.0, 0.0),
                   counts: dict | None = None, meta: dict | None = None):
    descs, blobs, offset = [], [], 0
    for name, arr in columns.items():
        arr = np.ascontiguousarray(arr)
        dt = DTYPES.get(arr.dtype.type)
        if dt is None:
            raise TypeError(f"{name}: unsupported dtype {arr.dtype}")
        le = arr.astype(arr.dtype.newbyteorder("<"), copy=False)
        shuffle = name.endswith("|shuffle")
        if shuffle:
            name = name[: -len("|shuffle")]
            b = le.view(np.uint8).reshape(-1, le.itemsize).T.copy().tobytes()
        else:
            b = le.tobytes()
        descs.append({"name": name, "dtype": dt, "length": int(arr.size), "offset": offset, "shuffle": shuffle})
        pad = (-len(b)) % 8
        blobs.append(b + b"\0" * pad)
        offset += len(b) + pad
    header = {"version": 1, "origin": [float(origin[0]), float(origin[1])], "counts": counts or {},
              "meta": meta or {}, "columns": descs}
    hj = json.dumps(header, separators=(",", ":")).encode()
    hj += b" " * ((-len(hj)) % 8)
    raw = b"BAYT" + np.uint32(len(hj)).tobytes() + hj + b"".join(blobs)
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wb", compresslevel=9) as f:
        f.write(raw)
    return len(raw), path.stat().st_size
