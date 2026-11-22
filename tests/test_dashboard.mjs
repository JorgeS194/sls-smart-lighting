import test from 'node:test';
import assert from 'node:assert/strict';
import { initialDemo, stateFromEvents, filterEvents, csv, escapeHTML, demoEvent } from '../dashboard/model.mjs';

test('la demo tiene tres zonas y dos luces encendidas', () => {
  const state = stateFromEvents(initialDemo());
  assert.equal(state.length, 3);
  assert.equal(state.filter(z => z.luz).length, 2);
  assert.equal(state[1].lectura, 60);
  assert.equal(state[2].lectura, 2593);
});
test('el modo sin datos no inventa estados ni lecturas', () => {
  for (const zone of stateFromEvents([])) {
    assert.equal(zone.luz, null);
    assert.equal(zone.lectura, null);
  }
});
test('filtros combinan zona y nombre legible de evento', () => {
  const filtered = filterEvents(initialDemo(), 'SALA', 'apagada');
  assert.equal(filtered.length, 1);
  assert.equal(filtered[0].evento, 'LUZ_APAGADA');
});
test('CSV y HTML tratan el texto importado como contenido', () => {
  const event = demoEvent('SALA', 'PRESENCIA', '', true, 1);
  event.dispositivo = '=FORMULA';
  assert.ok(csv([event]).includes("'=FORMULA"));
  assert.equal(escapeHTML('<img src=x>'), '&lt;img src=x&gt;');
});
test('un evento atrasado no sobreescribe el último estado de la sesión', () => {
  const off = demoEvent('SALA', 'LUZ_APAGADA', '', false, 2);
  const on = demoEvent('SALA', 'LUZ_ENCENDIDA', '', true, 1);
  assert.equal(stateFromEvents([off, on])[0].luz, false);
});
test('un reenvío de una sesión antigua no sustituye a la sesión nueva', () => {
  const old = demoEvent('SALA', 'LUZ_ENCENDIDA', '', true, 100);
  const fresh = { ...old, sesion: 'nuevo-arranque', secuencia: 1, luz: false };
  assert.equal(stateFromEvents([old, fresh, { ...old, secuencia: 101 }])[0].luz, false);
});

import { ControlManual } from '../dashboard/model.mjs';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

test('orden pendiente evita doble clic y espera la confirmación exacta', async () => {
  let resolver;
  const requests = [];
  const control = new ControlManual((...args) => {
    requests.push(args);
    return new Promise(resolve => { resolver = resolve; });
  });
  const envio = control.ordenar('HABITACION 1', 'encender');
  assert.equal(await control.ordenar('HABITACION 1', 'apagar'), false);
  assert.equal(requests.length, 1);
  assert.equal(requests[0][0], '/api/comandos');
  assert.deepEqual(JSON.parse(requests[0][1].body), { zona: 'HABITACION_1', accion: 'encender' });
  resolver({ status: 202, json: async () => ({ comando: { id: 'nueva' } }) });
  assert.equal(await envio, true);
  control.actualizar([{ id: 'HABITACION 1', luz: true, modo: 'manual', orden_id: 'vieja' }]);
  assert.equal(control.pendientes.size, 1);
  control.actualizar([{ id: 'HABITACION 1', luz: true, modo: 'manual', orden_id: 'nueva' }]);
  assert.equal(control.pendientes.size, 0);
});

test('sin confirmación en diez segundos conserva el estado real y muestra error', async () => {
  let ahora = 0;
  const control = new ControlManual(async () => ({ status: 202, json: async () => ({ comando: { id: 'x' } }) }), () => ahora);
  const zona = { id: 'SALA', luz: true, modo: 'auto' };
  await control.ordenar('SALA', 'apagar');
  ahora = 10000;
  control.actualizar([zona]);
  assert.equal(control.errores.get('SALA'), 'Sin confirmación de la placa');
  assert.equal(zona.luz, true);
  assert.equal(control.pendientes.size, 0);
});

test('rechazo HTTP y fallo de red permiten reintentar sin cambiar la luz', async () => {
  for (const enviar of [
    async () => ({ status: 503, json: async () => ({ error: 'MQTT desconectado' }) }),
    async () => { throw new Error('Sin conexión'); },
  ]) {
    const control = new ControlManual(enviar);
    assert.equal(await control.ordenar('SALA', 'apagar'), false);
    assert.equal(control.pendientes.size, 0);
    assert.ok(control.errores.get('SALA'));
  }
});

test('auto se confirma por modo e identificador independientemente de la luz', async () => {
  const control = new ControlManual(async () => ({ status: 202, json: async () => ({ comando: { id: 'auto' } }) }));
  await control.ordenar('SALA', 'auto');
  control.actualizar([{ id: 'SALA', luz: true, modo: 'auto', orden_id: 'auto' }]);
  assert.equal(control.pendientes.size, 0);
});

