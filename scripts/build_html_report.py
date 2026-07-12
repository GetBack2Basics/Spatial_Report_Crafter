#!/usr/bin/env python3
"""
build_html_report.py — Generate an HTML reconciliation review report for the client.

Reads Critical_Review_Assets.gpkg and produces a self-contained HTML report with:
  - Executive summary with counts and risk breakdown
  - Per-domain sections (Water Mains, Water Meters, Sewer Manholes, Sewer Mains)
  - Static map images (matplotlib) showing new assets, drift points, displacement vectors
  - Interactive Leaflet maps (folium) embedded via iframe
  - Sortable/filterable data tables
  - "Items Requiring Client Review" section highlighting issues needing decisions

Usage:
    cd /media/george-corea/GIS/Projects/014_Reflect Project/Working
    source scripts/.venv/bin/activate          # or use full path to python
    python scripts/build_html_report.py
    python scripts/build_html_report.py --gpkg " Pending Data/Critical_Review_Assets.gpkg"

Generic report usage:
    from pathlib import Path
    from scripts.build_html_report import generate_html_report, load_domain_data_from_layers

    report = generate_html_report(
        domains_data=...,
        output_html_path=Path("Output/report.html"),
    )
"""

import argparse
import base64
import io
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import fiona
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import folium
import folium.plugins
import pandas as pd
from jinja2 import Template

# ─── Paths ───────────────────────────────────────────────────────────────────

WORKING_DIR = Path(__file__).resolve().parent.parent
DEFAULT_GPKG = WORKING_DIR / "Pending Data" / "Critical_Review_Assets.gpkg"
SOURCE_GPKG = WORKING_DIR / "qscf_process" / "Reflect_Sources.gpkg"
OUT_HTML = WORKING_DIR / "Reconciliation_Review.html"
MAPS_DIR = WORKING_DIR / "Reconciliation_Review_maps"
DEFAULT_DOMAIN_CONFIG = {
    "water_mains": {
        "label": "Water Mains",
        "icon": "💧",
        "color": "#2E86C1",
        "high_color": "#C0392B",
        "med_color": "#E67E22",
        "low_color": "#27AE60",
    },
    "water_meters": {
        "label": "Water Meters",
        "icon": "🔢",
        "color": "#2874A6",
        "high_color": "#C0392B",
        "med_color": "#E67E22",
        "low_color": "#27AE60",
    },
    "sewer_manholes": {
        "label": "Sewer Manholes",
        "icon": "🕳️",
        "color": "#7D3C98",
        "high_color": "#C0392B",
        "med_color": "#E67E22",
        "low_color": "#27AE60",
    },
    "sewer_mains": {
        "label": "Sewer Mains",
        "icon": "🚰",
        "color": "#6C3483",
        "high_color": "#C0392B",
        "med_color": "#E67E22",
        "low_color": "#27AE60",
    },
    "facilities": {
        "label": "Facilities",
        "icon": "🏗️",
        "color": "#1F618D",
        "high_color": "#C0392B",
        "med_color": "#E67E22",
        "low_color": "#27AE60",
    },
    "footpaths": {
        "label": "Footpaths",
        "icon": "🛤️",
        "color": "#1F618D",
        "high_color": "#C0392B",
        "med_color": "#E67E22",
        "low_color": "#27AE60",
    },
    "gridsgate": {
        "label": "Gridsgate",
        "icon": "🚪",
        "color": "#1F618D",
        "high_color": "#C0392B",
        "med_color": "#E67E22",
        "low_color": "#27AE60",
    },
    "localroads": {
        "label": "Local Roads",
        "icon": "🛣️",
        "color": "#1F618D",
        "high_color": "#C0392B",
        "med_color": "#E67E22",
        "low_color": "#27AE60",
    },
    "openspaces": {
        "label": "Open Spaces",
        "icon": "🌳",
        "color": "#1F618D",
        "high_color": "#C0392B",
        "med_color": "#E67E22",
        "low_color": "#27AE60",
    },
    "rmpc_1314": {
        "label": "RMPC 1314",
        "icon": "📋",
        "color": "#1F618D",
        "high_color": "#C0392B",
        "med_color": "#E67E22",
        "low_color": "#27AE60",
    },
    "reflect": {
        "label": "Reflect",
        "icon": "🔄",
        "color": "#1F618D",
        "high_color": "#C0392B",
        "med_color": "#E67E22",
        "low_color": "#27AE60",
    },
    "smt": {
        "label": "SMT",
        "icon": "⚙️",
        "color": "#1F618D",
        "high_color": "#C0392B",
        "med_color": "#E67E22",
        "low_color": "#27AE60",
    },
}

RISK_COLORS = {
    "New Asset": "#3498DB",
    "Low Risk (<=5m)": "#27AE60",
    "Medium Risk (5-10m)": "#E67E22",
    "High Risk (>10m)": "#C0392B",
}

# ─── Data loading ────────────────────────────────────────────────────────────

def load_review_data(gpkg_path):
    layers = {}
    for layer_name in fiona.listlayers(str(gpkg_path)):
        gdf = gpd.read_file(gpkg_path, layer=layer_name)
        layers[layer_name] = gdf
    return layers


def categorize_layers(layers, domain_config=None):
    domains = {}
    cfg = domain_config or DEFAULT_DOMAIN_CONFIG
    for dk in cfg:
        domains[dk] = {"new": None, "drift": None, "vectors": None}

    for name, gdf in layers.items():
        name_lower = name.lower()
        for dk in cfg:
            tag = dk.replace("_", "")
            if tag in name_lower.replace("_", ""):
                if "new_review" in name_lower:
                    domains[dk]["new"] = gdf
                elif "drift_review" in name_lower:
                    domains[dk]["drift"] = gdf
                elif "displacement_vector" in name_lower:
                    domains[dk]["vectors"] = gdf
                break

    return domains


