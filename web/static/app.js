// ===================== CONFIG =====================
const USE_API = true;              // true: FastAPI + SQLite
const API_BASE = '';               // cùng origin
const HISTORY_DAYS = 180;          // preload để cuộn mượt
const WINDOW_DAYS = 7;            // luôn hiển thị 7 cột

// ===================== STATE ======================
let feedings = [];                 // {id?, date:'YYYY-MM-DD', time:'HH:MM', amount:number, type:'me'|'pre'|'sct'}
let selectedDate = isoToday();
let historyDays = [];
let currentEndIdx = 0;
let weeklyChart = null;

// ===================== HELPERS ====================
function pad(n) { return String(n).padStart(2, '0'); }
function isoToday() { const d = new Date(); d.setHours(0, 0, 0, 0); return d.toISOString().slice(0, 10); }
function nowHHMM() { const d = new Date(); return `${pad(d.getHours())}:${pad(d.getMinutes())}`; }
function sortFeedings() {
    feedings.sort((a, b) => a.date === b.date ? a.time.localeCompare(b.time) : a.date.localeCompare(b.date));
}
function rangeLastNDates(n, endISO) {
    const [y, m, d] = endISO.split('-').map(Number);
    const end = new Date(Date.UTC(y, m - 1, d));
    const out = [];
    for (let i = n - 1; i >= 0; i--) { const t = new Date(end); t.setUTCDate(end.getUTCDate() - i); out.push(t.toISOString().slice(0, 10)); }
    return out;
}
function buildHistory(endISO) { return rangeLastNDates(HISTORY_DAYS, endISO); }
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
function setDefaultDateTime(dateInput, timeInput) {
    const today = isoToday();
    if (dateInput && 'valueAsDate' in dateInput) dateInput.valueAsDate = new Date();
    if (dateInput) dateInput.value = today;
    if (timeInput) timeInput.value = nowHHMM();
    selectedDate = today;
}

