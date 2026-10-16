// Builds the derived brand assets from the one real logo in frontend/photo/.
//
//   node scripts/build_brand_assets.mjs        (run from frontend/)
//
// The source PNG is opaque on a near-white ground, and the UI shows the logo
// with no background at all, straight on the page. CSS can't make an opaque
// image's ground transparent without also recolouring the artwork (multiply
// shifts every pixel; darken clips a third of them), so this script lifts the
// white ground out once and writes:
//
//   src/assets/chineseverse-logo-matte.png   the logo, background transparent
//   public/favicon-{16,32,48,64}.png, favicon.ico, apple-touch-icon.png,
//   public/icon-512.png                      the emblem, background transparent
//   android/.../res/mipmap-*/, drawable*/splash.png, ios/.../Assets.xcassets,
//   store-assets/play-icon-512.png           the mobile app's launcher icons
//                                            and splash screens
//
// The artwork itself is never redrawn: every pixel away from the background
// keeps its exact colour and full opacity. Only background pixels become
// transparent, and the antialiased rim next to them is un-mixed from white
// so it composites cleanly onto any colour (and back onto white unchanged).
//
// No dependencies: PNG is decoded/encoded with node:zlib.
import fs from "node:fs";
import path from "node:path";
import zlib from "node:zlib";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const SOURCE = path.join(ROOT, "photo", "Chineseverse logo 🎀❤️✨.png");

// A pixel whose darkest channel is at least this bright is background.
const BG_MIN = 240;
// Un-mixing only touches the rim this many pixels from the background, so
// pale highlights inside the artwork stay opaque and exact.
const RIM = 2;
// Rim pixels whose darkest channel is at or below 255 * (1 - ALPHA_FULL) are
// solid ink and stay fully opaque; lighter rim pixels get partial alpha.
const ALPHA_FULL = 0.6;
// Off-white noise in the source (mostly inside letter counters) survives the
// background test as a few faint, disconnected pixels. Islands smaller than
// SPECK_PX whose strongest pixel is under SPECK_ALPHA are background residue,
// not artwork — every real part of the logo is far larger and fully opaque.
const SPECK_PX = 64;
const SPECK_ALPHA = 64;

// The emblem crop used for the icons — the same square as the collapsed
// sidebar mark (.brand-logo--mark in index.css): x 68..632, y 24..588, which
// stops just short of the wordmark's "C" at x 633.
const MARK = { x: 68, y: 24, size: 565 };

