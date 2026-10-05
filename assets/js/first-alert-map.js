/* FirstAlert / Dataminr CSV → Leaflet */
(function () {
  const MAP_ID = "first-alert-map";
  const CANDIDATES = [
    "/data/first-alert/latest.csv",
    "/jbrittonUSBR.github.io/data/first-alert/latest.csv"
  ];
  const TOPICS = [
    { id: "all", label: "All topics" },
    { id: "fire", label: "Fire" },
    { id: "outage", label: "Outage / utilities" },
    { id: "water", label: "Flood / water" },
    { id: "cyber", label: "Cyber" },
    { id: "attack", label: "Vandalism / attack" },
    { id: "other", label: "Other" }
  ];

  function status(msg) {
    const el = document.getElementById("first-alert-map-status");
    if (el) el.textContent = msg;
  }

  function norm(s) {
    return String(s || "").trim().toLowerCase().replace(/[^a-z0-9]+/g, "");
  }

  function esc(s) {
    return String(s || "")
      .replace(/&/g, "\u0026amp;")
      .replace(/</g, "\u0026lt;")
      .replace(/>/g, "\u0026gt;")
      .replace(/"/g, "\u0026quot;");
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

  function topicIds(topic) {
    const t = String(topic || "").toLowerCase();
    const ids = [];
    if (t.indexOf("fire") !== -1) ids.push("fire");
    if (t.indexOf("flood") !== -1 || t.indexOf("water") !== -1) ids.push("water");
    if (t.indexOf("cyber") !== -1) ids.push("cyber");
    if (t.indexOf("vandal") !== -1 || t.indexOf("attack") !== -1) ids.push("attack");
    if (t.indexOf("outage") !== -1 || t.indexOf("utilit") !== -1) ids.push("outage");
    if (!ids.length) ids.push("other");
    return ids;
  }

  function topicColor(topic) {
    const id = topicIds(topic)[0];
    if (id === "fire") return "#c0392b";
    if (id === "outage") return "#8e44ad";
    if (id === "water") return "#2980b9";
    if (id === "cyber") return "#16a085";
    if (id === "attack") return "#d35400";
    return "#2c3e50";
  }

  function rowTime(row) {
    const raw = val(row, function (n) { return n.indexOf("time") !== -1 || n.indexOf("stamp") !== -1; });
    const ms = Date.parse(raw);
    return isFinite(ms) ? ms : null;
  }

  function ensureFilters() {
    let bar = document.getElementById("fa-filters");
    if (bar) return bar;
    const mapEl = document.getElementById(MAP_ID);
    if (!mapEl || !mapEl.parentNode) return null;
    bar = document.createElement("div");
    bar.id = "fa-filters";
    mapEl.parentNode.insertBefore(bar, mapEl);
    return bar;
  }

  function fillFilters(bar) {
    if (bar.getAttribute("data-ready") === "1") return;
    bar.innerHTML =
      '<label>Dates <select id="fa-range">' +
        '<option value="1">Last 24 hours</option>' +
        '<option value="7" selected>Last 7 days</option>' +
        '<option value="30">Last 30 days</option>' +
        '<option value="all">All dates</option>' +
      '</select></label>' +
      '<label>Topic <select id="fa-topic">' +
        TOPICS.map(function (t) {
          return '<option value="' + t.id + '">' + t.label + "</option>";
        }).join("") +
      "</select></label>";
    bar.setAttribute("data-ready", "1");
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
    const bar = ensureFilters();
    if (bar) fillFilters(bar);

    const map = L.map(MAP_ID, { scrollWheelZoom: false }).setView([39.7, -98.3], 4);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: "&copy; OpenStreetMap"
    }).addTo(map);

    const group = L.featureGroup().addTo(map);
    let allPts = [];
    let fitted = false;

    function selectedRangeMs() {
      const sel = document.getElementById("fa-range");
      const v = sel ? sel.value : "7";
      if (v === "all") return null;
      const days = parseInt(v, 10);
      return Date.now() - (isFinite(days) ? days : 7) * 86400000;
    }

    function selectedTopic() {
      const sel = document.getElementById("fa-topic");
      return sel ? sel.value : "all";
    }

    function draw() {
      group.clearLayers();
      const cutoff = selectedRangeMs();
      const topic = selectedTopic();
      const pts = allPts.filter(function (item) {
        if (cutoff != null && (item.when == null || item.when < cutoff)) return false;
        if (topic !== "all" && item.topics.indexOf(topic) === -1) return false;
        return true;
      });
      if (!pts.length) {
        status("0 alerts in this date range and topic.");
        return;
      }
      const buckets = {};
      pts.forEach(function (item) {
        const k = item.ll.lat.toFixed(4) + "," + item.ll.lon.toFixed(4);
        if (!buckets[k]) buckets[k] = [];
        buckets[k].push(item);
      });
      const keys = Object.keys(buckets);
      keys.forEach(function (k) {
        const items = buckets[k];
        const ll = items[0].ll;
        const topicText = items[0].topicText;
        let html = "";
        items.forEach(function (item, idx) {
          html += "<div style=\"margin:0 0 8px 0;\">";
          html += "<strong>" + (items.length > 1 ? (idx + 1) + ". " : "") + esc(item.headline || item.topicText || "Alert") + "</strong><br>";
          if (item.place) html += esc(item.place) + "<br>";
          if (item.whenLabel) html += "Time: " + esc(item.whenLabel) + "<br>";
          if (item.href) html += "<a href=\"" + esc(item.href) + "\" target=\"_blank\" rel=\"noopener\">Open alert</a>";
          html += "</div>";
        });
        const n = items.length;
        const radiusForZoom = function (z) {
          var base = n <= 1 ? 7 : 7 + (n - 1) * 6;
          if (z <= 4) base += n <= 1 ? 0 : 4;
          else if (z >= 9) base -= n <= 1 ? 0 : 3;
          return Math.max(6, Math.min(40, base));
        };
        const m = L.circleMarker([ll.lat, ll.lon], {
          radius: radiusForZoom(map.getZoom()),
          color: "#fff",
          weight: 1,
          fillColor: topicColor(topicText),
          fillOpacity: 0.88
        });
        m._faRadiusForZoom = radiusForZoom;
        const title = n > 1 ? n + " alerts at this location" : "";
        m.bindPopup((title ? "<em>" + title + "</em><br>" : "") + html, { maxHeight: 240 });
        if (n > 1) {
          m.bindTooltip(String(n), { permanent: true, direction: "center", className: "fa-count" });
        }
        group.addLayer(m);
      });
      map.off("zoomend");
      map.on("zoomend", function () {
        var z = map.getZoom();
        group.eachLayer(function (layer) {
          if (layer._faRadiusForZoom) layer.setRadius(layer._faRadiusForZoom(z));
        });
      });
      if (!fitted && group.getLayers().length) {
        map.fitBounds(group.getBounds().pad(0.15));
        fitted = true;
      }
      setTimeout(function () { map.invalidateSize(); }, 200);
      status(pts.length + " alerts / " + keys.length + " locations (last " +
        (selectedRangeMs() == null ? "all dates" : (document.getElementById("fa-range").value === "1" ? "24 hours" : document.getElementById("fa-range").value + " days")) +
        ").");
    }

    ["fa-range", "fa-topic"].forEach(function (id) {
      const sel = document.getElementById(id);
      if (sel) sel.addEventListener("change", function () {
        fitted = false;
        draw();
      });
    });

    loadCsv()
      .then(function (text) {
        const table = parseCsv(text);
        if (!table.length) {
          status("CSV parsed to zero data rows.");
          return;
        }
        allPts = [];
        table.forEach(function (row) {
          const ll = parseLatLon(row);
          if (!ll) return;
          const topicText = val(row, function (n) { return n.indexOf("topic") !== -1; });
          allPts.push({
            row: row,
            ll: ll,
            when: rowTime(row),
            whenLabel: val(row, function (n) { return n.indexOf("time") !== -1 || n.indexOf("stamp") !== -1; }),
            headline: val(row, function (n) { return n === "headline" || n === "title"; }),
            place: val(row, function (n) { return n.indexOf("locationname") !== -1; }),
            href: val(row, function (n) { return n.indexOf("href") !== -1 || n.indexOf("alerturl") !== -1; }),
            topicText: topicText,
            topics: topicIds(topicText)
          });
        });
        if (!allPts.length) {
          status("CSV loaded (" + table.length + " rows) but no numeric lat/lng.");
          return;
        }
        draw();
      })
      .catch(function (err) {
        status("Could not load CSV: " + err.message);
      });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
