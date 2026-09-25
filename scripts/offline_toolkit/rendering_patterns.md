# Rendering patterns for offline "Map-in-a-Box" reports

Schema-free notes and snippets accompanying
`docs/lessons_learned_offline_case_study.md`. These cover two small,
reusable front-end patterns for the offline generator option: geometry-
appropriate feature rendering, and native collapsible sections.

## 1. Geometry-appropriate rendering: cluster points, cap lines/polygons

A single "cap the total number of rendered features" rule works poorly
across geometry types. Point features cluster well; polylines/polygons
don't cluster meaningfully in the same way, so cap those to the largest-N
features currently in view instead.

```js
// Points: cluster instead of capping, so all of them can be "shown" even
// when there are hundreds of thousands of them.
const pointCluster = L.markerClusterGroup({
  chunkedLoading: true,
  maxClusterRadius: 60,
  disableClusteringAtZoom: 18,
});
map.addLayer(pointCluster);

function drawPoints(pointRecords, pointToMarker) {
  pointCluster.clearLayers();
  if (pointRecords.length) pointCluster.addLayers(pointRecords.map(pointToMarker));
}

// Lines/polygons: rank by a size proxy (length/area/priority) and only
// render the largest VIEWPORT_FEATURE_CAP that intersect the current view,
// recomputed on every `moveend` (not just once on load).
const VIEWPORT_FEATURE_CAP = 500;

function drawCappedLayer(allRecordsOfThisGeometryType, recordToLayer, layerGroup) {
  const bounds = map.getBounds();
  const inView = allRecordsOfThisGeometryType.filter((record) => recordIntersectsBounds(record, bounds));
  const shown = inView
    .slice()
    .sort((a, b) => (b.size || 0) - (a.size || 0))
    .slice(0, VIEWPORT_FEATURE_CAP);
  layerGroup.clearLayers();
  shown.forEach((record) => layerGroup.addLayer(recordToLayer(record)));
  return { shown: shown.length, total: inView.length };
}

map.on("moveend", () => {
  const stats = drawCappedLayer(lineRecords, lineToLayer, lineLayerGroup);
  statusEl.textContent = `${stats.shown.toLocaleString()} of ${stats.total.toLocaleString()} lines in view shown, largest first (capped at ${VIEWPORT_FEATURE_CAP})`;
});
```

`recordIntersectsBounds` just needs a bounding box per record (see
`companion_data_writer.py`'s `bbox_key`) checked against
`bounds.intersects(L.latLngBounds([[minLat, minLon], [maxLat, maxLon]]))`.

## 2. Native `<details>/<summary>` progressive disclosure

Mark supplementary sections as collapsible using plain HTML — no
JavaScript required, and it degrades gracefully (stays readable, just not
collapsible) if a browser blocks the report's scripts entirely.

```html
<style>
details.collapsible > summary { cursor: pointer; list-style: none; font-weight: bold; }
details.collapsible > summary::-webkit-details-marker { display: none; }
details.collapsible > summary::before { content: "\25b8"; display: inline-block; margin-right: 6px; transition: transform .15s; }
details.collapsible[open] > summary::before { transform: rotate(90deg); }
</style>

<!-- Primary content: open by default -->
<details class="collapsible" open>
  <summary>Report summary</summary>
  <p>... KPI cards / headline stats ...</p>
</details>

<!-- Supplementary content: collapsed by default -->
<details class="collapsible">
  <summary>Breakdown tables</summary>
  <p>... detailed cross-tab tables ...</p>
</details>

<details class="collapsible">
  <summary>Data provenance and validation</summary>
  <p>... source file/worksheet/layer, generation time, exclusion counts ...</p>
</details>
```

Keep the primary content (summary KPIs, the map, the results table) open by
default and collapse only the genuinely supplementary sections.
