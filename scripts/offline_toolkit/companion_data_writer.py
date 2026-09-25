"""Generic companion ``<script src>`` data-file writer for offline "Map-in-a-
Box" reports, with optional largest-first "core" + spatial-chunk splitting
for very large payloads.

This is a schema-free, generalised extraction of a pattern used in an
offline case study of the Spatial Report Crafter method (see
``docs/lessons_learned_offline_case_study.md``). It contains no project
data, field names, or schema — only the mechanism.

Why a companion ``<script src="...">`` file rather than ``fetch()``/XHR of a
``.json`` file: Chromium-based browsers commonly block ``fetch``/XHR reads
of local files opened via a bare ``file://`` URL (CORS), which would break
an "open the HTML file directly, no server required" design. A classic
``<script src="...">`` tag has no such restriction and works identically
whether the report is opened from disk or served over HTTP.

Splitting the payload out of the HTML keeps the .html file itself small
(fast to open in an editor/diff/version control) even though the browser
still ultimately downloads the same number of bytes to render the report.

Why chunking on top of that: very large record sets (tens of thousands of
features and up) can be slow to download/parse before anything can be
shown. When the serialised payload exceeds ``chunk_threshold_bytes``,
``write_companion_data_js`` instead writes only the largest ``core_count``
records (ranked by a caller-supplied ``size_key``, e.g. a length/area/score
field — records without a usable size sort last) into the main companion
file, plus the remainder split into ``<name>_data_chunkN.js`` files of up to
``chunk_size`` records each. Each chunk file also records a bounding box
(derived from a caller-supplied ``bbox_key`` or longitude/latitude fields)
so a report page can load only the chunks that intersect the current
viewport as the reader pans/zooms in, rather than downloading everything up
front. See ``client-side chunk loader`` notes in
``docs/lessons_learned_offline_case_study.md`` for the companion browser-side
logic.

Example
-------
>>> write_companion_data_js(
...     {"records": my_records, "generated": "2026-01-01"},
...     "output/My_Report.html",
...     size_key=lambda record: record.get("size"),
...     bbox_key=lambda record: record.get("bbox"),
... )
'My_Report_data.js'
"""

import json
from pathlib import Path


def companion_data_js_name(html_path):
    """Return the companion data filename for a given report HTML path.

    e.g. ``My_Report.html`` -> ``My_Report_data.js``
    """
    return f"{Path(html_path).stem}_data.js"


def _dump_json(data):
    # Escape "</" so a literal "</script>" inside a JSON string can't
    # prematurely close the enclosing <script> tag.
    return json.dumps(data, ensure_ascii=True, separators=(",", ":")).replace("</", "<" + chr(92) + "/")


def _default_size_key(record):
    size = record.get("size") if isinstance(record, dict) else None
    return size if isinstance(size, (int, float)) else -1


def _default_bbox_key(record):
    if not isinstance(record, dict):
        return None
    bbox = record.get("bbox")
    if bbox:
        return bbox
    geometry = record.get("geometry") or {}
    coords = geometry.get("coordinates")
    if isinstance(coords, (list, tuple)) and len(coords) >= 2 and isinstance(coords[0], (int, float)):
        lon, lat = coords[0], coords[1]
        return [lon, lat, lon, lat]
    return None


def _morton_key(lon, lat, min_lon=-180.0, max_lon=180.0, min_lat=-90.0, max_lat=90.0, bits=16):
    """Interleave quantised longitude/latitude bits (a Z-order/Morton curve)
    so that sorting by this key groups nearby records together, giving each
    chunk of otherwise-unranked records (e.g. records with no usable "size")
    a reasonably tight bounding box instead of one that spans the whole
    dataset. Narrow ``min_lon``/``max_lon``/``min_lat``/``max_lat`` to your
    dataset's actual extent for better precision at a given ``bits``."""

    def quantize(value, lo, hi):
        value = max(lo, min(hi, value))
        return int((value - lo) / (hi - lo) * ((1 << bits) - 1))

    x = quantize(lon, min_lon, max_lon)
    y = quantize(lat, min_lat, max_lat)
    result = 0
    for i in range(bits):
        result |= ((x >> i) & 1) << (2 * i)
        result |= ((y >> i) & 1) << (2 * i + 1)
    return result


def _merge_bbox(a, b):
    if a is None:
        return b
    if b is None:
        return a
    return [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]


