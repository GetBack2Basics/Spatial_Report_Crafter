#!/usr/bin/env python3
"""Generic local-GDAL (OSGeo4W) File Geodatabase / vector-source extractor.

Schema-free extraction of a pattern used in an offline case study of the
Spatial Report Crafter method (see
``docs/lessons_learned_offline_case_study.md``). Contains no project data,
field names, or layer names — only the mechanism for shelling out to
``ogr2ogr`` from a local OSGeo4W (or other GDAL) install to read a File
Geodatabase (or any other GDAL-supported source) and reproject/simplify it
to browser-friendly WGS84 GeoJSON, with no Python GDAL/Fiona bindings and no
``pip install`` required.

Typical use: call ``extract_layer`` once per feature class you want to
include in a report, then feed the resulting GeoJSON files into your report
builder alongside any other record-building logic.

Example
-------
>>> extract_layer(
...     source_path="MySource.gdb",
...     layer="MyLayer",
...     fields=["field_a", "field_b"],
...     out_path="output/MyLayer.geojson",
...     osgeo4w_root=r"C:\\OSGeo4W",
...     simplify=2,
... )
"""

import argparse
import os
import subprocess
from pathlib import Path


DEFAULT_OSGEO4W_ROOT = os.environ.get("OSGEO4W_ROOT", r"C:\OSGeo4W")


def extract_layer(
    source_path,
    layer,
    fields,
    out_path,
    osgeo4w_root=DEFAULT_OSGEO4W_ROOT,
    target_srs="EPSG:4326",
    simplify=None,
    coordinate_precision=6,
):
    """Export a single layer/feature class from ``source_path`` (a File
    Geodatabase or any other GDAL-supported vector source) to GeoJSON,
    using a local GDAL install rather than Python GDAL bindings.

    Parameters
    ----------
    source_path:
        Path to the source dataset (e.g. a ``.gdb`` folder, ``.gpkg`` file,
        or shapefile). Opened read-only; never modified.
    layer:
        Name of the layer/feature class within ``source_path`` to export.
    fields:
        List of field names to keep (``-select``); keeps the output small
        and avoids leaking unrelated source columns into the report.
    out_path:
        Destination ``.geojson`` file path; overwritten if it already
        exists.
    osgeo4w_root:
        Root folder of the local OSGeo4W (or equivalent) GDAL install. Set
        the ``OSGEO4W_ROOT`` environment variable, or pass this explicitly,
        if it isn't at the default ``C:\\OSGeo4W``.
    target_srs:
        Output coordinate reference system; ``EPSG:4326`` (WGS84) is the
        right choice for web map display.
    simplify:
        Optional geometry simplification tolerance, in the source CRS's
        units (or ``target_srs``'s, depending on GDAL version/behaviour) —
        a couple of metres is often enough to keep dense line/polygon
        layers responsive in-browser without visibly changing their shape
        at typical zoom levels. Leave ``None`` to skip simplification
        (recommended for point layers).
    coordinate_precision:
        Number of decimal places to keep in output coordinates, trading
        precision for file size.

    Raises
    ------
    RuntimeError
        If ``ogr2ogr`` exits non-zero or does not produce ``out_path``.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()

    args = [
        "ogr2ogr",
        "-f", "GeoJSON",
        "-t_srs", target_srs,
        "-select", ",".join(fields),
        "-lco", f"COORDINATE_PRECISION={coordinate_precision}",
    ]
    if simplify:
        args += ["-simplify", str(simplify)]
    args += [str(out_path), str(source_path), layer]

    # Route through the OSGeo4W environment batch scripts so `ogr2ogr` is
    # resolved from that install rather than requiring it on PATH globally,
    # and so no Python GDAL bindings/pip install is needed.
    quoted = " ".join(f'"{value}"' for value in args)
    command = (
        f"set OSGEO4W_ROOT={osgeo4w_root}"
        f' && call "{osgeo4w_root}\\bin\\o4w_env.bat" >nul'
        f' && call "{osgeo4w_root}\\bin\\gdal-dev-env.bat" >nul'
        f" && {quoted}"
    )
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0 or not out_path.exists():
        raise RuntimeError(
            f"ogr2ogr failed for layer '{layer}' (exit {result.returncode}).\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
    return out_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="Path to the source dataset (e.g. a .gdb folder)")
    parser.add_argument("layer", help="Layer/feature class name within the source dataset")
    parser.add_argument("--fields", required=True, help="Comma-separated list of fields to keep")
    parser.add_argument("--output", required=True, help="Destination .geojson path")
    parser.add_argument("--osgeo4w-root", default=DEFAULT_OSGEO4W_ROOT)
    parser.add_argument("--simplify", type=float, default=None)
    args = parser.parse_args()

    out_path = extract_layer(
        source_path=args.source,
        layer=args.layer,
        fields=[field.strip() for field in args.fields.split(",") if field.strip()],
        out_path=args.output,
        osgeo4w_root=args.osgeo4w_root,
        simplify=args.simplify,
    )
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
