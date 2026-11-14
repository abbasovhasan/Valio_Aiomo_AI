import { useEffect, useRef, useState } from "react";
import { AudioLines, Check, ImagePlus, LoaderCircle, Mic, Square, Upload, X } from "lucide-react";
import "./multimodal.css";

type InputResult = { text: string; uncertainties: string[]; source: string; elapsed_ms: number; review_required: boolean };
type Props = {
  api: (path: string, options?: RequestInit) => Promise<any>;
  onText: (text: string) => void;
  disabled?: boolean;
  requiresSignIn?: boolean;
  active?: boolean;
  onSignIn?: () => void;
};
const maxBytes = 5 * 1024 * 1024;

export function MultimodalInput({ api, onText, disabled, requiresSignIn, active = true, onSignIn }: Props) {
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [result, setResult] = useState<InputResult | null>(null);
  const [draft, setDraft] = useState("");
  const [imageProvider, setImageProvider] = useState("local");
  const [cloudConsent, setCloudConsent] = useState(false);
  const imageInput = useRef<HTMLInputElement>(null);
  const audioInput = useRef<HTMLInputElement>(null);
  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const cancelled = useRef(false);
  const alive = useRef(true);
  const pending = useRef<AbortController | null>(null);
  const timer = useRef<number | undefined>(undefined);
  const ticker = useRef<number | undefined>(undefined);

  function clearTimers() {
    window.clearTimeout(timer.current);
    window.clearInterval(ticker.current);
  }
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
      cancelled.current = true;
      clearTimers();
      pending.current?.abort();
      if (recorder.current?.state === "recording") recorder.current.stop();
      stream.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);
  useEffect(() => {
    if (!active) {
      cancelled.current = true;
      clearTimers();
      if (recorder.current?.state === "recording") recorder.current.stop();
      stream.current?.getTracks().forEach((track) => track.stop());
      setRecording(false);
    }
  }, [active]);

  async function extract(file: File, kind: "image" | "audio") {
    if (disabled) return;
    if (!file.size || file.size > maxBytes) {
      setError("Choose a nonempty file up to 5 MB.");
      return;
    }
    setError(""); setBusy(kind); setResult(null);
    const form = new FormData(); form.append("file", file);
    const controller = new AbortController(); pending.current = controller;
    try {
      const query = kind === "image" ? `?provider=${imageProvider}${imageProvider === "nvidia" && cloudConsent ? "&cloud_consent=true" : ""}` : "";
      const data: InputResult = await api(`/input/${kind}${query}`, { method: "POST", body: form, signal: controller.signal });
      if (!alive.current) return;
      setResult(data); setDraft(data.text || "");
    } catch (err) {
      if (alive.current && !controller.signal.aborted) setError(err instanceof Error ? err.message : "This input could not be read. Try a clearer file or type the request.");
    } finally {
      if (alive.current) { setBusy(""); if (kind === "image") setCloudConsent(false); }
      if (imageInput.current) imageInput.current.value = "";
      if (audioInput.current) audioInput.current.value = "";
    }
  }

  function stopRecording(cancel = false) {
    cancelled.current = cancel;
    clearTimers();
    if (recorder.current?.state === "recording") recorder.current.stop();
    stream.current?.getTracks().forEach((track) => track.stop());
    setRecording(false);
  }
  async function startRecording() {
    if (disabled) { if (requiresSignIn) onSignIn?.(); return; }
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setError("Microphone recording is unavailable in this browser. Upload an audio clip or type your request.");
      return;
    }
    setError(""); setResult(null); setSeconds(0); cancelled.current = false;
    try {
      const media = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1 }, video: false });
      if (!alive.current) { media.getTracks().forEach((track) => track.stop()); return; }
      stream.current = media;
      const mime = ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/mp4"].find((type) => MediaRecorder.isTypeSupported(type));
      const capture = new MediaRecorder(media, mime ? { mimeType: mime } : undefined);
      recorder.current = capture;
      const parts: Blob[] = []; let total = 0;
      capture.ondataavailable = (event) => {
        if (!event.data.size) return;
        total += event.data.size;
        if (total > maxBytes) { stopRecording(true); setError("The audio clip exceeded 5 MB. Record a shorter request."); return; }
        parts.push(event.data);
      };
      capture.onerror = () => { stopRecording(true); setError("The microphone stopped unexpectedly. Try an audio upload instead."); };
      capture.onstop = () => {
        media.getTracks().forEach((track) => track.stop()); clearTimers();
        if (!alive.current || cancelled.current) return;
        setRecording(false);
        const type = capture.mimeType || "audio/webm";
        const extension = type.includes("mp4") ? "m4a" : type.includes("ogg") ? "ogg" : "webm";
        void extract(new File(parts, `purchasing-request.${extension}`, { type }), "audio");
      };
      capture.start(250); setRecording(true);
      ticker.current = window.setInterval(() => setSeconds((value) => value + 1), 1000);
      timer.current = window.setTimeout(() => stopRecording(), 30000);
    } catch (err) {
      stream.current?.getTracks().forEach((track) => track.stop());
      setError(err instanceof DOMException && err.name === "NotAllowedError" ? "Microphone permission was declined. Allow it in your browser settings, upload an audio clip, or type the request." : "The microphone is unavailable. Upload an audio clip or type your request.");
    }
  }

  return <div className="input-tools" aria-label="Voice and image ordering">
    <input ref={imageInput} type="file" accept="image/jpeg,image/png" hidden aria-label="Shopping list image file" onChange={(event) => { const file = event.target.files?.[0]; if (file) void extract(file, "image"); }} />
    <input ref={audioInput} type="file" accept="audio/*,.webm,.m4a,.ogg,.wav,.mp3" hidden aria-label="Purchasing audio file" onChange={(event) => { const file = event.target.files?.[0]; if (file) void extract(file, "audio"); }} />
    <div className="input-tool-buttons">
      {recording ? <><button type="button" className="input-recording" onClick={() => stopRecording()}><Square size={14} />Stop & transcribe · {seconds}s</button><button type="button" onClick={() => stopRecording(true)}><X size={14} />Cancel recording</button></> : <>
        <button type="button" disabled={Boolean(busy) || Boolean(disabled && !requiresSignIn)} onClick={() => { if (requiresSignIn) { onSignIn?.(); return; } void startRecording(); }}><Mic size={15} />Speak your order</button>
        <button type="button" disabled={Boolean(busy) || Boolean(disabled && !requiresSignIn) || (imageProvider === "nvidia" && !cloudConsent)} onClick={() => { if (requiresSignIn) { onSignIn?.(); return; } imageInput.current?.click(); }}><ImagePlus size={15} />Add photo or list</button>
        <button type="button" disabled={Boolean(busy) || Boolean(disabled && !requiresSignIn)} onClick={() => { if (requiresSignIn) { onSignIn?.(); return; } audioInput.current?.click(); }}><Upload size={14} />Upload audio</button>
      </>}
    </div>
    <p className="input-tools-note">Combine typing with a photo or a voice clip. Review the extracted text before adding it. Audio: up to 30 seconds; files: up to 5 MB.</p>
    <details className="input-privacy"><summary>Image reading & privacy</summary><label>Image reader<select value={imageProvider} onChange={(event) => { setImageProvider(event.target.value); setCloudConsent(false); }} disabled={Boolean(busy) || recording}><option value="local">On this server · no external image service</option><option value="nvidia">NVIDIA vision · nonconfidential demo lists only</option></select></label><p>Audio is transcribed on this server. Uploaded files are processed for extraction without being saved to your workspace.</p>{imageProvider === "nvidia" && <label className="input-cloud-consent"><input type="checkbox" checked={cloudConsent} onChange={(event) => setCloudConsent(event.target.checked)} /><span>This image contains only nonconfidential demonstration content. Send it to NVIDIA’s trial vision service for reading.</span></label>}</details>
    {recording && <p className="input-recording-note" role="status"><AudioLines size={16} />Recording your microphone. Stopping sends this clip for transcription.</p>}
    {busy && <div className="input-progress" role="status"><LoaderCircle size={16} className="spin" />{busy === "image" ? "Reading your shopping list…" : "Transcribing your audio…"}<button type="button" onClick={() => { pending.current?.abort(); setBusy(""); }}>Cancel</button></div>}
    {error && <p className="input-error" role="alert">{error}</p>}
    {result && <section className="input-review" aria-label="Review extracted purchasing text">
      <div className="input-review-heading"><strong>Check the details before adding</strong><button type="button" aria-label="Discard extracted text" onClick={() => setResult(null)}><X size={16} /></button></div>
      <label htmlFor="extracted-purchase-text">Editable extracted text</label>
      <textarea id="extracted-purchase-text" rows={4} maxLength={3000} value={draft} onChange={(event) => setDraft(event.target.value)} />
      {result.uncertainties?.length > 0 && <ul>{result.uncertainties.map((item, index) => <li key={index}>{item}</li>)}</ul>}
      <p>{result.source}. Product specifications, prices and stock will be checked when you build the cart.</p>
      <button type="button" className="input-use-text" disabled={!draft.trim() || disabled} onClick={() => { onText(draft.trim()); setResult(null); }}><Check size={15} />Add this text to my request</button>
    </section>}
  </div>;
}
