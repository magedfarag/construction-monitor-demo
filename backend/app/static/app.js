const state = {
  config: null,
  drawnLayer: null,
  geometry: null,
  areaKm2: 0,
  analysis: null,
  filteredChanges: [],
};

const map = L.map('map').setView([24.7136, 46.6753], 11);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
  attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

const drawnItems = new L.FeatureGroup();
map.addLayer(drawnItems);

const drawControl = new L.Control.Draw({
  edit: { featureGroup: drawnItems, remove: false },
  draw: {
    polyline: false,
    marker: false,
    circlemarker: false,
    polygon: { allowIntersection: false, showArea: true },
    rectangle: true,
    circle: true,
  }
});
map.addControl(drawControl);

function setMessage(msg, isError = false) {
  const el = document.getElementById('submitMessage');
  el.textContent = msg;
  el.style.color = isError ? '#fca5a5' : '#9ca3af';
}

function updateSelectionUI() {
  document.getElementById('geometryType').textContent = state.geometry ? state.geometry.type : 'None';
  document.getElementById('areaDisplay').textContent = `${state.areaKm2.toFixed(4)} km²`;
  const valid = state.areaKm2 >= 0.01 && state.areaKm2 <= 100;
  document.getElementById('selectionStatus').textContent = state.geometry ? (valid ? 'Valid selection' : 'Outside allowed range') : 'No valid selection';
  document.getElementById('analyzeBtn').disabled = !(state.geometry && valid);
}

function setCurrentLayer(layer) {
  drawnItems.clearLayers();
  drawnItems.addLayer(layer);
  state.drawnLayer = layer;

  let feature = layer.toGeoJSON();
  if (layer instanceof L.Circle) {
    feature = turf.circle([layer.getLatLng().lng, layer.getLatLng().lat], layer.getRadius() / 1000, {
      steps: 64,
      units: 'kilometers',
    });
    feature.properties = { shape: 'Circle', radius_m: layer.getRadius() };
  }

  state.geometry = feature.geometry;
  state.areaKm2 = turf.area(feature) / 1_000_000;
  updateSelectionUI();
}

map.on(L.Draw.Event.CREATED, (event) => setCurrentLayer(event.layer));
map.on(L.Draw.Event.EDITED, (event) => {
  event.layers.eachLayer((layer) => setCurrentLayer(layer));
});

function clearSelection() {
  drawnItems.clearLayers();
  state.drawnLayer = null;
  state.geometry = null;
  state.areaKm2 = 0;
  updateSelectionUI();
  setMessage('Selection cleared.');
}

document.getElementById('clearBtn').addEventListener('click', clearSelection);

document.getElementById('applyBboxBtn').addEventListener('click', () => {
  const minLat = parseFloat(document.getElementById('minLat').value);
  const minLng = parseFloat(document.getElementById('minLng').value);
  const maxLat = parseFloat(document.getElementById('maxLat').value);
  const maxLng = parseFloat(document.getElementById('maxLng').value);
  if ([minLat, minLng, maxLat, maxLng].some(Number.isNaN)) {
    setMessage('Enter all bounding box coordinates before drawing.', true);
    return;
  }
  if (!(minLat < maxLat && minLng < maxLng)) {
    setMessage('Bounding box values are invalid. Min values must be lower than max values.', true);
    return;
  }

  const bounds = [[minLat, minLng], [maxLat, maxLng]];
  const layer = L.rectangle(bounds, { color: '#0ea5e9', weight: 2 });
  setCurrentLayer(layer);
  map.fitBounds(layer.getBounds(), { padding: [20, 20] });
  setMessage('Bounding box applied to the map.');
});

function isoDate(date) {
  return date.toISOString().slice(0, 10);
}

async function loadConfig() {
  const response = await fetch('/api/config');
  const config = await response.json();
  state.config = config;
  document.getElementById('todayBadge').textContent = `Dataset date: ${config.today}`;
  const today = new Date(config.today);
  const start = new Date(today);
  start.setDate(today.getDate() - 30);
  document.getElementById('startDate').value = isoDate(start);
  document.getElementById('endDate').value = isoDate(today);
}

