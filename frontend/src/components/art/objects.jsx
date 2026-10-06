import { Backdrop, Bubble, Card, Dossier, Magnifier, Notes, Phone, Room, Star, range } from "./kit.jsx";

// The things learners meet in the world, painted with the same kit as the
// places (art/places.jsx): Chinese Internet pages by kind
// (services/internet_content.py), Detective case types and hand-written case
// files (services/detective.py, seed_content/cases), and the pronunciation
// lessons of Sound World (services/pronunciation.py). Buildings stand
// outside under the sky; objects lie on a desk in the same light.

// ------------------------------------------------------- Chinese Internet

export const NET_ART = {
  news: () => (
    <>
      <Room />
      <g transform="rotate(-5 32 30)">
        <rect className="f-shadow ns" x="11.5" y="12" width="43" height="33" rx="1" />
        <rect className="f-paper" x="10" y="10" width="43" height="33" rx="1" />
        <text className="tx f-ink" x="21.4" y="15.6" fontSize="6.4">晚报</text>
        <path className="ln s-roof" d="M31 13.4h18M31 17h14" style={{ strokeWidth: 1.4 }} />
        <path className="ln" d="M13 21h37" />
        <rect className="f-glass" x="13" y="24" width="17" height="15" />
        <path className="f-blue" d="M14.6 35v-4.4q0-2 2-2h8q3 0 3.6 3.4V35z" />
        <path className="ln s-paper dt" d="M17 31h2.4M21 31h2.4" />
        <path className="ln dt" d="M33 25h16M33 28.4h16M33 31.8h12M33 35.2h16M33 38.6h10" />
      </g>
    </>
  ),

  social: () => (
    <>
      <Room />
      <Phone x={19} y={6} w={24} h={40}>
        <rect className="f-sky ns" x="21" y="9" width="20" height="16" />
        <circle className="f-sun ns" cx="36" cy="13" r="2.2" />
        <path className="f-leaf" d="M21 25l6-8l4 5l3-3l7 6z" />
        <circle className="f-roof ns" cx="24.6" cy="29.6" r="2" />
        <path className="ln dt" d="M28 29h10M28 31.6h7" />
        <path className="ln dt" d="M23 36h16M23 39h12" />
      </Phone>
      <g transform="translate(48 17)">
        <circle className="f-paper" r="6" />
        <path className="f-roof" d="M0 3.4l-3.6-3.6a2.2 2.2 0 0 1 3.6-2.8a2.2 2.2 0 0 1 3.6 2.8z" />
      </g>
    </>
  ),

  comments: () => (
    <>
      <Room />
      <rect className="f-tile-2" x="6" y="11" width="38" height="27" rx="3" />
      <rect className="f-sky" x="8.4" y="13.4" width="33.2" height="22.2" rx="1.2" />
      <ellipse className="f-paper" cx="25" cy="30" rx="10" ry="2.6" />
      <path className="f-wall" d="M17 29.6q2-5 4-1q2-5 4-1q2-5 4-1q2-5 4 0z" />
      <circle className="f-paper" cx="25" cy="21" r="4.6" opacity="0.92" />
      <path className="f-roof ns" d="M23.6 18.8v4.4l3.8-2.2z" />
      <Bubble x={38} y={22} w={20} h={10} flip tone="paper">
        <path className="ln dt" d="M41 26h14M41 28.6h9" />
      </Bubble>
      <Bubble x={36} y={36} w={20} h={8.4} tone="jade">
        <path className="ln s-paper dt" d="M39 40.4h13" />
      </Bubble>
    </>
  ),

  product: () => (
    <>
      <Room />
      <Phone x={19} y={6} w={26} h={40}>
        <rect className="f-room-2 ns" x="21" y="9" width="22" height="18" rx="1" />
        <rect className="f-blue" x="28" y="12.6" width="8" height="13" rx="2.4" />
        <rect className="f-stone" x="28.6" y="10.2" width="6.8" height="3" rx="1" />
        <path className="hl dt" d="M30 15v8" />
        <text className="tx f-roof" x="27" y="31.6" fontSize="4.4">¥59</text>
        <path className="ln dt" d="M23 35.6h18" />
        <rect className="f-gold" x="23" y="38" width="18" height="4.6" rx="2.3" />
        <path className="ln s-wood" d="M28.6 39.4h1l1.2 2.4h3.4l1-1.8" style={{ strokeWidth: 0.9 }} />
      </Phone>
    </>
  ),

  review: () => (
    <>
      <Room />
      {[16, 24, 32, 40, 48].map((x) => <Star key={x} x={x} y={10} r={3.2} />)}
      <path className="ln dt" d="M24 21q-1.6-2 0-4.4M32 21q-1.6-2 0-4.4M40 21q-1.6-2 0-4.4" opacity="0.7" />
      <path className="f-tile-2" d="M10 26h44l-3 12q-1 4-5 4H18q-4 0-5-4z" />
      <path className="f-tile" d="M8 24h48v3H8z" />
      <ellipse className="f-roof" cx="32" cy="27.4" rx="20" ry="3" />
      <g className="dt">
        <circle className="f-gold ns" cx="24" cy="27" r="1.1" />
        <circle className="f-gold ns" cx="38" cy="27.6" r="1" />
        <path className="f-roof-2 ns" d="M28 26.4l3 -0.8l0.6 1.4l-3 0.6z" />
        <circle className="f-leaf ns" cx="33" cy="26.8" r="0.9" />
      </g>
      <path className="ln" d="M6 31h4M54 31h4" style={{ strokeWidth: 2 }} />
    </>
  ),

  notice: () => (
    <>
      <Room />
      <rect className="f-wood" x="8" y="5" width="48" height="39" rx="2" />
      <rect className="f-gold-2" x="11" y="8" width="42" height="33" />
      <g transform="rotate(-3 32 27)">
        <rect className="f-paper" x="17" y="12" width="30" height="31" />
        <text className="tx f-roof" x="32" y="17.4" fontSize="5">通知</text>
        <path className="ln dt" d="M21 22.6h22M21 26h22M21 29.4h15" />
        <path className="f-blue" d="M40 31.4q-3 4 -3 5.6a3 3 0 0 0 6 0q0 -1.6 -3 -5.6z" />
        <path className="ln dt" d="M21 33h10M21 36.4h12" />
      </g>
      <circle className="f-roof" cx="32" cy="12.4" r="1.4" />
      <rect className="f-paper" x="13" y="34" width="8" height="8" transform="rotate(8 17 38)" opacity="0.9" />
      <circle className="f-jade" cx="17" cy="34.6" r="1.1" />
    </>
  ),

  travel: () => (
    <>
      <Backdrop far="hills" ground="grass" />
      <path className="ln s-wood" d="M17 48V34M47 48V34" style={{ strokeWidth: 2.4 }} />
      <rect className="f-wood" x="9" y="10" width="46" height="26" rx="2" />
      <rect className="f-sky-2" x="12" y="13" width="26" height="20" />
      <circle className="f-sun ns" cx="32" cy="17.6" r="2.4" />
      <path className="f-leaf" d="M12 33l8-11l5 6l4-4l9 9z" />
      <path className="f-paper ns" d="M20 22l1.6 2.2l-2.6 0.2z" />
      <path className="ln s-paper" d="M41 17h10M41 21h8M41 25h10" style={{ strokeWidth: 1.2 }} />
      <path className="f-gold" d="M41 28h7v-2l4 3.4l-4 3.4v-2h-7z" />
    </>
  ),

  shopping: () => (
    <>
      <Room />
      <g transform="rotate(-14 30 26)">
        <path className="f-gold" d="M14 14h22l10 12l-10 12H14z" />
        <circle className="f-room" cx="40.6" cy="26" r="2" />
        <text className="tx f-roof-2" x="24.6" y="22.6" fontSize="9">折</text>
        <text className="tx f-roof-2" x="24.6" y="31.6" fontSize="4.4">-50%</text>
      </g>
      <path className="ln" d="M44 21q6-8 12-2" />
      <g transform="rotate(10 46 38)">
        <path className="f-paper" d="M38 32h12l4 5l-4 5H38z" />
        <circle className="f-room" cx="51" cy="37" r="1" />
        <text className="tx f-roof" x="43.6" y="37.2" fontSize="4">¥</text>
      </g>
    </>
  ),

  messages: () => (
    <>
      <Room />
      <Phone x={18} y={5} w={28} h={41}>
        <rect className="f-jade ns" x="20" y="8" width="24" height="5" rx="1" />
        <path className="ln s-paper dt" d="M26 10.5h12" style={{ strokeWidth: 1.1 }} />
        <circle className="f-gold" cx="23" cy="17.6" r="1.9" />
        <rect className="f-room-2" x="26" y="15.6" width="12" height="4.6" rx="1.6" />
        <circle className="f-blue" cx="23" cy="25.4" r="1.9" />
        <rect className="f-room-2" x="26" y="23.4" width="9" height="4.6" rx="1.6" />
        <rect className="f-jade" x="25" y="31" width="13" height="4.6" rx="1.6" />
        <circle className="f-pink" cx="41" cy="33.2" r="1.9" />
        <circle className="f-gold" cx="23" cy="39.6" r="1.9" />
        <rect className="f-room-2" x="26" y="37.6" width="11" height="4.6" rx="1.6" />
      </Phone>
      <circle className="f-roof" cx="46" cy="7" r="3.4" />
      <text className="tx f-paper" x="46" y="7.2" fontSize="4">9</text>
    </>
  ),

  chat: () => (
    <>
      <Room />
      <Bubble x={6} y={9} w={32} h={17} tone="paper">
        <g className="f-tile ns">
          <circle cx="15" cy="17.5" r="1.8" /><circle cx="22" cy="17.5" r="1.8" /><circle cx="29" cy="17.5" r="1.8" />
        </g>
      </Bubble>
      <Bubble x={26} y={26} w={32} h={17} tone="jade" flip>
        <text className="tx f-paper" x="42" y="34.6" fontSize="7">吃饭?</text>
      </Bubble>
    </>
  ),
};