// ===================== API ========================
async function apiListByDate(dateISO) {
    const res = await fetch(`${API_BASE}/feedings?date=${dateISO}`);
    if (!res.ok) throw new Error('API list error');
    return await res.json();
}
async function apiCreate({ date, time, amount, type }) {
    const res = await fetch(`${API_BASE}/feedings`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ date, time, milk_type: type, amount })
    });
    if (!res.ok) throw new Error('API create error');
    return await res.json();
}
async function apiDelete(id) {
    const res = await fetch(`${API_BASE}/feedings/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('API delete error');
}

// preload nhiều ngày
async function loadInitialHistory(endISO) {
    if (!USE_API) return;
    const days = rangeLastNDates(HISTORY_DAYS, endISO);
    const reqs = days.map(d => apiListByDate(d).then(rows => rows.map(r => ({
        id: r.id, date: r.date, time: r.time, amount: r.amount, type: r.milk_type
    }))));
    const all = await Promise.all(reqs);
    feedings = all.flat(); sortFeedings();
}

// load 1 ngày
async function loadDay(dateISO, listEl, tRefs, chartCanvas, slider, aggRefs = null) {
    if (USE_API) {
        const rows = await apiListByDate(dateISO);
        feedings = feedings.filter(f => f.date !== dateISO);
        for (const r of rows) { feedings.push({ id: r.id, date: r.date, time: r.time, amount: r.amount, type: r.milk_type }); }
        sortFeedings(); rebuildDatasets();
    }
    renderListForDate(dateISO, listEl, tRefs, aggRefs);
    setWindowRightAt(dateISO, chartCanvas, slider);
}

// ===================== CHART ======================
// Plugin hiển thị tổng trên đầu mỗi cột
// ===== Plugin: vẽ tổng trên đỉnh cột stack (Chart.js v3/v4) =====
// ====== Pretty total-on-bar (pill) for Chart.js v3/v4 ======
const totalLabels = {
    id: 'totalLabels',
    afterDatasetsDraw(chart) {
        const { ctx, data, chartArea, scales } = chart;
        const x = scales?.x, y = scales?.y;
        if (!x || !y) return;

        const iMin = Math.round(x.min ?? 0);
        const iMax = Math.round(x.max ?? (data.labels.length - 1));
        const meta0 = chart.getDatasetMeta(0);
        if (!meta0 || !meta0.data) return;

        // helper: rounded rect
        function roundRect(c, x, y, w, h, r) {
            const rr = Math.min(r, h / 2, w / 2);
            c.beginPath();
            c.moveTo(x + rr, y);
            c.arcTo(x + w, y, x + w, y + h, rr);
            c.arcTo(x + w, y + h, x, y + h, rr);
            c.arcTo(x, y + h, x, y, rr);
            c.arcTo(x, y, x + w, y, rr);
            c.closePath();
        }

        ctx.save();
        ctx.rect(chartArea.left, chartArea.top, chartArea.right - chartArea.left, chartArea.bottom - chartArea.top);
        ctx.clip();

        const baseFont = 12; // px
        ctx.font = `${baseFont}px ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';

        for (let i = iMin; i <= iMax; i++) {
            // tổng theo cột
            let sum = 0;
            for (const ds of data.datasets) {
                const v = Number(ds.data?.[i] ?? 0);
                if (!Number.isNaN(v)) sum += v;
            }
            if (sum <= 0) continue;

            const el = meta0.data[i];
            if (!el) continue;

            const text = String(sum);
            const padX = 8, padY = 4, radius = 10;
            const metrics = ctx.measureText(text);
            const w = Math.ceil(metrics.width) + padX * 2;
            const h = baseFont + padY * 2;

            const cx = el.x;
            // hơi cao hơn đỉnh stack
            let cy = y.getPixelForValue(sum) - 10 - h / 2;
            cy = Math.max(chartArea.top + h / 2 + 6, Math.min(cy, chartArea.bottom - h / 2 - 6));

            // nền pill (semi-transparent)
            const bgX = cx - w / 2, bgY = cy - h / 2;

            // thêm shadow
            ctx.shadowColor = 'rgba(0,0,0,0.35)';
            ctx.shadowBlur = 6;
            ctx.shadowOffsetY = 2;

            // nền sáng mờ
            ctx.fillStyle = 'rgba(255,255,255,0.92)';
            roundRect(ctx, bgX, bgY, w, h, radius);
            ctx.fill();

            // viền mảnh
            ctx.shadowColor = 'transparent';
            ctx.lineWidth = 1;
            ctx.strokeStyle = 'rgba(0,0,0,0.08)';
            roundRect(ctx, bgX, bgY, w, h, radius);
            ctx.stroke();

            // chữ đậm, màu tối dễ đọc
            ctx.fillStyle = '#0f172a'; // slate-900
            ctx.fillText(text, cx, cy);
        }

        ctx.restore();
    }
};

if (window.Chart?.register) Chart.register(totalLabels);

