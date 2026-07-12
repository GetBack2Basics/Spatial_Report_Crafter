# Spatial Report Crafter

Purpose:
- Generate offline-ready spatial review reports from a review GeoPackage.
- Provide a reusable HTML renderer an agent can call with different datasets.

What this project contains:
- scripts/build_html_report.py — generates an HTML reconciliation review report
- scripts/build_html_report.md — usage notes for the HTML report script

Inputs:
- Critical_Review_Assets.gpkg with review layers:
  - *_new_review
  - *_drift_review
  - *_displacement_vector

Recommended columns:
- Asset_ID or asset_id
- Drift_m
- Risk_Level
- Review_PotentialChange
- Review_Status
- Src_CSV, Src_Type, Src_Date, Src_Value, Comments

Outputs:
- Reconciliation_Review.html
- Reconciliation_Review_maps/

How an agent can use this:
- Run the HTML script against any review GPKG matching the expected schema.
- Use the agent workflow cheatsheet for ingest, matching, classification, and review GPKG creation.
- Keep source data read-only; write all outputs to a separate draft/output location.

Reference:
- DOCX workflow: https://github.com/GetBack2Basics/Spatial_Document_Crafter
- Reflect reconciliation workflow: https://github.com/GetBack2Basics/014_CSC_Reflect
- QGIS portal patterns: https://github.com/GetBack2Basics/QGIS_PortalCrafter

Notes:
- HTML reports use folium's native basemap controls; only post-process for metadata links and optional custom WMS form.
