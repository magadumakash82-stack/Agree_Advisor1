/**
 * SMART SOIL TESTING & CROP OPTIMIZATION SYSTEM
 * Dashboard Real-Time Polling & Reactive Telemetry Controller
 */

let quickChart = null;

// Initialize Dashboard
document.addEventListener('DOMContentLoaded', () => {
  initQuickChart();
  fetchLatestSoilData();

  // Poll every 5 seconds as specified in Section 8
  setInterval(fetchLatestSoilData, 5000);
});

// Expose refresh function globally so Demo toggle can trigger immediate update
window.refreshDashboardData = function() {
  fetchLatestSoilData();
};

async function fetchLatestSoilData() {
  try {
    const res = await fetch('/api/latest-soil-data');
    if (!res.ok) return;
    const data = await res.json();

    if (data.status === 'empty' || !data.device_id) {
      document.getElementById('topLastUpdated').textContent = "No Data";
      document.getElementById('topExactTime').textContent = "Waiting for ESP32";
      return;
    }

    renderParameterCards(data);
    renderTopSummaries(data);
    renderCropTeaser(data);
    renderAlerts(data);
    updateQuickChart(data);

  } catch (err) {
    console.warn("Failed to retrieve latest soil data:", err);
  }
}

function renderTopSummaries(data) {
  // Device ID & Location
  const devIdEl = document.getElementById('topDeviceId');
  if (devIdEl) devIdEl.textContent = data.device_id;

  // Sensor Status & Dot
  const sensorDot = document.getElementById('topSensorDot');
  const sensorStatus = document.getElementById('topSensorStatus');
  if (sensorStatus && sensorDot) {
    sensorStatus.textContent = data.device_status;
    sensorDot.className = 'indicator-dot ' + (data.is_online ? 'online' : 'offline');
  }

  // Health Index
  if (data.health_analysis) {
    const hiEl = document.getElementById('topHealthIndex');
    const hlEl = document.getElementById('topHealthLabel');
    if (hiEl) hiEl.textContent = `${data.health_analysis.health_index}%`;
    if (hlEl) hlEl.textContent = data.health_analysis.health_status;
  }

  // Last Updated
  const lastUpEl = document.getElementById('topLastUpdated');
  const exactEl = document.getElementById('topExactTime');
  if (lastUpEl) {
    if (data.seconds_ago < 5) {
      lastUpEl.textContent = "Just now";
    } else if (data.seconds_ago < 60) {
      lastUpEl.textContent = `${data.seconds_ago}s ago`;
    } else {
      lastUpEl.textContent = `${Math.floor(data.seconds_ago / 60)}m ago`;
    }
  }
  if (exactEl) {
    exactEl.textContent = data.formatted_time || data.timestamp;
  }
}

function renderParameterCards(data) {
  const params = [
    { key: 'moisture', id: 'Moisture', val: data.moisture, unit: '%' },
    { key: 'temperature', id: 'Temperature', val: data.temperature, unit: '°C' },
    { key: 'ec', id: 'EC', val: data.ec, unit: 'µS/cm' },
    { key: 'ph', id: 'PH', val: data.ph, unit: '' },
    { key: 'nitrogen', id: 'Nitrogen', val: data.nitrogen, unit: 'mg/kg' },
    { key: 'phosphorus', id: 'Phosphorus', val: data.phosphorus, unit: 'mg/kg' },
    { key: 'potassium', id: 'Potassium', val: data.potassium, unit: 'mg/kg' },
  ];

  const analysisParams = data.health_analysis?.parameters || {};
  const trends = data.trends || {};

  params.forEach(p => {
    // Value
    const valEl = document.getElementById(`val${p.id}`);
    if (valEl) valEl.textContent = p.val;

    // Badge
    const badgeEl = document.getElementById(`badge${p.id}`);
    const paramMeta = analysisParams[p.key];
    if (badgeEl && paramMeta) {
      badgeEl.textContent = paramMeta.label;
      badgeEl.className = 'badge ' + getBadgeClass(paramMeta.level);
    }

    // Trend
    const trendEl = document.getElementById(`trend${p.id}`);
    const trendData = trends[p.key];
    if (trendEl && trendData) {
      let icon = '<i class="fa-solid fa-minus"></i>';
      let cls = 'trend-stable';
      if (trendData.direction === 'up') {
        icon = '<i class="fa-solid fa-arrow-up"></i>';
        cls = 'trend-up';
      } else if (trendData.direction === 'down') {
        icon = '<i class="fa-solid fa-arrow-down"></i>';
        cls = 'trend-down';
      }
      trendEl.className = `trend-indicator ${cls}`;
      trendEl.innerHTML = `${icon} ${Math.abs(trendData.delta)}`;
    }

    // Time
    const timeEl = document.getElementById(`time${p.id}`);
    if (timeEl) {
      timeEl.textContent = data.seconds_ago < 5 ? "Just now" : `${data.seconds_ago}s ago`;
    }
  });
}

