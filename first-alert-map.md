---
layout: page
title: "First Alert map"
permalink: /first-alert/map/
---

Dam / facility First Alert points from the latest CSV drop. Default view is the last 7 days.

<div id="fa-filters" style="display:flex;gap:12px;align-items:center;margin:0 0 8px;font-size:0.9rem;"></div>
<p id="first-alert-map-status">Loading map…</p>
<div style="position:relative;">
  <div class="fa-legend" style="position:absolute;right:8px;bottom:8px;z-index:1000;background:rgba(255,255,255,.94);padding:8px 10px;border-radius:4px;font:12px/1.35 sans-serif;box-shadow:0 1px 4px rgba(0,0,0,.25);">
    <div style="font-weight:700;margin-bottom:4px;">Topic</div>
    <div style="display:flex;align-items:center;gap:6px;margin:3px 0;"><span style="width:10px;height:10px;border-radius:50%;background:#c0392b;display:inline-block;"></span>Fire</div>
    <div style="display:flex;align-items:center;gap:6px;margin:3px 0;"><span style="width:10px;height:10px;border-radius:50%;background:#8e44ad;display:inline-block;"></span>Outage / utilities</div>
    <div style="display:flex;align-items:center;gap:6px;margin:3px 0;"><span style="width:10px;height:10px;border-radius:50%;background:#2980b9;display:inline-block;"></span>Flood / water</div>
    <div style="display:flex;align-items:center;gap:6px;margin:3px 0;"><span style="width:10px;height:10px;border-radius:50%;background:#16a085;display:inline-block;"></span>Cyber</div>
    <div style="display:flex;align-items:center;gap:6px;margin:3px 0;"><span style="width:10px;height:10px;border-radius:50%;background:#d35400;display:inline-block;"></span>Vandalism / attack</div>
    <div style="display:flex;align-items:center;gap:6px;margin:3px 0;"><span style="width:10px;height:10px;border-radius:50%;background:#2c3e50;display:inline-block;"></span>Other</div>
  </div>
  <div id="first-alert-map" style="height: 480px; width: 100%; border: 1px solid #ddd4c4; border-radius: 4px;"></div>
</div>
<p class="lede"><a href="{{ '/first-alert/' | relative_url }}">Dashboard log</a> · update file: <code>data/first-alert/latest.csv</code></p>

<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="{{ '/assets/js/first-alert-map.js' | relative_url }}?v=9"></script>
