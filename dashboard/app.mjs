import { ZONES, LABELS, escapeHTML as h, timeLabel, filterEvents, csv, stateFromEvents, demoEvent, initialDemo, reading } from './model.mjs';
const $ = id => document.getElementById(id);
const icon = name => `<svg class="icon" aria-hidden="true"><use href="#i-${name}"/></svg>`;
let demo = true;
let demoEvents = initialDemo();
let real = { zonas: [], eventos: [], total_eventos: 0, actualizado: null, mqtt: { configurado: false, conectado: false } };
let backendOK = false;
let selected = 'SALA';
let view = 'inicio';
let limit = 50;
let manual = new Set();
let toastTimer;
const headings = {
  inicio: ['Vista general', 'Todo en su mejor luz', 'Un vistazo a tus espacios. El control, donde debe estar.'],
  zonas: ['Mis zonas', 'Espacios que responden a ti', 'Tres zonas, tres sensores. Una casa más inteligente.'],
  actividad: ['Actividad', 'Cada cambio cuenta', 'Un registro claro de lo que sucede en tu hogar.'],
  conexion: ['Conexión', 'Siempre al tanto', 'Datos locales, conexiones claras y el control en tu ESP32.'],
};
const events = () => demo ? demoEvents : real.eventos;
function zones() {
  if (demo) return stateFromEvents(demoEvents);
  const fromHistory = stateFromEvents(real.eventos);
  return ZONES.map(z => {
    const current = real.zonas.find(v => v.nombre === z.id || v.zona === z.id);
    const local = fromHistory.find(v => v.id === z.id);
    return { ...local, ...(current ? { luz: current.luz, recibido: current.recibido, evento: current.evento, lectura: current.lectura ?? local.lectura, presencia: current.presencia ?? local.presencia } : {}) };
  });
}
function toast(message) { clearTimeout(toastTimer); $('toast').textContent = message; $('toast').hidden = false; toastTimer = setTimeout(() => $('toast').hidden = true, 5000); }
function setView(next) {
  view = headings[next] ? next : 'inicio';
  const [label, title, description] = headings[view];
  $('breadcrumb').textContent = label; $('page-title').innerHTML = `${h(title)}<span>.</span>`; $('page-description').textContent = description;
  $('overview').hidden = view !== 'inicio'; $('zones-view').hidden = view !== 'zonas'; $('activity-view').hidden = view !== 'actividad'; $('connection-view').hidden = view !== 'conexion';
  document.querySelectorAll('.nav-item').forEach(b => { const active = b.dataset.view === view; b.classList.toggle('active', active); if (active) b.setAttribute('aria-current', 'page'); else b.removeAttribute('aria-current'); });
  setMenu(false); history.replaceState(null, '', '#' + view);
}
function setDemo(value) { demo = value; render(); toast(demo ? 'Demos activadas. Los controles no afectan a la placa.' : 'Modo conectado: solo se muestran eventos recibidos por el backend.'); }
function card(zone, expanded = false) {
  const on = zone.luz === true, unknown = zone.luz === null;
  return `<article class="zone-card ${on ? 'on' : ''} ${selected === zone.id ? 'selected' : ''}"><div class="zone-card-top"><button class="zone-title-button" data-select="${zone.id}" aria-label="Ver ${h(zone.name)}"><span class="zone-bulb">${icon('bulb')}</span><span><span class="zone-name">${zone.name}</span><span class="zone-subtitle">${zone.sensor} · ${demo && manual.has(zone.id) ? 'Manual · demo' : 'Automático'}</span></span></button><button class="switch" role="switch" aria-label="${on ? 'Apagar' : 'Encender'} ${h(zone.name)}${demo ? ' en demostración' : ' (control real no disponible)'}" aria-checked="${on}" data-toggle="${zone.id}" ${demo ? '' : 'disabled'} title="${demo ? 'Control simulado, sin efecto en el ESP32' : 'El firmware aún no admite comandos remotos'}"></button></div>${expanded ? `<div class="expanded-content"><span class="expanded-label">${zone.subtitle}</span><div class="expanded-value">${h(reading(zone))}</div><p class="zone-description">${zone.description}</p><div class="control-mode"><span>Control ${manual.has(zone.id) && demo ? 'manual · demo' : 'automático'}</span><button class="auto-button ${manual.has(zone.id) && demo ? 'manual' : ''}" data-auto="${zone.id}" ${demo ? '' : 'disabled'}>${manual.has(zone.id) && demo ? 'Volver a auto' : 'Auto activo'}</button></div></div>` : ''}<div class="zone-card-bottom"><span class="zone-light-state"><i class="tiny-dot"></i>${unknown ? 'Sin datos' : on ? 'Luz encendida' : 'Luz apagada'}</span><span class="zone-reading">${h(reading(zone))}</span></div></article>`;
}
function eventTable(rows, empty = 'Tu hogar aún no tiene eventos') {
  if (!rows.length) return `<div class="empty-state">${icon('activity')}<b>${h(empty)}</b><p>${demo ? 'Prueba los controles de las zonas o cambia los filtros.' : 'Importa eventos JSON o configura el receptor MQTT para comenzar.'}</p></div>`;
  return `<div class="table-scroll"><table><thead><tr><th>HORA</th><th>ESPACIO</th><th>EVENTO</th><th>SENSOR / VALOR</th><th>ORIGEN</th></tr></thead><tbody>${rows.map(e => `<tr><td class="time-cell">${timeLabel(e.recibido)}</td><td class="event-zone">${ZONES.find(z => z.id === e.zona)?.name ?? h(e.zona)}</td><td><span class="event-tag ${['LUZ_ENCENDIDA','OSCURIDAD'].includes(e.evento) ? 'light' : ''}"><i class="tiny-dot"></i>${h(LABELS[e.evento] ?? e.evento)}</span></td><td>${h(e.sensor)}${e.valor !== '' && e.valor !== null && e.valor !== undefined ? ' · ' + h(e.valor) : ''}</td><td class="source-label">${demo ? 'Demo local' : h(e.dispositivo)}</td></tr>`).join('')}</tbody></table></div>`;
}
function renderHistory() {
  const filtered = filterEvents(events(), $('zone-filter').value, $('event-search').value);
  $('history-events').innerHTML = eventTable(filtered.slice(0, limit), events().length ? 'No encontramos eventos con esos filtros' : undefined);
  $('filtered-count').textContent = `${filtered.length} eventos${!demo && real.total_eventos > real.eventos.length ? ' recientes' : ''}`;
  $('load-more').hidden = filtered.length <= limit;
}
function render() {
  const state = zones(); const known = state.filter(z => z.luz !== null); const lights = state.filter(z => z.luz === true).length;
  $('stat-lights').textContent = known.length ? lights : '—'; $('stat-lights-note').textContent = known.length ? lights ? 'Iluminación donde hace falta' : 'Todos los espacios en reposo' : 'Esperando estado de la placa';
  $('stat-sensors').textContent = known.length; $('stat-sensors-note').textContent = demo ? 'Lecturas simuladas' : known.length ? 'Zonas con eventos recibidos' : 'Sin lecturas recibidas';
  $('stat-events').textContent = new Intl.NumberFormat('es-PA').format(demo ? demoEvents.length : real.total_eventos); $('stat-events-note').textContent = demo ? 'En esta demostración' : 'Guardados en este equipo';
  const latest = events().at(-1)?.recibido; const fresh = latest && Date.now() - new Date(latest).getTime() < 45000;
  $('stat-connection').textContent = demo ? 'Demo' : !backendOK ? 'Sin servidor' : real.mqtt.conectado ? 'Conectado' : 'Local';
  $('stat-connection-note').textContent = demo ? 'Sin conexión a la placa' : !backendOK ? 'Inicia el backend en Python' : real.mqtt.conectado ? fresh ? 'MQTT activo · datos recientes' : 'MQTT activo · sin eventos recientes' : 'Receptor MQTT sin conexión';
  $('connection-dot').className = `tiny-dot ${!demo && real.mqtt.conectado ? 'green-dot' : 'amber-dot'}`;
  $('mode-label').textContent = demo ? 'Modo demostración' : 'Modo conectado';
  $('notice-text').textContent = demo ? 'Estás explorando una demostración. Los datos y controles son simulados.' : !backendOK ? 'El backend no responde. Los datos mostrados pueden estar desactualizados.' : 'Datos recibidos del backend local. El control remoto de la placa aún no está habilitado.';
  $('live-button').textContent = demo ? 'Ver datos reales ↗' : 'Explorar demo ↗';
  document.querySelector('.stat-line').hidden = !demo;
  document.querySelectorAll('.mini-bars i').forEach((bar, i) => bar.classList.toggle('lit', i < lights));
  $('zone-cards').innerHTML = state.map(z => card(z)).join(''); $('expanded-zones').innerHTML = state.map(z => card(z, true)).join('');
  document.querySelectorAll('.room').forEach(room => { const z = state.find(z => z.id === room.dataset.room); room.classList.toggle('on', z.luz === true); room.classList.toggle('selected', z.id === selected); room.setAttribute('aria-label', `${z.name}: ${z.luz === null ? 'sin datos' : z.luz ? 'luz encendida' : 'luz apagada'}. Seleccionar`); });
  const zone = state.find(z => z.id === selected);
  $('detail-title').textContent = `${zone.name} · Sensor ${zone.sensor}`;
  $('detail-text').textContent = `${reading(zone)}${zone.recibido ? ' · Último evento ' + timeLabel(zone.recibido, false) : ' · Esperando datos'}`;
  $('detail-tag').textContent = demo && manual.has(zone.id) ? 'Manual · demo' : 'Automático';
  $('sensor-view').innerHTML = state.map(z => `<div class="sensor-row"><b>${z.name}</b><span>${z.sensor}</span><strong>${h(reading(z))}</strong></div>`).join('');
  $('recent-events').innerHTML = eventTable(filterEvents(events(), '', '').slice(0, 4)); renderHistory();
  $('all-off').disabled = !demo; $('connection-mode').textContent = demo ? 'Demostración aislada' : 'Datos recibidos'; $('backend-status').textContent = backendOK ? 'Disponible · local' : 'No disponible';
  $('mqtt-status').textContent = real.mqtt.conectado ? 'Conectado' : real.mqtt.configurado ? 'Esperando conexión' : 'Sin configurar'; $('last-received').textContent = real.actualizado ? timeLabel(real.actualizado) : 'Sin datos';
}
function addDemo(zone, name, value, light) { demoEvents.push(demoEvent(zone, name, value, light, demoEvents.length + 1)); }
function toggleZone(id) {
  if (!demo) return; const zone = zones().find(z => z.id === id); const on = !zone.luz; manual.add(id); addDemo(id, on ? 'LUZ_ENCENDIDA' : 'LUZ_APAGADA', '', on); render(); toast(`${zone.name}: luz ${on ? 'encendida' : 'apagada'} en la demostración.`);
}
document.addEventListener('click', e => {
  const toggle = e.target.closest('[data-toggle]'); if (toggle) toggleZone(toggle.dataset.toggle);
  const select = e.target.closest('[data-select]'); if (select) { selected = select.dataset.select; render(); }
  const auto = e.target.closest('[data-auto]'); if (auto && demo) { manual.delete(auto.dataset.auto); render(); toast('Control automático restaurado en la demostración.'); }
});
document.querySelectorAll('[data-view]').forEach(b => b.addEventListener('click', () => setView(b.dataset.view)));
document.querySelectorAll('.room').forEach(room => { const select = () => { selected = room.dataset.room; render(); }; room.addEventListener('click', select); room.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); select(); } }); });
$('mode-toggle').addEventListener('click', () => setDemo(!demo)); $('live-button').addEventListener('click', () => setDemo(!demo));
$('all-events').addEventListener('click', () => setView('actividad'));
function setMenu(open) {
  $('sidebar').classList.toggle('open', open);
  $('menu').setAttribute('aria-expanded', open);
  $('sidebar').inert = matchMedia('(max-width:650px)').matches && !open;
}
$('menu').addEventListener('click', () => setMenu(!$('sidebar').classList.contains('open')));
document.addEventListener('keydown', e => { if (e.key === 'Escape') { setMenu(false); $('menu').focus(); } });
document.addEventListener('click', e => { if (matchMedia('(max-width:650px)').matches && !$('sidebar').contains(e.target) && !$('menu').contains(e.target)) setMenu(false); });
window.addEventListener('resize', () => setMenu(false));
window.addEventListener('hashchange', () => setView(location.hash.slice(1)));
function selectTab(sensors) { $('plan-container').hidden = sensors; $('sensor-view').hidden = !sensors; for (const [id, active] of [['plan-tab', !sensors], ['sensors-tab', sensors]]) { $(id).classList.toggle('selected', active); $(id).setAttribute('aria-pressed', active); } }
$('plan-tab').addEventListener('click', () => selectTab(false)); $('sensors-tab').addEventListener('click', () => selectTab(true));
$('zone-filter').addEventListener('change', () => { limit = 50; renderHistory(); }); $('event-search').addEventListener('input', () => { limit = 50; renderHistory(); }); $('load-more').addEventListener('click', () => { limit += 50; renderHistory(); });
$('all-off').addEventListener('click', () => { if (!demo) return; zones().forEach(z => { manual.add(z.id); if (z.luz) addDemo(z.id, 'LUZ_APAGADA', '', false); }); render(); toast('Todas las luces apagadas en la demostración.'); });
$('export-history').addEventListener('click', () => {
  const rows = [...filterEvents(events(), $('zone-filter').value, $('event-search').value)].reverse();
  if (!rows.length) return toast('Todavía no hay eventos para exportar.');
  const url = URL.createObjectURL(new Blob([csv(rows)], { type: 'text/csv;charset=utf-8' })); const a = document.createElement('a'); a.href = url; a.download = `sls-${demo ? 'demostracion' : 'eventos'}-${new Date().toISOString().slice(0,10)}.csv`; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); toast(`Se exportaron ${rows.length} eventos${demo ? ' simulados' : ''}.`);
});
for (const id of ['import-button', 'connection-import']) $(id).addEventListener('click', () => $('import-file').click());
$('import-file').addEventListener('change', async e => {
  const file = e.target.files[0]; if (!file) return;
  try {
    if (file.size > 512000) throw new Error('El archivo supera el límite de 500 KB.');
    const data = JSON.parse(await file.text());
    const response = await fetch('/api/eventos', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    const result = await response.json(); if (!response.ok) throw new Error(result.error || 'No se pudo importar.');
    demo = false; await poll(); render(); toast(`${result.agregados} eventos importados. Los duplicados se omitieron.`);
  } catch (error) { toast(error instanceof SyntaxError ? 'JSON inválido. Revisa el contenido del archivo.' : error.message); }
  finally { e.target.value = ''; }
});
async function poll() {
  try {
    const response = await fetch('/api/estado', { cache: 'no-store', signal: AbortSignal.timeout(5000) }); if (!response.ok) throw new Error();
    const next = await response.json(); const changed = !backendOK || JSON.stringify(next) !== JSON.stringify(real); real = next; backendOK = true; if (changed) render();
  } catch { if (backendOK) { backendOK = false; render(); } }
}
function clock() { $('local-clock').textContent = new Intl.DateTimeFormat('es-PA', { timeZone: 'America/Panama', weekday: 'short', day: 'numeric', month: 'short' }).format(new Date()); }
// La demo es determinista e independiente del backend. No genera tráfico MQTT.
let tick = 0;
setInterval(() => {
  if (!demo || document.hidden) return; tick++;
  const zone = zones()[tick % 3]; if (manual.has(zone.id)) return;
  const on = !zone.luz;
  addDemo(zone.id, zone.id === 'HABITACION 2' ? on ? 'OSCURIDAD' : 'LUZ_SUFICIENTE' : on ? 'PRESENCIA' : 'SIN_PRESENCIA', zone.id === 'HABITACION 2' ? on ? 2593 : 700 : zone.id === 'HABITACION 1' ? on ? 60 : 180 : '', zone.luz);
  addDemo(zone.id, on ? 'LUZ_ENCENDIDA' : 'LUZ_APAGADA', zone.id === 'HABITACION 2' ? on ? 2593 : 700 : '', on);
  render();
}, 12000);
setInterval(poll, 2500); setInterval(clock, 60000); clock(); render(); setView(location.hash.slice(1)); poll();
