const usuarioSelect = document.getElementById("filtro-usuario");
const materiaSelect = document.getElementById("filtro-materia");
const statusEl = document.getElementById("status");
const tituloEl = document.getElementById("titulo-reporte");
const notaEl = document.getElementById("nota-reporte");

let chartEstados;
let chartMaterias;

Chart.defaults.font.family = "'Plus Jakarta Sans', sans-serif";
Chart.defaults.color = "#66768a";

function fillSelect(select, items, placeholder) {
  select.innerHTML = `<option value="">${placeholder}</option>`;
  for (const item of items) {
    const option = document.createElement("option");
    option.value = item.id;
    option.textContent = item.extra ? `${item.nombre} · ${item.extra}` : item.nombre;
    select.appendChild(option);
  }
}

async function fetchJson(url) {
  const response = await fetch(url);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.mensaje || `Error ${response.status}`);
  }
  return data;
}

function setKpi(id, value) {
  document.getElementById(id).textContent = value;
}

function porcentaje(completadas, total) {
  if (!total) return 0;
  return Math.round((completadas / total) * 100);
}

function renderMaterias(items, tareas) {
  const body = document.querySelector("#tabla-materias tbody");
  body.innerHTML = "";
  let filas = items || [];
  if (!filas.length && tareas) {
    filas = [{
      materia_id: "-",
      nombre: "Resumen del filtro",
      tareas_completadas: tareas.completadas,
      tareas_total: tareas.total,
    }];
  }
  if (!filas.length) {
    body.innerHTML = `<tr><td colspan="4">Sin materias en este reporte.</td></tr>`;
    return;
  }
  for (const item of filas) {
    const pct = porcentaje(item.tareas_completadas, item.tareas_total);
    body.innerHTML += `
      <tr>
        <td>
          <span class="materia-name">${item.nombre}</span>
          <span class="materia-id">materia_id ${item.materia_id}</span>
        </td>
        <td>
          <div class="bar" title="${pct}%"><i style="width:${pct}%"></i></div>
        </td>
        <td>${item.tareas_completadas}</td>
        <td>${item.tareas_total}</td>
      </tr>`;
  }
}

function drawCharts(tareas, materias) {
  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { position: "bottom", labels: { boxWidth: 12, usePointStyle: true } } },
  };

  chartEstados?.destroy();
  chartEstados = new Chart(document.getElementById("chart-estados"), {
    type: "doughnut",
    data: {
      labels: ["Pendientes", "Completadas", "Vencidas"],
      datasets: [{
        data: [tareas.pendientes, tareas.completadas, tareas.vencidas],
        backgroundColor: ["#c99212", "#1f8a5b", "#c44536"],
        borderWidth: 0,
        hoverOffset: 6,
      }],
    },
    options: { ...chartOptions, cutout: "62%" },
  });

  chartMaterias?.destroy();
  chartMaterias = new Chart(document.getElementById("chart-materias"), {
    type: "bar",
    data: {
      labels: (materias || []).map((item) => item.nombre),
      datasets: [{
        label: "Tareas",
        data: (materias || []).map((item) => item.tareas_total),
        backgroundColor: "#16497a",
        borderRadius: 8,
        maxBarThickness: 42,
      }],
    },
    options: {
      ...chartOptions,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false } },
        y: { beginAtZero: true, ticks: { stepSize: 1 }, grid: { color: "#eef3f8" } },
      },
    },
  });
}

function pintar(reporte, etiqueta) {
  const tareas = reporte.tareas;
  const grupos = reporte.grupos || { grupos_activos: 0, total_grupos: 0 };
  const materias = reporte.materias || [];
  setKpi("kpi-pendientes", tareas.pendientes);
  setKpi("kpi-completadas", tareas.completadas);
  setKpi("kpi-vencidas", tareas.vencidas);
  setKpi("kpi-porcentaje", `${tareas.porcentaje_completado}%`);
  setKpi("kpi-grupos", `${grupos.grupos_activos}/${grupos.total_grupos}`);
  tituloEl.textContent = etiqueta;
  notaEl.textContent = `${tareas.total} tareas · fecha de cálculo ${reporte.fecha_calculo}`;
  drawCharts(tareas, materias);
  renderMaterias(materias, tareas);
  statusEl.textContent = "Caché local en SQLite · este servicio no es dueño de las tareas, solo las agrega.";
}

async function cargar() {
  statusEl.textContent = "Cargando estadísticas...";
  try {
    if (usuarioSelect.value) {
      const reporte = await fetchJson(`/api/v1/estadisticas/usuario/${usuarioSelect.value}`);
      pintar(reporte, reporte.nombre);
      return;
    }
    if (materiaSelect.value) {
      const reporte = await fetchJson(`/api/v1/estadisticas/materia/${materiaSelect.value}`);
      pintar(reporte, reporte.nombre);
      return;
    }
    if (usuarioSelect.options.length > 1) {
      usuarioSelect.value = usuarioSelect.options[1].value;
      const reporte = await fetchJson(`/api/v1/estadisticas/usuario/${usuarioSelect.value}`);
      pintar(reporte, reporte.nombre);
      return;
    }
    tituloEl.textContent = "Sin datos";
    statusEl.textContent = "No hay usuarios en la caché local.";
  } catch (error) {
    tituloEl.textContent = "No se pudo cargar el reporte";
    statusEl.textContent = error.message;
  }
}

async function iniciar() {
  const [usuarios, materias] = await Promise.all([
    fetchJson("/api/v1/estadisticas/catalogo/usuarios"),
    fetchJson("/api/v1/estadisticas/catalogo/materias"),
  ]);
  fillSelect(usuarioSelect, usuarios, "Selecciona un estudiante");
  fillSelect(materiaSelect, materias, "Todas las materias");
  usuarioSelect.addEventListener("change", () => {
    if (usuarioSelect.value) materiaSelect.value = "";
    cargar();
  });
  materiaSelect.addEventListener("change", () => {
    if (materiaSelect.value) usuarioSelect.value = "";
    cargar();
  });
  await cargar();
}

iniciar();
