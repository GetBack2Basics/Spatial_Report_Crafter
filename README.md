# Spatial Offline Report Crafter

Purpose:
- Generate offline-ready spatial review reports from a review GeoPackage.
- Provide reusable HTML and DOCX renderers an agent can call with different datasets.

What this project contains:
- scripts/build_html_report.py — generates an HTML reconciliation review report
- scripts/build_html_report.md — usage notes for the HTML report script
- scripts/create_extract_docx.py — generates a native DOCX summary extract

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
- Water_Sewer_Reconciliation_Extract.docx

How an agent can use this:
- Run the HTML/DOCX scripts against any review GPKG matching the expected schema.
- Use the agent workflow cheatsheet for ingest, matching, classification, and review GPKG creation.
- Keep source data read-only; write all outputs to a separate draft/output location.

Reference:
- Reflect reconciliation workflow: https://github.com/GetBack2Basics/014_CSC_Reflect
- QGIS portal patterns: https://github.com/GetBack2Basics/QGIS_PortalCrafter

Notes:
- HTML reports use folium's native basemap controls; only post-process for metadata links and optional custom WMS form.
- DOCX reports are native documents with structured tables and summary sections.
