(() => {
  function createPoller(task, { interval = 10000, maxInterval = 60000, timeout = 8000 } = {}) {
    let timer;
    let controller;
    let delay = interval;
    let stopped = false;
    let suspended = false;
    const available = () => !stopped && !suspended && !document.hidden && navigator.onLine !== false;

    function schedule(wait = delay) {
      clearTimeout(timer);
      if (available() && !controller) timer = setTimeout(run, wait);
    }

    async function run() {
      if (!available() || controller) return;
      const request = new AbortController();
      controller = request;
      const deadline = setTimeout(() => request.abort(), timeout);
      try {
        const keepPolling = await task(request.signal);
        if (!request.signal.aborted) {
          delay = interval;
          if (keepPolling === false) stopped = true;
        } else if (available()) {
          delay = Math.min(delay * 2, maxInterval);
        }
      } catch {
        if (available()) delay = Math.min(delay * 2, maxInterval);
      } finally {
        clearTimeout(deadline);
        controller = null;
        schedule();
      }
    }

    function pause() {
      clearTimeout(timer);
      controller?.abort();
    }
    function resume() {
      if (available()) schedule(0);
      else pause();
    }
    document.addEventListener('visibilitychange', resume);
    window.addEventListener('offline', pause);
    window.addEventListener('online', resume);
    window.addEventListener('pagehide', () => { suspended = true; pause(); });
    window.addEventListener('pageshow', event => {
      if (event.persisted) { suspended = false; resume(); }
    });
    return {
      start: () => { stopped = false; schedule(); },
      stop: () => { stopped = true; pause(); }
    };
  }

  function updateClearances(root, records) {
    const body = root.querySelector('[data-clearance-rows]');
    const previous = new Map([...body.rows].map(row => [row.dataset.clearanceId, row]));
    const labels = { pending: 'Pending', cleared: 'Approved', blocked: 'Rejected' };
    let changed = false;
    const setText = (element, value) => {
      if (element.textContent !== value) { element.textContent = value; changed = true; }
    };

    records.forEach((record, index) => {
      const id = String(record.id);
      let row = previous.get(id);
      if (!row) {
        row = document.createElement('tr');
        row.dataset.clearanceId = id;
        for (const label of ['Course', 'Instructor', 'Status', 'Note']) {
          const cell = row.insertCell();
          cell.dataset.label = label;
          if (label === 'Course') cell.append(document.createElement('strong'));
          if (label === 'Status') cell.append(document.createElement('span'));
          if (label === 'Note') cell.className = 'muted';
        }
        changed = true;
      }
      previous.delete(id);
      setText(row.cells[0].firstElementChild, `${record.course_code} - ${record.course_name}`);
      setText(row.cells[1], record.instructor_names);
      const badge = row.cells[2].firstElementChild;
      const stateChanged = row.dataset.state !== record.state;
      setText(badge, labels[record.state] || record.state);
      badge.className = labels[record.state] ? `badge badge--${record.state}` : 'badge';
      row.dataset.state = record.state;
      setText(row.cells[3], record.note || '\u2014');
      if (body.children[index] !== row) body.insertBefore(row, body.children[index] || null);
      if (stateChanged) window.Check8Motion?.enter(badge);
    });
    previous.forEach(row => { row.remove(); changed = true; });

    const total = records.length;
    const approved = records.filter(record => record.state === 'cleared').length;
    root.querySelectorAll('[data-has-clearances]').forEach(element => { element.hidden = !total; });
    root.querySelector('[data-clearance-empty]').hidden = total > 0;
    setText(root.querySelector('[data-clearance-count]'), `${total} record${total === 1 ? '' : 's'}`);
    setText(root.querySelector('[data-clearance-summary]'), `${approved} of ${total} courses approved`);
    setText(root.querySelector('[data-clearance-percent]'), `${total ? Math.floor(approved / total * 100) : 0}%`);
    const progress = root.querySelector('progress');
    progress.max = Math.max(1, total);
    progress.value = approved;
    progress.textContent = `${approved} of ${total}`;
    if (changed) root.querySelector('[data-clearance-announcement]').textContent = 'Clearance status updated.';
  }

  function setup() {
    const root = document.querySelector('[data-clearance-dashboard]');
    if (!root) return;
    const notice = root.querySelector('[data-clearance-notice]');
    const poller = createPoller(async signal => {
      try {
        const response = await fetch(root.dataset.statusUrl, {
          signal, cache: 'no-store', headers: { Accept: 'application/json' }
        });
        if (signal.aborted) return;
        if (response.redirected || response.status === 401 || response.status === 403) {
          notice.textContent = 'Live updates stopped. Refresh the page to sign in again.';
          notice.hidden = false;
          return false;
        }
        if (!response.ok) throw new Error('Refresh failed');
        const records = await response.json();
        if (signal.aborted) return;
        if (!Array.isArray(records)) throw new Error('Invalid clearance response');
        updateClearances(root, records);
        notice.hidden = true;
        notice.textContent = '';
      } catch (error) {
        if (!signal.aborted) {
          notice.textContent = 'Live updates are temporarily unavailable. Retrying shortly.';
          notice.hidden = false;
        }
        throw error;
      }
    });
    poller.start();
  }

  window.Check8Polling = { createPoller, updateClearances };
  document.addEventListener('DOMContentLoaded', setup);
})();
