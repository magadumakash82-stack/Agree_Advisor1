/**
 * SMART SOIL TESTING & CROP OPTIMIZATION SYSTEM
 * Interactive Historical Charting & Paginated Telemetry Table Controller
 */

let historyChart = null;
let currentRange = '24h';
let currentParamView = 'all';
let rawHistoryData = null;
let currentPage = 1;

document.addEventListener('DOMContentLoaded', () => {
  initHistoryChart();
  loadHistoricalData();
  loadTableData(1);

  // Range Selector Buttons
  document.querySelectorAll('.range-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      document.querySelectorAll('.range-btn').forEach(b => {
        b.className = 'btn btn-sm btn-outline range-btn';
      });
      btn.className = 'btn btn-sm btn-primary range-btn';

      const range = btn.getAttribute('data-range');
      currentRange = range;

      const customBar = document.getElementById('customDateRangeBar');
      if (range === 'custom') {
        customBar.style.display = 'flex';
      } else {
        customBar.style.display = 'none';
        loadHistoricalData();
      }
    });
  });

  // Apply Custom Date Range Button
  const applyCustomBtn = document.getElementById('applyCustomRangeBtn');
  if (applyCustomBtn) {
    applyCustomBtn.addEventListener('click', () => {
      loadHistoricalData();
    });
  }

  // Parameter Tabs Selector
  document.querySelectorAll('.param-tab-btn').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.param-tab-btn').forEach(t => {
        t.className = 'btn btn-sm btn-outline param-tab-btn';
      });
      tab.className = 'btn btn-sm btn-primary param-tab-btn';
      currentParamView = tab.getAttribute('data-param');
      renderChartForSelectedView();
    });
  });

  // Table Search Input
  const searchInput = document.getElementById('tableSearchInput');
  if (searchInput) {
    let debounceTimer;
    searchInput.addEventListener('input', () => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        currentPage = 1;
        loadTableData(1);
      }, 350);
    });
  }

  // Refresh Table Button
  const refreshBtn = document.getElementById('refreshTableBtn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      loadTableData(currentPage);
    });
  }

  // Pagination buttons
  const prevBtn = document.getElementById('prevPageBtn');
  const nextBtn = document.getElementById('nextPageBtn');
  if (prevBtn) {
    prevBtn.addEventListener('click', () => {
      if (currentPage > 1) {
        currentPage--;
        loadTableData(currentPage);
      }
    });
  }
  if (nextBtn) {
    nextBtn.addEventListener('click', () => {
      currentPage++;
      loadTableData(currentPage);
    });
  }
});

function initHistoryChart() {
  const ctx = document.getElementById('historicalChart');
  if (!ctx) return;

  historyChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: []
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false
      },
      plugins: {
        legend: {
          position: 'top',
          labels: { boxWidth: 12, font: { size: 11 } }
        },
        tooltip: {
          enabled: true,
          padding: 10
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { maxTicksLimit: 10, font: { size: 10 } }
        },
        y: {
          grid: { color: '#f1f5f9' },
          ticks: { font: { size: 10 } }
        }
      }
    }
  });
}

async function loadHistoricalData() {
  const countEl = document.getElementById('dataPointsCount');
  if (countEl) countEl.textContent = "Loading telemetry data...";

  let url = `/api/soil-history?range=${currentRange}`;
  if (currentRange === 'custom') {
    const s = document.getElementById('startDateInput').value;
    const e = document.getElementById('endDateInput').value;
    if (s) url += `&start_date=${encodeURIComponent(s)}`;
    if (e) url += `&end_date=${encodeURIComponent(e)}`;
  }

  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error("HTTP error " + res.status);
    rawHistoryData = await res.json();

    if (countEl) {
      countEl.textContent = `${rawHistoryData.count} data points recorded`;
    }

    renderChartForSelectedView();

  } catch (err) {
    console.error("Failed to load historical telemetry:", err);
    if (countEl) countEl.textContent = "Error loading history data";
  }
}

