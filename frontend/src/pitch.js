// Pitch tracking for the Tone Coach, entirely in the browser: the learner's
// recording never leaves the device -- only the numbers this returns (pitch
// and loudness every 10 ms) are sent to the server, which judges the tone
// from the pitch SHAPE (backend services/tone_coach.py).
//
// The tracker is YIN (de Cheveigné & Kawahara, 2002): for each 40 ms frame
// it finds the lag at which the signal best repeats itself (the cumulative
// mean normalised difference first dips under a threshold), refines it by
// parabolic interpolation, and reports sampleRate / lag. Quiet frames and
// frames without a clear period are unvoiced (0).

const TARGET_RATE = 16000;
const FRAME_S = 0.04;
const THRESHOLD = 0.15;

function downsample(samples, sampleRate) {
  const factor = Math.max(1, Math.round(sampleRate / TARGET_RATE));
  if (factor === 1) return { data: samples, rate: sampleRate };
  const out = new Float32Array(Math.floor(samples.length / factor));
  for (let i = 0; i < out.length; i++) {
    let sum = 0;
    for (let k = 0; k < factor; k++) sum += samples[i * factor + k];
    out[i] = sum / factor; // averaging is the low-pass that keeps it alias-free enough for speech pitch
  }
  return { data: out, rate: sampleRate / factor };
}

function yinFrame(x, start, size, tauMin, tauMax, rate) {
  const w = size - tauMax;
  const d = new Float32Array(tauMax + 1);
  for (let tau = 1; tau <= tauMax; tau++) {
    let sum = 0;
    for (let j = 0; j < w; j++) {
      const diff = x[start + j] - x[start + j + tau];
      sum += diff * diff;
    }
    d[tau] = sum;
  }
  let running = 0;
  let tau = -1;
  const cmnd = new Float32Array(tauMax + 1);
  cmnd[0] = 1;
  for (let t = 1; t <= tauMax; t++) {
    running += d[t];
    cmnd[t] = running ? (d[t] * t) / running : 1;
  }
  for (let t = tauMin; t <= tauMax; t++) {
    if (cmnd[t] < THRESHOLD) {
      while (t + 1 <= tauMax && cmnd[t + 1] < cmnd[t]) t++;
      tau = t;
      break;
    }
  }
  if (tau < 0) return 0;
  // Parabolic interpolation around the minimum for sub-sample precision.
  const a = cmnd[tau - 1] ?? cmnd[tau];
  const b = cmnd[tau];
  const c = cmnd[tau + 1] ?? cmnd[tau];
  const denom = a - 2 * b + c;
  const shift = denom ? (0.5 * (a - c)) / denom : 0;
  return rate / (tau + Math.max(-1, Math.min(1, shift)));
}

// samples: Float32Array (mono); returns { f0: number[], rms: number[] } per 10 ms.
export function analysePitch(samples, sampleRate, { hopMs = 10, minHz = 70, maxHz = 500, maxFrames = 500 } = {}) {
  const { data, rate } = downsample(samples, sampleRate);
  const size = Math.round(rate * FRAME_S);
  const hop = Math.round((rate * hopMs) / 1000);
  const tauMin = Math.floor(rate / maxHz);
  const tauMax = Math.min(Math.ceil(rate / minHz), size - 1);
  const f0 = [];
  const rms = [];
  for (let start = 0; start + size <= data.length && f0.length < maxFrames; start += hop) {
    let energy = 0;
    for (let j = 0; j < size; j++) energy += data[start + j] * data[start + j];
    rms.push(Math.sqrt(energy / size));
    f0.push(yinFrame(data, start, size, tauMin, tauMax, rate));
  }
  // Voicing gate relative to the loudest frame: room noise is not speech.
  const peak = Math.max(0, ...rms);
  const gate = Math.max(0.008, peak * 0.12);
  for (let i = 0; i < f0.length; i++) {
    if (rms[i] < gate || f0[i] < minHz || f0[i] > maxHz) f0[i] = 0;
  }
  return { f0: f0.map((v) => Math.round(v * 10) / 10), rms: rms.map((v) => Math.round(v * 10000) / 10000) };
}

export const recordingSupported =
  typeof window !== "undefined" &&
  !!navigator.mediaDevices?.getUserMedia &&
  typeof window.MediaRecorder !== "undefined" &&
  !!(window.AudioContext || window.webkitAudioContext);

// Records `ms` of microphone audio and analyses it. Resolves with
// { f0, rms, url } (url plays the learner's own recording back, locally).
export async function recordAndAnalyse(ms) {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
  try {
    const recorder = new MediaRecorder(stream);
    const chunks = [];
    recorder.ondataavailable = (e) => e.data.size && chunks.push(e.data);
    const stopped = new Promise((resolve) => {
      recorder.onstop = resolve;
    });
    recorder.start();
    await new Promise((r) => setTimeout(r, ms));
    recorder.stop();
    await stopped;
    const blob = new Blob(chunks, { type: recorder.mimeType || "audio/webm" });
    const Ctx = window.AudioContext || window.webkitAudioContext;
    const ctx = new Ctx();
    try {
      const audio = await ctx.decodeAudioData(await blob.arrayBuffer());
      return { ...analysePitch(audio.getChannelData(0), audio.sampleRate), url: URL.createObjectURL(blob) };
    } finally {
      ctx.close?.();
    }
  } finally {
    stream.getTracks().forEach((t) => t.stop());
  }
}