function createChart(chartCanvas) {
    if (!chartCanvas) { console.error('weeklyChart canvas không tồn tại'); return; }
    const ctx = chartCanvas.getContext('2d');
    weeklyChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: [], datasets: [
                { label: 'me', data: [], stack: 'milk', borderWidth: 1, backgroundColor: '#4CC9F0' },
                { label: 'pre', data: [], stack: 'milk', borderWidth: 1, backgroundColor: '#F72585' },
                { label: 'sct', data: [], stack: 'milk', borderWidth: 1, backgroundColor: '#FFB703' },
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false, animation: false,
            scales: { x: { stacked: true, min: 0, max: WINDOW_DAYS - 1 }, y: { stacked: true, beginAtZero: true, title: { display: true, text: 'ml' } } },
            plugins: { legend: { position: 'bottom' } }
        },
        plugins: [totalLabels]
    });
}
function rebuildDatasets() {
    if (!weeklyChart) return;
    const buckets = Object.fromEntries(historyDays.map(d => [d, { me: 0, pre: 0, sct: 0 }]));
    for (const f of feedings) { if (buckets[f.date]) buckets[f.date][f.type] += Number(f.amount) || 0; }
    weeklyChart.data.labels = historyDays.map(d => d.slice(5)); // MM-DD
    weeklyChart.data.datasets[0].data = historyDays.map(d => buckets[d].me);
    weeklyChart.data.datasets[1].data = historyDays.map(d => buckets[d].pre);
    weeklyChart.data.datasets[2].data = historyDays.map(d => buckets[d].sct);
    weeklyChart.update();
}
function setWindowRightAt(dateISO, chartCanvas, slider) {
    if (!historyDays.includes(dateISO)) {
        historyDays = buildHistory(dateISO);
        rebuildDatasets();
        if (slider) slider.max = String(historyDays.length - 1);
    }
    const idx = historyDays.indexOf(dateISO);
    currentEndIdx = idx;
    const start = Math.max(0, idx - (WINDOW_DAYS - 1));
    if (weeklyChart) {
        weeklyChart.options.scales.x.min = start;
        weeklyChart.options.scales.x.max = start + (WINDOW_DAYS - 1);
        weeklyChart.update('none');
    }
    if (slider) slider.value = String(idx);
}

// ===================== RENDERERS ==================
function renderListForDate(dISO, listEl, tRefs, aggRefs = null) {
    if (!listEl) { console.error('list element không tồn tại'); return; }
    listEl.innerHTML = '';
    const items = feedings.filter(f => f.date === dISO);

    if (items.length === 0) {
        listEl.innerHTML = '<li class="feed-item"><span class="meta">Chưa có dữ liệu</span></li>';
        renderTotals({ me: 0, pre: 0, sct: 0 }, tRefs);
        if (aggRefs?.aggModeEl) renderAggregateTotals(aggRefs);
        return;
    }

    for (const f of items) {
        const li = document.createElement('li');
        li.className = 'feed-item';
        li.dataset.id = f.id ?? '';
        li.innerHTML = `
      <div>
        <div><strong>${f.time}</strong> • ${f.amount} ml</div>
        <div class="meta">${f.date}</div>
      </div>
      <div class="actions">
        <span class="badge ${f.type}">${f.type}</span>
        <button class="btn danger btn-del" title="Xoá">✕</button>
      </div>`;
        listEl.appendChild(li);
    }

    listEl.querySelectorAll('.btn-del').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const li = e.currentTarget.closest('li');
            const id = li?.dataset.id;
            if (!id) return;
            if (!confirm('Xoá bản ghi này?')) return;
            try { if (USE_API) await apiDelete(id); }
            catch (err) { console.error(err); alert('Xoá thất bại khi gọi API.'); return; }
            feedings = feedings.filter(x => String(x.id) !== String(id));
            sortFeedings(); rebuildDatasets();
            renderListForDate(dISO, listEl, tRefs, aggRefs);
            if (aggRefs?.aggModeEl) renderAggregateTotals(aggRefs);
        });
    });

    const totals = { me: 0, pre: 0, sct: 0 };
    for (const f of items) { totals[f.type] += Number(f.amount) || 0; }
    renderTotals(totals, tRefs);
    if (aggRefs?.aggModeEl) renderAggregateTotals(aggRefs);
}

function renderTotals(t, { tMe, tPre, tSct, tAll }) {
    if (!tMe) return;
    tMe.textContent = t.me || 0;
    tPre.textContent = t.pre || 0;
    tSct.textContent = t.sct || 0;
    tAll.textContent = (t.me || 0) + (t.pre || 0) + (t.sct || 0);
}

