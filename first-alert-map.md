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
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="{{ '/assets/js/first-alert-map.js' | relative_url }}?v=4"></script>
