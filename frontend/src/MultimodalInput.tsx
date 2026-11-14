import { useEffect, useRef, useState } from "react";
import { AudioLines, Check, ImagePlus, LoaderCircle, Mic, Square, Camera, Type, X } from "lucide-react";
import "./multimodal.css";

type InputResult = { text: string; uncertainties: string[]; source: string; elapsed_ms: number; review_required: boolean };
type Props = {
  api: (path: string, options?: RequestInit) => Promise<any>;
  onText: (text: string) => void;
  disabled?: boolean;
  requiresSignIn?: boolean;
  active?: boolean;
  onSignIn?: () => void;
  onType?: () => void;
  onBusyChange?: (busy: boolean) => void;
};
const maxBytes = 5 * 1024 * 1024;

// Browser decoding applies EXIF orientation; a fresh raster carries no original metadata.
export async function normalizePurchasingImage(file: File, signal: AbortSignal): Promise<File> {
  const check = () => { if (signal.aborted) throw new DOMException("Image preparation cancelled.", "AbortError"); };
  if (!file.size || file.size > maxBytes) throw new Error("Choose a nonempty JPEG or PNG up to 5 MB.");
  check();
  const bytes = new Uint8Array(await file.arrayBuffer());
  check();
  const jpeg = bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff;
  const png = [137, 80, 78, 71, 13, 10, 26, 10].every((value, index) => bytes[index] === value);
  if (!jpeg && !png) throw new Error("Use a JPEG or PNG image.");
  if (png) {
    const view = new DataView(bytes.buffer);
    for (let offset = 8; offset + 12 <= bytes.length;) {
      const length = view.getUint32(offset);
      if (bytes[offset + 4] === 97 && bytes[offset + 5] === 99 && bytes[offset + 6] === 84 && bytes[offset + 7] === 76) throw new Error("Choose a single still JPEG or PNG image.");
      offset += length + 12;
    }
  }
  let bitmap: ImageBitmap | null = null;
  let image: HTMLImageElement | null = null;
  let objectUrl: string | null = null;
  let canvas: HTMLCanvasElement | null = null;
  try {
    if (typeof createImageBitmap === "function") {
      try { bitmap = await createImageBitmap(file, { imageOrientation: "from-image" }); }
      catch { check(); /* Older browsers can still decode the supported raster through Image. */ }
    }
    check();
    if (!bitmap) {
      image = new Image();
      objectUrl = URL.createObjectURL(file);
      const target = image;
      await new Promise<void>((resolve, reject) => {
        const finish = (error?: Error) => { target.onload = null; target.onerror = null; signal.removeEventListener("abort", abort); error ? reject(error) : resolve(); };
        const abort = () => { target.src = ""; finish(new DOMException("Image preparation cancelled.", "AbortError")); };
        target.onload = () => finish();
        target.onerror = () => finish(new Error("The image could not be read. Choose a clear JPEG or PNG."));
        signal.addEventListener("abort", abort, { once: true });
        target.src = objectUrl!;
      });
    }
    check();
    const width = bitmap ? bitmap.width : image!.naturalWidth;
    const height = bitmap ? bitmap.height : image!.naturalHeight;
    if (!Number.isFinite(width) || !Number.isFinite(height) || Math.min(width, height) < 16) throw new Error("Choose a clear image at least 16 pixels on each side.");
    const scale = Math.min(1, 1600 / Math.max(width, height));
    canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.round(width * scale));
    canvas.height = Math.max(1, Math.round(height * scale));
    const context = canvas.getContext("2d");
    if (!context) throw new Error("This browser could not prepare the image. Try a different browser or type the request.");
    context.fillStyle = "white";
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.drawImage(bitmap || image!, 0, 0, canvas.width, canvas.height);
    const raster = canvas;
    const blob = await new Promise<Blob>((resolve, reject) => {
      const abort = () => reject(new DOMException("Image preparation cancelled.", "AbortError"));
      signal.addEventListener("abort", abort, { once: true });
      raster.toBlob((value) => {
        signal.removeEventListener("abort", abort);
        if (signal.aborted) { reject(new DOMException("Image preparation cancelled.", "AbortError")); return; }
        value ? resolve(value) : reject(new Error("The image could not be prepared. Choose a different JPEG or PNG."));
      }, "image/jpeg", 0.9);
    });
    check();
    if (!blob.size || blob.size > maxBytes || !["image/jpeg", "image/png"].includes(blob.type)) throw new Error("The prepared image could not fit within 5 MB. Choose a different image.");
    return new File([blob], blob.type === "image/png" ? "purchasing-list.png" : "purchasing-list.jpg", { type: blob.type });
  } finally {
    bitmap?.close();
    if (image) { image.onload = null; image.onerror = null; image.src = ""; }
    if (objectUrl) URL.revokeObjectURL(objectUrl);
    if (canvas) { canvas.width = 0; canvas.height = 0; }
  }
}