function renderChartForSelectedView() {
  if (!historyChart || !rawHistoryData) return;

  const labels = rawHistoryData.timestamps || [];
  const s = rawHistoryData.series || {};
  let datasets = [];

  const heading = document.getElementById('chartHeading');

  if (currentParamView === 'all') {
    if (heading) heading.textContent = "All Soil Parameters Overview";
    datasets = [
      { label: 'Moisture (%)', borderColor: '#0284c7', backgroundColor: 'transparent', data: s.moisture, tension: 0.2 },
      { label: 'Temp (°C)', borderColor: '#ea580c', backgroundColor: 'transparent', data: s.temperature, tension: 0.2 },
      { label: 'pH', borderColor: '#854d0e', backgroundColor: 'transparent', data: s.ph, tension: 0.2 },
      { label: 'EC / 10 (µS/cm)', borderColor: '#9333ea', backgroundColor: 'transparent', data: s.ec.map(v => (v/10).toFixed(1)), tension: 0.2 },
      { label: 'Nitrogen (mg/kg)', borderColor: '#16a34a', backgroundColor: 'transparent', data: s.nitrogen, tension: 0.2 },
      { label: 'Phosphorus (mg/kg)', borderColor: '#dc2626', backgroundColor: 'transparent', data: s.phosphorus, tension: 0.2 },
      { label: 'Potassium (mg/kg)', borderColor: '#4f46e5', backgroundColor: 'transparent', data: s.potassium, tension: 0.2 }
    ];
  } else if (currentParamView === 'moisture') {
    if (heading) heading.textContent = "Soil Moisture vs Time (%)";
    datasets = [
      { label: 'Soil Moisture (%)', borderColor: '#0284c7', backgroundColor: 'rgba(2, 132, 199, 0.15)', fill: true, data: s.moisture, tension: 0.3 }
    ];
  } else if (currentParamView === 'temperature') {
    if (heading) heading.textContent = "Soil Temperature vs Time (°C)";
    datasets = [
      { label: 'Temperature (°C)', borderColor: '#ea580c', backgroundColor: 'rgba(234, 88, 12, 0.15)', fill: true, data: s.temperature, tension: 0.3 }
    ];
  } else if (currentParamView === 'ec') {
    if (heading) heading.textContent = "Electrical Conductivity vs Time (µS/cm)";
    datasets = [
      { label: 'EC (µS/cm)', borderColor: '#9333ea', backgroundColor: 'rgba(147, 51, 234, 0.15)', fill: true, data: s.ec, tension: 0.3 }
    ];
  } else if (currentParamView === 'ph') {
    if (heading) heading.textContent = "Soil pH Level vs Time";
    datasets = [
      { label: 'Soil pH', borderColor: '#854d0e', backgroundColor: 'rgba(133, 77, 14, 0.15)', fill: true, data: s.ph, tension: 0.3 }
    ];
  } else if (currentParamView === 'npk') {
    if (heading) heading.textContent = "Primary Nutrients (N - P - K) vs Time (mg/kg)";
    datasets = [
      { label: 'Nitrogen (N)', borderColor: '#16a34a', backgroundColor: 'transparent', data: s.nitrogen, tension: 0.3 },
      { label: 'Phosphorus (P)', borderColor: '#dc2626', backgroundColor: 'transparent', data: s.phosphorus, tension: 0.3 },
      { label: 'Potassium (K)', borderColor: '#4f46e5', backgroundColor: 'transparent', data: s.potassium, tension: 0.3 }
    ];
  }

  historyChart.data.labels = labels;
  historyChart.data.datasets = datasets;
  historyChart.update();
}

async function loadTableData(page = 1) {
  const search = document.getElementById('tableSearchInput')?.value || '';
  const tbody = document.getElementById('historyTableBody');
  if (!tbody) return;

  try {
    const res = await fetch(`/api/readings-table?page=${page}&per_page=12&search=${encodeURIComponent(search)}`);
    if (!res.ok) return;
    const data = await res.json();

    if (!data.items || data.items.length === 0) {
      tbody.innerHTML = `<tr><td colspan="10" style="text-align:center;padding:24px;color:var(--text-muted);">No records found matching criteria.</td></tr>`;
      document.getElementById('paginationInfo').textContent = "Showing 0 of 0 entries";
      document.getElementById('prevPageBtn').disabled = true;
      document.getElementById('nextPageBtn').disabled = true;
      return;
    }

    let rowsHtml = '';
    data.items.forEach(item => {
      const sourceBadge = item.is_simulated ? 
        '<span class="badge-demo">Demo</span>' : 
        '<span class="badge-live">Hardware</span>';

      rowsHtml += `
        <tr>
          <td><code style="font-weight:600;">${item.formatted_time || item.timestamp}</code></td>
          <td><strong>${item.device_id}</strong></td>
          <td>${item.moisture} %</td>
          <td>${item.temperature} °C</td>
          <td>${item.ec}</td>
          <td>${item.ph}</td>
          <td>${item.nitrogen}</td>
          <td>${item.phosphorus}</td>
          <td>${item.potassium}</td>
          <td>${sourceBadge}</td>
        </tr>
      `;
    });

    tbody.innerHTML = rowsHtml;

    // Update pagination controls
    const startIdx = (data.page - 1) * data.per_page + 1;
    const endIdx = Math.min(data.page * data.per_page, data.total);
    document.getElementById('paginationInfo').textContent = `Showing ${startIdx} to ${endIdx} of ${data.total} records`;
    document.getElementById('prevPageBtn').disabled = !data.has_prev;
    document.getElementById('nextPageBtn').disabled = !data.has_next;

  } catch (e) {
    console.error("Table data load error:", e);
  }
}
