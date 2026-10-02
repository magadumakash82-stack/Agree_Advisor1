/**
 * SMART SOIL TESTING & CROP OPTIMIZATION SYSTEM
 * Transparent Crop Scoring Engine & Simulation Controller
 */

let evaluatedCropsData = [];
let liveSoilValues = null;

document.addEventListener('DOMContentLoaded', () => {
  loadLiveConditionsAndEvaluate();

  const simBtn = document.getElementById('runSimulationBtn');
  if (simBtn) {
    simBtn.addEventListener('click', runSimulation);
  }

  const resetBtn = document.getElementById('resetToLiveBtn');
  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      if (liveSoilValues) {
        populateSimulatorInputs(liveSoilValues);
        evaluateSoilData(liveSoilValues, "Reset to Live Telemetry");
      } else {
        loadLiveConditionsAndEvaluate();
      }
    });
  }
});

async function loadLiveConditionsAndEvaluate() {
  try {
    const res = await fetch('/api/latest-soil-data');
    if (!res.ok) return;
    const data = await res.json();

    if (data && data.status !== 'empty') {
      liveSoilValues = data;
      updateConditionHeader(data);
      populateSimulatorInputs(data);
      evaluateSoilData(data, "Live Telemetry");
    } else {
      // Default baseline values
      const fallback = {
        moisture: 48.6,
        temperature: 34.1,
        ec: 1500,
        ph: 6.5,
        nitrogen: 32,
        phosphorus: 37,
        potassium: 48
      };
      liveSoilValues = fallback;
      populateSimulatorInputs(fallback);
      evaluateSoilData(fallback, "Default Soil Baseline");
    }
  } catch (e) {
    console.error("Error loading baseline soil data:", e);
  }
}

function updateConditionHeader(d) {
  document.getElementById('condPH').textContent = d.ph;
  document.getElementById('condMoisture').textContent = d.moisture;
  document.getElementById('condTemp').textContent = d.temperature;
  document.getElementById('condEC').textContent = d.ec;
  document.getElementById('condN').textContent = d.nitrogen;
  document.getElementById('condP').textContent = d.phosphorus;
  document.getElementById('condK').textContent = d.potassium;
}

function populateSimulatorInputs(d) {
  document.getElementById('simPH').value = d.ph;
  document.getElementById('simMoisture').value = d.moisture;
  document.getElementById('simTemp').value = d.temperature;
  document.getElementById('simEC').value = d.ec;
  document.getElementById('simN').value = d.nitrogen;
  document.getElementById('simP').value = d.phosphorus;
  document.getElementById('simK').value = d.potassium;
}

function runSimulation() {
  const simData = {
    ph: parseFloat(document.getElementById('simPH').value) || 6.5,
    moisture: parseFloat(document.getElementById('simMoisture').value) || 50.0,
    temperature: parseFloat(document.getElementById('simTemp').value) || 28.0,
    ec: parseFloat(document.getElementById('simEC').value) || 1200.0,
    nitrogen: parseFloat(document.getElementById('simN').value) || 40.0,
    phosphorus: parseFloat(document.getElementById('simP').value) || 30.0,
    potassium: parseFloat(document.getElementById('simK').value) || 50.0
  };

  updateConditionHeader(simData);
  evaluateSoilData(simData, "Interactive Simulator Profile");
}

async function evaluateSoilData(soilData, sourceLabel) {
  const grid = document.getElementById('cropCardsGrid');
  const countLabel = document.getElementById('cropCountLabel');
  const sourceText = document.getElementById('currentSoilSource');

  if (sourceText) sourceText.textContent = `Source: ${sourceLabel}`;
  if (grid) grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 30px;">Evaluating crops...</div>';

  try {
    const res = await fetch('/api/crops/recommendations', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(soilData)
    });

    if (!res.ok) throw new Error("API error");
    const result = await res.json();
    evaluatedCropsData = result.crops || [];

    if (countLabel) {
      countLabel.textContent = `${evaluatedCropsData.length} Crops Evaluated`;
    }

    renderCropCards(evaluatedCropsData);

  } catch (err) {
    console.error("Crop evaluation error:", err);
    if (grid) grid.innerHTML = '<div style="grid-column: 1/-1; color: #dc2626; text-align: center;">Error evaluating crop recommendations.</div>';
  }
}