function getBadgeClass(level) {
  switch (level) {
    case 'optimal':
    case 'normal':
      return 'badge-normal';
    case 'warning':
      return 'badge-warning';
    case 'critical':
      return 'badge-critical';
    default:
      return 'badge-normal';
  }
}

async function renderCropTeaser(soilData) {
  const container = document.getElementById('topCropsContainer');
  if (!container) return;

  try {
    const res = await fetch('/api/crops/recommendations', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(soilData)
    });
    if (!res.ok) return;
    const result = await res.json();
    const crops = result.crops || [];

    if (crops.length === 0) {
      container.innerHTML = '<div style="color:var(--text-muted);padding:10px;">No crop data configured.</div>';
      return;
    }

    // Take top 3 crops
    let html = '';
    crops.slice(0, 3).forEach((c, idx) => {
      let badgeStyle = 'background-color:#dcfce7; color:#15803d;';
      if (c.suitability_percent < 70) badgeStyle = 'background-color:#fef3c7; color:#b45309;';
      if (c.suitability_percent < 50) badgeStyle = 'background-color:#fee2e2; color:#b91c1c;';

      html += `
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 10px 14px; background: #f8fafc; border: 1px solid var(--border-light); border-radius: 8px;">
          <div style="display: flex; align-items: center; gap: 10px;">
            <div style="width: 28px; height: 28px; border-radius: 50%; background: #e2e8f0; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 11px;">
              #${idx + 1}
            </div>
            <div>
              <div style="font-weight: 700; font-size: 13.5px;">${c.crop_name}</div>
              <div style="font-size: 11px; color: var(--text-muted);">${c.category} &bull; ${c.water_requirement}</div>
            </div>
          </div>
          <div style="text-align: right;">
            <span style="display: inline-block; padding: 3px 10px; border-radius: 9999px; font-weight: 800; font-size: 12px; ${badgeStyle}">
              ${c.suitability_percent}%
            </span>
            <div style="font-size: 10px; color: var(--text-muted); margin-top: 2px;">${c.suitability_label}</div>
          </div>
        </div>
      `;
    });

    container.innerHTML = html;
  } catch (e) {
    console.error("Crop teaser render error:", e);
  }
}