def categorize_source_layers(layers):
    source_map = {
        "facilities": "facilities",
        "footpaths": "footpaths",
        "gridsgate": "gridsgate",
        "localroads": "localroads",
        "openspaces": "openspaces",
        "rmpc_1314": "rmpc_1314",
        "reflect": "reflect",
        "smt": "smt",
    }
    result = {}
    for name, gdf in layers.items():
        key = name.lower()
        if key in source_map:
            dk = source_map[key]
            result[dk] = {"new": gdf, "drift": None, "vectors": None}
    return result


def load_domain_data_from_layers(layers, domain_config=None, source_layers=None):
    domains = categorize_layers(layers, domain_config=domain_config)

    if source_layers is not None:
        source_domains = categorize_source_layers(source_layers)
        for dk, data in source_domains.items():
            if dk in domains:
                if domains[dk]["new"] is None or domains[dk]["new"].empty:
                    domains[dk]["new"] = data["new"]
            else:
                domains[dk] = data
    return domains


# ─── Plot helpers ────────────────────────────────────────────────────────────

BASEMAP_METADATA = {
    "OpenStreetMap": "https://www.openstreetmap.org/about",
    "Light": "https://www.openstreetmap.org/about",
    "QLD Topo": "https://spatial-gis.information.qld.gov.au/arcgis/rest/services/Basemaps/QldMap_Topo/MapServer/WMTS/1.0.0/WMTSCapabilities.xml",
    "Satellite": "https://spatial-img.information.qld.gov.au/arcgis/services/Basemaps/LatestSatelliteWOS_AllUsers/ImageServer/WMSServer?request=GetCapabilities&service=WMS",
}

BASEMAPS = [
    {
        "name": "OpenStreetMap",
        "url": "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        "attr": "&copy; <a href='https://www.openstreetmap.org/about'>OpenStreetMap</a> contributors",
        "options": {"maxZoom": 19},
        "type": "xyz",
        "default": False,
    },
    {
        "name": "Light",
        "url": "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        "attr": "&copy; OpenStreetMap contributors &copy; <a href='https://carto.com/'>CARTO</a>",
        "options": {"subdomains": "abcd", "maxZoom": 19},
        "type": "xyz",
        "default": False,
    },
    {
        "name": "QLD Topo",
        "url": "https://spatial-gis.information.qld.gov.au/arcgis/rest/services/Basemaps/QldMap_Topo/MapServer/WMTS/tile/1.0.0/QldMap_Topo/default/GoogleMapsCompatible/{z}/{y}/{x}.png",
        "attr": "Queensland Government - QLD Spatial",
        "options": {"maxZoom": 18},
        "type": "xyz",
        "default": True,
    },
    {
        "name": "Satellite",
        "url": "https://spatial-img.information.qld.gov.au/arcgis/services/Basemaps/LatestSatelliteWOS_AllUsers/ImageServer/WMSServer",
        "options": {"layers": "LatestSatelliteWOS_AllUsers", "format": "image/png", "transparent": True, "version": "1.1.1"},
        "attr": "Queensland Government - QLD Spatial",
        "type": "wms",
        "default": False,
    },
]


def add_info_to_layer_control(html_path, label_url_map):
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    if "</body>" not in html:
        return

    # Patch the existing folium baselayer controls to add (i) metadata links.
    for label, url in label_url_map.items():
        old = f'"{label}" : '
        new = f'"{label} " : '
        html = html.replace(old, new)
    html = html.replace('</body>', """<style>
.basemap-meta { text-decoration:none; color:#1a73e8; font-size:11px; margin-left:4px; }
.leaflet-tooltip { user-select: text; -webkit-user-select: text; }
.copy-btn { margin-top:6px; padding:4px 8px; cursor:pointer; }
</style>
<script>
function copyPopup(btn){
  var text = btn.parentElement.querySelector('div').innerText;
  var ta = document.createElement('textarea');
  ta.value = text;
  document.body.appendChild(ta);
  ta.select();
  try { document.execCommand('copy'); btn.textContent = 'Copied'; } catch(e){}
  document.body.removeChild(ta);
  setTimeout(function(){ btn.textContent = 'Copy'; }, 1500);
}
(function(){
  function getMap(){
    var el = document.querySelector('.folium-map');
    if (!el) return null;
    return el._leaflet_map || null;
  }
  function walk(root){
    var labels = root.querySelectorAll('.leaflet-control-layers-base label');
    labels.forEach(function(el){
      var span = el.querySelector('span') || el;
      var txt = (span.textContent || '').trim();
      if (span.querySelector('.basemap-meta')) return;
      var urls = """ + repr(label_url_map) + """;
      if (urls[txt]) {
        var a = document.createElement('a');
        a.className = 'basemap-meta';
        a.href = urls[txt];
        a.target = '_blank';
        a.textContent = '(i)';
        span.appendChild(document.createTextNode(' '));
        span.appendChild(a);
      }
    });
  }
  function addCustomWmsForm(){
    if (document.getElementById('custom-wms-root')) return;
    var root = document.createElement('div');
    root.id = 'custom-wms-root';
    root.style.cssText = 'margin-top:6px;';
    root.innerHTML = '<b>Custom WMS</b><br>' +
      '<input id="cw-url" placeholder="WMS URL" style="width:220px;margin:2px 0;"/><br>' +
      '<input id="cw-layer" placeholder="Layers" style="width:220px;margin:2px 0;"/><br>' +
      '<button id="cw-add">Add</button> <button id="cw-cancel">Cancel</button>';
    var ctrl = document.querySelector('.leaflet-top.leaflet-right');
    if (!ctrl) return;
    ctrl.appendChild(root);
    document.getElementById('cw-cancel').addEventListener('click', function(){ root.style.display='none'; });
    document.getElementById('cw-add').addEventListener('click', function(){
      var url = document.getElementById('cw-url').value.trim();
      var layer = document.getElementById('cw-layer').value.trim();
      if (!url || !layer) return;
      var map = getMap(); if (!map) return;
      var wms = L.tileLayer.wms(url, {
        layers: layer,
        format: 'image/png',
        transparent: true,
        version: '1.1.1',
        attribution: 'Custom WMS'
      }).addTo(map);
      var label = document.createElement('label');
      label.style.display='block';
      label.innerHTML = '<input type="checkbox" class="leaflet-control-layers-selector" checked> Custom WMS: ' + layer;
      var inp = label.querySelector('input');
      inp.addEventListener('change', function(){
        if (this.checked) wms.addTo(map); else map.removeLayer(wms);
      });
      var base = document.querySelector('.leaflet-control-layers-overlays');
      if (base) base.appendChild(label);
      root.style.display='none';
      document.getElementById('cw-url').value = '';
      document.getElementById('cw-layer').value = '';
    });
  }
  window.addEventListener('load', function(){
    walk(document);
    setTimeout(walk, 250);
    setTimeout(addCustomWmsForm, 150);
    setTimeout(addCustomWmsForm, 400);
  });
})();
</script>
</body>""")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)