function renderCropCards(crops) {
  const grid = document.getElementById('cropCardsGrid');
  if (!grid) return;

  if (crops.length === 0) {
    grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 20px;">No crops found.</div>';
    return;
  }

  let html = '';
  crops.forEach((crop, idx) => {
    let scoreColor = '#15803d';
    let badgeClass = 'badge-optimal';
    if (crop.suitability_percent < 70) {
      scoreColor = '#b45309';
      badgeClass = 'badge-warning';
    }
    if (crop.suitability_percent < 55) {
      scoreColor = '#b91c1c';
      badgeClass = 'badge-critical';
    }

    const p = crop.parameters || {};

    html += `
      <div class="crop-card">
        <div class="crop-card-header">
          <div class="crop-name-wrap">
            <div style="font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">#${idx + 1} &bull; ${crop.category}</div>
            <h3>${crop.crop_name}</h3>
            <span>${crop.scientific_name}</span>
          </div>
          <div class="suitability-score-ring">
            <div class="score-number" style="color: ${scoreColor};">${crop.suitability_percent}%</div>
            <span class="badge ${badgeClass}" style="margin-top: 4px;">${crop.suitability_label}</span>
          </div>
        </div>

        <div class="crop-card-body">
          <div class="crop-details-row">
            <span style="color: var(--text-muted);"><i class="fa-solid fa-droplet" style="color: #0284c7;"></i> Water Need:</span>
            <strong>${crop.water_requirement}</strong>
          </div>
          <div class="crop-details-row">
            <span style="color: var(--text-muted);"><i class="fa-solid fa-mountain" style="color: #854d0e;"></i> Preferred Soil:</span>
            <strong>${crop.preferred_soil}</strong>
          </div>

          <!-- Parameter Compatibility Mini Badges -->
          <div class="param-score-list">
            <div class="param-score-item">
              <span>pH Compatibility:</span>
              <strong style="color: ${getGradeColor(p.ph?.grade)};">${p.ph?.status || '--'}</strong>
            </div>
            <div class="param-score-item">
              <span>Moisture:</span>
              <strong style="color: ${getGradeColor(p.moisture?.grade)};">${p.moisture?.status || '--'}</strong>
            </div>
            <div class="param-score-item">
              <span>EC (Salinity):</span>
              <strong style="color: ${getGradeColor(p.ec?.grade)};">${p.ec?.status || '--'}</strong>
            </div>
            <div class="param-score-item">
              <span>Nitrogen (N):</span>
              <strong style="color: ${getGradeColor(p.nitrogen?.grade)};">${p.nitrogen?.status || '--'}</strong>
            </div>
            <div class="param-score-item">
              <span>Phosphorus (P):</span>
              <strong style="color: ${getGradeColor(p.phosphorus?.grade)};">${p.phosphorus?.status || '--'}</strong>
            </div>
            <div class="param-score-item">
              <span>Potassium (K):</span>
              <strong style="color: ${getGradeColor(p.potassium?.grade)};">${p.potassium?.status || '--'}</strong>
            </div>
          </div>

          <div style="margin-top: 16px; text-align: right;">
            <button class="btn btn-sm btn-outline" onclick="openCropModal('${crop.crop_id}')" style="width: 100%;">
              <i class="fa-solid fa-circle-question"></i> View Scoring Breakdown &rarr;
            </button>
          </div>
        </div>
      </div>
    `;
  });

  grid.innerHTML = html;
}

function getGradeColor(grade) {
  switch (grade) {
    case 'optimal': return '#16a34a';
    case 'moderate': return '#ca8a04';
    case 'suboptimal': return '#ea580c';
    case 'low': return '#dc2626';
    default: return '#64748b';
  }
}

function openCropModal(cropId) {
  const crop = evaluatedCropsData.find(c => c.crop_id === cropId);
  if (!crop) return;

  const modal = document.getElementById('cropDetailModal');
  const title = document.getElementById('modalCropTitle');
  const body = document.getElementById('modalCropBody');

  title.innerHTML = `<i class="fa-solid fa-wheat-awn" style="color: var(--primary);"></i> ${crop.crop_name} &bull; Scoring Breakdown`;

  const p = crop.parameters || {};

  let rows = '';
  const paramTitles = [
    { key: 'ph', name: 'Soil pH', unit: 'scale' },
    { key: 'moisture', name: 'Soil Moisture', unit: '%' },
    { key: 'temperature', name: 'Soil Temperature', unit: '°C' },
    { key: 'ec', name: 'Electrical Conductivity (EC)', unit: 'µS/cm' },
    { key: 'nitrogen', name: 'Nitrogen (N)', unit: 'mg/kg' },
    { key: 'phosphorus', name: 'Phosphorus (P)', unit: 'mg/kg' },
    { key: 'potassium', name: 'Potassium (K)', unit: 'mg/kg' }
  ];

  paramTitles.forEach(item => {
    const evalData = p[item.key] || {};
    rows += `
      <tr>
        <td><strong>${item.name}</strong></td>
        <td>${evalData.actual} ${item.unit}</td>
        <td>${evalData.min} - ${evalData.max} ${item.unit}</td>
        <td><strong style="color: ${getGradeColor(evalData.grade)};">${evalData.status} (${evalData.score}%)</strong></td>
        <td style="font-size: 11px; color: var(--text-muted);">${evalData.details}</td>
      </tr>
    `;
  });

  body.innerHTML = `
    <div style="background: #f0fdf4; border: 1px solid #86efac; border-radius: 8px; padding: 12px; margin-bottom: 16px;">
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
          <h4 style="color: #166534; font-size: 14px; font-weight: 700;">Overall Compatibility: ${crop.suitability_percent}%</h4>
          <p style="font-size: 11.5px; color: #15803d;">${crop.description}</p>
        </div>
        <span class="badge badge-normal" style="font-size: 12px;">${crop.suitability_label}</span>
      </div>
    </div>

    <div class="table-responsive">
      <table class="data-table" style="font-size: 12px;">
        <thead>
          <tr>
            <th>Parameter</th>
            <th>Measured</th>
            <th>Configured Range</th>
            <th>Compatibility</th>
            <th>Agronomic Notes</th>
          </tr>
        </thead>
        <tbody>
          ${rows}
        </tbody>
      </table>
    </div>

    <div style="margin-top: 14px; font-size: 11px; color: var(--text-muted); font-style: italic;">
      Note: Transparency scoring evaluates each physical and nutrient factor against the calibrated optimal agronomic range for this crop.
    </div>
  `;

  modal.classList.add('active');
}

function closeCropModal() {
  const modal = document.getElementById('cropDetailModal');
  if (modal) modal.classList.remove('active');
}