def write_companion_data_js(
    data,
    html_path,
    var_name="REPORT_DATA",
    records_key="records",
    chunk_threshold_bytes=5_000_000,
    core_count=500,
    chunk_size=4000,
    size_key=None,
    bbox_key=None,
    extent=None,
):
    """Write ``data`` as ``window.<var_name> = {...};`` next to ``html_path``.

    Parameters
    ----------
    data:
        A JSON-serialisable dict. ``data[records_key]`` (if present and a
        list) is the record set eligible for chunking.
    html_path:
        Path to the report HTML file; the companion file is written
        alongside it.
    size_key:
        Optional ``callable(record) -> float`` used to rank records
        largest-first for the "core" batch. Defaults to reading a numeric
        ``record["size"]`` field, with non-numeric/missing sizes ranked
        last.
    bbox_key:
        Optional ``callable(record) -> [minLon, minLat, maxLon, maxLat] |
        None`` used to compute each chunk's bounding box. Defaults to
        reading a ``record["bbox"]`` field, falling back to a point
        bounding box from ``record["geometry"]["coordinates"]``.
    extent:
        Optional ``(min_lon, max_lon, min_lat, max_lat)`` tuple narrowing
        the Morton-key quantisation range to your dataset's extent, for
        better spatial grouping precision.

    If the serialised payload is larger than ``chunk_threshold_bytes`` and
    ``data[records_key]`` is a list, only the ``core_count`` largest records
    (by ``size_key``) are kept in the main companion file; the rest are
    split into ``<name>_data_chunkN.js`` files (with a bounding box each)
    referenced from ``data["chunkManifest"]`` and ``data["recordsTotal"]``,
    for the report page to load on demand as the reader zooms/pans into
    each chunk's area. Reports whose payload stays under the threshold are
    unaffected and behave as a single companion file, same as before.

    Returns the companion file's name (not full path) for use in a
    ``<script src="...">`` tag in the same folder as the HTML report.
    """
    size_key = size_key or _default_size_key
    bbox_key = bbox_key or _default_bbox_key
    html_path = Path(html_path)
    js_name = companion_data_js_name(html_path)
    js_path = html_path.parent / js_name
    records = data.get(records_key)

    if not isinstance(records, list) or len(records) <= core_count:
        js_path.write_text(f"window.{var_name} = {_dump_json(data)};\n", encoding="utf-8")
        return js_name

    full_json = _dump_json(data)
    if len(full_json.encode("utf-8")) <= chunk_threshold_bytes:
        js_path.write_text(f"window.{var_name} = {full_json};\n", encoding="utf-8")
        return js_name

    def spatial_sort_key(record):
        bbox = bbox_key(record)
        if not bbox:
            return -1
        lon = (bbox[0] + bbox[2]) / 2
        lat = (bbox[1] + bbox[3]) / 2
        if extent:
            min_lon, max_lon, min_lat, max_lat = extent
            return _morton_key(lon, lat, min_lon, max_lon, min_lat, max_lat)
        return _morton_key(lon, lat)

    # Chunking: largest-first core batch, remainder split into
    # viewport-loadable chunks (spatially sorted so each chunk's bbox stays
    # reasonably tight for records with no explicit "size").
    ordered = sorted(records, key=size_key, reverse=True)
    core = ordered[:core_count]
    rest = ordered[core_count:]
    rest.sort(key=spatial_sort_key)

    manifest = []
    for index in range(0, len(rest), chunk_size):
        chunk = rest[index : index + chunk_size]
        bbox = None
        for record in chunk:
            bbox = _merge_bbox(bbox, bbox_key(record))
        chunk_index = len(manifest)
        chunk_filename = f"{html_path.stem}_data_chunk{chunk_index}.js"
        chunk_json = _dump_json(chunk)
        (html_path.parent / chunk_filename).write_text(
            f"window.REPORT_DATA_CHUNKS=window.REPORT_DATA_CHUNKS||{{}};"
            f"window.REPORT_DATA_CHUNKS[{chunk_index}]={chunk_json};\n",
            encoding="utf-8",
        )
        manifest.append({"file": chunk_filename, "count": len(chunk), "bbox": bbox})

    data[records_key] = core
    data["recordsTotal"] = len(records)
    data["chunkManifest"] = manifest

    js_path.write_text(f"window.{var_name} = {_dump_json(data)};\n", encoding="utf-8")
    return js_name