export function netFallback() {
  return (
    <>
      <Room />
      <Phone>
        <rect className="f-sky ns" x="23" y="11" width="18" height="12" />
        <path className="ln dt" d="M25 28h14M25 31.4h10M25 34.8h14M25 38.2h8" />
      </Phone>
    </>
  );
}

// -------------------------------------------------------------- Detective

export const CASE_ART = {
  who_took: () => (
    <>
      <Room />
      <path className="f-wood-2" d="M10 26h34v20H10z" />
      <path className="f-tile-2" d="M12 28h30v8H12z" />
      <path className="f-wood" d="M8 36h38v12H8z" />
      <rect className="f-gold" x="23" y="40.6" width="8" height="2.4" rx="1.2" />
      <path className="f-paper" d="M20 33l-3 -9h20l-3 9z" opacity="0.92" />
      <text className="tx f-roof" x="27" y="27.6" fontSize="6">?</text>
      <Magnifier x={47} y={19} r={7} angle={35} />
    </>
  ),

  where_lost: () => (
    <>
      <Room />
      <g transform="rotate(-6 30 28)">
        <path className="f-paper" d="M8 14l14-3l14 3l14-3v30l-14 3l-14-3l-14 3z" />
        <path className="ln dt" d="M22 11v30M36 14v30" opacity="0.5" />
        <rect className="f-jade ns" x="11" y="18" width="8" height="7" rx="1" opacity="0.7" />
        <rect className="f-water ns" x="38" y="30" width="9" height="6" rx="1" opacity="0.8" />
        <path className="ln s-roof" d="M12 36q8-2 10-8t12-6q6 0 8-4" style={{ strokeDasharray: "1.6 1.6", strokeWidth: 1.2 }} />
        <path className="f-roof" d="M42 18a3.4 3.4 0 1 0 -6.8 0q0 3 3.4 7q3.4 -4 3.4 -7z" />
        <circle className="f-paper ns" cx="38.6" cy="18" r="1.2" />
      </g>
      <Magnifier x={18} y={34} r={6} angle={-35} />
    </>
  ),

  who_lies: () => (
    <>
      <Room />
      <path className="f-paper" d="M14 14q14-6 28 0q2 14 -4 22q-5 6 -10 0q-6 -8 -14 -22z" />
      <path className="f-roof ns" d="M28 11.4q7 -0.6 14 2.6q2 14 -4 22q-5 6 -10 0z" />
      <path className="ln" d="M28 11.4v28.4" opacity="0.6" />
      <path className="f-ink" d="M18 22q4-3 8 0q-4 2 -8 0zM30 22q4-3 8 0q-4 2 -8 0z" />
      <path className="ln" d="M17.6 18.4q4-2.6 8 0M30.4 18.4q4-2.6 8 0" style={{ strokeWidth: 1.4 }} />
      <path className="f-roof-2" d="M24 31q4 2 8 0q-4 4 -8 0z" />
      <Bubble x={42} y={8} w={16} h={13} tone="gold" flip>
        <text className="tx f-roof-2" x="50" y="14.6" fontSize="8">?</text>
      </Bubble>
      <path className="f-shadow ns" d="M16 46q12 -3 24 0z" />
    </>
  ),

  who_late: () => (
    <>
      <Room />
      <path className="ln" d="M22 42l-3 5M42 42l3 5" style={{ strokeWidth: 1.8 }} />
      <circle className="f-gold" cx="21" cy="12" r="4.4" />
      <circle className="f-gold" cx="43" cy="12" r="4.4" />
      <circle className="f-roof" cx="32" cy="28" r="15" />
      <circle className="f-paper" cx="32" cy="28" r="11.6" />
      <g className="f-ink ns dt">
        {range(12).map((i) => {
          const a = (Math.PI / 6) * i;
          return <circle key={i} cx={32 + Math.cos(a) * 9.6} cy={28 + Math.sin(a) * 9.6} r="0.55" />;
        })}
      </g>
      <path className="ln" d="M32 28V20.4M32 28l5.4 3.4" style={{ strokeWidth: 1.6 }} />
      <circle className="f-roof ns" cx="32" cy="28" r="1.2" />
      <path className="ln s-roof dt" d="M10 22q-2 6 0 12M54 22q2 6 0 12M6.4 20q-2.6 8 0 16M57.6 20q2.6 8 0 16" style={{ strokeWidth: 1.1 }} />
    </>
  ),

  who_has: () => (
    <>
      <Room />
      <rect className="f-roof" x="13" y="24" width="30" height="21" rx="1" />
      <rect className="f-roof-2" x="11" y="19" width="34" height="6.4" rx="1" />
      <rect className="f-gold ns" x="25.6" y="19.6" width="4.8" height="25" />
      <path className="ln" d="M25.6 19v26M30.4 19v26" opacity="0.6" />
      <path className="f-gold" d="M28 19q-8-9 -10-3q0 4 10 3zM28 19q8-9 10-3q0 4 -10 3z" />
      <path className="ln" d="M43 30l7 -4" />
      <g transform="rotate(-24 51 25)">
        <path className="f-paper" d="M47 20h10v11H47l-3-5.5z" />
        <circle className="f-room ns" cx="47.6" cy="25.5" r="0.9" />
        <text className="tx f-roof" x="52.2" y="25.8" fontSize="6.6">?</text>
      </g>
    </>
  ),
};

