// Runs actual MultimodalInput handlers using fake camera streams and canvas callbacks.
// This does not prove actual camera permission UI, hardware, image OCR quality or browser E2E.
const fs = require('fs'), vm = require('vm'), path = require('path');
const taskRoot = path.resolve(__dirname, '../..');
const reportDirectory = path.join(taskRoot, '.local');
const req = require('module').createRequire(path.join(taskRoot, 'frontend/package.json')), ts = req('typescript');
const source = ts.transpileModule(fs.readFileSync(path.join(taskRoot, 'frontend/src/MultimodalInput.tsx'), 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX } }).outputText;
const assert = (value, message) => { if (!value)
    throw Error(message); };
const tick = async () => { for (let i = 0; i < 16; i++) await Promise.resolve(); };
function harness(options = {}) {
    const slots = [], effects = [], requests = [], photos = [], busy = [], apiCalls = [], texts = [], canvases = [], bitmapRequests = [];
    let index = 0, tree, active = true;
    const frame = { videoWidth: 2560, videoHeight: 1920, srcObject: null, plays: 0, play() { this.plays++; return Promise.resolve(); } };
    const hooks = { useState(initial) { const i = index++; if (!slots[i])
            slots[i] = { value: initial }; return [slots[i].value, value => { slots[i].value = typeof value === 'function' ? value(slots[i].value) : value; }]; }, useRef(initial) { const i = index++; return slots[i] || (slots[i] = { current: initial }); }, useEffect(fn, deps) { const i = index++, old = slots[i]; if (!old || deps.some((value, j) => !Object.is(value, old.deps[j]))) {
            effects.push(() => { old?.cleanup?.(); slots[i] = { deps, cleanup: fn() }; });
        } } };
    class CaptureFile extends Blob {
        constructor(parts, name, options) { super(parts, options); this.name = name; }
    }
    class CaptureFormData {
        constructor() { this.fields = new Map(); }
        append(name, value) { this.fields.set(name, value); }
        get(name) { return this.fields.get(name); }
    }
    const m = { exports: {} };
    vm.runInNewContext(source, { module: m, exports: m.exports, require: id => id === 'react' ? hooks : id.endsWith('.css') ? {} : req(id), navigator: { userAgent: 'Desktop regression check', platform: 'Linux', maxTouchPoints: 0, mediaDevices: { getUserMedia: constraints => new Promise((resolve, reject) => requests.push({ constraints, resolve, reject })) } }, document: { createElement(tag) { assert(tag === 'canvas', 'Unexpected DOM element'); const canvas = { width: 0, height: 0, draws: [], getContext() { return { fillRect() {}, drawImage: (...args) => canvas.draws.push(args) }; }, toBlob(callback, type, quality) { if (canvas.draws[0]?.[0]?.normalizedBitmap) callback(new Blob([new Uint8Array([255,216,255,217])], {type:'image/jpeg'})); else photos.push({ callback, type, quality, canvas }); } }; canvases.push(canvas); return canvas; } }, window: { clearTimeout() { }, clearInterval() { }, setTimeout() { return 1; }, setInterval() { return 2; } }, createImageBitmap: () => { const bitmap = {width:1600,height:1200,normalizedBitmap:true,closed:0,close(){this.closed++;}}; return options.deferBitmap ? new Promise(resolve => bitmapRequests.push({resolve,bitmap})) : Promise.resolve(bitmap); }, Uint8Array, DataView, DOMException, File: CaptureFile, FormData: CaptureFormData, AbortController, Blob });
    const onBusyChange = value => busy.push(value), api = async (path, options) => { apiCalls.push({ path, options }); return { text: '20 litres of milk and 5 kg butter', uncertainties: [], source: 'Fake local OCR result' }; };
    function nodes(node, out = []) { if (Array.isArray(node)) {
        node.forEach(value => nodes(value, out));
        return out;
    } if (node && typeof node === 'object' && node.props) {
        out.push(node);
        nodes(node.props.children, out);
    } return out; }
    const text = node => node == null ? '' : Array.isArray(node) ? node.map(text).join('') : typeof node === 'object' ? text(node.props?.children) : String(node);
    function render() { index = 0; tree = m.exports.MultimodalInput({ api, onText: value => texts.push(value), onBusyChange, active }); for (const node of nodes(tree)) {
        if (node.props.ref && node.type === 'video')
            node.props.ref.current = frame;
        if (node.props.ref && node.type === 'input' && !node.props.ref.current)
            node.props.ref.current = { value: '', click() { } };
    } while (effects.length)
        effects.shift()(); return tree; }
    const button = label => { const node = nodes(tree).find(n => n.type === 'button' && (text(n) === label || n.props['aria-label'] === label)); assert(node, 'Missing button ' + label); return node; };
    const contains = value => text(tree).includes(value);
    render();
    return { render, button, contains, requests, photos, busy, apiCalls, texts, canvases, bitmapRequests, frame, get tree() { return tree; }, nodes: () => nodes(tree), hide() { active = false; render(); render(); }, unmount() { slots.forEach(slot => slot?.cleanup?.()); } };
}
function media() { const tracks = [{ kind: 'video', stops: 0 }, { kind: 'video', stops: 0 }, { kind: 'audio', stops: 0 }]; tracks.forEach(track => track.stop = () => { track.stops++; }); return { tracks, getTracks: () => tracks, getVideoTracks: () => tracks.filter(track => track.kind === 'video') }; }
function stopped(stream) { return stream.tracks.every(track => track.stops > 0); }
async function grant(h) { h.button('Take a photo').props.onClick(); h.render(); const stream = media(); h.requests.at(-1).resolve(stream); await tick(); h.render(); return stream; }
(async () => {
    const checks = [];
    for (const [name, expected] of [['NotAllowedError', 'Camera permission was declined.'], ['NotFoundError', 'No camera was found.']]) {
        const h = harness();
        h.button('Take a photo').props.onClick();
        h.render();
        assert(h.contains('Allow camera access') && h.busy.at(-1) === true, 'Pending camera permission must block submit');
        h.requests[0].reject(new DOMException('test permission error', name));
        await tick();
        h.render();
        assert(h.contains(expected) && h.busy.at(-1) === false && !h.apiCalls.length, 'Permission error lost or left busy: ' + name);
    }
    checks.push('Permission denied and no-device errors render useful recovery and release busy');
    const late = harness();
    late.button('Take a photo').props.onClick();
    late.render();
    late.button('Cancel').props.onClick();
    late.render();
    const staleStream = media();
    late.requests[0].resolve(staleStream);
    await tick();
    late.render();
    assert(stopped(staleStream) && !late.apiCalls.length && !late.contains('Capture photo') && late.busy.at(-1) === false, 'Cancelled permission grant leaked tracks');
    checks.push('Cancel before late permission grant stops every returned track');
    const happy = harness(), current = await grant(happy);
    assert(happy.frame.srcObject === current && happy.frame.plays === 1, 'Granted stream missing preview');
    assert(happy.requests[0].constraints.audio === false, 'Camera requested audio');
    happy.button('Capture photo').props.onClick();
    happy.render();
    assert(happy.photos.length === 1 && happy.photos[0].type === 'image/jpeg' && happy.photos[0].quality === 0.9, 'Capture is not a single JPEG');
    assert(happy.photos[0].canvas.width === 1600 && happy.photos[0].canvas.height === 1200 && happy.photos[0].canvas.draws.length === 1, 'Capture did not bound the image dimensions');
    happy.photos[0].callback(new Blob([new Uint8Array([255,216,255,217])], { type: 'image/jpeg' }));
    await tick();
    happy.render();
    const call = happy.apiCalls[0], file = call?.options.body.get('file');
    assert(happy.apiCalls.length === 1 && call.path === '/input/image' && file.name === 'purchasing-list.jpg' && file.type === 'image/jpeg', 'Photo did not use the image extraction endpoint');
    assert(stopped(current) && happy.frame.srcObject === null, 'Capture retained camera tracks');
    assert(happy.contains('Review extracted text') && happy.texts.length === 0 && happy.busy.at(-1) === true, 'Extraction bypassed pending editable review');
    for (const label of ['Voice input', 'Upload image', 'Take a photo']) assert(happy.button(label).props.disabled, 'Pending photo review permits replacement via ' + label);
    assert(!happy.button('Type a message').props.disabled && !happy.button('Add to request').props.disabled, 'Review disabled typing or explicit Add');
    const editable = happy.nodes().find(node => node.type === 'textarea' && node.props.id === 'extracted-purchase-text');
    assert(editable && editable.props.value === '20 litres of milk and 5 kg butter', 'Extracted editable text missing');
    editable.props.onChange({ target: { value: '20 litres of milk and 4 kg butter' } });
    happy.render();
    happy.button('Add to request').props.onClick();
    happy.render();
    assert(happy.texts.join() === '20 litres of milk and 4 kg butter' && !happy.contains('Review extracted text') && happy.busy.at(-1) === false, 'Explicit Add must apply edited text and release submission');
    checks.push('Successful frame becomes bounded JPEG, uses image OCR, remains editable and only adds text on explicit Add');
    const discarded = harness();
    await grant(discarded);
    discarded.button('Capture photo').props.onClick();
    discarded.photos[0].callback(new Blob([new Uint8Array([255,216,255,217])], { type: 'image/jpeg' }));
    await tick();
    discarded.render();
    assert(discarded.busy.at(-1) === true && !discarded.texts.length, 'Photo review did not hold submission');
    discarded.button('Discard extracted text').props.onClick();
    discarded.render();
    assert(!discarded.texts.length && !discarded.contains('Review extracted text') && discarded.busy.at(-1) === false, 'Discard must release submission without adding photo text');
    checks.push('Pending photo review blocks submission/replacement until explicit Add or Discard, keeping typing available');
    for (const leave of ['hide', 'unmount']) {
        const h = harness(), stream = await grant(h);
        h[leave]();
        assert(stopped(stream) && h.frame.srcObject === null && h.busy.at(-1) === false, leave + ' retained the live preview');
        const pending = harness();
        pending.button('Take a photo').props.onClick();
        pending.render();
        pending[leave]();
        const lateStream = media();
        pending.requests[0].resolve(lateStream);
        await tick();
        assert(stopped(lateStream) && !pending.apiCalls.length, leave + ' late permission leaked tracks');
    }
    checks.push('Hide and unmount clean up active preview and stop late-granted streams');
    const cancelled = harness(), cancelledStream = await grant(cancelled);
    cancelled.button('Capture photo').props.onClick();
    cancelled.render();
    cancelled.button('Cancel').props.onClick();
    cancelled.render();
    cancelled.photos[0].callback(new Blob(['late frame'], { type: 'image/jpeg' }));
    await tick();
    cancelled.render();
    assert(stopped(cancelledStream) && !cancelled.apiCalls.length && !cancelled.contains('Review extracted text') && cancelled.busy.at(-1) === false, 'Cancelled canvas callback uploaded a stale photo');
    checks.push('Late canvas blob callback after Cancel is ignored with no extraction or text');
    const pendingImage = harness({deferBitmap:true});
    const imageFile = new Blob([new Uint8Array([255,216,255,217])], {type:'image/jpeg'});
    function uploadImage(h) { h.nodes().find(node => node.type === 'input' && node.props['aria-label'] === 'Shopping list image file').props.onChange({target:{files:[imageFile]}}); }
    uploadImage(pendingImage);
    await tick();
    pendingImage.render();
    assert(pendingImage.busy.at(-1) === true && !pendingImage.apiCalls.length, 'Image decode did not hold pending work');
    pendingImage.button('Cancel').props.onClick();
    pendingImage.render();
    uploadImage(pendingImage);
    await tick();
    pendingImage.render();
    pendingImage.bitmapRequests[0].resolve(pendingImage.bitmapRequests[0].bitmap);
    await tick();
    pendingImage.render();
    assert(pendingImage.bitmapRequests[0].bitmap.closed === 1 && !pendingImage.apiCalls.length && pendingImage.busy.at(-1) === true, 'Cancelled decode uploaded or cleared the newer request');
    pendingImage.bitmapRequests[1].resolve(pendingImage.bitmapRequests[1].bitmap);
    await tick();
    pendingImage.render();
    assert(pendingImage.apiCalls.length === 1 && pendingImage.contains('Review extracted text') && pendingImage.busy.at(-1) === true && !pendingImage.texts.length, 'Newer image did not reach explicit review safely');
    assert(!pendingImage.contains('NVIDIA') && !pendingImage.contains('Fake local OCR result'), 'Customer media review exposes provider internals');
    checks.push('Cancelled image normalization cannot upload, clear newer work or overwrite its explicit review');
    const report = { scope: 'Actual MultimodalInput handlers with deferred getUserMedia, fake streams and canvas; unit/state-machine evidence only, not browser or actual device QA', checks_passed: checks.length, checks };
    fs.mkdirSync(reportDirectory, { recursive: true });
    fs.writeFileSync(path.join(reportDirectory, 'camera-lifecycle-report.json'), JSON.stringify(report, null, 2) + '\n');
    console.log(JSON.stringify(report, null, 2));
})().catch(error => { console.error(error); process.exitCode = 1; });