def plot_map(gdf_new, gdf_drift, gdf_vectors, domain_key, out_path, basemap=False):
    """Generate a static matplotlib map image for a domain."""
    cfg = DEFAULT_DOMAIN_CONFIG[domain_key]
    fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    ax.set_title(f"{cfg['icon']} {cfg['label']} — Review Items", fontsize=13, fontweight="bold", color=cfg["color"])

    legend_handles = []

    # Reproject to EPSG:4326 for basemap compatibility if needed
    plot_new = (gdf_new.to_crs(epsg=4326) if gdf_new is not None and not gdf_new.empty else None)
    plot_drift = (gdf_drift.to_crs(epsg=4326) if gdf_drift is not None and not gdf_drift.empty else None)
    plot_vectors = (gdf_vectors.to_crs(epsg=4326) if gdf_vectors is not None and not gdf_vectors.empty else None)

    # Draw displacement vectors first (behind points)
    if plot_vectors is not None:
        plot_vectors.plot(ax=ax, color="#E74C3C", linewidth=1.5, linestyle="--", alpha=0.7, zorder=2)
        legend_handles.append(mpatches.Patch(color="#E74C3C", label="Displacement Vector"))

    # Draw drift points coloured by risk
    if plot_drift is not None:
        for risk_label, color in RISK_COLORS.items():
            subset = plot_drift[plot_drift["Risk_Level"] == risk_label] if "Risk_Level" in plot_drift.columns else gpd.GeoDataFrame()
            if not subset.empty:
                subset.plot(ax=ax, color=color, markersize=50, zorder=3, edgecolor="white", linewidth=0.5)
                legend_handles.append(plt.scatter([], [], c=color, s=50, edgecolors="white", linewidths=0.5, label=risk_label))

        if domain_key == "water_meters" and "duplicate" in getattr(plot_drift, "columns", []):
            dup_mask = plot_drift["duplicate"].fillna(0) > 0
            dup_gdf = plot_drift[dup_mask]
            if not dup_gdf.empty:
                dup_gdf.plot(ax=ax, color="#FF4500", markersize=70, marker="X", zorder=5, edgecolor="black", linewidth=0.8)
                legend_handles.append(plt.scatter([], [], c="#FF4500", s=70, marker="X", edgecolors="black", linewidths=0.8, label="Duplicate Water Meter"))

    # Draw new asset points
    if plot_new is not None:
        plot_new.plot(ax=ax, color="#3498DB", markersize=60, marker="D", zorder=4, edgecolor="white", linewidth=0.5)
        legend_handles.append(plt.scatter([], [], c="#3498DB", s=60, marker="D", edgecolors="white", linewidths=0.5, label="New Asset"))

    if legend_handles:
        ax.legend(handles=legend_handles, loc="upper right", fontsize=8, framealpha=0.9)

    # QLD Topo at ~65% opacity so GIS data remains legible
    try:
        basemap_rgba = basemap_rgb.convert("RGBA")
        data = np.array(basemap_rgba)
        data[..., 3] = 163
        basemap_rgba = Image.fromarray(data, "RGBA")
        ax.set_axis_off()
        ax.imshow(np.array(basemap_rgba), extent=w, zorder=0)
    except Exception:
        ax.set_axis_off()

    fig.tight_layout()
    fig.savefig(
        str(out_path),
        dpi=150,
        bbox_inches="tight",
        facecolor="white",
        pad_inches=0.05,
    )
    plt.close(fig)


def _build_row_tooltip(row, domain_key=None, risk_label=None, drift_m=None, limit=None):
    tooltip_parts = []
    asset_id = None
    for id_col in ["Asset_ID", "asset_id"]:
        if id_col in row.index:
            asset_id = row.get(id_col)
            break
    if risk_label:
        tooltip_parts.append(f"<b>Asset:</b> {asset_id}")
        tooltip_parts.append(f"<b>Risk:</b> {risk_label}")
    elif asset_id:
        tooltip_parts.append(f"<b>Asset:</b> {asset_id}")
    if drift_m is not None:
        tooltip_parts.append(f"<b>Drift:</b> {drift_m}m")
    if domain_key:
        cfg = DOMAIN_CONFIG.get(domain_key, {})
        label = cfg.get("label", domain_key)
        tooltip_parts.append(f"<b>Domain:</b> {label}")

    skip_fields = {"geometry", "geometry_type"}
    if limit is not None:
        shown = 0
        for col, val in row.items():
            if shown >= limit:
                break
            if col in skip_fields:
                continue
            if pd.isna(val):
                continue
            text = str(val).strip()
            if not text or text.lower() == "nan":
                continue
            if text.lower() in ("0", "false"):
                continue
            header = str(col).replace("_", " ").title()
            tooltip_parts.append(f"<b>{header}:</b> {text}")
            shown += 1
    else:
        for col, val in row.items():
            if col in skip_fields:
                continue
            if pd.isna(val):
                continue
            text = str(val).strip()
            if not text or text.lower() == "nan":
                continue
            if text.lower() in ("0", "false"):
                continue
            header = str(col).replace("_", " ").title()
            tooltip_parts.append(f"<b>{header}:</b> {text}")
    return "<br>".join(tooltip_parts)