export function caseFallback() {
  return (
    <>
      <Room />
      <Dossier />
      <Magnifier x={30} y={30} r={7} angle={35} />
    </>
  );
}

// A hand-written case file: the dossier with its key evidence clipped on as
// a photograph.
function Evidence({ children }) {
  return (
    <>
      <Room />
      <Dossier />
      <g transform="rotate(-6 29 26)">
        <rect className="f-shadow ns" x="15.5" y="10.5" width="28" height="31" />
        <rect className="f-paper" x="14" y="9" width="28" height="31" />
        <rect className="f-sky-2" x="16.5" y="11.5" width="23" height="21" />
        <g transform="translate(28 22)">{children}</g>
        <path className="ln dt" d="M18 36h12" />
      </g>
      <path className="ln" d="M24 13V6.4a2.2 2.2 0 0 1 4.4 0V15a1.4 1.4 0 0 1 -2.8 0V8" style={{ stroke: "var(--art-stone-2)", strokeWidth: 1.2 }} />
    </>
  );
}

export const FILE_ART = {
  "the-fish-for-dinner": () => (
    <Evidence>
      <ellipse className="f-paper" cx="0" cy="5" rx="10" ry="3" />
      <path className="f-blue" d="M-8 1q5-7 12-1l4-3.6v9.2l-4-3.6q-7 6-12-1z" />
      <circle className="f-paper ns" cx="-4.6" cy="0.2" r="1.1" />
      <circle className="f-ink ns" cx="-4.6" cy="0.2" r="0.5" />
      <path className="ln s-blue dt" d="M-1 -2.4q1.4 2.4 0 5M2 -2q1.2 2 0 4.4" />
    </Evidence>
  ),
  "the-teachers-cup": () => (
    <Evidence>
      <path className="f-paper" d="M-6 -5h11v10a3 3 0 0 1 -3 3h-5a3 3 0 0 1 -3 -3z" />
      <rect className="f-roof ns" x="-5.4" y="-1" width="9.8" height="2.6" />
      <path className="ln" d="M5 -2.6a3 3 0 0 1 0 6" />
      <path className="ln dt" d="M-3 -7.6q-1-1.4 0-2.6M0.4 -7.6q-1-1.4 0-2.6" />
    </Evidence>
  ),
  "the-drawing-in-the-book": () => (
    <Evidence>
      <path className="f-paper" d="M-10 7V-6q5-2 10 0q5-2 10 0V7q-5-2 -10 0q-5-2 -10 0z" />
      <path className="ln" d="M0 -6V7" opacity="0.6" />
      <circle className="ln s-roof" cx="-5" cy="-1" r="2.4" />
      <path className="ln s-roof dt" d="M-5 -5v1M-5 2.4v1M-9 -1h1M-2 -1h1" />
      <path className="f-gold" d="M3 5l7-10l2 1.4l-7 10l-2.6 1z" />
      <path className="f-roof" d="M10 -5l0.8 -1.2l2 1.4l-0.8 1.2z" />
    </Evidence>
  ),
  "the-midnight-music": () => (
    <Evidence>
      <rect className="f-sky ns" x="-11.5" y="-10.5" width="23" height="21" />
      <path className="f-sun" d="M-3 -8a6 6 0 1 0 5 9a5 5 0 1 1 -5 -9z" />
      <Notes x={2} y={-1} s={1.3} tone="gold" />
      <g className="f-star ns"><circle cx="-8" cy="6" r="0.6" /><circle cx="8" cy="-7" r="0.6" /></g>
    </Evidence>
  ),
  "the-broken-flowers": () => (
    <Evidence>
      <path className="f-roof" d="M-9 2l9 -3l3 7l-9 3z" />
      <path className="f-wood-2" d="M3 6l6 2l-11 1z" />
      <path className="ln s-leaf" d="M-2 -1l-3 -7M1 -2l2 -7" style={{ strokeWidth: 1 }} />
      <path className="f-pink" d="M-7 -8a2 2 0 0 1 3 -3l1 1.4l1-1.4a2 2 0 0 1 0 3q-2 2 -5 0z" />
      <path className="f-gold" d="M1 -9a2 2 0 0 1 3 -3l1 1.4l1-1.4a2 2 0 0 1 0 3q-2 2 -5 0z" />
      <path className="ln dt" d="M5 0l2 -1M6 2.6l2.4 0" />
    </Evidence>
  ),
  "the-restaurant-wallet": () => (
    <Evidence>
      <rect className="f-jade" x="-5" y="-6" width="12" height="5" rx="0.6" transform="rotate(-10)" />
      <rect className="f-wood-2" x="-9" y="-3" width="18" height="11" rx="2" />
      <path className="f-wood" d="M-9 -1h18v4H-9z" />
      <circle className="f-gold" cx="5" cy="1" r="1.3" />
    </Evidence>
  ),
  "the-leaked-exam": () => (
    <Evidence>
      <rect className="f-paper" x="-8" y="-9" width="16" height="18" rx="0.6" />
      <text className="tx f-roof" x="0" y="-5.6" fontSize="4">考试</text>
      <path className="ln dt" d="M-5 -1h10M-5 2h10M-5 5h7" />
      <path className="ln s-roof" d="M3 3l2 2l4-6" style={{ strokeWidth: 1.4 }} />
    </Evidence>
  ),
  "the-missing-laptop": () => (
    <Evidence>
      <rect className="f-tile-2" x="-8" y="-8" width="16" height="11" rx="1" />
      <rect className="f-glass ns" x="-6.6" y="-6.6" width="13.2" height="8.2" />
      <path className="f-stone" d="M-10.4 3h20.8l1.6 3h-24z" />
      <path className="hl dt" d="M-5 0l4-5" />
    </Evidence>
  ),
  "the-teahouse-recipe": () => (
    <Evidence>
      <path className="f-paper" d="M-10 -8h9v14h-9z" transform="rotate(-8)" />
      <path className="ln dt" d="M-8.6 -4.4h5.6M-8.6 -1.6h5.6M-8.6 1.2h4" transform="rotate(-8)" />
      <path className="f-jade" d="M-1 0h11a5.5 5.5 0 0 1 -11 0z" />
      <ellipse className="f-jade-2" cx="4.5" cy="0" rx="5.5" ry="1.2" />
      <path className="ln dt" d="M3 -2.4q-1-1.6 0-3M6 -2.4q-1-1.6 0-3" />
    </Evidence>
  ),
  "the-forged-letter": () => (
    <Evidence>
      <rect className="f-paper" x="-9" y="-8" width="18" height="15" rx="0.6" />
      <path className="ln dt" d="M-6.6 -4.6h10M-6.6 -1.6h13M-6.6 1.4h9" />
      <rect className="f-roof" x="2.4" y="1.8" width="5" height="5" rx="0.6" />
      <text className="tx f-paper" x="4.9" y="4.4" fontSize="3.4">印</text>
    </Evidence>
  ),
};

