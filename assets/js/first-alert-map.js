/* FirstAlert CSV → Leaflet. Expects /data/first-alert/latest.csv */
(function () {
  const CSV_URL = "/data/first-alert/latest.csv";
  const MAP_ID = "first-alert-map";

  function norm(s) {
    return String(s || "")
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "");
  }

  function pick(row, names) {
    const keys = Object.keys(row);
    for (const want of names) {
      const w = norm(want);
      for (const k of keys) {
        if (norm(k) === w) return row[k];
      }
    }
    return "";
  }

  function pickContains(row, parts, excludeParts) {
    const keys = Object.keys(row);
    for (const k of keys) {
      const n = norm(k);
      if (!parts.every((p) => n.indexOf(norm(p)) !== -1)) continue;
      if (excludeParts && excludeParts.some((p) => n.indexOf(norm(p)) !== -1)) continue;
      const v = row[k];
      if (v !== undefined && String(v).trim() !== "") return v;
    }
    return "";
  }

  function parsePublicPos(val) {
    if (!val) return null;
    const s = String(val).trim();
    let m = s.match(/POINT\s*\(\s*([+-]?\d+(?:\.\d+)?)\s+([+-]?\d+(?:\.\d+)?)\s*\)/i);
    if (m) return { lon: +m[1], lat: +m[2] };
    m = s.match(/([+-]?\d+(?:\.\d+)?)\s*[,;\s]\s*([+-]?\d+(?:\.\d+)?)/);
    if (m) {
      const a = +m[1], b = +m[2];
      if (Math.abs(a) <= 90 && Math.abs(b) <= 180) return { lat: a, lon: b };
      if (Math.abs(b) <= 90 && Math.abs(a) <= 180) return { lat: b, lon: a };
    }
    return null;
  }

  function parseLatLon(row) {
    let lat = pick(row, [
      "latitude", "lat", "estimatedlatitude", "estimatedlat",
      "estimatedeventlocationcoordinateslat",
      "y", "alertlat", "publiclat"
    ]);
    let lon = pick(row, [
      "longitude", "lon", "lng", "long",
      "estimatedlongitude", "estimatedlon", "estimatedlng",
      "estimatedeventlocationcoordinateslng",
      "x", "alertlon", "publiclon"
    ]);
    if (lat === "") lat = pickContains(row, ["lat"], ["lng", "lon", "long", "platitude"]);
    if (lon === "") lon = pickContains(row, ["lng"], ["lat"]);
    if (lon === "") lon = pickContains(row, ["lon"], ["lat"]);
    if (lat !== "" && lon !== "" && isFinite(+lat) && isFinite(+lon)) {
      return { lat: +lat, lon: +lon };
    }
    return parsePublicPos(
      pick(row, ["publicpos", "publicposition", "position", "geom", "geometry", "wkt", "location"])
    );
  }

  function topicColor(topic) {
    const t = String(topic || "").toLowerCase();
    if (t.includes("fire") || t.includes("wildfire") || t.includes("hotspot")) return "#c0392b";
    if (t.includes("outage") || t.includes("power")) return "#8e44ad";
    if (t.includes("flood") || t.includes("water")) return "#2980b9";
    if (t.includes("cyber") || t.includes("hack")) return "#16a085";
    if (t.includes("security") || t.includes("threat") || t.includes("attack")) return "#d35400";
    return "#2c3e50";
  }

  function parseCsv(text) {
    const rows = [];
    let row = [], field = "", i = 0, inQ = false;
    const pushField = () => { row.push(field); field = ""; };
    const pushRow = () => {
      if (row.length && row.some((c) => c.trim() !== "")) rows.push(row);
      row = [];
    };
    while (i < text.length) {
      const c = text[i];
      if (inQ) {
        if (c === '"') {
          if (text[i + 1] === '"') { field += '"'; i++; }
          else inQ = false;
        } else field += c;
      } else if (c === '"') inQ = true;
      else if (c === ",") pushField();
      else if (c === "\n") { pushField(); pushRow(); }
      else if (c !== "\r") field += c;
      i++;
    }
    if (field.length || row.length) { pushField(); pushRow(); }
    if (!rows.length) return [];
    const headers = rows[0].map((h) => h.trim());
    return rows.slice(1).map((cols) => {
      const obj = {};
      headers.forEach((h, idx) => { obj[h] = cols[idx] != null ? cols[idx] : ""; });
      return obj;
    });
  }

  function statusEl() {
    return document.getElementById("first-alert-map-status");
  }

  function boot() {
    const el = document.getElementById(MAP_ID);
    if (!el || typeof L === "undefined") return;
    const map = L.map(MAP_ID, { scrollWheelZoom: false }).setView([39.7, -98.3], 4);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: "&copy; OpenStreetMap"
    }).addTo(map);

    fetch(CSV_URL, { cache: "no-store" })
      .then((r) => {
        if (!r.ok) throw new Error("CSV not found at " + CSV_URL);
        return r.text();
      })
      .then((text) => {
        const table = parseCsv(text);
        const pts = [];
        table.forEach((row) => {
          const ll = parseLatLon(row);
          if (!ll) return;
          if (Math.abs(ll.lat) > 90 || Math.abs(ll.lon) > 180) return;
          pts.push({ row, ll });
        });
        const st = statusEl();
        if (!pts.length) {
          if (st) st.textContent = "CSV loaded but no mappable coordinates (check publicPos / lat / lon columns).";
          return;
        }
        const group = L.featureGroup();
        pts.forEach(({ row, ll }) => {
          const topic = pick(row, ["alerttopics", "alerttopic", "topic", "hazard", "type"]);
          const headline = pick(row, ["headline", "title", "subject", "alert"]);
          const when = pick(row, ["alerttimestamp", "alerttime", "time", "datetime", "published"]);
          const id = pick(row, ["alertid", "id"]);
          const href = pick(row, ["publicposthref", "dataminralerturl", "url", "link"]);
          const m = L.circleMarker([ll.lat, ll.lon], {
            radius: 7,
            color: "#fff",
            weight: 1,
            fillColor: topicColor(topic),
            fillOpacity: 0.9
          });
          m.bindPopup(
            "<strong>" + (headline || topic || "Alert") + "</strong><br>" +
            (topic ? "Topic: " + topic + "<br>" : "") +
            (when ? "Time: " + when + "<br>" : "") +
            (id ? "ID: " + id + "<br>" : "") +
            ll.lat.toFixed(4) + ", " + ll.lon.toFixed(4) +
            (href ? "<br><a href=\"" + href + "\" target=\"_blank\" rel=\"noopener\">Open alert</a>" : "")
          );
          group.addLayer(m);
        });
        group.addTo(map);
        map.fitBounds(group.getBounds().pad(0.15));
        if (st) st.textContent = pts.length + " mapped alerts from latest.csv (" + table.length + " rows).";
      })
      .catch((err) => {
        const st = statusEl();
        if (st) st.textContent = "Could not load map data: " + err.message;
      });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();