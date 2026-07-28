# Spatial Report Crafter

**Spatial Report Crafter** is a generalized utility for generating premium, offline-ready interactive spatial HTML reports and reconciliation reviews from diverse geospatial backends. It supports both cloud database queries (Wherobots / Apache Sedona) and offline desktop databases (OGC GeoPackage).

---

## 1. Cloud-Based Spatial Reporting (Wherobots / Sedona)

Generate interactive, config-driven reports directly from cloud database clusters.

### Structure & Modules
- `scripts/build_config_report.py`: Generic python script that reads configuration maps, connects to Wherobots, queries tables, builds GeoJSON overlay arrays, and replaces template variables.
- `configs/national_suitability.json`: Configuration mapping SQL queries, table schemas, layer geometries, and metadata placeholders.
- `templates/national_suitability_report_template.html`: Self-contained Leaflet dashboard template equipped with WMS layers, layer controls, and leaderboards.

### Usage
Ensure your `.env` contains `WHEROBOTS_API_KEY` and run:
```bash
python scripts/build_config_report.py \
  --config configs/national_suitability.json \
  --template templates/national_suitability_report_template.html \
  --output Siting_Suitability_Report.html
```

---

## 2. Offline GIS Desktop Reporting (GeoPackage)

Build interactive reconciliation reviews and displacement maps from local GeoPackage layers.

### Structure & Modules
- `scripts/build_html_report.py`: Ingests a review GPKG, structures executive summaries, plots displacement vectors via matplotlib, and generates local folium maps.
- `scripts/build_html_report.md`: Detailed notes for the GeoPackage review script.

### Input Specifications
The GPKG (`Critical_Review_Assets.gpkg`) expects:
- `*_new_review` (New features)
- `*_drift_review` (Asset drift points)
- `*_displacement_vector` (Line vectors showing original vs. surveyed drift)

Recommended attribute columns:
- `asset_id`, `drift_m`, `risk_level`, `review_status`, `comments`.

### Usage
```bash
python scripts/build_html_report.py --gpkg "Pending Data/Critical_Review_Assets.gpkg"
```

---

## How an Agent Uses This
- Use the config-driven `build_config_report.py` for direct Wherobots database reports by mapping tables and templates.
- Use `build_html_report.py` for offline GeoPackage reconciliation.
- Keep source tables read-only; write all generated HTML files to designated project output/draft directories.

## Reference Repositories
- Word/DOCX Generation: [Spatial_Document_Crafter](https://github.com/GetBack2Basics/Spatial_Document_Crafter)
- Spatial Matching: [014_CSC_Reflect](https://github.com/GetBack2Basics/014_CSC_Reflect)
- QGIS Integrations: [QGIS_PortalCrafter](https://github.com/GetBack2Basics/QGIS_PortalCrafter)

---

### Notes:
- Interactive HTML reports use folium/Leaflet native basemap layers; keep custom overlays grouped in layer control modules.