def build_interactive_map(gdf_new, gdf_drift, gdf_vectors, domain_key, out_path):
    """Generate an interactive Folium map and save as HTML for iframe embedding."""
    cfg = DEFAULT_DOMAIN_CONFIG[domain_key]

    all_gdfs = []
    for g in [gdf_new, gdf_drift, gdf_vectors]:
        if g is not None and not g.empty:
            all_gdfs.append(g.to_crs(epsg=4326))
    if not all_gdfs:
        return

    combined = pd.concat(all_gdfs, ignore_index=True)
    center = combined.geometry.centroid
    lat = center.y.mean()
    lon = center.x.mean()

    m = folium.Map(location=[lat, lon], zoom_start=16, tiles=None)
    folium.TileLayer("OpenStreetMap", name="OpenStreetMap", show=False).add_to(m)
    folium.TileLayer("CartoDB positron", name="Light", show=False).add_to(m)
    folium.TileLayer(
        tiles="https://spatial-gis.information.qld.gov.au/arcgis/rest/services/Basemaps/QldMap_Topo/MapServer/WMTS/tile/1.0.0/QldMap_Topo/default/GoogleMapsCompatible/{z}/{y}/{x}.png",
        attr="Queensland Government - QLD Spatial",
        name="QLD Topo",
        overlay=False,
        control=True,
        show=True,
    ).add_to(m)
    folium.WmsTileLayer(
        url="https://spatial-img.information.qld.gov.au/arcgis/services/Basemaps/LatestSatelliteWOS_AllUsers/ImageServer/WMSServer",
        layers="LatestSatelliteWOS_AllUsers",
        fmt="image/png",
        transparent=True,
        version="1.1.1",
        attr="Queensland Government - QLD Spatial",
        name="Satellite",
        overlay=False,
        control=True,
        show=False,
    ).add_to(m)

    feature_groups = {
        "New Assets": folium.FeatureGroup(name="New Assets"),
        "High Risk Drift (>10m)": folium.FeatureGroup(name="High Risk Drift (>10m)"),
        "Medium Risk Drift (5-10m)": folium.FeatureGroup(name="Medium Risk Drift (5-10m)"),
        "Low Risk Drift (≤5m)": folium.FeatureGroup(name="Low Risk Drift (≤5m)"),
        "Displacement Vectors": folium.FeatureGroup(name="Displacement Vectors"),
    }
    dup_fg = None
    if domain_key == "water_meters":
        dup_fg = folium.FeatureGroup(name="Duplicate Water Meters", show=True)
        feature_groups["Duplicate Water Meters"] = dup_fg

    if gdf_vectors is not None and not gdf_vectors.empty:
        gdf_v = gdf_vectors.to_crs(epsg=4326)
        for _, row in gdf_v.iterrows():
            if row.geometry is None:
                continue
            coords = [(y, x) for x, y in row.geometry.coords]
            html = _build_row_tooltip(row, domain_key=domain_key)
            folium.PolyLine(
                coords,
                color="#E74C3C",
                weight=2,
                dash_array="5",
                opacity=0.7,
                popup=folium.Popup(f'<div class="attr-popup"><button class="copy-btn" onclick="copyPopup(this)">Copy</button><div>{html}</div></div>', max_width=350),
                tooltip=folium.Tooltip(_build_row_tooltip(row, domain_key=domain_key, limit=3), sticky=True),
            ).add_to(feature_groups["Displacement Vectors"])

    if gdf_drift is not None and not gdf_drift.empty:
        gdf_d = gdf_drift.to_crs(epsg=4326)
        risk_col = "Risk_Level" if "Risk_Level" in gdf_d.columns else None
        drift_col = "Drift_m" if "Drift_m" in gdf_d.columns else None

        for _, row in gdf_d.iterrows():
            pt = row.geometry
            if pt is None:
                continue

            risk = row.get(risk_col, "") if risk_col else ""
            drift = row.get(drift_col, "") if drift_col else ""

            dup_val = row.get("duplicate") if domain_key == "water_meters" and "duplicate" in row.index else None
            dup_num = None
            if pd.notna(dup_val) and str(dup_val).strip() not in ("", "nan"):
                try:
                    dup_num = int(float(str(dup_val).strip()))
                except Exception:
                    dup_num = None

            if domain_key == "water_meters" and dup_num is not None and dup_num > 0:
                color, group, radius = "#ADD8E6", dup_fg, 8
            elif "High" in str(risk):
                color, group = "#C0392B", feature_groups["High Risk Drift (>10m)"]
                radius = 8
            elif "Medium" in str(risk):
                color, group = "#E67E22", feature_groups["Medium Risk Drift (5-10m)"]
                radius = 7
            else:
                color, group = "#27AE60", feature_groups["Low Risk Drift (≤5m)"]
                radius = 6

            html = _build_row_tooltip(row, domain_key=domain_key, risk_label=risk, drift_m=drift)
            folium.CircleMarker(
                location=[pt.y, pt.x],
                radius=radius,
                color=True,
                fill=True,
                fill_color=color,
                fill_opacity=0.8,
                popup=folium.Popup(f'<div class="attr-popup"><button class="copy-btn" onclick="copyPopup(this)">Copy</button><div>{html}</div></div>', max_width=350),
                tooltip=folium.Tooltip(_build_row_tooltip(row, domain_key=domain_key, risk_label=risk, drift_m=drift, limit=3), sticky=True),
            ).add_to(group)

    if gdf_new is not None and not gdf_new.empty:
        gdf_n = gdf_new.to_crs(epsg=4326)
        for _, row in gdf_n.iterrows():
            pt = row.geometry
            if pt is None:
                continue
            html = _build_row_tooltip(row, domain_key=domain_key)
            folium.Marker(
                location=[pt.y, pt.x],
                popup=folium.Popup(f'<div class="attr-popup"><button class="copy-btn" onclick="copyPopup(this)">Copy</button><div>{html}</div></div>', max_width=350),
                icon=folium.Icon(color="blue", icon="plus-sign", prefix="glyphicon"),
                tooltip=folium.Tooltip(_build_row_tooltip(row, domain_key=domain_key, limit=3), sticky=True),
            ).add_to(feature_groups["New Assets"])

    for fg in feature_groups.values():
        fg.add_to(m)

    folium.LayerControl(collapsed=True).add_to(m)
    m.save(str(out_path))
    add_info_to_layer_control(str(out_path), BASEMAP_METADATA)


