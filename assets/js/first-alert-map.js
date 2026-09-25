/* FirstAlert / Dataminr CSV → Leaflet */
(function () {
  const MAP_ID = "first-alert-map";
  const CANDIDATES = [
    "/data/first-alert/latest.csv",
    "/jbrittonUSBR.github.io/data/first-alert/latest.csv"
  ];

  function status(msg) {
    const el = document.getElementById("first-alert-map-status");
    if (el) el.textContent = msg;
  }

  function norm(s) {
    return String(s || "").trim().toLowerCase().replace(/[^a-z0-9]+/g, "");
  }

  function parseCsv(text) {
    if (text.charCodeAt(0) === 0xfeff) text = text.slice(1);
    const rows = [];
    let row = [];
    let field = "";
    let inQ = false;
    for (let i = 0; i < text.length; i++) {
      const c = text[i];
      if (inQ) {
        if (c === '"') {
          if (text[i + 1] === '"') { field += '"'; i++; }
          else inQ = false;
        } else field += c;
      } else if (c === '"') {
        inQ = true;
      } else if (c === ",") {
        row.push(field);
        field = "";
      } else if (c === "\n") {
        row.push(field);
        field = "";
        if (row.some((x) => String(x).trim() !== "")) rows.push(row);
        row = [];
      } else if (c !== "\r") {
        field += c;
      }
    }
    if (field.length || row.length) {
      row.push(field);
      if (row.some((x) => String(x).trim() !== "")) rows.push(row);
    }
    if (!rows.length) return [];
    const headers = rows[0].map((h) => h.trim());
    return rows.slice(1).map((cols) => {
      const obj = {};
      headers.forEach((h, idx) => { obj[h] = cols[idx] != null ? cols[idx] : ""; });
      return obj;
    });
  }

  function val(row, pred) {
    for (const k of Object.keys(row)) {
      if (pred(norm(k))) {
        const v = row[k];
        if (v != null && String(v).trim() !== "") return String(v).trim();
      }
    }
    return "";
  }

  function parseLatLon(row) {
    const latS = val(row, (n) =>
      n === "lat" || n === "latitude" ||
      (n.indexOf("lat") !== -1 && n.indexOf("lng") === -1 && n.indexOf("lon") === -1 && n.indexOf("plat") === -1)
    );
    const lonS = val(row, (n) =>
      n === "lon" || n === "lng" || n === "long" || n === "longitude" ||
      n.indexOf("lng") !== -1 ||
      (n.indexOf("lon") !== -1 && n.indexOf("lat") === -1)
    );
    const lat = parseFloat(latS);
    const lon = parseFloat(lonS);
    if (isFinite(lat) && isFinite(lon) && Math.abs(lat) <= 90 && Math.abs(lon) <= 180) {
      return { lat: lat, lon: lon };
    }
    return null;
  }

  function topicColor(topic) {
    const t = String(topic || "").toLowerCase();
    if (t.indexOf("fire") !== -1) return "#c0392b";
    if (t.indexOf("outage") !== -1 || t.indexOf("utilit") !== -1) return "#8e44ad";
    if (t.indexOf("flood") !== -1 || t.indexOf("water") !== -1) return "#2980b9";
    if (t.indexOf("cyber") !== -1) return "#16a085";
    if (t.indexOf("vandal") !== -1 || t.indexOf("attack") !== -1) return "#d35400";
    return "#2c3e50";
  }

  function loadCsv() {
    const urls = CANDIDATES.map((u) => u + "?t=" + Date.now());
    return urls.reduce(function (p, url) {
      return p.catch(function () {
        return fetch(url, { cache: "no-store" }).then(function (r) {
          if (!r.ok) throw new Error(url + " " + r.status);
          return r.text();
        });
      });
    }, Promise.reject());
  }

  function boot() {
    const el = document.getElementById(MAP_ID);
    if (!el) return;
    if (typeof L === "undefined") {
      status("Leaflet failed to load.");
      return;
    }
    const map = L.map(MAP_ID, { scrollWheelZoom: false }).setView([39.7, -98.3], 4);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: "&copy; OpenStreetMap"
    }).addTo(map);

    loadCsv()
      .then(function (text) {
        const table = parseCsv(text);
        if (!table.length) {
          status("CSV parsed to zero data rows.");
          return;
        }
        const headers = Object.keys(table[0]);
        const pts = [];
        table.forEach(function (row) {
          const ll = parseLatLon(row);
          if (!ll) return;
          pts.push({ row: row, ll: ll });
        });
        if (!pts.length) {
          status("CSV loaded (" + table.length + " rows). Headers: " + headers.join(" | ") + ". No numeric lat/lng found.");
          return;
        }
        const group = L.featureGroup();
        pts.forEach(function (item) {
          const row = item.row;
          const ll = item.ll;
          const topic = val(row, function (n) { return n.indexOf("topic") !== -1; });
          const headline = val(row, function (n) { return n === "headline" || n === "title"; });
          const when = val(row, function (n) { return n.indexOf("time") !== -1 || n.indexOf("stamp") !== -1; });
          const place = val(row, function (n) { return n.indexOf("locationname") !== -1; });
          const href = val(row, function (n) { return n.indexOf("href") !== -1 || n.indexOf("alerturl") !== -1; });
          const m = L.circleMarker([ll.lat, ll.lon], {
            radius: 7,
            color: "#fff",
            weight: 1,
            fillColor: topicColor(topic),
            fillOpacity: 0.9
          });
          m.bindPopup(
            "<strong>" + (headline || topic || "Alert") + "</strong><br>" +
            (place ? place + "<br>" : "") +
            (topic ? "Topic: " + topic + "<br>" : "") +
            (when ? "Time: " + when + "<br>" : "") +
            ll.lat.toFixed(4) + ", " + ll.lon.toFixed(4) +
            (href ? "<br><a href=\"" + href + "\" target=\"_blank\" rel=\"noopener\">Open alert</a>" : "")
          );
          group.addLayer(m);
        });
        group.addTo(map);
        map.fitBounds(group.getBounds().pad(0.15));
        setTimeout(function () { map.invalidateSize(); }, 200);
        status(pts.length + " mapped / " + table.length + " rows.");
      })
      .catch(function (err) {
        status("Could not load CSV: " + err.message);
      });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();