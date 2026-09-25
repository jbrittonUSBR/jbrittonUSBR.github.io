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
  <script src="{{ '/assets/js/first-alert-map.js' | relative_url }}?v=3"></script>
</body>
</html>