// ---------- PNG ----------
const CRC_TABLE = new Uint32Array(256).map((_, n) => {
  let c = n;
  for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
  return c >>> 0;
});
function crc32(buf) {
  let c = 0xffffffff;
  for (const b of buf) c = CRC_TABLE[(c ^ b) & 255] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

function decodePng(file) {
  const b = fs.readFileSync(file);
  let pos = 8;
  let w, h, depth, type, interlace;
  const idat = [];
  while (pos < b.length) {
    const len = b.readUInt32BE(pos);
    const kind = b.toString("ascii", pos + 4, pos + 8);
    const data = b.subarray(pos + 8, pos + 8 + len);
    if (kind === "IHDR") {
      w = data.readUInt32BE(0);
      h = data.readUInt32BE(4);
      depth = data[8];
      type = data[9];
      interlace = data[12];
    } else if (kind === "IDAT") idat.push(data);
    pos += 12 + len;
  }
  if (depth !== 8 || (type !== 6 && type !== 2) || interlace !== 0) {
    throw new Error(`unsupported PNG (depth ${depth}, colour type ${type}, interlace ${interlace})`);
  }
  const bpp = type === 6 ? 4 : 3;
  const raw = zlib.inflateSync(Buffer.concat(idat));
  const stride = w * bpp;
  const rows = Buffer.alloc(stride * h);
  for (let y = 0; y < h; y++) {
    const f = raw[y * (stride + 1)];
    for (let x = 0; x < stride; x++) {
      const r = raw[y * (stride + 1) + 1 + x];
      const a = x >= bpp ? rows[y * stride + x - bpp] : 0;
      const u = y ? rows[(y - 1) * stride + x] : 0;
      const c = x >= bpp && y ? rows[(y - 1) * stride + x - bpp] : 0;
      let v;
      if (f === 0) v = r;
      else if (f === 1) v = r + a;
      else if (f === 2) v = r + u;
      else if (f === 3) v = r + ((a + u) >> 1);
      else {
        const p = a + u - c, pa = Math.abs(p - a), pb = Math.abs(p - u), pc = Math.abs(p - c);
        v = r + (pa <= pb && pa <= pc ? a : pb <= pc ? u : c);
      }
      rows[y * stride + x] = v & 255;
    }
  }
  const px = Buffer.alloc(w * h * 4);
  for (let i = 0, j = 0; i < w * h; i++, j += bpp) {
    px[i * 4] = rows[j];
    px[i * 4 + 1] = rows[j + 1];
    px[i * 4 + 2] = rows[j + 2];
    px[i * 4 + 3] = bpp === 4 ? rows[j + 3] : 255;
  }
  return { w, h, px };
}

function encodePng({ w, h, px }) {
  const stride = w * 4;
  const out = Buffer.alloc((stride + 1) * h);
  const line = Buffer.alloc(stride);
  for (let y = 0; y < h; y++) {
    // Adaptive filter: pick whichever filter gives the smallest residuals.
    let best = null, bestSum = Infinity, bestF = 0;
    for (let f = 0; f < 5; f++) {
      let sum = 0;
      for (let x = 0; x < stride; x++) {
        const cur = px[y * stride + x];
        const a = x >= 4 ? px[y * stride + x - 4] : 0;
        const u = y ? px[(y - 1) * stride + x] : 0;
        const c = x >= 4 && y ? px[(y - 1) * stride + x - 4] : 0;
        let pred = 0;
        if (f === 1) pred = a;
        else if (f === 2) pred = u;
        else if (f === 3) pred = (a + u) >> 1;
        else if (f === 4) {
          const p = a + u - c, pa = Math.abs(p - a), pb = Math.abs(p - u), pc = Math.abs(p - c);
          pred = pa <= pb && pa <= pc ? a : pb <= pc ? u : c;
        }
        const v = (cur - pred) & 255;
        line[x] = v;
        sum += v < 128 ? v : 256 - v;
      }
      if (sum < bestSum) {
        bestSum = sum;
        bestF = f;
        best = Buffer.from(line);
      }
    }
    out[y * (stride + 1)] = bestF;
    best.copy(out, y * (stride + 1) + 1);
  }
  const chunk = (kind, data) => {
    const len = Buffer.alloc(4);
    len.writeUInt32BE(data.length);
    const body = Buffer.concat([Buffer.from(kind, "ascii"), data]);
    const crc = Buffer.alloc(4);
    crc.writeUInt32BE(crc32(body));
    return Buffer.concat([len, body, crc]);
  };
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(w, 0);
  ihdr.writeUInt32BE(h, 4);
  ihdr[8] = 8;
  ihdr[9] = 6;
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk("IHDR", ihdr),
    chunk("IDAT", zlib.deflateSync(out, { level: 9 })),
    chunk("IEND", Buffer.alloc(0)),
  ]);
}

// ---------- matte ----------
function matte({ w, h, px }) {
  const isBg = new Uint8Array(w * h);
  for (let i = 0; i < w * h; i++) {
    isBg[i] = Math.min(px[i * 4], px[i * 4 + 1], px[i * 4 + 2]) >= BG_MIN ? 1 : 0;
  }
  // Chebyshev distance <= RIM to any background pixel.
  const nearBg = new Uint8Array(w * h);
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      if (isBg[y * w + x]) continue;
      search: for (let dy = -RIM; dy <= RIM; dy++) {
        for (let dx = -RIM; dx <= RIM; dx++) {
          const yy = y + dy, xx = x + dx;
          if (yy >= 0 && yy < h && xx >= 0 && xx < w && isBg[yy * w + xx]) {
            nearBg[y * w + x] = 1;
            break search;
          }
        }
      }
    }
  }
  const out = Buffer.from(px);
  for (let i = 0; i < w * h; i++) {
    const o = i * 4;
    if (isBg[i]) {
      out[o] = out[o + 1] = out[o + 2] = out[o + 3] = 0;
      continue;
    }
    if (!nearBg[i]) continue;
    // Un-mix from white: c = a * ink + (1 - a) * 255  =>  ink = 255 - (255 - c) / a.
    const darkest = Math.min(px[o], px[o + 1], px[o + 2]);
    const a = Math.min(1, (255 - darkest) / 255 / ALPHA_FULL);
    if (a >= 1) continue;
    for (let k = 0; k < 3; k++) {
      out[o + k] = Math.max(0, Math.min(255, Math.round(255 - (255 - px[o + k]) / a)));
    }
    out[o + 3] = Math.round(a * 255);
  }
  dropSpecks(w, h, out);
  return { w, h, px: out };
}