// ======= Tổng theo loại: WEEK / MONTH / YEAR =======
function renderAggregateTotals(aggRefs) {
    const { aggModeEl, aggMonthEl, aggYearEl, aggExtraEl, tRefs } = aggRefs;
    if (!aggModeEl) return;
    const mode = aggModeEl.value; // 'week' | 'month' | 'year'
    let items = [], label = '';

    if (mode === 'week') {
        const days = rangeLastNDates(7, selectedDate);
        const set = new Set(days);
        label = `${days[0]} → ${days[6]}`;
        items = feedings.filter(f => set.has(f.date));
    } else if (mode === 'month') {
        const ym = (aggMonthEl?.value) || isoToday().slice(0, 7);
        label = ym;
        items = feedings.filter(f => f.date.startsWith(ym));
    } else {
        const y = (aggYearEl?.value) || isoToday().slice(0, 4);
        label = y;
        items = feedings.filter(f => f.date.startsWith(`${y}-`));
    }

    const totals = { me: 0, pre: 0, sct: 0 };
    for (const it of items) { totals[it.type] += Number(it.amount) || 0; }
    const totalAll = totals.me + totals.pre + totals.sct;

    renderTotals(totals, tRefs);

    if (!aggExtraEl) return;
    if (mode === 'year') {
        const months = new Set(items.map(i => i.date.slice(0, 7))).size;
        const avg = months ? Math.round(totalAll / months) : 0;
        aggExtraEl.textContent = `Năm ${label} • Trung bình mỗi tháng (chỉ ${months} tháng có dữ liệu): ${avg} ml`;
    } else {
        const days = new Set(items.map(i => i.date)).size;
        const avg = days ? Math.round(totalAll / days) : 0;
        const scope = (mode === 'week') ? `Tuần ${label}` : `Tháng ${label}`;
        aggExtraEl.textContent = `${scope} • Trung bình mỗi ngày (chỉ ${days} ngày có dữ liệu): ${avg} ml`;
    }
}
function syncAggInputsVisibility({ aggModeEl, aggMonthEl, aggYearEl }) {
    if (!aggModeEl) return;
    const mode = aggModeEl.value;
    if (mode === 'week') {
        aggMonthEl?.classList.add('hidden');
        aggYearEl?.classList.add('hidden');
    } else if (mode === 'month') {
        aggMonthEl?.classList.remove('hidden');
        aggYearEl?.classList.add('hidden');
    } else {
        aggMonthEl?.classList.add('hidden');
        aggYearEl?.classList.remove('hidden');
    }
}

