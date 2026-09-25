---
layout: null
permalink: /first-alert/embed/
---
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>First Alert map</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
  <style>
    html, body { margin: 0; padding: 0; height: 100%; overflow: hidden; }
    #first-alert-map { height: 100%; width: 100%; }
    .fa-legend {
      background: rgba(255,255,255,.92);
      padding: 8px 10px;
      border-radius: 4px;
      font: 12px/1.35 sans-serif;
      box-shadow: 0 1px 4px rgba(0,0,0,.2);
    }
    .fa-legend-title { font-weight: 700; margin-bottom: 4px; }
    .fa-legend-row { display: flex; align-items: center; gap: 6px; margin: 2px 0; }
    .fa-swatch {
      width: 10px; height: 10px; border-radius: 50%;
      border: 1px solid #fff; box-shadow: 0 0 0 1px #ccc;
      flex: 0 0 10px;
    }
    .leaflet-tooltip.fa-count {
      background: transparent; border: 0; box-shadow: none;
      color: #fff; font-weight: 700; text-shadow: 0 0 2px #000;
    }

    #first-alert-map-status {
      position: absolute; z-index: 1000; left: 8px; bottom: 8px;
      background: rgba(255,255,255,.9); font: 12px/1.3 sans-serif;
      padding: 4px 8px; border-radius: 3px; max-width: 70%;
    }
  </style>
</head>
<body>
  <div id="first-alert-map-status">Loading map…</div>
  <div id="first-alert-map"></div>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script src="{{ '/assets/js/first-alert-map.js' | relative_url }}?v=5"></script>
</body>
</html>