function dropSpecks(w, h, px) {
  const seen = new Uint8Array(w * h);
  for (let i = 0; i < w * h; i++) {
    if (seen[i] || px[i * 4 + 3] === 0) continue;
    const island = [];
    const stack = [i];
    seen[i] = 1;
    let maxAlpha = 0;
    while (stack.length) {
      const j = stack.pop();
      island.push(j);
      maxAlpha = Math.max(maxAlpha, px[j * 4 + 3]);
      const x = j % w, y = (j / w) | 0;
      for (let dy = -1; dy <= 1; dy++) {
        for (let dx = -1; dx <= 1; dx++) {
          const xx = x + dx, yy = y + dy;
          if (xx < 0 || yy < 0 || xx >= w || yy >= h) continue;
          const k = yy * w + xx;
          if (!seen[k] && px[k * 4 + 3] > 0) {
            seen[k] = 1;
            stack.push(k);
          }
        }
      }
    }
    if (island.length < SPECK_PX && maxAlpha < SPECK_ALPHA) {
      for (const j of island) px[j * 4] = px[j * 4 + 1] = px[j * 4 + 2] = px[j * 4 + 3] = 0;
    }
  }
}

// ---------- icons ----------
// Crop the emblem square and box-filter it down to `size`, keeping the
// transparent background. Colour is averaged premultiplied by alpha so the
// rim never picks up a dark or light fringe, and area-averaging keeps small
// sizes clean instead of aliasing.
function icon(img, size) {
  return encodePng({ w: size, h: size, px: emblemPixels(img, size) });
}

// The emblem's RGBA pixels at `size`: the box filter for every size up to
// the crop's own 565px, bilinear above it (the 1024px store icon, splash
// screens) -- a box narrower than one source pixel would only repeat pixels.
function emblemPixels(img, size) {
  if (size > MARK.size) return emblemUpscaled(img, size);
  const { w, px } = img;
  const out = Buffer.alloc(size * size * 4);
  const scale = MARK.size / size;
  for (let oy = 0; oy < size; oy++) {
    for (let ox = 0; ox < size; ox++) {
      const x0 = MARK.x + ox * scale, x1 = x0 + scale;
      const y0 = MARK.y + oy * scale, y1 = y0 + scale;
      let r = 0, g = 0, b = 0, alpha = 0, wsum = 0;
      for (let sy = Math.floor(y0); sy < Math.ceil(y1); sy++) {
        const wy = Math.min(y1, sy + 1) - Math.max(y0, sy);
        for (let sx = Math.floor(x0); sx < Math.ceil(x1); sx++) {
          const wx = Math.min(x1, sx + 1) - Math.max(x0, sx);
          const wt = wx * wy;
          const o = (sy * w + sx) * 4;
          const a = px[o + 3] / 255;
          r += wt * px[o] * a;
          g += wt * px[o + 1] * a;
          b += wt * px[o + 2] * a;
          alpha += wt * a;
          wsum += wt;
        }
      }
      const o = (oy * size + ox) * 4;
      const a = Math.round((alpha / wsum) * 255);
      if (a === 0) continue;
      out[o] = Math.round(r / alpha);
      out[o + 1] = Math.round(g / alpha);
      out[o + 2] = Math.round(b / alpha);
      out[o + 3] = a;
    }
  }
  return out;
}