export function fileFallback() {
  return (
    <Evidence>
      <text className="tx f-roof" x="0" y="0.4" fontSize="13">?</text>
    </Evidence>
  );
}

// --------------------------------------------- Sound World pronunciation

// A contour of a Mandarin tone drawn in a box (x, y, w, h): 1 high level,
// 2 rising, 3 dipping, 4 falling.
function contour(tone, x, y, w, h) {
  const top = y;
  const bot = y + h;
  return {
    1: `M${x} ${top + h * 0.15}H${x + w}`,
    2: `M${x} ${top + h * 0.6}L${x + w} ${top + h * 0.1}`,
    3: `M${x} ${top + h * 0.45}Q${x + w * 0.4} ${bot + h * 0.2} ${x + w} ${top + h * 0.15}`,
    4: `M${x} ${top + h * 0.1}L${x + w} ${bot - h * 0.05}`,
  }[tone];
}

const TONE_TONE = { 1: "roof", 2: "gold", 3: "jade", 4: "blue" };

function Tile({ x, y, w = 14, h = 14, tone = "jade", text, color = "f-paper", size = 8 }) {
  return (
    <g>
      <rect className={`f-${tone}`} x={x} y={y} width={w} height={h} rx="2.4" />
      {text && <text className={`tx ${color}`} x={x + w / 2} y={y + h / 2 + 0.3} fontSize={size}>{text}</text>}
    </g>
  );
}