# ─── Data summarization ─────────────────────────────────────────────────────

def summarize_domain(domain_key, data, limit=None):
    """Build a summary dict for one domain."""
    cfg = DEFAULT_DOMAIN_CONFIG[domain_key]
    new_gdf = data["new"]
    drift_gdf = data["drift"]
    vec_gdf = data["vectors"]

    n_new = len(new_gdf) if new_gdf is not None and not new_gdf.empty else 0
    n_drift = len(drift_gdf) if drift_gdf is not None and not drift_gdf.empty else 0
    n_vec = len(vec_gdf) if vec_gdf is not None and not vec_gdf.empty else 0

    risk_counts = {}
    if drift_gdf is not None and not drift_gdf.empty and "Risk_Level" in drift_gdf.columns:
        risk_counts = drift_gdf["Risk_Level"].value_counts().to_dict()

    high_risk_items = []
    if drift_gdf is not None and not drift_gdf.empty:
        id_col = "Asset_ID" if "Asset_ID" in drift_gdf.columns else ("asset_id" if "asset_id" in drift_gdf.columns else None)
        mask = drift_gdf["Risk_Level"].str.contains("High", na=False) if "Risk_Level" in drift_gdf.columns else []
        if isinstance(mask, pd.Series):
            high_risk_items = _rows_to_dicts(drift_gdf[mask], id_col, limit=limit)

    new_items = []
    if new_gdf is not None and not new_gdf.empty:
        id_col = "Asset_ID" if "Asset_ID" in new_gdf.columns else ("asset_id" if "asset_id" in new_gdf.columns else None)
        new_items = _rows_to_dicts(new_gdf, id_col, limit=limit)

    drift_items = []
    if drift_gdf is not None and not drift_gdf.empty:
        id_col = "Asset_ID" if "Asset_ID" in drift_gdf.columns else ("asset_id" if "asset_id" in drift_gdf.columns else None)
        drift_items = _rows_to_dicts(drift_gdf, id_col, limit=limit)

    client_questions = _generate_client_questions(domain_key, new_gdf, drift_gdf, vec_gdf)

    return {
        "label": cfg["label"],
        "icon": cfg["icon"],
        "color": cfg["color"],
        "n_new": n_new,
        "n_drift": n_drift,
        "n_vec": n_vec,
        "risk_counts": risk_counts,
        "high_risk_items": high_risk_items,
        "new_items": new_items,
        "drift_items": drift_items,
        "client_questions": client_questions,
    }


def _rows_to_dicts(gdf, id_col, limit=None):
    """Convert a GDF subset to a list of dicts for the template."""
    if limit is not None:
        gdf = gdf.head(limit)
    records = []
    for _, row in gdf.iterrows():
        d = {}
        if id_col and id_col in gdf.columns:
            d["id"] = str(row.get(id_col, ""))
        for col in ["Location", "Type", "Drift_m", "Risk_Level", "Src_CSV", "Src_Type",
                     "Review_PotentialChange", "Review_Status", "Comments"]:
            if col in gdf.columns:
                val = row.get(col, "")
                if pd.notna(val) and str(val).strip() not in ("", "None", "nan"):
                    d[col.lower()] = str(val)
                else:
                    d[col.lower()] = ""
        records.append(d)
    return records