function renderSummary() {
  const summary = document.getElementById('resultsSummary');
  if (!state.analysis) {
    summary.className = 'summary-card empty-state';
    summary.textContent = 'Run an analysis to populate the summary.';
    return;
  }
  const stats = state.analysis.stats;
  summary.className = 'summary-card';
  summary.innerHTML = `
    <div class="meta-grid">
      <div><strong>Analysis ID</strong><br>${state.analysis.analysis_id}</div>
      <div><strong>Provider</strong><br>${state.analysis.provider}</div>
      <div><strong>Area</strong><br>${state.analysis.requested_area_km2.toFixed(4)} km²</div>
      <div><strong>Total changes</strong><br>${stats.total_changes}</div>
      <div><strong>Average confidence</strong><br>${stats.avg_confidence}%</div>
      <div><strong>Window</strong><br>${state.analysis.imagery_window.start_date} to ${state.analysis.imagery_window.end_date}</div>
    </div>
    <div style="margin-top:12px;color:#9ca3af;"><strong>Warnings</strong><br>${state.analysis.warnings.join('<br>')}</div>
  `;
}

function filterChangesByTimeline() {
  if (!state.analysis) return;
  const sliderValue = parseInt(document.getElementById('timelineSlider').value, 10);
  document.getElementById('timelineLabel').textContent = sliderValue === 30
    ? 'Showing all results from last 30 days'
    : `Showing results from the last ${sliderValue} day(s)`;

  const endDate = new Date(state.analysis.imagery_window.end_date);
  const cutoff = new Date(endDate);
  cutoff.setDate(endDate.getDate() - sliderValue);
  state.filteredChanges = state.analysis.changes.filter(change => new Date(change.detected_at) >= cutoff);
  renderResultsList();
}

function renderResultsList() {
  const list = document.getElementById('resultsList');
  if (!state.analysis) {
    list.innerHTML = '';
    return;
  }
  if (state.filteredChanges.length === 0) {
    list.innerHTML = '<div class="summary-card empty-state">No detections match the current timeline filter.</div>';
    return;
  }

  list.innerHTML = state.filteredChanges.map(change => `
    <article class="result-card">
      <div class="result-card-header">
        <div>
          <h3 style="margin:0 0 6px;">${change.change_type}</h3>
          <div class="muted">Detected: ${change.detected_at.replace('T', ' ').slice(0, 16)}</div>
        </div>
        <div class="pill">${change.confidence}% confidence</div>
      </div>
      <p style="margin:0;">${change.summary}</p>
      <div class="result-images">
        <div>
          <div class="muted" style="margin-bottom:6px;">Before</div>
          <img src="${change.before_image}" alt="Before image for ${change.change_type}" />
        </div>
        <div>
          <div class="muted" style="margin-bottom:6px;">After</div>
          <img src="${change.after_image}" alt="After image for ${change.change_type}" />
        </div>
      </div>
      <div class="meta-grid">
        <div><strong>Center</strong><br>${change.center.lat}, ${change.center.lng}</div>
        <div><strong>Bounding box</strong><br>${change.bbox.join(', ')}</div>
        <div><strong>Provider</strong><br>${change.provider}</div>
        <div><strong>Change ID</strong><br>${change.change_id}</div>
      </div>
      <div>
        <strong>Model rationale</strong>
        <ul class="rationale-list">${change.rationale.map(item => `<li>${item}</li>`).join('')}</ul>
      </div>
    </article>
  `).join('');
}

document.getElementById('timelineSlider').addEventListener('input', filterChangesByTimeline);

document.getElementById('analyzeBtn').addEventListener('click', async () => {
  if (!state.geometry) {
    setMessage('Create a valid selection before analyzing.', true);
    return;
  }

  const startDate = document.getElementById('startDate').value;
  const endDate = document.getElementById('endDate').value;
  const provider = document.getElementById('providerSelect').value;
  const btn = document.getElementById('analyzeBtn');
  btn.disabled = true;
  btn.textContent = 'Analyzing...';
  setMessage('Submitting area and simulating construction-change analysis...');

  try {
    const response = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        geometry: state.geometry,
        start_date: startDate,
        end_date: endDate,
        provider,
        area_km2: state.areaKm2,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Analysis failed');
    }

    state.analysis = await response.json();
    state.filteredChanges = [...state.analysis.changes];
    document.getElementById('timelineSlider').value = 30;
    renderSummary();
    filterChangesByTimeline();
    setMessage(`Analysis complete. ${state.analysis.stats.total_changes} change event(s) returned.`);
  } catch (error) {
    state.analysis = null;
    renderSummary();
    renderResultsList();
    setMessage(error.message || 'Analysis failed.', true);
  } finally {
    btn.textContent = 'Analyze Last Month';
    updateSelectionUI();
  }
});

loadConfig().then(() => {
  updateSelectionUI();
  renderSummary();
});