// ===================== BOOT =======================
document.addEventListener('DOMContentLoaded', async () => {
    // ---- DOM refs ----
    const dateInput = document.getElementById('picker-date');
    const listEl = document.getElementById('day-list');
    const tRefs = {
        tMe: document.getElementById('t-me'),
        tPre: document.getElementById('t-pre'),
        tSct: document.getElementById('t-sct'),
        tAll: document.getElementById('t-all'),
    };
    const timeInput = document.getElementById('time');
    const amountInput = document.getElementById('amount');
    const typeSelect = document.getElementById('type');
    const form = document.getElementById('feed-form');
    const slider = document.getElementById('day-slider');
    const chartWrap = document.querySelector('.chart-wrap');
    const chartCanvas = document.getElementById('weeklyChart');
    const minus10 = document.getElementById('minus10');
    const plus10 = document.getElementById('plus10');

    // Agg panel refs
    const aggModeEl = document.getElementById('agg-mode');
    const aggMonthEl = document.getElementById('agg-month');
    const aggYearEl = document.getElementById('agg-year');
    const aggExtraEl = document.getElementById('agg-extra');
    const aggRefs = { aggModeEl, aggMonthEl, aggYearEl, aggExtraEl, tRefs };

    // 1) defaults
    setDefaultDateTime(dateInput, timeInput);

    // 2) chart + history + slider
    if (!window.Chart) { console.error('Chart.js chưa load'); return; }
    createChart(chartCanvas);
    historyDays = buildHistory(selectedDate);
    if (slider) {
        slider.max = String(historyDays.length - 1);
        slider.value = String(historyDays.length - 1);
    }

    // 3) preload + vẽ ban đầu
    await loadInitialHistory(selectedDate);
    rebuildDatasets();
    await loadDay(selectedDate, listEl, tRefs, chartCanvas, slider, aggRefs);

    // 4) Agg panel
    if (aggModeEl) {
        aggModeEl.value = 'week';
        if (aggMonthEl) aggMonthEl.value = isoToday().slice(0, 7);
        if (aggYearEl) aggYearEl.value = isoToday().slice(0, 4);
        syncAggInputsVisibility(aggRefs);
        renderAggregateTotals(aggRefs);

        aggModeEl.addEventListener('change', () => {
            syncAggInputsVisibility(aggRefs);
            renderAggregateTotals(aggRefs);
        });
        aggMonthEl?.addEventListener('change', () => renderAggregateTotals(aggRefs));
        aggYearEl?.addEventListener('change', () => renderAggregateTotals(aggRefs));
    }

    // 5) events
    dateInput?.addEventListener('change', async e => {
        selectedDate = e.target.value || isoToday();
        await loadDay(selectedDate, listEl, tRefs, chartCanvas, slider, aggRefs);
        if (aggModeEl) renderAggregateTotals(aggRefs);
    });

    form?.addEventListener('submit', async e => {
        e.preventDefault();
        const time = timeInput.value, amount = amountInput.value, type = typeSelect.value;
        if (!time || !amount || !type) return;

        let created = null;
        if (USE_API) created = await apiCreate({ date: selectedDate, time, amount: Number(amount), type });
        feedings.push({
            id: created?.id ?? (crypto.randomUUID?.() ?? Math.random()),
            date: selectedDate, time, amount: Number(amount), type
        });
        sortFeedings(); rebuildDatasets();
        await loadDay(selectedDate, listEl, tRefs, chartCanvas, slider, aggRefs);
        if (aggModeEl) renderAggregateTotals(aggRefs);

        timeInput.value = nowHHMM();
        amountInput.value = '';
        typeSelect.value = 'me';
    });

    minus10?.addEventListener('click', () => {
        const v = Math.max(0, (Number(amountInput.value) || 0) - 10);
        amountInput.value = String(v);
    });
    plus10?.addEventListener('click', () => {
        const v = (Number(amountInput.value) || 0) + 10;
        amountInput.value = String(v);
    });

    slider?.addEventListener('input', async () => {
        const idx = Number(slider.value);
        const iso = historyDays[idx];
        selectedDate = iso;
        if (dateInput) dateInput.value = iso;
        await loadDay(selectedDate, listEl, tRefs, chartCanvas, slider, aggRefs);
        if (aggModeEl) renderAggregateTotals(aggRefs);
    });

    chartWrap?.addEventListener('wheel', async (e) => {
        e.preventDefault();
        const step = Math.sign(e.deltaY) || 1;
        const maxIdx = historyDays.length - 1;
        const minIdx = WINDOW_DAYS - 1;
        const nextIdx = clamp(currentEndIdx + step, minIdx, maxIdx);
        if (nextIdx === currentEndIdx) return;
        currentEndIdx = nextIdx;
        const iso = historyDays[currentEndIdx];
        selectedDate = iso;
        if (dateInput) dateInput.value = iso;
        if (slider) slider.value = String(currentEndIdx);
        await loadDay(selectedDate, listEl, tRefs, chartCanvas, slider, aggRefs);
        if (aggModeEl) renderAggregateTotals(aggRefs);
    }, { passive: false });

    // Auto sang ngày mới sau 0h
    setInterval(async () => {
        const today = isoToday();
        if (today !== selectedDate) {
            selectedDate = today;
            if (dateInput) dateInput.value = today;
            if (timeInput) timeInput.value = nowHHMM();
            await loadDay(selectedDate, listEl, tRefs, chartCanvas, slider, aggRefs);
            if (aggModeEl) renderAggregateTotals(aggRefs);
        }
    }, 60_000);
});