def _generate_client_questions(domain_key, new_gdf, drift_gdf, vec_gdf):
    """Generate client-facing questions/issues similar to the email format."""
    questions = []
    q_num = 1

    # High-risk drift items always need client attention
    if drift_gdf is not None and not drift_gdf.empty and "Risk_Level" in drift_gdf.columns:
        high = drift_gdf[drift_gdf["Risk_Level"].str.contains("High", na=False)]
        if not high.empty:
            id_col = "Asset_ID" if "Asset_ID" in high.columns else "asset_id"
            ids = high[id_col].tolist() if id_col in high.columns else [f"item {i+1}" for i in range(len(high))]
            questions.append({
                "num": q_num,
                "type": "critical",
                "title": f"High drift detected ({len(high)} assets)",
                "body": (
                    f"The following assets show significant positional drift (>10m) between "
                    f"the field survey data and the GIS database. Please confirm whether the "
                    f"GIS locations should be updated to match the field survey positions: "
                    f"{', '.join(str(i) for i in ids[:10])}"
                    f"{'...' if len(ids) > 10 else ''}"
                ),
            })
            q_num += 1

    # New assets
    if new_gdf is not None and not new_gdf.empty:
        n = len(new_gdf)
        id_col = "Asset_ID" if "Asset_ID" in new_gdf.columns else "asset_id"
        ids = new_gdf[id_col].tolist() if id_col in new_gdf.columns else []
        sample_ids = ", ".join(str(i) for i in ids[:5])
        questions.append({
            "num": q_num,
            "type": "info",
            "title": f"New assets found in field data ({n} assets)",
            "body": (
                f"{n} assets were found in the Reflect field data that do not exist in the "
                f"current GIS database. These appear to be new installations or previously "
                f"unrecorded assets. Should these be added to the GIS? "
                f"IDs: {sample_ids}{'...' if len(ids) > 5 else ''}"
            ),
        })
        q_num += 1

    # Medium risk drift
    if drift_gdf is not None and not drift_gdf.empty and "Risk_Level" in drift_gdf.columns:
        med = drift_gdf[drift_gdf["Risk_Level"].str.contains("Medium", na=False)]
        if not med.empty:
            id_col = "Asset_ID" if "Asset_ID" in med.columns else "asset_id"
            ids = med[id_col].tolist() if id_col in med.columns else []
            questions.append({
                "num": q_num,
                "type": "warning",
                "title": f"Medium drift detected ({len(med)} assets, 5-10m)",
                "body": (
                    f"{len(med)} assets show moderate positional drift (5-10m). "
                    f"Should the GIS locations be adjusted to match the field survey? "
                    f"IDs: {', '.join(str(i) for i in ids[:10])}{'...' if len(ids) > 10 else ''}"
                ),
            })
            q_num += 1

    return questions