function renderAlerts(data) {
  const container = document.getElementById('alertsContainer');
  if (!container) return;

  const analysis = data.health_analysis;
  if (!analysis) return;

  const alerts = analysis.alerts || [];
  const recs = analysis.recommendations || [];

  if (alerts.length === 0 && recs.length === 0) {
    container.innerHTML = `
      <div style="padding: 16px; text-align: center; color: var(--primary); background: #f0fdf4; border-radius: 8px;">
        <i class="fa-solid fa-circle-check" style="font-size: 20px; margin-bottom: 6px; display: block;"></i>
        All 7 parameters are within nominal agronomic thresholds!
      </div>
    `;
    return;
  }

  let html = '';
  // Add alerts
  alerts.forEach(al => {
    const isCrit = al.severity === 'critical';
    html += `
      <div style="display: flex; gap: 10px; padding: 10px 14px; border-radius: 8px; font-size: 12px; background: ${isCrit ? '#fee2e2' : '#fef3c7'}; color: ${isCrit ? '#991b1b' : '#92400e'}; border: 1px solid ${isCrit ? '#fca5a5' : '#fcd34d'};">
        <i class="fa-solid fa-triangle-exclamation" style="margin-top: 2px;"></i>
        <div>
          <strong>${al.parameter}:</strong> ${al.message}
        </div>
      </div>
    `;
  });

  // Add top recommendations
  recs.slice(0, 2).forEach(r => {
    html += `
      <div style="display: flex; gap: 10px; padding: 10px 14px; border-radius: 8px; font-size: 12px; background: #f0fdf4; color: #166534; border: 1px solid #86efac;">
        <i class="fa-solid fa-lightbulb" style="margin-top: 2px;"></i>
        <div>
          <strong>${r.title}:</strong> ${r.text}
        </div>
      </div>
    `;
  });

  container.innerHTML = html;
}

function initQuickChart() {
  const ctx = document.getElementById('quickTrendChart');
  if (!ctx) return;

  quickChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [
        {
          label: 'Moisture (%)',
          borderColor: '#0284c7',
          backgroundColor: 'rgba(2, 132, 199, 0.1)',
          data: [],
          tension: 0.3,
          yAxisID: 'y'
        },
        {
          label: 'Temperature (°C)',
          borderColor: '#ea580c',
          backgroundColor: 'transparent',
          data: [],
          tension: 0.3,
          yAxisID: 'y'
        },
        {
          label: 'pH',
          borderColor: '#854d0e',
          backgroundColor: 'transparent',
          data: [],
          tension: 0.3,
          yAxisID: 'y'
        },
        {
          label: 'Nitrogen (mg/kg)',
          borderColor: '#16a34a',
          backgroundColor: 'transparent',
          data: [],
          tension: 0.3,
          yAxisID: 'y'
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false
      },
      plugins: {
        legend: { position: 'top' },
        tooltip: { enabled: true }
      },
      scales: {
        x: {
          grid: { display: false }
        },
        y: {
          type: 'linear',
          display: true,
          position: 'left',
          grid: { color: '#f1f5f9' }
        }
      }
    }
  });

  // Load initial history for chart
  fetchHistoryForQuickChart();
}

async function fetchHistoryForQuickChart() {
  try {
    const res = await fetch('/api/soil-history?range=24h');
    if (!res.ok) return;
    const history = await res.json();
    if (!history.timestamps || history.timestamps.length === 0) return;

    if (quickChart) {
      quickChart.data.labels = history.timestamps.slice(-15);
      quickChart.data.datasets[0].data = history.series.moisture.slice(-15);
      quickChart.data.datasets[1].data = history.series.temperature.slice(-15);
      quickChart.data.datasets[2].data = history.series.ph.slice(-15);
      quickChart.data.datasets[3].data = history.series.nitrogen.slice(-15);
      quickChart.update();
    }
  } catch (e) {
    console.warn("Could not load initial quick chart history:", e);
  }
}

function updateQuickChart(latestReading) {
  if (!quickChart || !latestReading.timestamp) return;

  const timeLabel = latestReading.formatted_time?.split(' ')[1] || new Date().toLocaleTimeString();

  // If this timestamp isn't already the last label
  const labels = quickChart.data.labels;
  if (labels.length === 0 || labels[labels.length - 1] !== timeLabel) {
    labels.push(timeLabel);
    quickChart.data.datasets[0].data.push(latestReading.moisture);
    quickChart.data.datasets[1].data.push(latestReading.temperature);
    quickChart.data.datasets[2].data.push(latestReading.ph);
    quickChart.data.datasets[3].data.push(latestReading.nitrogen);

    // Keep max 15 points in the quick trend chart
    if (labels.length > 15) {
      labels.shift();
      quickChart.data.datasets.forEach(ds => ds.data.shift());
    }

    quickChart.update('none'); // Update smoothly without full animation
  }
}
