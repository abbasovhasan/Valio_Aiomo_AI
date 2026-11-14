// Bounded state-machine checks of actual component handlers with deferred permissions.
// Native devices, browser permission UI, audio recognition and visual layout are not simulated as proven E2E.
const fs = require('fs'), vm = require('vm'), path = require('path');
const taskRoot = path.resolve(__dirname, '../..');
const reportDirectory = path.join(taskRoot, '.local');
const req = require('module').createRequire(path.join(taskRoot, 'frontend/package.json')), ts = req('typescript');
const source = ts.transpileModule(fs.readFileSync(path.join(taskRoot, 'frontend/src/MultimodalInput.tsx'), 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX } }).outputText;
const assert = (v, m) => { if (!v)
    throw Error(m); };
const tick = async () => { await Promise.resolve(); await Promise.resolve(); };
function harness() {
    const slots = [], effects = [], requests = [], busy = [], apiCalls = [], texts = [], recorders = [];
    let index = 0, tree, active = true;
    const hooks = { useState(initial) { const i = index++; if (!slots[i])
            slots[i] = { value: initial }; return [slots[i].value, v => { slots[i].value = typeof v === 'function' ? v(slots[i].value) : v; }]; }, useRef(initial) { const i = index++; return slots[i] || (slots[i] = { current: initial }); }, useEffect(fn, deps) { const i = index++, old = slots[i]; if (!old || deps.some((v, j) => !Object.is(v, old.deps[j]))) {
            effects.push(() => { old?.cleanup?.(); slots[i] = { deps, cleanup: fn() }; });
        } } };
    class Recorder {
        static isTypeSupported() { return true; }
        constructor(media) { this.media = media; this.mimeType = 'audio/webm'; this.state = 'inactive'; recorders.push(this); }
        start() { this.state = 'recording'; }
        stop() { this.state = 'inactive'; this.ondataavailable?.({ data: new Blob(['audio']) }); this.onstop?.(); }
    }
    const m = { exports: {} };
    vm.runInNewContext(source, { module: m, exports: m.exports, require: id => id === 'react' ? hooks : id.endsWith('.css') ? {} : req(id), navigator: { mediaDevices: { getUserMedia: () => new Promise((resolve, reject) => requests.push({ resolve, reject })) } }, window: { clearTimeout() { }, clearInterval() { }, setTimeout() { return 1; }, setInterval() { return 2; } }, MediaRecorder: Recorder, DOMException, File: class extends Blob {
            constructor(parts, name, opts) { super(parts, opts); this.name = name; }
        }, FormData: class {
            append() { }
        }, AbortController, Blob });
    const onBusyChange = v => busy.push(v), api = async (p) => { apiCalls.push(p); return { text: '20 litres of milk', uncertainties: [], source: 'test local ASR' }; };
    function render() { index = 0; tree = m.exports.MultimodalInput({ api, onText: t => texts.push(t), onBusyChange, active }); while (effects.length)
        effects.shift()(); return tree; }
    function nodes(n, out = []) { if (Array.isArray(n)) {
        n.forEach(v => nodes(v, out));
        return out;
    } if (n && typeof n === 'object' && n.props) {
        out.push(n);
        nodes(n.props.children, out);
    } return out; }
    const text = n => n == null ? '' : Array.isArray(n) ? n.map(text).join('') : typeof n === 'object' ? text(n.props?.children) : String(n);
    const button = label => { const b = nodes(tree).find(n => n.type === 'button' && (text(n) === label || n.props['aria-label'] === label)); assert(b, 'Missing ' + label); return b; };
    const contains = s => text(tree).includes(s);
    render();
    return { render, button, contains, requests, busy, apiCalls, texts, recorders, hide() { active = false; render(); render(); }, unmount() { slots.forEach(s => s?.cleanup?.()); } };
}
function media() { const value = { stops: 0 }; value.getTracks = () => [{ stop() { value.stops++; } }]; return value; }
(async () => {
    const a = harness(), start = a.button('Voice input').props.onClick;
    start();
    start();
    assert(a.requests.length === 1, 'Duplicate permission requests');
    a.render();
    assert(a.contains('Allow microphone access') && a.busy.at(-1) === true, 'Pending control/busy missing');
    a.button('Cancel').props.onClick();
    a.render();
    assert(a.busy.at(-1) === false, 'Cancel did not release composer');
    const stale = media();
    a.requests[0].resolve(stale);
    await tick();
    a.render();
    assert(stale.stops === 1 && !a.recorders.length && !a.contains('permission was declined'), 'Stale grant started recording');
    const b = harness();
    b.button('Voice input').props.onClick();
    b.render();
    b.button('Cancel').props.onClick();
    b.render();
    b.button('Voice input').props.onClick();
    b.render();
    b.requests[0].reject(new DOMException('declined', 'NotAllowedError'));
    await tick();
    b.render();
    assert(b.contains('Allow microphone access') && !b.contains('permission was declined') && b.busy.at(-1) === true, 'Old rejection overwrote new request');
    const current = media();
    b.requests[1].resolve(current);
    await tick();
    b.render();
    assert(b.recorders.length === 1 && b.contains('Stop & transcribe'), 'Current request failed to record');
    b.button('Stop & transcribe · 0s').props.onClick();
    await tick();
    b.render();
    assert(b.apiCalls.join() === '/input/audio' && b.contains('Review extracted text') && b.busy.at(-1) === true && !b.texts.length, 'Pending ASR review must block submission without applying text');
    for (const label of ['Voice input', 'Upload image', 'Take a photo']) assert(b.button(label).props.disabled, 'Pending review permits replacement via ' + label);
    assert(!b.button('Type a message').props.disabled && !b.button('Add to request').props.disabled, 'Review disabled typing or explicit Add');
    b.button('Add to request').props.onClick();
    b.render();
    assert(b.texts[0] === '20 litres of milk' && b.busy.at(-1) === false, 'Explicit Add must apply reviewed text and release submission');
    const discarded = harness();
    discarded.button('Voice input').props.onClick();
    discarded.requests[0].resolve(media());
    await tick();
    discarded.render();
    discarded.button('Stop & transcribe · 0s').props.onClick();
    await tick();
    discarded.render();
    assert(discarded.busy.at(-1) === true, 'Transcript review did not hold submission');
    discarded.button('Discard extracted text').props.onClick();
    discarded.render();
    assert(!discarded.texts.length && !discarded.contains('Review extracted text') && discarded.busy.at(-1) === false, 'Discard must release submission without adding text');
    const c = harness();
    c.button('Voice input').props.onClick();
    c.render();
    c.hide();
    const hidden = media();
    c.requests[0].resolve(hidden);
    await tick();
    c.render();
    assert(hidden.stops === 1 && !c.recorders.length && c.busy.at(-1) === false, 'Hidden request activated microphone');
    const d = harness();
    d.button('Voice input').props.onClick();
    d.render();
    d.unmount();
    const removed = media();
    d.requests[0].resolve(removed);
    await tick();
    assert(removed.stops === 1 && !d.recorders.length && d.busy.at(-1) === false, 'Unmount leaked permission stream');
    const report = { scope: 'Actual MultimodalInput handlers with deferred permission promises and fake MediaRecorder; not real device or browser E2E', checks_passed: 7, checks: ['Duplicate start guarded before rerender', 'Pending permission reports busy and offers Cancel', 'Cancelled late grant stops its stream', 'Old rejection cannot overwrite newer request', 'Transcript review blocks submission/replacement until explicit Add while typing remains available', 'Explicit Discard releases submission without applying text', 'Hidden/unmounted late grants stop without starting recorder'] };
    fs.mkdirSync(reportDirectory, { recursive: true });
    fs.writeFileSync(path.join(reportDirectory, 'microphone-permission-report.json'), JSON.stringify(report, null, 2) + '\n');
    console.log(JSON.stringify(report, null, 2));
})().catch(e => { console.error(e); process.exitCode = 1; });
