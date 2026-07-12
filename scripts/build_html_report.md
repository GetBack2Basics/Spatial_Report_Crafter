# build_html_report.py — Usage

Generates a self-contained HTML reconciliation review report from `Critical_Review_Assets.gpkg`.

## Summary

- Reads review layers from the GPKG
- Builds per-domain summaries: new assets, drift features, displacement vectors, risk counts
- Generates static matplotlib maps and interactive Leaflet maps
- Writes a single HTML report plus map assets under the report folder
- Best-effort map generation; if maps fail, the report still renders

## Input

Required:
- `Critical_Review_Assets.gpkg` with review layers:
  - `*_new_review`
  - `*_drift_review`
  - `*_displacement_vector`

Expected columns used in rendering:
- `Asset_ID` or `asset_id`
- `Drift_m`
- `Risk_Level`
- `Review_PotentialChange`
- `Review_Status`
- `Src_CSV`, `Src_Type`, `Src_Date`, `Src_Value`, `Comments`

Optional:
- `Reflect_Sources.gpkg` for raw-source domains merged into the report

CLI:
- `--gpkg` path to the review GPKG
- `--output` path for the generated HTML

Python:
- `generate_html_report(domains_data, output_html_path)`
- `load_domain_data_from_layers(layers, domain_config, source_layers)`

## Output

Default output file:
- `Working/Reconciliation_Review.html`

Map assets:
- `Working/Reconciliation_Review_maps/`

## Example usage

From project `Working/` folder with venv activated:
- `python scripts/build_html_report.py`
- `python scripts/build_html_report.py --gpkg "Pending Data/Critical_Review_Assets.gpkg"`
- `python scripts/build_html_report.py --output Draft_Output/Reconciliation_Review.html`

## Map behavior

- Uses folium's native `TileLayer` and `WmsTileLayer`
- Uses native `LayerControl(collapsed=True)`
- Adds click-to-reveal popups with a Copy button
- Adds small `(i)` metadata links and an optional Custom WMS form only after save

## Limits and fallback

- New assets tables cap at first 50 in DOCX generation, but HTML shows all
- Drift tables show all
- Very long attribute values are truncated in grep mode
- Map generation exceptions are caught at call sites so the HTML still renders

## Notes

- Report paths are relative to `Working/`
- Domain labels, icons, colors, and risk colors are configurable via `DEFAULT_DOMAIN_CONFIG`
- Source-driven domains can be merged in via `source_layers`
- This doc does not cover pipeline matching or GPKG creation