export function MultimodalInput({ api, onText, disabled, requiresSignIn, active = true, onSignIn, onType, onBusyChange }: Props) {
  const [recording, setRecording] = useState(false);
  const [requestingMic, setRequestingMic] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [result, setResult] = useState<InputResult | null>(null);
  const [draft, setDraft] = useState("");
  const imageInput = useRef<HTMLInputElement>(null);
  const cameraInput = useRef<HTMLInputElement>(null);
  const video = useRef<HTMLVideoElement>(null);
  const cameraStream = useRef<MediaStream | null>(null);
  const cameraGeneration = useRef(0);
  const activeRef = useRef(active);
  activeRef.current = active;
  const [cameraOpen, setCameraOpen] = useState(false);
  const [cameraReady, setCameraReady] = useState(false);
  const [capturing, setCapturing] = useState(false);
  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const micGeneration = useRef(0);
  const micRequestPending = useRef(false);
  const cancelled = useRef(false);
  const alive = useRef(true);
  const pending = useRef<AbortController | null>(null);
  const timer = useRef<number | undefined>(undefined);
  const ticker = useRef<number | undefined>(undefined);

  useEffect(() => {
    onBusyChange?.(requestingMic || recording || Boolean(busy) || cameraOpen || Boolean(result));
  }, [requestingMic, recording, busy, cameraOpen, result, onBusyChange]);
  useEffect(() => () => onBusyChange?.(false), [onBusyChange]);

  function clearTimers() {
    window.clearTimeout(timer.current);
    window.clearInterval(ticker.current);
  }
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
      cancelled.current = true;
      micGeneration.current += 1;
      micRequestPending.current = false;
      clearTimers();
      pending.current?.abort();
      stopCamera(false);
      if (recorder.current?.state === "recording") recorder.current.stop();
      stream.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);
  useEffect(() => {
    if (!active) {
      cancelMicrophoneRequest();
      clearTimers();
      if (recorder.current?.state === "recording") recorder.current.stop();
      stream.current?.getTracks().forEach((track) => track.stop());
      setRecording(false);
      stopCamera();
      pending.current?.abort(); setBusy("");
    }
  }, [active]);

  async function extract(file: File, kind: "image" | "audio") {
    if (disabled || result) return;
    if (!file.size || file.size > maxBytes) {
      setError("Choose a nonempty file up to 5 MB.");
      return;
    }
    setError(""); setBusy(kind); setResult(null);
    pending.current?.abort();
    const controller = new AbortController(); pending.current = controller;
    try {
      const upload = kind === "image" ? await normalizePurchasingImage(file, controller.signal) : file;
      if (!alive.current || !activeRef.current || controller.signal.aborted || pending.current !== controller) return;
      const form = new FormData(); form.append("file", upload);
      const data: InputResult = await api(`/input/${kind}`, { method: "POST", body: form, signal: controller.signal });
      if (!alive.current || !activeRef.current || controller.signal.aborted || pending.current !== controller) return;
      setResult(data); setDraft(data.text || "");
    } catch (err) {
      if (alive.current && activeRef.current && !controller.signal.aborted && pending.current === controller) setError(err instanceof Error ? err.message : "This input could not be read. Try a clearer file or type the request.");
    } finally {
      if (alive.current && pending.current === controller) {
        pending.current = null;
        setBusy("");
        if (imageInput.current) imageInput.current.value = "";
        if (cameraInput.current) cameraInput.current.value = "";
      }
    }
  }

  function stopRecording(cancel = false) {
    cancelled.current = cancel;
    clearTimers();
    if (recorder.current?.state === "recording") recorder.current.stop();
    stream.current?.getTracks().forEach((track) => track.stop());
    setRecording(false);
  }
  function cancelMicrophoneRequest() {
    micGeneration.current += 1;
    micRequestPending.current = false;
    cancelled.current = true;
    setRequestingMic(false);
  }
  async function startRecording() {
    if (disabled) { if (requiresSignIn) onSignIn?.(); return; }
    if (micRequestPending.current || recording || recorder.current?.state === "recording" || !activeRef.current) return;
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setError("Microphone recording is unavailable in this browser. Type your request instead.");
      return;
    }
    const generation = ++micGeneration.current;
    micRequestPending.current = true;
    setRequestingMic(true);
    setError(""); setResult(null); setSeconds(0); cancelled.current = false;
    let requestedMedia: MediaStream | null = null;
    try {
      const media = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1 }, video: false });
      requestedMedia = media;
      if (!alive.current || !activeRef.current || cancelled.current || generation !== micGeneration.current) { media.getTracks().forEach((track) => track.stop()); return; }
      stream.current = media;
      const mime = ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/mp4"].find((type) => MediaRecorder.isTypeSupported(type));
      const capture = new MediaRecorder(media, mime ? { mimeType: mime } : undefined);
      recorder.current = capture;
      const parts: Blob[] = []; let total = 0;
      capture.ondataavailable = (event) => {
        if (generation !== micGeneration.current || cancelled.current) return;
        if (!event.data.size) return;
        total += event.data.size;
        if (total > maxBytes) { stopRecording(true); setError("The audio clip exceeded 5 MB. Record a shorter request."); return; }
        parts.push(event.data);
      };
      capture.onerror = () => { if (!alive.current || generation !== micGeneration.current) return; stopRecording(true); setError("The microphone stopped unexpectedly. Type your request instead."); };
      capture.onstop = () => {
        media.getTracks().forEach((track) => track.stop());
        if (!alive.current || cancelled.current || generation !== micGeneration.current) return;
        clearTimers();
        setRecording(false);
        const type = capture.mimeType || "audio/webm";
        const extension = type.includes("mp4") ? "m4a" : type.includes("ogg") ? "ogg" : "webm";
        void extract(new File(parts, `purchasing-request.${extension}`, { type }), "audio");
      };
      capture.start(250); setRecording(true);
      ticker.current = window.setInterval(() => setSeconds((value) => value + 1), 1000);
      timer.current = window.setTimeout(() => stopRecording(), 30000);
    } catch (err) {
      requestedMedia?.getTracks().forEach((track) => track.stop());
      if (!alive.current || !activeRef.current || cancelled.current || generation !== micGeneration.current) return;
      setError(err instanceof DOMException && err.name === "NotAllowedError" ? "Microphone permission was declined. Allow it in your browser settings, type the request instead." : "The microphone is unavailable. Type your request instead.");
    } finally {
      if (alive.current && generation === micGeneration.current) {
        micRequestPending.current = false;
        setRequestingMic(false);
      }
    }
  }

  function stopCamera(update = true) {
    cameraGeneration.current += 1;
    cameraStream.current?.getTracks().forEach((track) => track.stop());
    cameraStream.current = null;
    if (video.current) video.current.srcObject = null;
    if (update) { setCameraOpen(false); setCameraReady(false); setCapturing(false); }
  }
  useEffect(() => {
    if (!cameraOpen || !cameraReady || !video.current || !cameraStream.current) return;
    video.current.srcObject = cameraStream.current;
    void video.current.play().catch(() => { setError("Camera preview could not start. Try Upload image instead."); stopCamera(); });
  }, [cameraOpen, cameraReady]);
  async function openCamera() {
    if (disabled) return;
    const mobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
    setError("");
    if (mobile) { cameraInput.current?.click(); return; }
    if (!navigator.mediaDevices?.getUserMedia) { setError("Camera capture is unavailable. Use Upload image instead."); return; }
    const generation = ++cameraGeneration.current;
    setCameraOpen(true); setCameraReady(false);
    try {
      const media = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 }, height: { ideal: 960 } }, audio: false });
      if (!alive.current || !activeRef.current || generation !== cameraGeneration.current) { media.getTracks().forEach((track) => track.stop()); return; }
      cameraStream.current = media;
      media.getVideoTracks().forEach((track) => { track.onended = () => { if (generation === cameraGeneration.current) { setError("The camera disconnected. Use Upload image or try again."); stopCamera(); } }; });
      setCameraReady(true);
    } catch (err) {
      if (!alive.current || generation !== cameraGeneration.current) return;
      const name = err instanceof DOMException ? err.name : "";
      setError(name === "NotAllowedError" ? "Camera permission was declined. Allow the camera in browser settings or use Upload image." : name === "NotFoundError" ? "No camera was found. Use Upload image instead." : "The camera could not be opened. Close other camera apps or use Upload image.");
      stopCamera();
    }
  }
  function capturePhoto() {
    if (!video.current || !cameraReady || capturing) return;
    const frame = video.current;
    if (!frame.videoWidth || !frame.videoHeight) { setError("Wait for the camera preview before taking a photo."); return; }
    setCapturing(true);
    const generation = cameraGeneration.current;
    const canvas = document.createElement("canvas");
    const scale = Math.min(1, 1600 / Math.max(frame.videoWidth, frame.videoHeight));
    canvas.width = Math.round(frame.videoWidth * scale); canvas.height = Math.round(frame.videoHeight * scale);
    const context = canvas.getContext("2d");
    if (!context) { setCapturing(false); setError("Photo capture is unavailable. Use Upload image instead."); return; }
    context.drawImage(frame, 0, 0, canvas.width, canvas.height);
    canvas.toBlob((blob) => {
      if (!alive.current || !activeRef.current || generation !== cameraGeneration.current) return;
      if (!blob) { setCapturing(false); setError("The photo could not be captured. Try again."); return; }
      stopCamera();
      void extract(new File([blob], "purchasing-photo.jpg", { type: "image/jpeg" }), "image");
    }, "image/jpeg", 0.9);
  }

  return <div className="input-tools" aria-label="Voice and image ordering">
    <input ref={imageInput} type="file" accept="image/jpeg,image/png" hidden aria-label="Shopping list image file" onChange={(event) => { const file = event.target.files?.[0]; if (file) void extract(file, "image"); }} />
    <input ref={cameraInput} type="file" accept="image/jpeg,image/png" capture="environment" hidden aria-label="Take a photo of the purchasing list" onChange={(event) => { const file = event.target.files?.[0]; if (file) void extract(file, "image"); }} />
    <div className="input-tool-buttons">
      {requestingMic ? <><span role="status"><LoaderCircle size={14} className="spin" />Allow microphone access in your browser…</span><button type="button" onClick={cancelMicrophoneRequest}><X size={14} />Cancel</button></> : recording ? <><button type="button" className="input-recording" onClick={() => stopRecording()}><Square size={14} />Stop & transcribe · {seconds}s</button><button type="button" onClick={() => stopRecording(true)}><X size={14} />Cancel</button></> : <>
        <button type="button" disabled={Boolean(busy) || cameraOpen || Boolean(disabled && !requiresSignIn)} onClick={onType}><Type size={15} />Type a message</button>
        <button type="button" disabled={Boolean(busy) || cameraOpen || Boolean(result) || Boolean(disabled && !requiresSignIn)} onClick={() => { if (requiresSignIn) { onSignIn?.(); return; } void startRecording(); }}><Mic size={15} />Voice input</button>
        <button type="button" disabled={Boolean(busy) || cameraOpen || Boolean(result) || Boolean(disabled && !requiresSignIn)} onClick={() => { if (requiresSignIn) { onSignIn?.(); return; } imageInput.current?.click(); }}><ImagePlus size={15} />Upload image</button>
        <button type="button" disabled={Boolean(busy) || cameraOpen || Boolean(result) || Boolean(disabled && !requiresSignIn)} onClick={() => { if (requiresSignIn) { onSignIn?.(); return; } void openCamera(); }}><Camera size={15} />Take a photo</button>
      </>}
    </div>
    {cameraOpen && <section className="input-camera" aria-label="Camera preview" onKeyDown={(event) => { if (event.key === "Escape") stopCamera(); }}><div><strong>Camera</strong><button type="button" aria-label="Close camera" onClick={() => stopCamera()}><X size={18} /></button></div><video ref={video} autoPlay muted playsInline aria-label="Live camera preview" />{!cameraReady && <p role="status">Allow camera access in your browser to continue.</p>}<div className="input-camera-actions"><button type="button" disabled={!cameraReady || capturing} onClick={capturePhoto}>{capturing ? "Capturing…" : "Capture photo"}</button><button type="button" onClick={() => stopCamera()}>Cancel</button></div></section>}
    <details className="input-privacy"><summary>Input privacy</summary><p>Images may be processed by an external service. Use nonconfidential demonstration lists only. Images up to 5 MB; voice up to 30 seconds. Media is not saved to your workspace.</p></details>
    {recording && <p className="input-recording-note" role="status"><AudioLines size={16} />Recording your microphone. Stopping sends this clip for transcription.</p>}
    {busy && <div className="input-progress" role="status"><LoaderCircle size={16} className="spin" />{busy === "image" ? "Reading your shopping list…" : "Transcribing your audio…"}<button type="button" onClick={() => { pending.current?.abort(); setBusy(""); }}>Cancel</button></div>}
    {error && <p className="input-error" role="alert">{error}</p>}
    {result && <section className="input-review" aria-label="Review extracted purchasing text">
      <div className="input-review-heading"><strong>Review extracted text</strong><button type="button" aria-label="Discard extracted text" onClick={() => setResult(null)}><X size={16} /></button></div>
      <label htmlFor="extracted-purchase-text">Editable extracted text</label>
      <textarea id="extracted-purchase-text" rows={4} maxLength={3000} value={draft} onChange={(event) => setDraft(event.target.value)} />
      {result.uncertainties?.length > 0 && <ul>{result.uncertainties.map((item, index) => <li key={index}>{item}</li>)}</ul>}
      <button type="button" className="input-use-text" disabled={!draft.trim() || disabled} onClick={() => { onText(draft.trim()); setResult(null); }}><Check size={15} />Add to request</button>
    </section>}
  </div>;
}
