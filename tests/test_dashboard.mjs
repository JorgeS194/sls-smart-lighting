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