// Bilinear, premultiplied by alpha like the box filter, clamped to the crop.
function emblemUpscaled(img, size) {
  const { w, px } = img;
  const out = Buffer.alloc(size * size * 4);
  const scale = MARK.size / size;
  const at = (x, y) => {
    const cx = Math.min(MARK.x + MARK.size - 1, Math.max(MARK.x, x));
    const cy = Math.min(MARK.y + MARK.size - 1, Math.max(MARK.y, y));
    return (cy * w + cx) * 4;
  };
  for (let oy = 0; oy < size; oy++) {
    const fy = MARK.y + (oy + 0.5) * scale - 0.5;
    const y0 = Math.floor(fy), ty = fy - y0;
    for (let ox = 0; ox < size; ox++) {
      const fx = MARK.x + (ox + 0.5) * scale - 0.5;
      const x0 = Math.floor(fx), tx = fx - x0;
      let r = 0, g = 0, b = 0, alpha = 0;
      for (const [sx, sy, wt] of [
        [x0, y0, (1 - tx) * (1 - ty)],
        [x0 + 1, y0, tx * (1 - ty)],
        [x0, y0 + 1, (1 - tx) * ty],
        [x0 + 1, y0 + 1, tx * ty],
      ]) {
        const o = at(sx, sy);
        const a = (px[o + 3] / 255) * wt;
        r += px[o] * a;
        g += px[o + 1] * a;
        b += px[o + 2] * a;
        alpha += a;
      }
      const a = Math.round(alpha * 255);
      if (a === 0) continue;
      const o = (oy * size + ox) * 4;
      out[o] = Math.round(r / alpha);
      out[o + 1] = Math.round(g / alpha);
      out[o + 2] = Math.round(b / alpha);
      out[o + 3] = a;
    }
  }
  return out;
}

// .ico with embedded PNG images (supported by every current browser).
function ico(pngs) {
  const head = Buffer.alloc(6 + 16 * pngs.length);
  head.writeUInt16LE(0, 0);
  head.writeUInt16LE(1, 2);
  head.writeUInt16LE(pngs.length, 4);
  let offset = head.length;
  pngs.forEach(({ size, data }, i) => {
    const e = 6 + 16 * i;
    head[e] = size >= 256 ? 0 : size;
    head[e + 1] = size >= 256 ? 0 : size;
    head.writeUInt16LE(1, e + 4);
    head.writeUInt16LE(32, e + 6);
    head.writeUInt32LE(data.length, e + 8);
    head.writeUInt32LE(offset, e + 12);
    offset += data.length;
  });
  return Buffer.concat([head, ...pngs.map((p) => p.data)]);
}

const source = decodePng(SOURCE);
const matted = matte(source);

const write = (rel, data) => {
  const file = path.join(ROOT, rel);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, data);
  console.log(`${rel}  ${data.length} bytes`);
};

write("src/assets/chineseverse-logo-matte.png", encodePng(matted));
const sizes = {};
for (const size of [16, 32, 48, 64, 180, 512]) sizes[size] = icon(matted, size);
for (const size of [16, 32, 48, 64]) write(`public/favicon-${size}.png`, sizes[size]);
write("public/apple-touch-icon.png", sizes[180]);
write("public/icon-512.png", sizes[512]);
write("public/favicon.ico", ico([16, 32, 48].map((size) => ({ size, data: sizes[size] }))));

// ---------- mobile app (Capacitor: android/, ios/) ----------
// Launcher icons sit on white, the ground the logo was drawn on: its navy
// book stripes vanish on a dark tile. Splash screens use the Ink theme's
// --bg (index.css), the colour the app opens in, with the emblem as-is --
// the same picture as the app's own boot screen (.boot in index.css), so
// the hand-over from splash to app doesn't flash.
const ICON_BG = "#ffffff";
const SPLASH_BG = "#0b1020";
const rgb = (hex) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));

