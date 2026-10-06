const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function harness() {
  let now = 0;
  let id = 0;
  const timers = new Map();
  const document = new EventTarget();
  document.hidden = false;
  const window = new EventTarget();
  const navigator = { onLine: true };
  const context = vm.createContext({
    document, window, navigator, AbortController,
    setTimeout(fn, delay) { timers.set(++id, { fn, at: now + delay }); return id; },
    clearTimeout(key) { timers.delete(key); }
  });
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../app/static/clearance-polling.js'), 'utf8'), context);
  return {
    document, window, navigator, timers, create: window.Check8Polling.createPoller,
    render: window.Check8Polling.updateClearances,
    async tick(ms) {
      const target = now + ms;
      while (true) {
        const next = [...timers.entries()].filter(([, t]) => t.at <= target).sort((a, b) => a[1].at - b[1].at)[0];
        if (!next) break;
        now = next[1].at;
        timers.delete(next[0]);
        next[1].fn();
        for (let i = 0; i < 8; i++) await Promise.resolve();
      }
      now = target;
    }
  };
}

test('polls every 10 seconds, without an unnecessary initial request', async () => {
  const h = harness();
  let calls = 0;
  h.create(async () => { calls++; }).start();
  await h.tick(9999);
  assert.equal(calls, 0);
  await h.tick(1);
  assert.equal(calls, 1);
  await h.tick(10000);
  assert.equal(calls, 2);
});

test('pauses while hidden and refreshes once on return', async () => {
  const h = harness();
  let calls = 0;
  h.create(async () => { calls++; }).start();
  h.document.hidden = true;
  h.document.dispatchEvent(new Event('visibilitychange'));
  await h.tick(60000);
  assert.equal(calls, 0);
  h.document.hidden = false;
  h.document.dispatchEvent(new Event('visibilitychange'));
  h.window.dispatchEvent(new Event('online'));
  await h.tick(0);
  assert.equal(calls, 1);
});

test('backs off to 20, 40, then 60 seconds and resets after recovery', async () => {
  const h = harness();
  let calls = 0;
  h.create(async () => { if (++calls <= 4) throw Error('offline'); }).start();
  for (const [wait, count] of [[10000, 1], [20000, 2], [40000, 3], [60000, 4], [60000, 5], [10000, 6]]) {
    await h.tick(wait - 1);
    assert.equal(calls, count - 1);
    await h.tick(1);
    assert.equal(calls, count);
  }
});

test('aborts timed-out requests without overlap', async () => {
  const h = harness();
  let calls = 0;
  let active = 0;
  h.create(signal => new Promise((resolve, reject) => {
    calls++;
    active++;
    assert.equal(active, 1);
    signal.addEventListener('abort', () => { active--; reject(Error('aborted')); });
  })).start();
  await h.tick(10000);
  assert.equal(active, 1);
  await h.tick(8000);
  assert.equal(active, 0);
  await h.tick(19999);
  assert.equal(calls, 1);
  await h.tick(1);
  assert.equal(calls, 2);
});

test('offline pauses and online resumes', async () => {
  const h = harness();
  let calls = 0;
  h.create(async () => { calls++; }).start();
  h.navigator.onLine = false;
  h.window.dispatchEvent(new Event('offline'));
  await h.tick(60000);
  assert.equal(calls, 0);
  h.navigator.onLine = true;
  h.window.dispatchEvent(new Event('online'));
  await h.tick(0);
  assert.equal(calls, 1);
});

test('terminal authentication result stops all future requests', async () => {
  const h = harness();
  let calls = 0;
  h.create(async () => { calls++; return false; }).start();
  await h.tick(10000);
  h.window.dispatchEvent(new Event('online'));
  h.document.dispatchEvent(new Event('visibilitychange'));
  await h.tick(120000);
  assert.equal(calls, 1);
});

test('pagehide pauses and a back-forward cache restoration resumes', async () => {
  const h = harness();
  let calls = 0;
  h.create(async () => { calls++; }).start();
  h.window.dispatchEvent(new Event('pagehide'));
  await h.tick(60000);
  assert.equal(calls, 0);
  const event = new Event('pageshow');
  event.persisted = true;
  h.window.dispatchEvent(event);
  await h.tick(0);
  assert.equal(calls, 1);
});

test('explicit stop cancels scheduled work', async () => {
  const h = harness();
  let calls = 0;
  const poller = h.create(async () => { calls++; });
  poller.start();
  poller.stop();
  await h.tick(60000);
  assert.equal(calls, 0);
});

function clearanceView(h) {
  class Element {
    constructor() { this.children = []; this.dataset = {}; this.textContent = ''; this.hidden = false; }
    get rows() { return this.children; }
    get cells() { return this.children; }
    get firstElementChild() { return this.children[0]; }
    append(child) { this.insertBefore(child, null); }
    insertCell() { const cell = new Element(); this.append(cell); return cell; }
    insertBefore(child, next) {
      child.remove();
      const index = next ? this.children.indexOf(next) : this.children.length;
      this.children.splice(index, 0, child);
      child.parent = this;
    }
    remove() {
      if (this.parent) this.parent.children.splice(this.parent.children.indexOf(this), 1);
      this.parent = null;
    }
  }
  h.document.createElement = () => new Element();
  const elements = Object.fromEntries(['rows', 'empty', 'count', 'summary', 'percent', 'announcement'].map(key => [`[data-clearance-${key}]`, new Element()]));
  elements.progress = new Element();
  const sections = [new Element(), new Element()];
  return {
    elements, sections,
    querySelector: key => elements[key],
    querySelectorAll: () => sections
  };
}

test('refresh updates rows and progress without replacing unchanged rows', () => {
  const h = harness();
  const view = clearanceView(h);
  const record = { id: 1, course_code: 'TEST', course_name: 'Course', instructor_names: 'Instructor', state: 'pending', note: '' };
  h.render(view, [record]);
  const row = view.elements['[data-clearance-rows]'].rows[0];
  assert.equal(row.cells[2].firstElementChild.textContent, 'Pending');
  view.elements['[data-clearance-announcement]'].textContent = '';
  h.render(view, [record]);
  assert.equal(view.elements['[data-clearance-rows]'].rows[0], row);
  assert.equal(view.elements['[data-clearance-announcement]'].textContent, '');
  h.render(view, [{ ...record, state: 'cleared', note: '<img src=x onerror=alert(1)>' }]);
  assert.equal(row.cells[2].firstElementChild.textContent, 'Approved');
  assert.equal(row.cells[3].textContent, '<img src=x onerror=alert(1)>');
  assert.equal(view.elements.progress.value, 1);
  assert.equal(view.elements['[data-clearance-percent]'].textContent, '100%');
});

test('refresh handles adding and removing the final clearance', () => {
  const h = harness();
  const view = clearanceView(h);
  h.render(view, []);
  assert.equal(view.elements['[data-clearance-empty]'].hidden, false);
  assert.equal(view.sections[0].hidden, true);
  h.render(view, [{ id: 1, course_code: 'TEST', course_name: 'Course', instructor_names: 'Instructor', state: 'blocked', note: '' }]);
  assert.equal(view.elements['[data-clearance-empty]'].hidden, true);
  assert.equal(view.sections[0].hidden, false);
  h.render(view, []);
  assert.equal(view.elements['[data-clearance-rows]'].rows.length, 0);
  assert.equal(view.elements.progress.max, 1);
  assert.equal(view.elements.progress.value, 0);
});
