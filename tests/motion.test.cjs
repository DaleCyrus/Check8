const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function harness(reduced = false) {
  const preference = new EventTarget();
  preference.matches = reduced;
  const document = new EventTarget();
  const window = { matchMedia: () => preference };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../app/static/motion.js'), 'utf8'), { window, document });
  const animations = [];
  const element = { animate(frames, options) {
    const animation = { frames, options, cancelled: false, finished: new Promise(() => {}), cancel() { this.cancelled = true; } };
    animations.push(animation);
    return animation;
  } };
  return { preference, element, animations, enter: window.Check8Motion.enter };
}

test('screen transitions are short and interruptible', () => {
  const h = harness();
  h.enter(h.element);
  assert.equal(h.animations[0].options.duration, 220);
  h.enter(h.element);
  assert.equal(h.animations[0].cancelled, true);
  assert.equal(h.animations.length, 2);
});

test('reduced motion skips entrance and cancels active motion on preference change', () => {
  const h = harness(true);
  h.enter(h.element);
  assert.equal(h.animations.length, 0);
  h.preference.matches = false;
  h.enter(h.element);
  h.preference.matches = true;
  h.preference.dispatchEvent(new Event('change'));
  assert.equal(h.animations[0].cancelled, true);
});

test('unsupported animation remains a functional no-op', () => {
  const h = harness();
  h.enter(null);
  h.enter({});
  assert.equal(h.animations.length, 0);
});