function Ear({ x = 32, y = 28 }) {
  return (
    <g transform={`translate(${x} ${y})`}>
      <path className="f-wall-2" d="M-6 -6a10 10 0 0 1 18 2q0 6 -5 9q-3 2 -3 6a4 4 0 0 1 -8 0" />
      <path className="ln" d="M-1 -4a5 5 0 0 1 8 2q0 3 -3 5" />
    </g>
  );
}

export const PRON_ART = {
  tones: () => (
    <>
      <Room />
      <Card />
      {[1, 2, 3, 4].map((tone, i) => {
        const x = 13 + (i % 2) * 20;
        const y = 13 + Math.floor(i / 2) * 15;
        return (
          <g key={tone}>
            <rect className="f-room ns" x={x} y={y} width="18" height="13" rx="2" />
            <path className={`ln s-${TONE_TONE[tone]}`}
                  d={contour(tone, x + 3, y + 2.6, 12, 7.6)} style={{ strokeWidth: 2.4 }} />
            <text className="tx f-ink dt" x={x + 15} y={y + 10.6} fontSize="3">{tone}</text>
          </g>
        );
      })}
    </>
  ),

  neutral: () => (
    <>
      <Room />
      <Card />
      <text className="tx f-ink" x="32" y="23" fontSize="13">妈妈</text>
      <text className="tx f-roof" x="23" y="36" fontSize="6.4">mā</text>
      <text className="tx f-ink" x="39" y="36.6" fontSize="4.6" opacity="0.5">ma</text>
      <circle className="ln s-gold dt" cx="39" cy="36.6" r="5" style={{ strokeDasharray: "1 1.4" }} />
    </>
  ),

  initials: () => (
    <>
      <Room />
      <Tile x={14} y={8} text="b" />
      <Tile x={35} y={8} text="p" tone="jade-2" />
      <Tile x={14} y={27} text="m" tone="jade-2" />
      <Tile x={35} y={27} text="f" />
    </>
  ),

  finals: () => (
    <>
      <Room />
      <Tile x={14} y={8} text="a" tone="gold" color="f-roof-2" />
      <Tile x={35} y={8} text="o" tone="gold-2" color="f-paper" />
      <Tile x={14} y={27} text="e" tone="gold-2" color="f-paper" />
      <Tile x={35} y={27} text="ü" tone="gold" color="f-roof-2" />
    </>
  ),

  tone_pairs: () => (
    <>
      <Room />
      <Card y={7} h={38} />
      {/* 中国 zhōng guó: a first tone then a second (a pair without sandhi). */}
      <path className="ln s-roof" d={contour(1, 14, 12, 14, 8)} style={{ strokeWidth: 2.4 }} />
      <path className="ln s-gold" d={contour(2, 36, 12, 14, 8)} style={{ strokeWidth: 2.4 }} />
      <text className="tx f-ink" x="21" y="31" fontSize="10">中</text>
      <text className="tx f-ink" x="43" y="31" fontSize="10">国</text>
      <text className="tx f-roof dt" x="21" y="40" fontSize="4">zhōng</text>
      <text className="tx f-roof dt" x="43" y="40" fontSize="4">guó</text>
    </>
  ),

  sandhi: () => (
    <>
      <Room />
      <Card y={10} h={30} />
      <rect className="f-room ns" x="12" y="15" width="16" height="12" rx="2" />
      <path className="ln s-jade" d={contour(3, 14.5, 17, 11, 7)} style={{ strokeWidth: 2.4 }} />
      <rect className="f-room ns" x="36" y="15" width="16" height="12" rx="2" />
      <path className="ln s-gold" d={contour(2, 38.5, 17, 11, 7)} style={{ strokeWidth: 2.4 }} />
      <path className="f-roof" d="M29 20h3v-2.4l3.6 3.4l-3.6 3.4V22h-3z" />
      <text className="tx f-ink" x="20" y="33.6" fontSize="5">3 + 3</text>
      <text className="tx f-ink" x="44" y="33.6" fontSize="5">2 + 3</text>
    </>
  ),

  pairs: () => (
    <>
      <Room />
      <Ear x={38} y={24} />
      <path className="ln s-roof" d="M6 18q3-3 6 0t6 0t6 0" style={{ strokeWidth: 1.8 }} />
      <path className="ln s-blue" d="M6 30l3 -4l3 4l3 -4l3 4l3 -4" style={{ strokeWidth: 1.8 }} />
      <Tile x={6} y={36} w={9} h={9} text="b" size={5.6} />
      <Tile x={17} y={36} w={9} h={9} text="p" tone="blue" size={5.6} />
    </>
  ),

  dialogues: () => (
    <>
      <Room />
      <Bubble x={5} y={8} w={30} h={15} tone="paper">
        <text className="tx f-ink" x="20" y="15.8" fontSize="7">你好!</text>
      </Bubble>
      <Bubble x={27} y={27} w={32} h={15} tone="jade" flip>
        <text className="tx f-paper" x="43" y="34.8" fontSize="7">早上好</text>
      </Bubble>
    </>
  ),
};

export function pronFallback() {
  return (
    <>
      <Room />
      <Ear x={36} y={24} />
      <path className="ln s-gold" d="M10 20q4 4 0 8M15 17q6 7 0 14" style={{ strokeWidth: 1.8 }} />
    </>
  );
}