# ─── HTML template ───────────────────────────────────────────────────────────

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Asset Reconciliation Review — {{ date }}</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  :root {
    --primary: #1F4E78;
    --secondary: #2E74B5;
    --bg: #F5F6FA;
    --card-bg: #FFFFFF;
    --text: #333333;
    --border: #D5D8DC;
    --high: #C0392B;
    --med: #E67E22;
    --low: #27AE60;
    --new: #3498DB;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', Calibri, Arial, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }
  .container { max-width: 1200px; margin: 0 auto; padding: 20px; }

  /* Header */
  .header { background: linear-gradient(135deg, var(--primary), var(--secondary)); color: white; padding: 30px 40px; border-radius: 12px; margin-bottom: 24px; }
  .header h1 { font-size: 28px; margin-bottom: 6px; }
  .header p { opacity: 0.9; font-size: 14px; }

  /* Summary cards */
  .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px; }
  .summary-card { background: var(--card-bg); border-radius: 10px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); border-left: 4px solid var(--secondary); }
  .summary-card h3 { font-size: 32px; color: var(--primary); }
  .summary-card p { font-size: 13px; color: #666; text-transform: uppercase; letter-spacing: 0.5px; }
  .summary-card.critical { border-left-color: var(--high); }
  .summary-card.critical h3 { color: var(--high); }
  .summary-card.warning { border-left-color: var(--med); }
  .summary-card.warning h3 { color: var(--med); }
  .summary-card.info { border-left-color: var(--new); }
  .summary-card.info h3 { color: var(--new); }

  /* Sections */
  .section { background: var(--card-bg); border-radius: 10px; padding: 24px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
  .section-header { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 2px solid var(--border); }
  .section-header h2 { font-size: 20px; color: var(--primary); }
  .section-header .badge { background: var(--secondary); color: white; padding: 2px 10px; border-radius: 12px; font-size: 12px; font-weight: bold; }

  /* Risk bar */
  .risk-bar { display: flex; height: 24px; border-radius: 12px; overflow: hidden; margin: 12px 0; }
  .risk-bar div { display: flex; align-items: center; justify-content: center; color: white; font-size: 11px; font-weight: bold; min-width: 30px; }

  /* Tables */
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th { background: var(--primary); color: white; padding: 10px 12px; text-align: left; font-weight: 600; }
  td { padding: 8px 12px; border-bottom: 1px solid var(--border); }
  tr:nth-child(even) { background: #F8F9FA; }
  tr:hover { background: #EBF5FB; }
  .risk-high { color: var(--high); font-weight: bold; }
  .risk-med { color: var(--med); font-weight: bold; }
  .risk-low { color: var(--low); font-weight: bold; }
  .risk-new { color: var(--new); font-weight: bold; }

  /* Client questions */
  .question { border-left: 4px solid var(--secondary); padding: 14px 18px; margin: 12px 0; background: #F8F9FA; border-radius: 0 8px 8px 0; }
  .question.critical { border-left-color: var(--high); background: #FDEDEC; }
  .question.warning { border-left-color: var(--med); background: #FEF5E7; }
  .question.info { border-left-color: var(--new); background: #EBF5FB; }
  .question h4 { font-size: 14px; margin-bottom: 6px; }
  .question p { font-size: 13px; color: #555; }

  /* Map */
  .map-container { margin: 16px 0; border-radius: 8px; overflow: hidden; border: 1px solid var(--border); }
  .map-container img { width: 100%; display: block; }
  .map-container iframe { width: 100%; height: 450px; border: none; }

  /* Tabs */
  .tab-buttons { display: flex; gap: 4px; margin-bottom: 12px; }
  .tab-btn { padding: 8px 16px; border: 1px solid var(--border); background: white; cursor: pointer; border-radius: 6px 6px 0 0; font-size: 13px; color: #666; }
  .tab-btn.active { background: var(--primary); color: white; border-color: var(--primary); }
  .tab-content { display: none; }
  .tab-content.active { display: block; }

  /* Footer */
  .footer { text-align: center; padding: 20px; color: #999; font-size: 12px; }

  @media print {
    .tab-buttons { display: none; }
    .tab-content { display: block !important; }
    body { background: white; }
    .section { box-shadow: none; border: 1px solid #ddd; }
  }
</style>
</head>
<body>
<div class="container">

<div class="header">
  <h1>🔍 Asset Reconciliation Review Report</h1>
  <p>Reflect Project — Water &amp; Sewer Asset Comparison | Generated: {{ date }}</p>
</div>

<!-- Summary Cards -->
<div class="summary-grid">
  <div class="summary-card info">
    <h3>{{ total_new }}</h3>
    <p>New Assets</p>
  </div>
  <div class="summary-card warning">
    <h3>{{ total_drift }}</h3>
    <p>Drift Features</p>
  </div>
  <div class="summary-card critical">
    <h3>{{ total_high_risk }}</h3>
    <p>High Risk (&gt;10m)</p>
  </div>
  <div class="summary-card">
    <h3>{{ total_medium_risk }}</h3>
    <p>Medium Risk (5-10m)</p>
  </div>
</div>

<!-- Per-domain sections -->
{% for domain in domains_data %}
<div class="section">
  <div class="section-header">
    <h2>{{ domain.icon }} {{ domain.label }}</h2>
    <span class="badge">{{ domain.n_new }} new</span>
    <span class="badge">{{ domain.n_drift }} drift</span>
  </div>

  <!-- Risk breakdown bar -->
  {% if domain.risk_counts %}
  <div style="margin: 12px 0;">
    <p style="font-size: 13px; color: #666; margin-bottom: 6px;">Drift Risk Distribution:</p>
    <div class="risk-bar">
      {% for risk_label, count in domain.risk_counts.items() %}
      <div style="background: {{ risk_colors.get(risk_label, '#999') }}; width: {{ (count / domain.n_drift * 100) if domain.n_drift > 0 else 0 }}%;">
        {{ count }}
      </div>
      {% endfor %}
    </div>
  </div>
  {% endif %}

  <!-- Map tabs -->
  <div class="tab-buttons">
    <button class="tab-btn active" onclick="showTab(this, 'map-static-{{ loop.index }}')">Static Map</button>
    <button class="tab-btn" onclick="showTab(this, 'map-interactive-{{ loop.index }}')">Interactive Map</button>
    <button class="tab-btn" onclick="showTab(this, 'table-new-{{ loop.index }}')">New Assets Table</button>
    <button class="tab-btn" onclick="showTab(this, 'table-drift-{{ loop.index }}')">Drift Table</button>
  </div>

  <div id="map-static-{{ loop.index }}" class="tab-content active">
    <div class="map-container">
      <img src="Reconciliation_Review_maps/{{ domain.label | lower | replace(' ', '_') }}_map.png" alt="{{ domain.label }} map" onerror="this.style.display='none'; this.parentElement.innerHTML='<p style=\\'padding:20px;color:#999;\\'>Map image not available</p>'">
    </div>
  </div>

  <div id="map-interactive-{{ loop.index }}" class="tab-content">
    <div class="map-container">
      <iframe src="Reconciliation_Review_maps/{{ domain.label | lower | replace(' ', '_') }}_interactive.html"></iframe>
    </div>
  </div>

  <div id="table-new-{{ loop.index }}" class="tab-content">
    {% if domain.new_items %}
    <table>
      <thead>
        <tr>
          <th>Asset ID</th>
          <th>Location</th>
          <th>Type</th>
          <th>Source CSV</th>
          <th>Source Type</th>
          <th>Comments</th>
        </tr>
      </thead>
      <tbody>
        {% for item in domain.new_items %}
        <tr>
          <td>{{ item.get('id', '') }}</td>
          <td>{{ item.get('location', '') }}</td>
          <td>{{ item.get('type', '') }}</td>
          <td>{{ item.get('src_csv', '') }}</td>
          <td>{{ item.get('src_type', '') }}</td>
          <td>{{ item.get('comments', '') }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
    {% else %}
    <p style="color: #999; padding: 12px;">No new assets found.</p>
    {% endif %}
  </div>

  <div id="table-drift-{{ loop.index }}" class="tab-content">
    {% if domain.drift_items %}
    <table>
      <thead>
        <tr>
          <th>Asset ID</th>
          <th>Drift (m)</th>
          <th>Risk Level</th>
          <th>Location</th>
          <th>Type</th>
          <th>Potential Change</th>
          <th>Status</th>
          <th>Comments</th>
        </tr>
      </thead>
      <tbody>
        {% for item in domain.drift_items %}
        <tr>
          <td>{{ item.get('id', '') }}</td>
          <td>{{ item.get('drift_m', '') }}</td>
          <td class="{% if 'High' in item.get('risk_level', '') %}risk-high{% elif 'Medium' in item.get('risk_level', '') %}risk-med{% elif 'Low' in item.get('risk_level', '') %}risk-low{% endif %}">
            {{ item.get('risk_level', '') }}
          </td>
          <td>{{ item.get('location', '') }}</td>
          <td>{{ item.get('type', '') }}</td>
          <td>{{ item.get('review_potentialchange', '') }}</td>
          <td>{{ item.get('review_status', '') }}</td>
          <td>{{ item.get('comments', '') }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
    {% else %}
    <p style="color: #999; padding: 12px;">No drift features found.</p>
    {% endif %}
  </div>
</div>
{% endfor %}

<!-- Client Review Section -->
<div class="section">
  <div class="section-header">
    <h2>📋 Items Requiring Client Review</h2>
  </div>
  <p style="margin-bottom: 16px; color: #555; font-size: 14px;">
    The following items have been identified during the reconciliation process and require
    your review and confirmation before we proceed with any updates to the GIS database.
  </p>

  {% for domain in domains_data %}
    {% for q in domain.client_questions %}
    <div class="question {{ q.type }}">
      <h4>Q{{ q.num }}: {{ q.title }}</h4>
      <p>{{ q.body }}</p>
    </div>
    {% endfor %}
  {% endfor %}

  {% if not any_questions %}
  <p style="color: #999; padding: 12px;">No outstanding client review items.</p>
  {% endif %}
</div>

<!-- Next Steps -->
<div class="section">
  <div class="section-header">
    <h2>📌 Recommended Next Steps</h2>
  </div>
  <ol style="padding-left: 20px; font-size: 14px;">
    <li style="margin-bottom: 8px;"><strong>Review this report</strong> — Check each section above, especially the "Items Requiring Client Review" section.</li>
    <li style="margin-bottom: 8px;"><strong>Open the QGIS project</strong> — Load <code>Critical_Review_Project.qgs</code> to visually inspect all flagged features with differentiated symbology.</li>
    <li style="margin-bottom: 8px;"><strong>Confirm high-risk drift items</strong> — For assets with &gt;10m drift, confirm whether GIS locations should be updated to match field survey positions.</li>
    <li style="margin-bottom: 8px;"><strong>Validate new assets</strong> — Cross-reference new asset IDs with field crew records to confirm they are genuine new installations.</li>
    <li style="margin-bottom: 8px;"><strong>Approve write-back</strong> — Once reviewed, approve production write-back to auto-update GIS geometries (drift ≤ 10m) and append lineage columns.</li>
  </ol>
</div>

<div class="footer">
  <p>Generated by build_html_report.py | Reflect Project | {{ date }}</p>
</div>

</div>

<script>
function showTab(btn, tabId) {
  var parent = btn.closest('.section');
  parent.querySelectorAll('.tab-btn').forEach(function(b) { b.classList.remove('active'); });
  parent.querySelectorAll('.tab-content').forEach(function(c) { c.classList.remove('active'); });
  btn.classList.add('active');
  document.getElementById(tabId).classList.add('active');
}
</script>
</body>
</html>
"""


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate HTML reconciliation review report")
    parser.add_argument("--gpkg", type=str, default=str(DEFAULT_GPKG), help="Path to Critical_Review_Assets.gpkg")
    parser.add_argument("--output", type=str, default=str(OUT_HTML), help="Output HTML path")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of rows shown per table (for testing)")
    args = parser.parse_args()

    gpkg_path = Path(args.gpkg)
    if not gpkg_path.exists():
        print(f"ERROR: GPKG not found: {gpkg_path}")
        sys.exit(1)

    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    MAPS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Loading review data from: {gpkg_path}")
    layers = load_review_data(gpkg_path)
    print(f"Found {len(layers)} layers")

    domains = categorize_layers(layers)

    # Merge Reflect_Sources as additional domain data (treated as new/raw source assets)
    if SOURCE_GPKG.exists():
        print(f"Loading source data from: {SOURCE_GPKG}")
        source_layers = load_review_data(SOURCE_GPKG)
        source_domains = categorize_source_layers(source_layers)
        for dk, data in source_domains.items():
            if dk in domains:
                # If review data already exists, prefer review new/drift over raw source
                if domains[dk]["new"] is None or domains[dk]["new"].empty:
                    domains[dk]["new"] = data["new"]
            else:
                domains[dk] = data

    # Summarize and generate maps
    domains_data = []
    total_new = total_drift = total_high = total_medium = 0
    any_questions = False

    for dk, data in domains.items():
        if dk not in DOMAIN_CONFIG:
            continue

        new_gdf = data["new"]
        drift_gdf = data["drift"]
        vec_gdf = data["vectors"]

        n_new = len(new_gdf) if new_gdf is not None and not new_gdf.empty else 0
        n_drift = len(drift_gdf) if drift_gdf is not None and not drift_gdf.empty else 0
        total_new += n_new
        total_drift += n_drift

        if drift_gdf is not None and not drift_gdf.empty and "Risk_Level" in drift_gdf.columns:
            total_high += len(drift_gdf[drift_gdf["Risk_Level"].str.contains("High", na=False)])
            total_medium += len(drift_gdf[drift_gdf["Risk_Level"].str.contains("Medium", na=False)])

        # Generate static map
        safe_name = DOMAIN_CONFIG[dk]["label"].lower().replace(" ", "_")
        static_map_path = MAPS_DIR / f"{safe_name}_map.png"
        interactive_map_path = MAPS_DIR / f"{safe_name}_interactive.html"

        has_data = any(g is not None and not g.empty for g in [new_gdf, drift_gdf, vec_gdf])
        if has_data:
            print(f"  Generating maps for {dk}...")
            try:
                plot_map(new_gdf, drift_gdf, vec_gdf, dk, static_map_path)
                print(f"    Static map: {static_map_path}")
            except Exception as e:
                print(f"    WARNING: static map failed for {dk}: {e}")

            try:
                build_interactive_map(new_gdf, drift_gdf, vec_gdf, dk, interactive_map_path)
                print(f"    Interactive map: {interactive_map_path}")
            except Exception as e:
                print(f"    WARNING: interactive map failed for {dk}: {e}")

        summary = summarize_domain(dk, data, limit=args.limit)
        domains_data.append(summary)
        if summary["client_questions"]:
            any_questions = True

    # Renumber questions globally
    q_counter = 1
    for dd in domains_data:
        for q in dd["client_questions"]:
            q["num"] = q_counter
            q_counter += 1

    # Render HTML
    template = Template(HTML_TEMPLATE)
    html = template.render(
        date=datetime.now().strftime("%d %B %Y %H:%M"),
        total_new=total_new,
        total_drift=total_drift,
        total_high_risk=total_high,
        total_medium_risk=total_medium,
        domains_data=domains_data,
        risk_colors=RISK_COLORS,
        any_questions=any_questions,
    )

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"\nHTML report generated: {out_path}")
    print(f"Open in browser: file://{out_path}")


if __name__ == "__main__":
    main()