function interfaz() {
  const elements = new Map();
  const clicks = [];
  const requests = [];
  let resolver;
  const state = { zonas: Object.fromEntries(['SALA', 'HABITACION_1', 'HABITACION_2'].map(zona =>
    [zona, { luz: false, valor: 0, sensor: 'PIR', clasificacion: 'SIN_PRESENCIA', ultima_actualizacion: null }])),
    lecturas: 0, ultima_actualizacion: null };
  const element = id => {
    if (!elements.has(id)) elements.set(id, {
      value: '', innerHTML: '', textContent: '', hidden: false, disabled: false,
      classList: { toggle() {}, contains() { return false; } },
      setAttribute() {}, addEventListener() {}, contains() { return false; }, focus() {},
    });
    return elements.get(id);
  };
  const document = {
    getElementById: element, querySelector: element, querySelectorAll: () => [],
    addEventListener: (name, callback) => { if (name === 'click') clicks.push(callback); },
    hidden: false,
  };
  const modules = { initialDemo, stateFromEvents, filterEvents, csv, escapeHTML, demoEvent, ControlManual };
  // Ejecuta app.mjs con su DOM y transporte sustituidos, conservando el código de eventos.
  const model = readFileSync(new URL('../dashboard/model.mjs', import.meta.url), 'utf8');
  const app = readFileSync(new URL('../dashboard/app.mjs', import.meta.url), 'utf8');
  const code = model.replaceAll('export ', '') + '\n' + app.replace(/^import .*;\r?\n/, '') +
    '\nglobalThis.probar = { poll, setDemo, zones, control };';
  const context = {
    h: escapeHTML, ...modules, document, console, Intl, AbortSignal, Date, Map, Set, JSON,
    matchMedia: () => ({ matches: false }), history: { replaceState() {} }, location: { hash: '' },
    window: { addEventListener() {} }, setInterval() {}, setTimeout() { return 1; }, clearTimeout() {},
    fetch: async (path, options) => {
      if (options?.method === 'POST') {
        requests.push(JSON.parse(options.body));
        return new Promise(resolve => { resolver = resolve; });
      }
      const data = path === '/api/estado' ? state : path === '/api/salud' ?
        { mqtt_conectado: true, mqtt_configurado: true, dispositivo_comandos: 'demo' } : { historial: [] };
      return { ok: true, json: async () => data };
    },
  };
  vm.runInNewContext(code, context);
  return { ...context.probar, state, requests, element,
    responder: response => resolver(response),
    click(attribute, id) {
      const target = { closest: selector => selector === '[' + attribute + ']' ?
        { dataset: { [attribute.slice(5).replace(/-([a-z])/g, (_, c) => c.toUpperCase())]: id } } : null };
      for (const callback of clicks) callback({ target });
    },
  };
}

test('interruptor real queda pendiente, confirma Manual y permite volver a automático', async () => {
  const ui = interfaz();
  await ui.poll();
  ui.click('data-toggle', 'SALA');
  assert.equal(ui.requests[0].accion, 'encender');
  assert.match(ui.element('zone-cards').innerHTML, /Enviando orden/);
  assert.match(ui.element('zone-cards').innerHTML, /aria-busy="true"/);
  assert.equal(ui.zones()[0].luz, false);
  ui.responder({ status: 202, json: async () => ({ comando: { id: 'orden1' } }) });
  await new Promise(resolve => setImmediate(resolve));
  assert.match(ui.element('zone-cards').innerHTML, /Orden enviada/);
  Object.assign(ui.state.zonas.SALA, { luz: true, modo: 'manual', orden_id: 'orden1' });
  await ui.poll();
  assert.match(ui.element('zone-cards').innerHTML, /Manual/);
  assert.match(ui.element('zone-cards').innerHTML, /Volver a automático/);
  assert.equal(ui.control.pendientes.size, 0);
  ui.click('data-auto', 'SALA');
  assert.equal(ui.requests[1].accion, 'auto');
  ui.responder({ status: 202, json: async () => ({ comando: { id: 'orden2' } }) });
  await new Promise(resolve => setImmediate(resolve));
  Object.assign(ui.state.zonas.SALA, { modo: 'auto', orden_id: 'orden2' });
  await ui.poll();
  assert.equal(ui.control.pendientes.size, 0);
});

test('error visible revierte al confirmado y demo conserva controles sin publicar', async () => {
  const ui = interfaz();
  await ui.poll();
  ui.click('data-toggle', 'SALA');
  ui.responder({ status: 503, json: async () => ({ error: 'MQTT desconectado' }) });
  await new Promise(resolve => setImmediate(resolve));
  assert.match(ui.element('zone-cards').innerHTML, /role="alert"/);
  assert.match(ui.element('zone-cards').innerHTML, /MQTT desconectado/);
  assert.equal(ui.zones()[0].luz, false);
  ui.setDemo(true);
  const previo = ui.zones()[0].luz;
  ui.click('data-toggle', 'SALA');
  assert.equal(ui.zones()[0].luz, !previo);
  assert.equal(ui.requests.length, 1);
  assert.match(ui.element('zone-cards').innerHTML, /Manual · demo/);
});


test('la interfaz muestra el timeout y conserva el interruptor confirmado', async () => {
  const ui = interfaz();
  await ui.poll();
  let ahora = 0;
  ui.control.reloj = () => ahora;
  ui.click('data-toggle', 'SALA');
  ui.responder({ status: 202, json: async () => ({ comando: { id: 'perdida' } }) });
  await new Promise(resolve => setImmediate(resolve));
  ahora = 10000;
  await ui.poll();
  assert.match(ui.element('zone-cards').innerHTML, /Sin confirmación de la placa/);
  assert.match(ui.element('zone-cards').innerHTML, /aria-checked="false" aria-busy="false"/);
  assert.equal(ui.zones()[0].luz, false);
});