// A w x h canvas (`bg` colour, or transparent when null) with the emblem
// `mark` px wide in the middle; `round` clips it to a circle (the legacy
// round launcher icon).
function compose(w, h, bg, mark, { round = false } = {}) {
  const px = Buffer.alloc(w * h * 4);
  if (bg) {
    const [r, g, b] = rgb(bg);
    for (let i = 0; i < w * h; i++) px.set([r, g, b, 255], i * 4);
  }
  const em = emblemPixels(matted, mark);
  const left = Math.round((w - mark) / 2), top = Math.round((h - mark) / 2);
  for (let y = 0; y < mark; y++) {
    for (let x = 0; x < mark; x++) {
      const s = (y * mark + x) * 4;
      const sa = em[s + 3] / 255;
      if (!sa) continue;
      const d = ((top + y) * w + left + x) * 4;
      const da = px[d + 3] / 255;
      const oa = sa + da * (1 - sa);
      for (let k = 0; k < 3; k++) px[d + k] = Math.round((em[s + k] * sa + px[d + k] * da * (1 - sa)) / oa);
      px[d + 3] = Math.round(oa * 255);
    }
  }
  if (round) {
    const c = (w - 1) / 2, radius = w / 2;
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const edge = radius - Math.hypot(x - c, y - c); // >= 1 inside, <= 0 outside
        if (edge >= 1) continue;
        const o = (y * w + x) * 4;
        px[o + 3] = Math.round(px[o + 3] * Math.max(0, edge));
      }
    }
  }
  return encodePng({ w, h, px });
}

const RES = "android/app/src/main/res";
const DENSITY = { mdpi: 1, hdpi: 1.5, xhdpi: 2, xxhdpi: 3, xxxhdpi: 4 };
for (const [d, k] of Object.entries(DENSITY)) {
  const legacy = Math.round(48 * k);
  write(`${RES}/mipmap-${d}/ic_launcher.png`, compose(legacy, legacy, ICON_BG, Math.round(legacy * 0.8)));
  write(`${RES}/mipmap-${d}/ic_launcher_round.png`, compose(legacy, legacy, ICON_BG, Math.round(legacy * 0.66), { round: true }));
  // Adaptive icon (Android 8+): a 108dp transparent layer over the white
  // background colour (values/ic_launcher_background.xml). Launchers mask
  // it to their own shape and keep only the middle 66dp circle for sure, so
  // the emblem stays inside it -- its book corners included.
  const adaptive = Math.round(108 * k);
  write(`${RES}/mipmap-${d}/ic_launcher_foreground.png`, compose(adaptive, adaptive, null, Math.round(adaptive * 0.5)));
}
// Pre-Android-12 splash (Android 12+ draws its own from the launcher icon
// on windowSplashScreenBackground, values/styles.xml), at the sizes
// Capacitor's template ships.
const SPLASH = {
  "drawable": [480, 320],
  "drawable-port-mdpi": [320, 480], "drawable-port-hdpi": [480, 800], "drawable-port-xhdpi": [720, 1280],
  "drawable-port-xxhdpi": [960, 1600], "drawable-port-xxxhdpi": [1280, 1920],
  "drawable-land-mdpi": [480, 320], "drawable-land-hdpi": [800, 480], "drawable-land-xhdpi": [1280, 720],
  "drawable-land-xxhdpi": [1600, 960], "drawable-land-xxxhdpi": [1920, 1280],
};
for (const [dir, [w, h]] of Object.entries(SPLASH)) {
  write(`${RES}/${dir}/splash.png`, compose(w, h, SPLASH_BG, Math.round(Math.min(w, h) * 0.36)));
}
// Google Play's 512px store-listing icon (uploaded by hand in Play Console).
write("store-assets/play-icon-512.png", compose(512, 512, ICON_BG, Math.round(512 * 0.8)));

// iOS: one 1024px icon (Xcode derives every size; no transparency allowed)
// and the 2732px splash Capacitor's storyboard scales to fit every device.
const XC = "ios/App/App/Assets.xcassets";
write(`${XC}/AppIcon.appiconset/AppIcon-512@2x.png`, compose(1024, 1024, ICON_BG, Math.round(1024 * 0.8)));
const iosSplash = compose(2732, 2732, SPLASH_BG, Math.round(2732 * 0.22));
for (const name of ["splash-2732x2732.png", "splash-2732x2732-1.png", "splash-2732x2732-2.png"]) {
  write(`${XC}/Splash.imageset/${name}`, iosSplash);
}
