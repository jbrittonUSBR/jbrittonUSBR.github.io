---
layout: page
title: "First Alert map"
permalink: /first-alert/map/
---

Dam / facility First Alert points from the latest CSV drop.

<p id="first-alert-map-status">Loading map…</p>
<div id="first-alert-map" style="height: 480px; width: 100%; border: 1px solid #ddd4c4; border-radius: 4px;"></div>
<p class="lede"><a href="{{ '/first-alert/' | relative_url }}">Dashboard log</a> · update file: <code>data/first-alert/latest.csv</code></p>

<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<style>
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
</style>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="{{ '/assets/js/first-alert-map.js' | relative_url }}?v=5"></script>
