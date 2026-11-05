export const ZONES = [
  { id: 'SALA', name: 'Sala', sensor: 'PIR', subtitle: 'Presencia por movimiento', unit: '', description: 'La luz se enciende con movimiento y se apaga tras 5 segundos sin presencia.' },
  { id: 'HABITACION 1', name: 'Habitación 1', sensor: 'HC-SR04', subtitle: 'Presencia por distancia', unit: 'cm', description: 'Detecta presencia a menos de 100 cm. Apaga la luz tras 5 segundos sin detección.' },
  { id: 'HABITACION 2', name: 'Habitación 2', sensor: 'LDR', subtitle: 'Iluminación ambiental', unit: 'ADC', description: 'Enciende con oscuridad. Usa histéresis alrededor de 2000 ADC para evitar parpadeos.' },
];
export const LABELS = { IRQ_PIR: 'Interrupción del PIR', PRESENCIA: 'Presencia detectada', SIN_PRESENCIA: 'Sin presencia', OSCURIDAD: 'Oscuridad detectada', LUZ_SUFICIENTE: 'Luz ambiente suficiente', LUZ_ENCENDIDA: 'Luz encendida', LUZ_APAGADA: 'Luz apagada' };
export function escapeHTML(value) { return String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char])); }
export function timeLabel(date, seconds = true) { return date ? new Intl.DateTimeFormat('es-PA', { timeZone: 'America/Panama', hour: '2-digit', minute: '2-digit', ...(seconds ? { second: '2-digit' } : {}), hour12: false }).format(new Date(date)) : '—'; }
export function filterEvents(events, zone, query) { const q = query.trim().toLocaleLowerCase('es'); return [...events].reverse().filter(e => (!zone || e.zona === zone) && (!q || [LABELS[e.evento], e.evento, e.zona, e.sensor].join(' ').toLocaleLowerCase('es').includes(q))); }
export function csv(events) {
  const fields = ['recibido', 'dispositivo', 'sesion', 'secuencia', 'tiempo_ms', 'zona', 'sensor', 'evento', 'valor', 'luz'];
  const cell = value => { let text = String(value ?? ''); if (/^[=+\-@]/.test(text)) text = "'" + text; return '"' + text.replace(/"/g, '""') + '"'; };
  return '\ufeff' + [fields.join(','), ...events.map(e => fields.map(f => cell(e[f])).join(','))].join('\r\n');
}
export function stateFromEvents(events) {
  const zones = ZONES.map(z => ({ ...z, luz: null, lectura: null, presencia: null, recibido: null, evento: null }));
  const session = new Map();
  const seen = new Set();
  for (const e of events) { const key = JSON.stringify([e.dispositivo, e.sesion]); if (!seen.has(key)) { seen.add(key); session.set(e.dispositivo, e.sesion); } }
  const relevant = events.filter(e => session.get(e.dispositivo) === e.sesion);
  // Dentro de la sesión, la secuencia del emisor manda sobre el orden de llegada.
  const ordered = [...relevant].sort((a, b) => a.dispositivo === b.dispositivo ? a.secuencia - b.secuencia : new Date(a.recibido) - new Date(b.recibido));
  for (const e of ordered) {
    const zone = zones.find(z => z.id === e.zona); if (!zone) continue;
    zone.luz = e.luz; zone.recibido = e.recibido; zone.evento = e.evento;
    if (['PRESENCIA', 'SIN_PRESENCIA'].includes(e.evento)) zone.presencia = e.evento === 'PRESENCIA';
    if (e.sensor !== 'PIR' && typeof e.valor === 'number') zone.lectura = e.valor;
  }
  return zones;
}
export function demoEvent(zone, event, value, light, sequence, now = Date.now()) {
  return { version: 1, dispositivo: 'casa-demo', sesion: 'demostracion', secuencia: sequence, tiempo_ms: sequence * 1000, zona: zone, sensor: ZONES.find(z => z.id === zone).sensor, evento: event, valor: value, luz: light, recibido: new Date(now).toISOString() };
}
export function initialDemo(now = Date.now()) {
  const rows = [ ['SALA','IRQ_PIR',1,false], ['SALA','PRESENCIA','',true], ['SALA','LUZ_ENCENDIDA','',true], ['HABITACION 1','PRESENCIA',60,true], ['HABITACION 1','LUZ_ENCENDIDA',60,true], ['HABITACION 2','OSCURIDAD',2593,true], ['HABITACION 2','LUZ_ENCENDIDA',2593,true], ['SALA','SIN_PRESENCIA','',true], ['SALA','LUZ_APAGADA','',false] ];
  return rows.map((r,i) => demoEvent(...r, i+1, now - (rows.length - i) * 16000));
}
export function reading(zone) {
  if (zone.sensor === 'PIR') return zone.presencia === null ? 'Sin datos' : zone.presencia ? 'Movimiento' : 'Sin movimiento';
  return zone.lectura === null || zone.lectura === undefined ? 'Sin lectura' : `${zone.lectura} ${zone.unit}`;
}
