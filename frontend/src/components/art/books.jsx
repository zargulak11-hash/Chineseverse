import {
  Backdrop, Bubble, Door, Flag, Lantern, Magnifier, Notes, Person, Room, Shadow, Star, Tree, WallWindow, range,
} from "./kit.jsx";

// The covers of the Chinese Stories library (seed_content/books): one
// painting per story motif, in the same kit and palette as the places
// (art/places.jsx). Stories set in a place we already paint use that place
// (components/Art.jsx BOOK_ART_FOR); these are the rest -- food, weather,
// animals, letters, sport, family objects, people. Outdoors under the sky,
// indoors on the desk in the same light.

const Snow = () => (
  <g className="ns">
    <rect className="f-paper" y="46" width="64" height="18" />
    <rect className="f-sky-2" y="46" width="64" height="1.4" />
  </g>
);

const Sand = () => (
  <g className="ns">
    <rect className="f-wall-2" y="44" width="64" height="20" />
    <path className="f-gold dt" d="M0 52q16-6 34 0t30 -2V64H0z" opacity="0.55" />
  </g>
);

const Steam = ({ x, y }) => <path className="ln dt" d={`M${x} ${y}q-1.4-2 0-4M${x + 3} ${y}q-1.4-2 0-4M${x + 6} ${y}q-1.4-2 0-4`} opacity="0.7" />;

function Wheel({ x, y, r = 3.4 }) {
  return (
    <g>
      <circle className="f-tile-2" cx={x} cy={y} r={r} />
      <circle className="f-stone ns" cx={x} cy={y} r={r * 0.38} />
    </g>
  );
}

export const BOOK_ART = {
  // -------------------------------------------------------- daily life
  sick_day: () => (
    <>
      <Room desk={false} />
      <rect className="f-wood-2" y="50" width="64" height="14" />
      <WallWindow x={40} y={8} w={16} h={14} />
      <rect className="f-wood" x="6" y="24" width="6" height="26" rx="1" />
      <rect className="f-paper" x="8" y="38" width="50" height="8" rx="1.4" />
      <path className="f-blue" d="M22 35q18 -4 36 1v10H22z" />
      <path className="ln s-blue dt" d="M30 36v10M42 35.4v10.6" opacity="0.7" />
      <ellipse className="f-paper" cx="17" cy="36.6" rx="6" ry="3" />
      <circle className="f-skin" cx="17" cy="32" r="4.4" />
      <path className="f-tile-2" d="M12.6 32a4.4 4.4 0 0 1 8.8 0q-4.4 -2.4 -8.8 0z" />
      <rect className="f-paper" x="13.6" y="27.4" width="6.8" height="2.4" rx="0.8" />
      <circle className="f-roof ns" cx="15" cy="33.4" r="0.9" opacity="0.6" />
      <circle className="f-roof ns" cx="19" cy="33.4" r="0.9" opacity="0.6" />
      <path className="ln" d="M15.6 31.4h0.4M18 31.4h0.4" />
      <path className="ln s-roof" d="M19.4 34.6l5 1.6" style={{ strokeWidth: 1.1 }} />
      <rect className="f-wood" x="6" y="46" width="52" height="4" />
      <path className="ln" d="M10 50v4M54 50v4" style={{ strokeWidth: 1.6 }} />
    </>
  ),

  morning: () => (
    <>
      <Room />
      <WallWindow x={9} y={7} w={28} h={25} />
      <path className="f-far ns" d="M9 32v-6h4v-3h5v4h4v-5h5v6h4v-3h6v7z" />
      <g transform="translate(46 37)">
        <path className="ln" d="M-4 7l-2 2.4M4 7l2 2.4" style={{ strokeWidth: 1.4 }} />
        <circle className="f-gold" cx="-4" cy="-5" r="2.2" />
        <circle className="f-gold" cx="4" cy="-5" r="2.2" />
        <circle className="f-roof" r="6.6" />
        <circle className="f-paper" r="4.8" />
        <path className="ln" d="M0 0v-3.2M0 0h2.4" style={{ strokeWidth: 1.1 }} />
      </g>
      <path className="f-paper" d="M18 38h8l-0.8 8h-6.4z" />
      <rect className="f-wall-2 ns" x="18.6" y="39.4" width="6.8" height="2" />
      <Steam x={19} y={36.4} />
    </>
  ),

  bedroom: () => (
    <>
      <Room desk={false} />
      <rect className="f-wood-2" y="48" width="64" height="16" />
      <rect className="f-paper" x="17" y="9" width="16" height="12" rx="1" />
      <path className="f-leaf ns" d="M18.4 20l4.6-6l3.4 4l2.4-2.4l3.4 4.4z" />
      <circle className="f-sun ns" cx="29" cy="12.6" r="1.6" />
      <rect className="f-wood" x="6" y="26" width="5" height="22" rx="1" />
      <rect className="f-wood" x="8" y="38" width="38" height="10" rx="1" />
      <rect className="f-paper" x="9" y="34" width="36" height="5" rx="2" />
      <path className="f-jade" d="M20 33.4h25.6v6H20z" />
      <path className="ln s-jade dt" d="M26 33.4v6M33 33.4v6M40 33.4v6" opacity="0.6" />
      <ellipse className="f-paper" cx="14.6" cy="33.4" rx="4.6" ry="2.6" />
      <rect className="f-wood" x="49" y="38" width="10" height="10" rx="1" />
      <path className="ln" d="M54 38v-6" />
      <path className="f-gold" d="M50.6 32l1.6-6h3.6l1.6 6z" />
      <circle className="f-sun ns dt" cx="54" cy="30" r="5" opacity="0.25" />
    </>
  ),

  rain: () => (
    <>
      <Backdrop far="city" sun={false} clouds={false} />
      <g className="f-stone">
        <path d="M2 14a5 5 0 0 1 8 -4a6 6 0 0 1 11 2a4 4 0 0 1 0 7H4a3 3 0 0 1 -2 -5z" />
        <path d="M38 10a5 5 0 0 1 8 -4a6 6 0 0 1 11 2a4 4 0 0 1 0 7H40a3 3 0 0 1 -2 -5z" />
      </g>
      <path className="ln s-water" d={range(9).map((i) => `M${4 + i * 7} ${20 + (i % 3) * 4}l-2 4`).join("")} style={{ strokeWidth: 1.2 }} />
      <ellipse className="f-water" cx="14" cy="54" rx="8" ry="2" />
      <ellipse className="f-water" cx="50" cy="57" rx="7" ry="1.8" />
      <Shadow rx={10} />
      <Person x={32} s={0.95} shirt="jade" />
      <path className="ln" d="M37 30v12" style={{ strokeWidth: 1.2 }} />
      <path className="f-roof" d="M15 30a17 13 0 0 1 34 0q-4.25 -2.6 -8.5 0q-4.25 -2.6 -8.5 0q-4.25 -2.6 -8.5 0q-4.25 -2.6 -8.5 0z" />
      <path className="ln s-roof-2 dt" d="M23.5 30q2-9 8.5-13M40.5 30q-2-9 -8.5-13" />
      <circle className="f-gold" cx="32" cy="16.4" r="1" />
    </>
  ),

  snow: () => (
    <>
      <Backdrop far="hills" clouds={false} />
      <Snow />
      <rect className="f-wall" x="6" y="32" width="18" height="15" />
      <path className="f-tile" d="M3 33l11-9l11 9z" />
      <path className="f-paper" d="M4.6 31.6l9.4-7.6l9.4 7.6q-3 -1.4 -4.4 0.4q-2 -1.6 -3.6 0q-1.6 -1.6 -3 0q-2 -1.6 -3.4 0q-2 -1.6 -4.4 -0.4z" />
      <rect className="f-glass" x="9" y="36" width="5" height="5" />
      <rect className="f-wood" x="16.6" y="38" width="5" height="9" />
      <g>
        <path className="f-leaf-2" d="M53 46l-6 0l6-16l6 16z" />
        <path className="f-paper ns" d="M53 30l2.4 6.4q-2.4 -1 -4.8 0z" />
      </g>
      <circle className="f-paper" cx="35" cy="42" r="6.6" />
      <circle className="f-paper" cx="35" cy="31.6" r="4.6" />
      <rect className="f-tile-2" x="31.4" y="23.4" width="7.2" height="4.4" rx="0.6" />
      <rect className="f-tile-2" x="29.6" y="27" width="10.8" height="1.4" rx="0.6" />
      <path className="f-roof" d="M30.4 35.4h9.2v2.4h-9.2zM37 37.6h2.6v4.6H37z" />
      <path className="f-gold" d="M35 31.8l4 0.8l-4 0.8z" />
      <g className="f-ink ns">
        <circle cx="33.6" cy="30.6" r="0.6" /><circle cx="36.4" cy="30.6" r="0.6" />
        <circle cx="35" cy="41" r="0.6" /><circle cx="35" cy="44" r="0.6" />
      </g>
      <g className="f-paper ns">
        {[[8, 10], [20, 6], [28, 16], [46, 9], [58, 18], [42, 22], [14, 20], [52, 28]].map(([x, y]) => <circle key={`${x}${y}`} cx={x} cy={y} r="0.9" />)}
      </g>
    </>
  ),

  fog: () => (
    <>
      <Backdrop far="none" ground="grass" />
      <path className="f-jade-2" d="M-4 46L18 14L40 46z" />
      <path className="f-jade" d="M24 46L44 20L68 46z" />
      <path className="f-paper ns" d="M18 14l4.4 6.4q-2 -1 -4.4 1q-2 -2 -4.4 -1z" />
      <path className="ln" d="M30 64q4-10 -2-14t2-10" style={{ strokeDasharray: "1.6 1.6", stroke: "var(--art-wall-2)", strokeWidth: 1.4 }} />
      <g className="f-cloud ns" opacity="0.92">
        <rect x="-4" y="27" width="48" height="5" rx="2.5" />
        <rect x="18" y="35" width="52" height="5.4" rx="2.7" />
        <rect x="-6" y="42" width="40" height="4.6" rx="2.3" />
      </g>
      <Person x={42} y={56} s={0.55} shirt="roof" />
    </>
  ),

  mountain: () => (
    <>
      <Backdrop far="hills" ground="grass" />
      <path className="f-jade" d="M4 46L30 10L56 46z" />
      <path className="f-jade-2 ns" d="M30 10L56 46H36z" opacity="0.6" />
      <path className="f-paper" d="M30 10l5.4 7.4q-2.6 -1.2 -5.4 1q-2.8 -2.2 -5.4 -1z" />
      <path className="ln" d="M22 46q8-6 2-12t6-12" style={{ strokeDasharray: "1.6 1.6", stroke: "var(--art-wall)", strokeWidth: 1.6 }} />
      <Flag x={30} y={10} h={7} />
      <Tree x={8} r={3.4} tone="leaf" />
      <Tree x={58} r={3.8} tone="leaf" />
    </>
  ),

  sea: () => (
    <>
      <Backdrop far="none" ground="water" />
      <path className="f-wall-2" d="M0 52q18-6 34 2t30 10H0z" />
      <path className="ln s-paper" d="M4 49q4 -2 8 0t8 0M38 50q4 -2 8 0t8 0" style={{ strokeWidth: 1.1 }} />
      <g transform="translate(40 40)">
        <path className="f-wood-2" d="M-6 0h12l-2 3h-8z" />
        <path className="ln" d="M0 0v-12" style={{ strokeWidth: 0.9 }} />
        <path className="f-paper" d="M0.6 -11.4l6 10.4h-6z" />
        <path className="f-roof" d="M-0.6 -9.6l-4.4 8.6h4.4z" />
      </g>
      <Star x={12} y={57} r={2.6} />
      <path className="f-pink" d="M24 59a3 3 0 0 1 6 0z" />
      <path className="ln s-pink dt" d="M25 59l2-2.6M27 59v-3M29 59l-2-2.6" />
    </>
  ),

  voyage: () => (
    <>
      <Backdrop far="none" ground="water" clouds={false} />
      <path className="f-wood-2" d="M6 38H58L52 49H14L6 38zM6 38l-2 -5h8l2 5z" />
      <path className="ln s-gold" d="M10 42h44" />
      {[[18, 12, 9], [32, 6, 11], [46, 13, 8]].map(([x, top, hw]) => (
        <g key={x}>
          <path className="ln" d={`M${x} 38V${top}`} style={{ strokeWidth: 1.1 }} />
          <path className="f-roof" d={`M${x - hw} ${top + 2}h${hw * 2}l-1 ${30 - top - 4}h${-hw * 2 + 2}z`} />
          <path className="ln s-roof-2" d={range(4).map((i) => `M${x - hw + 0.4} ${top + 7 + i * 6}h${hw * 2 - 1}`).join("")} />
          <path className="f-gold" d={`M${x} ${top}l4 1.4l-4 1.4z`} />
        </g>
      ))}
      <path className="ln s-paper dt" d="M4 54q4-2 8 0t8 0M40 57q4-2 8 0t8 0" />
    </>
  ),

  // ---------------------------------------------------------------- food
  cooking: () => (
    <>
      <Room />
      <rect className="f-tile-2" x="8" y="40" width="48" height="6" rx="1" />
      <path className="f-gold ns" d="M24 40q2-5 4-2q2-6 4 0q2-5 4 0q2-4 4 2z" />
      <path className="f-roof ns" d="M27 40q1-3 2.4-1.4q1-3.6 2.6 0q1.2-3 2.6 1.4z" />
      <path className="f-tile-2" d="M14 28h32a16 10 0 0 1 -32 0z" />
      <path className="ln s-wood" d="M46 30l12-4" style={{ strokeWidth: 2.6 }} />
      <ellipse className="f-tile" cx="30" cy="28" rx="16" ry="2.4" />
      <path className="f-gold" d="M20 28q3-4 6-1q3-3 5 1z" />
      <path className="f-roof" d="M30 27.6q2-3.4 5-1.4q2-1 3 1.8z" />
      <circle className="f-roof" cx="24.6" cy="27" r="1.6" />
      <Steam x={24} y={22} />
      <path className="f-stone" d="M38 18l6-8l1.6 1.2l-5.6 8z" />
      <rect className="f-stone" x="36.4" y="18" width="5" height="3.4" rx="0.6" transform="rotate(-50 39 19.7)" />
    </>
  ),

  dumplings: () => (
    <>
      <Room />
      <g transform="translate(46 15) rotate(45)">
        <rect className="f-roof" x="-6.6" y="-6.6" width="13.2" height="13.2" rx="1" />
      </g>
      <text className="tx f-gold" x="46" y="15.4" fontSize="8">福</text>
      <ellipse className="f-gold-2" cx="26" cy="42" rx="18" ry="5" />
      <path className="f-gold-2" d="M8 34v8a18 5 0 0 0 36 0v-8z" />
      <ellipse className="f-wood" cx="26" cy="34" rx="18" ry="5" />
      <ellipse className="f-wall-2 ns" cx="26" cy="34" rx="15.6" ry="3.8" />
      <path className="ln s-wood dt" d="M8 38a18 5 0 0 0 36 0" />
      {[[18, 33], [26, 31.6], [34, 33], [22, 35.6], [30, 35.6]].map(([x, y]) => (
        <g key={`${x}${y}`}>
          <path className="f-paper" d={`M${x - 4} ${y + 1}q4 -6 8 0z`} />
          <path className="ln dt" d={`M${x - 1.6} ${y - 1.8}l0.6 1.4M${x} ${y - 2.4}v1.6M${x + 1.6} ${y - 1.8}l-0.6 1.4`} style={{ strokeWidth: 0.6 }} />
        </g>
      ))}
      <Steam x={22} y={26} />
      <path className="ln s-wood" d="M44 44l14-12M47 45l13-11" style={{ strokeWidth: 1.4 }} />
    </>
  ),

  red_envelope: () => (
    <>
      <Room />
      <g transform="rotate(-10 38 26)">
        <rect className="f-roof-2" x="30" y="8" width="20" height="30" rx="1.6" />
      </g>
      <rect className="f-roof" x="16" y="9" width="22" height="33" rx="1.6" />
      <path className="f-roof-2" d="M16 10.6q11 9 22 0V9H16z" />
      <circle className="f-gold" cx="27" cy="24" r="5.4" />
      <text className="tx f-roof-2" x="27" y="24.3" fontSize="6.6">福</text>
      <path className="ln s-gold dt" d="M19.4 37h15.2" />
      {[[48, 43], [53, 41.6], [44, 41.4]].map(([x, y]) => (
        <g key={x}>
          <ellipse className="f-gold" cx={x} cy={y} rx="3.6" ry="1.6" />
          <rect className="f-gold-2 ns" x={x - 0.8} y={y - 0.6} width="1.6" height="1.2" />
        </g>
      ))}
    </>
  ),

  watermelon: () => (
    <>
      <Backdrop far="hills" ground="grass" />
      <Shadow cx={28} rx={20} />
      <circle className="f-jade" cx="27" cy="31" r="16" />
      <path className="ln s-leaf" d="M15 22q4 10 0 20M22 16q4 15 0 30M30 15q4 16 0 32M38 19q3 12 0 24" style={{ strokeWidth: 1.6 }} />
      <path className="hl dt" d="M16 26a12 12 0 0 1 8 -8" />
      <g transform="translate(48 42) rotate(-8)">
        <path className="f-jade" d="M-11 0a11 11 0 0 0 22 0z" />
        <path className="f-paper ns" d="M-9.6 0a9.6 9.6 0 0 0 19.2 0z" />
        <path className="f-roof" d="M-8.6 0a8.6 8.6 0 0 0 17.2 0z" />
        <g className="f-ink ns">
          <ellipse cx="-4" cy="2.4" rx="0.5" ry="0.8" /><ellipse cx="0" cy="4.6" rx="0.5" ry="0.8" />
          <ellipse cx="4" cy="2.4" rx="0.5" ry="0.8" /><ellipse cx="-1.6" cy="1.4" rx="0.5" ry="0.8" />
        </g>
        <path className="ln" d="M-11 0h22" />
      </g>
    </>
  ),

  bread: () => (
    <>
      <Room />
      <ellipse className="f-paper" cx="28" cy="43" rx="20" ry="4" />
      <path className="f-gold-2" d="M12 40q-2-14 16-15q18 1 16 15z" />
      {/* The bite: two round notches out of the loaf's shoulder. */}
      <g className="f-room-2 ns">
        <circle cx="41.6" cy="28.4" r="3.2" />
        <circle cx="44" cy="33.2" r="2.8" />
      </g>
      <path className="ln" d="M38.6 27.4a3.2 3.2 0 0 0 4.6 3.6a2.8 2.8 0 0 0 2 4.6" />
      <path className="ln s-wood" d="M20 30q2-3 4 0M27 28q2-3 4 0M34 30q2-3 4 0" />
      <g className="f-gold-2 ns dt"><circle cx="48" cy="43" r="0.8" /><circle cx="51" cy="44.4" r="0.6" /></g>
      <Bubble x={44} y={8} w={14} h={12} tone="gold" flip>
        <text className="tx f-roof-2" x="51" y="14" fontSize="8">?</text>
      </Bubble>
    </>
  ),

  cake: () => (
    <>
      <Room />
      <ellipse className="f-paper" cx="32" cy="45" rx="22" ry="3.6" />
      <rect className="f-pink" x="13" y="31" width="38" height="13" rx="2" />
      <path className="f-paper" d="M13 33q0-2 2-2h34q2 0 2 2v1q-3 3 -5 0q-3 3 -6 0q-3 3 -6 0q-3 3 -6 0q-3 3 -6 0q-3 3 -6 0z" />
      <rect className="f-paper" x="19" y="22" width="26" height="9" rx="2" />
      <path className="f-pink-2 ns" d="M19 24h26v1.6H19z" />
      <text className="tx f-roof" x="32" y="38.6" fontSize="6.2">寿</text>
      {[25, 32, 39].map((x) => (
        <g key={x}>
          <rect className="f-blue" x={x - 0.9} y="15" width="1.8" height="7" />
          <path className="f-gold" d={`M${x} 10.4q2 2.6 0 4.4q-2 -1.8 0 -4.4z`} />
        </g>
      ))}
    </>
  ),

  mooncake: () => (
    <>
      <Backdrop far="hills" sun={false} clouds={false} />
      <circle className="f-sun" cx="32" cy="17" r="11" />
      <g className="f-stone ns dt" opacity="0.35">
        <circle cx="28" cy="14" r="2.2" /><circle cx="35" cy="20" r="3" /><circle cx="29" cy="22" r="1.4" />
      </g>
      <rect className="f-wood" x="6" y="40" width="52" height="4" />
      <path className="ln" d="M10 44v6M54 44v6" style={{ strokeWidth: 1.6 }} />
      <ellipse className="f-paper" cx="22" cy="39.4" rx="12" ry="2.4" />
      {[[17, 35], [27, 35]].map(([x, y]) => (
        <g key={x}>
          <ellipse className="f-gold-2" cx={x} cy={y + 2} rx="5" ry="2" />
          <rect className="f-gold-2 ns" x={x - 5} y={y - 1} width="10" height="3" />
          <ellipse className="f-gold" cx={x} cy={y - 1} rx="5" ry="2" />
          <text className="tx f-wood-2 dt" x={x} y={y - 0.8} fontSize="2.6">月</text>
        </g>
      ))}
      <g transform="translate(46 30) rotate(-6)">
        <rect className="f-tile-2" x="-5.4" y="-1" width="10.8" height="13" rx="1.6" />
        <rect className="f-sky-2" x="-4.2" y="0.4" width="8.4" height="10" rx="0.6" />
        <circle className="f-skin" cx="0" cy="4.4" r="2" />
        <path className="f-blue ns" d="M-3 10.4q0-3 3-3t3 3z" />
      </g>
    </>
  ),

  rice_field: () => (
    <>
      <Backdrop far="hills" ground="grass" />
      <path className="f-jade" d="M0 34q32-8 64 0v6q-32-8 -64 0z" />
      <path className="f-leaf" d="M0 40q32-8 64 0v6H0z" />
      <path className="ln s-leaf dt" d="M0 37q32-8 64 0M0 43q32-8 64 0" opacity="0.7" />
      <path className="f-water ns" d="M0 46h64v4q-32 -4 -64 0z" opacity="0.6" />
      {[16, 32, 48].map((x, i) => (
        <g key={x}>
          <path className="f-gold" d={`M${x - 5} ${54 - i % 2}l2 -12q3 -3 6 0l2 12z`} />
          <path className="ln s-wood" d={`M${x - 3.6} ${46 - i % 2}h7.2`} />
          <path className="ln s-wood dt" d={`M${x - 2} ${41 - i % 2}l-2 -5M${x} ${41 - i % 2}v-6M${x + 2} ${41 - i % 2}l2 -5`} />
        </g>
      ))}
      <ellipse className="f-gold" cx="32" cy="30" rx="8" ry="2" />
      <path className="f-gold" d="M28 30q4 -6 8 0z" />
    </>
  ),

  tea_hills: () => (
    <>
      <Backdrop far="hills" ground="grass" />
      {[[22, 30], [30, 38], [38, 46]].map(([y, w], i) => (
        // Each row of round tea bushes runs down to the bottom, so the next
        // row covers it and no ground shows between the rows.
        <path key={y} className={`f-${i % 2 ? "leaf" : "jade"}`}
              d={`M-2 ${y + 6}${"a4 4.6 0 0 1 8 0".repeat(9)}V64H-2z`} />
      ))}
      <g className="f-cloud ns dt" opacity="0.85">
        <rect x="-4" y="22" width="30" height="3" rx="1.5" />
        <rect x="36" y="26" width="32" height="3" rx="1.5" />
      </g>
      <g>
        <path className="f-gold-2" d="M40 50h16l-2 10H42z" />
        <path className="ln s-wood dt" d="M41 54h14M41.6 57h13" />
        <path className="f-leaf" d="M42 50q3-5 6-1q3-4 6 1z" />
      </g>
    </>
  ),

  tea_cup: () => (
    <>
      <Room />
      <path className="f-jade" d="M14 26h20q4 0 4 6v6q0 6 -8 6h-12q-8 0 -8 -6v-6q0 -6 4 -6z" />
      <path className="ln" d="M38 30q6 0 6 6" />
      <path className="f-jade" d="M11 31q-6 -1 -8 -7l2.4 -1q2 4 6 4.4z" />
      <rect className="f-jade-2" x="20" y="22.6" width="8" height="3.4" rx="1.2" />
      <circle className="f-gold" cx="24" cy="21.6" r="1.2" />
      <path className="ln s-paper dt" d="M12 34q12 4 24 0" />
      <path className="f-paper" d="M44 38h10a5 5 0 0 1 -10 0z" />
      <ellipse className="f-gold-2" cx="49" cy="38" rx="5" ry="1" />
      <Steam x={46} y={35} />
    </>
  ),

  // ------------------------------------------------ friends and family
  friends: () => (
    <>
      <Backdrop far="hills" ground="grass" />
      <Tree x={56} r={5} />
      <Shadow cx={30} rx={16} />
      <Person x={21} shirt="roof" arm="up" />
      <Person x={38} shirt="blue" hair="wood-2" />
      <Bubble x={36} y={8} w={18} h={9} tone="paper" flip>
        <text className="tx f-ink" x="45" y="12.6" fontSize="4.6">你好!</text>
      </Bubble>
    </>
  ),

  wedding: () => (
    <>
      <Room />
      <Lantern x={10} y={0} s={1.3} />
      <Lantern x={54} y={0} s={1.3} />
      <circle className="f-roof" cx="32" cy="22" r="13" />
      <text className="tx f-gold" x="32" y="22.4" fontSize="15">囍</text>
      <circle className="ln s-gold" cx="27.6" cy="41" r="3.6" style={{ strokeWidth: 1.6 }} />
      <circle className="ln s-gold" cx="35" cy="41" r="3.6" style={{ strokeWidth: 1.6 }} />
      <path className="f-paper ns" d="M35 36.4l1.2 -1.4h-2.4z" />
    </>
  ),

  graduation: () => (
    <>
      <Room />
      <rect className="f-wood" x="8" y="8" width="34" height="26" rx="1" />
      <rect className="f-sky-2" x="11" y="11" width="28" height="20" />
      {[[16, "roof"], [22, "blue"], [28, "jade"], [34, "gold"]].map(([x, tone]) => (
        <g key={x}>
          <path className={`f-${tone}`} d={`M${x - 2.6} 31v-3a2.6 2.6 0 0 1 5.2 0v3z`} />
          <circle className="f-skin" cx={x} cy="22.6" r="2" />
          <rect className="f-tile-2 ns" x={x - 2.4} y="19.2" width="4.8" height="1.4" />
        </g>
      ))}
      <g transform="translate(48 38)">
        <path className="f-tile-2" d="M-10 0l10 -4l10 4l-10 4z" />
        <path className="f-tile-2" d="M-5 2v4q5 3 10 0v-4l-5 2z" />
        <path className="ln s-gold" d="M7 1v6" style={{ strokeWidth: 1 }} />
        <circle className="f-gold" cx="7" cy="7.6" r="1" />
      </g>
    </>
  ),

  neighbour: () => (
    <>
      <Room desk={false} />
      <rect className="f-wood-2" y="50" width="64" height="14" />
      <rect className="f-wood-2" x="18" y="8" width="26" height="42" />
      <Door x={21} y={11} w={20} h={39} tone="roof" />
      <g transform="translate(31 22) rotate(45)">
        <rect className="f-gold" x="-4.4" y="-4.4" width="8.8" height="8.8" rx="0.6" />
      </g>
      <text className="tx f-roof-2" x="31" y="22.4" fontSize="5.4">福</text>
      <rect className="f-paper" x="27" y="4" width="8" height="3.6" rx="0.6" />
      <text className="tx f-ink" x="31" y="5.9" fontSize="2.8">302</text>
      <rect className="f-gold-2" x="20" y="50" width="22" height="3" rx="1" />
      <g>
        <path className="f-paper" d="M48 50l-1-9h12l-1 9z" />
        <path className="ln" d="M50 41q3-4 6 0" />
        <circle className="f-roof" cx="51" cy="40" r="2" />
        <circle className="f-gold" cx="55" cy="40.4" r="1.8" />
      </g>
      <circle className="f-leaf" cx="9" cy="42" r="4" />
      <path className="f-wood" d="M6 45h6l-1 5h-4z" />
    </>
  ),

  dog: () => (
    <>
      <Backdrop far="hills" ground="grass" />
      <path className="f-wood" d="M6 46V30l9-7l9 7v16z" />
      <path className="f-roof" d="M4 31l11-9l11 9l-1.6 1.4L15 25l-9.4 7.4z" />
      <path className="f-tile-2" d="M11 46v-7a4 4 0 0 1 8 0v7z" />
      <Shadow cx={42} rx={12} />
      <g>
        <ellipse className="f-tile-2" cx="42" cy="42" rx="9" ry="6" />
        <path className="f-tile-2" d="M35 46v2h3v-4zM46 46v2h3v-4zM50 40q6 -4 4 -8" />
        <circle className="f-tile-2" cx="35" cy="32" r="6" />
        <path className="f-tile" d="M30 28q-3 4 0 8l2 -6zM40 28q3 4 0 8l-2 -6z" />
        <ellipse className="f-tile" cx="35" cy="35" rx="3" ry="2.2" />
        <circle className="f-ink ns" cx="35" cy="34" r="0.9" />
        <circle className="f-paper ns" cx="33" cy="31" r="0.8" />
        <circle className="f-paper ns" cx="37" cy="31" r="0.8" />
        <path className="f-roof" d="M30.6 37.6q4.4 2.4 8.8 0v1.6q-4.4 2.4 -8.8 0z" />
        <circle className="f-gold" cx="35" cy="40.4" r="1.1" />
      </g>
    </>
  ),

  cat: () => (
    <>
      <Room />
      <ellipse className="f-roof" cx="30" cy="44" rx="18" ry="4" />
      <path className="f-gold-2" d="M18 43q-2-14 12-14q14 0 12 14z" />
      <path className="ln s-wood dt" d="M22 36q3 2 6 0M32 37q3 2 6 0" />
      <path className="f-gold-2" d="M42 42q10 0 8 -10" style={{ strokeWidth: 1.2 }} />
      <path className="ln" d="M42 42q10 0 8 -10" />
      <circle className="f-gold-2" cx="30" cy="25" r="7" />
      <path className="f-gold-2" d="M23.6 22l0.4 -7l5 4zM36.4 22l-0.4 -7l-5 4z" />
      <path className="f-pink ns" d="M25 19.4l0.2 -2.6l2 1.6zM35 19.4l-0.2 -2.6l-2 1.6z" />
      <path className="ln" d="M26.6 24.6q1 -1 2 0M31.4 24.6q1 -1 2 0" />
      <path className="f-pink ns" d="M29.2 26.6h1.6l-0.8 1z" />
      <path className="ln dt" d="M22 27h4M22 29l4 -1M34 27h4M34 28l4 1" style={{ strokeWidth: 0.6 }} />
      <circle className="f-pink" cx="52" cy="44" r="4" />
      <path className="ln s-pink dt" d="M49 42q3 3 6 0M49 46q3 -3 6 0" />
    </>
  ),

  panda: () => (
    <>
      <Backdrop far="hills" ground="grass" />
      {[[48, 4, 0.2], [54, 8, -0.1], [10, 10, 0.1]].map(([x, top, lean]) => (
        <g key={x}>
          <path className="ln s-jade" d={`M${x} 48L${x + lean * 40} ${top}`} style={{ strokeWidth: 2.4 }} />
          <path className="f-leaf ns" d={`M${x + lean * 30} ${top + 10}q5 -2 8 0q-4 2 -8 0z`} />
        </g>
      ))}
      <Shadow rx={15} />
      <ellipse className="f-paper" cx="32" cy="38" rx="12" ry="10" />
      <ellipse className="f-tile-2" cx="22" cy="44" rx="4.4" ry="3.6" />
      <ellipse className="f-tile-2" cx="42" cy="44" rx="4.4" ry="3.6" />
      <path className="f-tile-2" d="M21 34q-4 4 1 7l4 -4zM43 34q4 4 -1 7l-4 -4z" />
      <circle className="f-paper" cx="32" cy="22" r="9" />
      <circle className="f-tile-2" cx="24.6" cy="14.6" r="3" />
      <circle className="f-tile-2" cx="39.4" cy="14.6" r="3" />
      <ellipse className="f-tile-2" cx="28.4" cy="21.6" rx="2.2" ry="2.8" transform="rotate(25 28.4 21.6)" />
      <ellipse className="f-tile-2" cx="35.6" cy="21.6" rx="2.2" ry="2.8" transform="rotate(-25 35.6 21.6)" />
      <circle className="f-paper ns" cx="28.8" cy="21" r="0.7" />
      <circle className="f-paper ns" cx="35.2" cy="21" r="0.7" />
      <ellipse className="f-tile-2 ns" cx="32" cy="25.4" rx="1.4" ry="1" />
      <path className="ln s-jade" d="M38 36l8 -8" style={{ strokeWidth: 2.2 }} />
      <path className="f-leaf ns" d="M45 29q4 -3 6 -1q-3 3 -6 1z" />
    </>
  ),

  snow_leopard: () => (
    <>
      <Backdrop far="none" clouds={false} />
      <path className="f-stone" d="M-4 46L16 16L36 46z" />
      <path className="f-stone-2" d="M24 46L46 12L70 46z" />
      <path className="f-paper ns" d="M16 16l5 7.4q-2.6 -1.4 -5 0.6q-2.4 -2 -5 -0.6zM46 12l6 9q-3 -1.6 -6 0.6q-3 -2.2 -6 -0.6z" />
      <Snow />
      <path className="f-stone" d="M8 50q6-8 20-6q8 1 10 6z" />
      <g>
        <path className="f-paper" d="M12 45q2-6 12-6q8 0 9 4l-1 2z" />
        <path className="ln" d="M33 44q10 2 12 -4q1 -3 -1 -4" style={{ strokeWidth: 2.6 }} />
        <path className="ln s-paper" d="M33 44q10 2 12 -4q1 -3 -1 -4" style={{ strokeWidth: 1.4 }} />
        <circle className="f-paper" cx="13" cy="39" r="4.6" />
        <path className="f-paper" d="M10 35.4l0.6 -2.4l2 1.6zM16 35.4l-0.6 -2.4l-2 1.6z" />
        <g className="f-tile ns">
          <circle cx="18" cy="42" r="0.9" /><circle cx="22" cy="41" r="0.9" /><circle cx="26" cy="42" r="0.9" />
          <circle cx="29" cy="41" r="0.8" /><circle cx="20" cy="44" r="0.7" /><circle cx="24" cy="44" r="0.7" />
        </g>
        <circle className="f-jade ns" cx="11.4" cy="38.6" r="0.7" />
        <circle className="f-jade ns" cx="14.6" cy="38.6" r="0.7" />
        <path className="f-ink ns" d="M12.4 40.6h1.2l-0.6 0.7z" />
      </g>
      <g className="f-stone ns dt" opacity="0.7">
        <circle cx="44" cy="56" r="1" /><circle cx="49" cy="54" r="1" /><circle cx="54" cy="57" r="1" /><circle cx="59" cy="55" r="1" />
      </g>
    </>
  ),

  camel: () => (
    <>
      <Backdrop far="none" ground="pave" />
      <Sand />
      <path className="f-gold ns" d="M-4 46q16-12 34 -2q14 -8 38 2z" opacity="0.6" />
      <Shadow cx={30} y={51} rx={15} />
      <g>
        <path className="f-gold-2" d="M16 40q0-8 6-8q3 -6 6 0q3 -6 6 0q6 0 6 8z" />
        <path className="ln" d="M19 40v10M24 40v10M33 40v10M38 40v10" style={{ strokeWidth: 1.8 }} />
        <path className="f-gold-2" d="M40 37q6 -2 6 -10q0 -4 4 -4q3 0 3 2l-2 1q-2 0 -2 3q0 10 -7 12z" />
        <circle className="f-ink ns" cx="50" cy="24.6" r="0.6" />
        <path className="f-roof" d="M23 32h10v3H23z" />
        <path className="f-blue ns" d="M24 32.6h8v1.2h-8z" />
      </g>
    </>
  ),

  dunhuang: () => (
    <>
      <Backdrop far="none" ground="pave" />
      <Sand />
      <path className="f-wall-2" d="M0 14h64v32H0z" />
      <path className="ln s-wood dt" d="M0 22h64M0 30h18M46 30h18M0 38h64" opacity="0.4" />
      {[[6, 18], [52, 18], [6, 33], [54, 33]].map(([x, y]) => (
        <path key={`${x}${y}`} className="f-tile-2" d={`M${x} ${y + 7}v-4a3 3 0 0 1 6 0v4z`} />
      ))}
      <path className="ln s-roof dt" d="M53 24q2 -3 4 0" />
      <rect className="f-roof" x="22" y="18" width="20" height="28" />
      <rect className="f-roof" x="24.6" y="10" width="14.8" height="8" />
      <path className="ln s-gold" d="M22 26h20M22 34h20M22 42h20" />
      <path className="f-tile" d="M18 19l14-3l14 3l-1 1.6H19zM20 11l12-3l12 3l-1 1.6H21zM18 27l14-2l14 2l-1 1.4H19zM18 35l14-2l14 2l-1 1.4H19z" />
      <Door x={29} y={39} w={6} h={7} tone="wood-2" />
    </>
  ),

  // ----------------------------------------------------- things we keep
  letter: () => (
    <>
      <Room />
      <rect className="f-paper" x="18" y="8" width="26" height="22" rx="1" transform="rotate(8 31 19)" />
      <path className="ln dt" d="M22 14l18 2.6M21.6 18l18 2.6M21.2 22l12 1.8" transform="rotate(0)" />
      <rect className="f-wall" x="10" y="20" width="38" height="24" rx="1" />
      <path className="ln" d="M10 21l19 12l19 -12" />
      <rect className="f-roof" x="38" y="23" width="7" height="8.4" />
      <path className="f-paper ns" d="M39 30l2.4 -3l1.4 1.6l1.2 -1v2.4z" />
      <circle className="ln s-roof-2 dt" cx="36" cy="30" r="3.4" />
      <path className="f-tile-2" d="M50 44l8 -26l2 0.8l-7 26z" />
      <path className="f-gold" d="M58 18l1-3l2 1l-1 2.8z" />
    </>
  ),

  gift: () => (
    <>
      <Room />
      <rect className="f-jade" x="12" y="27" width="28" height="18" rx="1" />
      <rect className="f-jade-2" x="10" y="21" width="32" height="7" rx="1" />
      <rect className="f-roof ns" x="23.6" y="21.4" width="4.8" height="23.4" />
      <path className="ln" d="M23.6 21v24M28.4 21v24" opacity="0.6" />
      <path className="f-roof" d="M26 21q-8 -9 -10 -3q0 4 10 3zM26 21q8 -9 10 -3q0 4 -10 3z" />
      <g>
        <path className="ln s-leaf" d="M50 45V28" style={{ strokeWidth: 1.2 }} />
        <circle className="f-pink" cx="50" cy="25" r="3.4" />
        <circle className="f-gold ns" cx="50" cy="25" r="1.2" />
        <path className="f-leaf" d="M50 36q-5 -3 -6 -1q2 3 6 1z" />
      </g>
      <rect className="f-paper" x="38" y="38" width="16" height="9" rx="1" transform="rotate(-6 46 42)" />
      <text className="tx f-roof" x="46" y="42.4" fontSize="3.6" transform="rotate(-6 46 42)">谢谢</text>
    </>
  ),

  garden: () => (
    <>
      <Backdrop far="hills" ground="grass" />
      <g className="dt">
        {range(10).map((i) => <rect key={i} className="f-wood" x={2 + i * 6.4} y="38" width="2" height="10" rx="0.6" />)}
        <path className="f-wood" d="M0 41h64v1.4H0z" />
      </g>
      {[[16, 22, 1], [32, 14, 1.2], [48, 24, 0.9]].map(([x, y, s]) => (
        <g key={x}>
          <path className="ln s-leaf" d={`M${x} 48V${y}`} style={{ strokeWidth: 1.6 }} />
          <path className="f-leaf" d={`M${x} ${y + 14}q-6 -4 -7 0q3 3 7 0zM${x} ${y + 18}q6 -4 7 0q-3 3 -7 0z`} />
          <g transform={`translate(${x} ${y}) scale(${s})`}>
            {range(10).map((i) => (
              <ellipse key={i} className="f-gold" cx="0" cy="-5.6" rx="1.8" ry="3.2" transform={`rotate(${i * 36})`} />
            ))}
            <circle className="f-wood" r="3.6" />
            <g className="f-wood-2 ns dt"><circle cx="-1" cy="-1" r="0.5" /><circle cx="1.2" cy="0.6" r="0.5" /><circle cx="-0.4" cy="1.4" r="0.5" /></g>
          </g>
        </g>
      ))}
      <path className="f-blue" d="M52 54h8l-1 6h-6zM60 55l3 -3" />
    </>
  ),

  watch: () => (
    <>
      <Room />
      <rect className="f-wood" x="27" y="4" width="10" height="16" rx="2" />
      <rect className="f-wood" x="27" y="40" width="10" height="16" rx="2" />
      <path className="ln s-wood dt" d="M27 10h10M27 46h10M27 50h10" />
      <circle className="f-gold" cx="32" cy="30" r="12" />
      <rect className="f-gold-2" x="43.4" y="28.4" width="3" height="3.2" rx="0.8" />
      <circle className="f-paper" cx="32" cy="30" r="9.4" />
      <g className="f-ink ns dt">
        {range(12).map((i) => {
          const a = (Math.PI / 6) * i;
          return <circle key={i} cx={32 + Math.cos(a) * 7.8} cy={30 + Math.sin(a) * 7.8} r="0.5" />;
        })}
      </g>
      <path className="ln" d="M32 30v-6M32 30l4.4 2.4" style={{ strokeWidth: 1.4 }} />
      <circle className="f-roof ns" cx="32" cy="30" r="1" />
    </>
  ),

  calendar: () => (
    <>
      <Room />
      <rect className="f-paper" x="10" y="8" width="34" height="34" rx="2" />
      <rect className="f-roof" x="10" y="8" width="34" height="9" rx="2" />
      <text className="tx f-paper" x="27" y="12.8" fontSize="5">考试</text>
      <g className="f-wall-2 ns">
        {range(4).flatMap((j) => range(5).map((i) => <rect key={`${i}${j}`} x={13 + i * 6} y={20 + j * 5.4} width="4" height="3.6" rx="0.6" />))}
      </g>
      <circle className="ln s-roof" cx="27" cy="27.6" r="3.6" style={{ strokeWidth: 1.4 }} />
      <circle className="ln s-roof" cx="39" cy="33" r="3.6" style={{ strokeWidth: 1.4, strokeDasharray: "1.4 1.2" }} />
      <rect className="f-stone" x="16" y="5" width="2" height="6" rx="1" />
      <rect className="f-stone" x="36" y="5" width="2" height="6" rx="1" />
      <Bubble x={44} y={18} w={14} h={12} tone="gold" flip>
        <text className="tx f-roof-2" x="51" y="24" fontSize="8">?</text>
      </Bubble>
    </>
  ),

  hourglass: () => (
    <>
      <Room />
      <circle className="ln s-gold dt" cx="32" cy="26" r="20" style={{ strokeDasharray: "1 3" }} opacity="0.7" />
      <rect className="f-wood" x="18" y="6" width="28" height="4" rx="1.4" />
      <rect className="f-wood" x="18" y="40" width="28" height="4" rx="1.4" />
      <path className="ln s-wood" d="M20 10v30M44 10v30" style={{ strokeWidth: 1.8 }} />
      <path className="f-glass" d="M23 10h18q0 9 -7 13q7 4 7 17H23q0 -13 7 -17q-7 -4 -7 -13z" opacity="0.85" />
      <path className="f-gold ns" d="M26 14h12q-1 5 -6 8q-5 -3 -6 -8z" />
      <path className="f-gold ns" d="M25 40q1 -7 7 -8q6 1 7 8z" />
      <path className="ln s-gold" d="M32 22v11" style={{ strokeWidth: 0.8 }} />
    </>
  ),

  // ------------------------------------------------------------- school
  exam: () => (
    <>
      <Room />
      <g transform="rotate(-6 28 26)">
        <rect className="f-paper" x="12" y="8" width="30" height="36" rx="1" />
        <text className="tx f-roof" x="27" y="13.4" fontSize="5">考试</text>
        {range(4).map((i) => (
          <g key={i}>
            <rect className="ln" x="15" y={19 + i * 6} width="3" height="3" style={{ strokeWidth: 0.8 }} />
            <path className="ln dt" d={`M20.6 ${20.6 + i * 6}h17`} />
          </g>
        ))}
        <path className="ln s-roof" d="M15.4 20.6l1.2 1.2l2 -3M15.4 26.6l1.2 1.2l2 -3" style={{ strokeWidth: 1.1 }} />
      </g>
      <path className="f-gold" d="M42 40l12-20l3 1.8l-12 20l-3.6 1.6z" />
      <path className="f-pink" d="M54 20l1.4 -2.2l3 1.8l-1.4 2.2z" />
      <rect className="f-pink" x="46" y="42" width="8" height="4" rx="1" />
    </>
  ),

  classroom: () => (
    <>
      <Room desk={false} />
      <rect className="f-wood-2" y="50" width="64" height="14" />
      <rect className="f-wood" x="7" y="7" width="40" height="24" rx="1" />
      <rect className="f-jade-2" x="9" y="9" width="36" height="20" />
      <text className="tx f-paper" x="27" y="17" fontSize="7">你好</text>
      <path className="ln s-paper dt" d="M14 24h26" opacity="0.7" />
      <circle className="f-paper" cx="55" cy="13" r="5" />
      <path className="ln" d="M55 10.4v2.6h2" />
      <rect className="f-gold" x="50" y="22" width="10" height="5" rx="0.8" />
      <text className="tx f-roof-2" x="55" y="24.6" fontSize="3">305</text>
      {[6, 26, 46].map((x) => (
        <g key={x}>
          <rect className="f-wood" x={x} y="40" width="14" height="3" rx="0.6" />
          <path className="ln" d={`M${x + 2} 43v7M${x + 12} 43v7`} style={{ strokeWidth: 1.4 }} />
        </g>
      ))}
      <path className="ln s-gold dt" d="M9 32h36" />
    </>
  ),

  stage: () => (
    <>
      <Room desk={false} />
      <path className="f-sun ns" d="M32 6L18 52h28z" opacity="0.22" />
      <rect className="f-wood" y="48" width="64" height="16" />
      <path className="f-roof" d="M0 4h14q-2 22 4 44H0zM64 4H50q2 22 -4 44h18z" />
      <path className="ln s-roof-2 dt" d="M5 6q-1 20 3 42M58 6q1 20 -3 42" />
      <rect className="f-roof-2" x="0" y="3" width="64" height="9" />
      <text className="tx f-gold" x="32" y="7.8" fontSize="5.4">新年快乐</text>
      <path className="ln" d="M32 48V30" style={{ strokeWidth: 1.2 }} />
      <path className="ln" d="M28 48h8" style={{ strokeWidth: 1.4 }} />
      <rect className="f-tile-2" x="30" y="22" width="4" height="8" rx="2" />
      <Notes x={18} y={24} s={1} />
      <Notes x={42} y={20} s={0.8} tone="paper" />
    </>
  ),

  debate: () => (
    <>
      <Room desk={false} />
      <rect className="f-wood-2" y="50" width="64" height="14" />
      <rect className="f-roof" x="14" y="5" width="36" height="8" rx="1" />
      <text className="tx f-gold" x="32" y="9.2" fontSize="5">辩论</text>
      {[[6, "blue"], [38, "roof"]].map(([x, tone]) => (
        <g key={x}>
          <path className={`f-${tone}`} d={`M${x} 50l2 -18h16l2 18z`} />
          <path className="ln s-gold dt" d={`M${x + 3} 38h14`} />
          <path className="ln" d={`M${x + 12} 32l-2 -6`} style={{ strokeWidth: 1.2 }} />
          <ellipse className="f-tile-2" cx={x + 9.6} cy="24.6" rx="1.6" ry="2.2" transform={`rotate(-20 ${x + 9.6} 24.6)`} />
        </g>
      ))}
      <Bubble x={4} y={14} w={14} h={7} tone="paper"><path className="ln dt" d="M7 17.6h8" /></Bubble>
      <Bubble x={46} y={14} w={14} h={7} tone="gold" flip><path className="ln dt" d="M49 17.6h8" /></Bubble>
    </>
  ),

  mountain_school: () => (
    <>
      <Backdrop far="none" ground="grass" />
      <path className="f-jade-2" d="M-6 46L16 12L38 46z" />
      <path className="f-jade" d="M22 46L46 8L72 46z" />
      <path className="f-paper ns" d="M46 8l5 8q-2.6 -1.4 -5 0.6q-2.4 -2 -5 -0.6z" />
      <path className="f-pave-2 ns" d="M28 64q4 -10 0 -16" style={{ fill: "none", stroke: "var(--art-pave-2)", strokeWidth: 4 }} />
      <Shadow cx={30} rx={16} />
      <rect className="f-wall" x="16" y="32" width="28" height="16" />
      <path className="f-roof" d="M13 33l17 -9l17 9z" />
      <rect className="f-glass" x="19" y="36" width="6" height="5" />
      <rect className="f-glass" x="35" y="36" width="6" height="5" />
      <Door x={27} y={38} w={6} h={10} />
      <Flag x={30} y={24} h={8} />
      <Tree x={52} r={3.6} />
    </>
  ),

  // ------------------------------------------------------------- sport
  basketball: () => (
    <>
      <Backdrop far="city" />
      <path className="ln" d="M44 48V20" style={{ strokeWidth: 2.4 }} />
      <rect className="f-paper" x="26" y="8" width="24" height="16" rx="1" />
      <rect className="ln s-roof" x="33" y="13" width="9" height="7" style={{ strokeWidth: 1.2 }} />
      <ellipse className="ln s-roof" cx="37.5" cy="24" rx="5" ry="1.4" style={{ strokeWidth: 1.6 }} />
      <path className="ln" d="M33 24.4l1.6 6h6l1.6 -6M35.4 24.6l0.6 5.8M39.6 24.6l-0.6 5.8" style={{ strokeWidth: 0.6 }} />
      <Shadow cx={18} rx={8} />
      <circle className="f-gold-2" cx="18" cy="38" r="8" />
      <path className="ln" d="M10 38h16M18 30v16M12.4 32.4q4 5.6 0 11.2M23.6 32.4q-4 5.6 0 11.2" style={{ strokeWidth: 0.9 }} />
    </>
  ),

  football: () => (
    <>
      <Backdrop far="hills" ground="grass" />
      <path className="ln s-paper" d="M0 56h64M32 46v18" style={{ strokeWidth: 1.2 }} opacity="0.8" />
      <path className="ln" d="M8 46V18h48v28" style={{ strokeWidth: 2.6 }} />
      <path className="ln s-paper" d="M8 46V18h48v28" style={{ strokeWidth: 1.4 }} />
      <path className="ln s-stone dt" d={`${range(9).map((i) => `M${12 + i * 5} 19v27`).join("")}${range(5).map((i) => `M9 ${23 + i * 5}h46`).join("")}`} style={{ strokeWidth: 0.5 }} />
      <Shadow cx={32} y={55} rx={7} />
      <circle className="f-paper" cx="32" cy="48" r="7" />
      <path className="f-ink" d="M32 45l2.4 1.8l-0.9 2.8h-3l-0.9 -2.8z" />
      <path className="f-ink ns" d="M25.6 46.4l1.6 -1.6l1 2zM38.4 46.4l-1.6 -1.6l-1 2zM29 54l1.6 -1.6h2.8l1.6 1.6z" />
    </>
  ),

  pool: () => (
    <>
      <Backdrop far="city" ground="water" />
      <rect className="f-water" y="26" width="64" height="38" />
      <rect className="f-stone" y="24" width="64" height="3" />
      {[34, 46, 58].map((y, i) => (
        <path key={y} className={`ln s-${i % 2 ? "roof" : "paper"}`} d={`M0 ${y}h64`} style={{ strokeWidth: 1.4, strokeDasharray: "2 1.6" }} />
      ))}
      <path className="ln s-stone" d="M52 18v14M57 18v14M52 22h5M52 26h5" style={{ strokeWidth: 1.6 }} />
      <circle className="f-roof" cx="16" cy="44" r="6" />
      <circle className="f-water" cx="16" cy="44" r="3" />
      <path className="ln s-paper" d="M11 40l3 2M21 40l-3 2M11 48l3 -2M21 48l-3 -2" style={{ strokeWidth: 2 }} />
      <path className="f-blue" d="M30 41a5 5 0 0 1 10 0z" />
      <circle className="f-skin" cx="35" cy="41.4" r="3.2" />
      <path className="f-blue" d="M31.6 40a3.6 3.6 0 0 1 6.8 0z" />
      <rect className="f-gold ns" x="32.4" y="40.4" width="5.2" height="1.4" rx="0.6" />
      <path className="ln s-paper dt" d="M28 44q3 -1 6 0M38 44q3 -1 6 0" />
    </>
  ),

  running: () => (
    <>
      <Backdrop far="hills" ground="grass" />
      <path className="f-roof-2" d="M-4 64q20 -22 72 -18v8q-46 -2 -64 14z" />
      <path className="ln s-paper" d="M0 62q20 -16 64 -12" style={{ strokeWidth: 0.8, strokeDasharray: "2 2" }} />
      <g transform="translate(2 7)">
        <Shadow cx={30} y={47} rx={16} />
        <path className="f-jade" d="M14 44q0 -9 7 -10h6l4 5q11 0 15 4v3H14z" />
        <path className="f-paper" d="M13 44h34v3H13z" />
        <path className="ln s-paper" d="M23 35l3 3M25.6 34l3 3M28 36.6l3 2" style={{ strokeWidth: 1 }} />
        <path className="ln s-gold dt" d="M6 36h5M4 40h6" style={{ strokeWidth: 1.2 }} />
      </g>
    </>
  ),

  // ---------------------------------------------------- science & tech
  plant_music: () => (
    <>
      <Room />
      <path className="f-roof" d="M14 34h18l-2 12H16z" />
      <rect className="f-roof-2" x="13" y="32" width="20" height="3.4" rx="1" />
      <path className="ln s-leaf" d="M23 32V16" style={{ strokeWidth: 1.6 }} />
      <path className="f-leaf" d="M23 22q-9 -6 -10 0q4 4 10 0zM23 18q8 -8 10 -2q-4 5 -10 2zM23 28q8 -5 10 0q-4 4 -10 0z" />
      <g>
        <rect className="f-tile" x="40" y="32" width="16" height="12" rx="2" />
        <circle className="f-stone" cx="46" cy="38" r="3.4" />
        <rect className="f-gold ns" x="51" y="35" width="3" height="1.4" />
        <path className="ln" d="M44 32l4 -6" />
      </g>
      <Notes x={34} y={14} s={1} tone="jade" />
      <Notes x={44} y={8} s={0.8} tone="roof" />
    </>
  ),

  robot: () => (
    <>
      <Room />
      <Shadow cx={30} y={46} rx={12} />
      <path className="ln" d="M30 9V4" />
      <circle className="f-roof" cx="30" cy="3.6" r="1.8" />
      <rect className="f-stone" x="18" y="9" width="24" height="16" rx="4" />
      <rect className="f-screen" x="21" y="12" width="18" height="10" rx="2.4" />
      <g className="f-gold ns"><circle cx="26" cy="16.4" r="1.6" /><circle cx="34" cy="16.4" r="1.6" /></g>
      <path className="ln s-gold" d="M27 19.6q3 1.6 6 0" />
      <rect className="f-stone" x="20" y="27" width="20" height="17" rx="3" />
      <rect className="f-stone-2 ns" x="24" y="30" width="12" height="7" rx="1.4" />
      <g className="ns"><circle className="f-roof" cx="27" cy="33.4" r="1.1" /><circle className="f-jade" cx="30" cy="33.4" r="1.1" /><circle className="f-gold" cx="33" cy="33.4" r="1.1" /></g>
      <path className="f-stone" d="M20 30l-6 6l2 2l5 -4zM40 30l6 -8l2 1.6l-5 9z" />
      <Bubble x={46} y={6} w={15} h={9} tone="jade" flip>
        <text className="tx f-paper" x="53.5" y="10.6" fontSize="4.2">你好</text>
      </Bubble>
    </>
  ),

  // A week without phones: the phone asleep in its box, a kite outside.
  no_phone: () => (
    <>
      <Backdrop far="hills" ground="grass" />
      <path className="ln" d="M46 26q4 10 2 18t6 14" style={{ strokeWidth: 0.8 }} />
      <path className="f-pink" d="M46 5l8 10l-8 11l-8 -11z" />
      <path className="ln s-pink" d="M46 5v21M38 15h16" style={{ strokeWidth: 0.8 }} />
      <g className="f-gold"><path d="M47 32l3 -1l-1 3z" /><path d="M48 40l3 -1l-1 3z" /></g>
      <Shadow cx={24} rx={15} />
      <rect className="f-wood" x="9" y="35" width="30" height="13" rx="1" />
      <path className="f-wood-2" d="M7 35l3 -4h28l3 4z" />
      <rect className="f-tile-2" x="14" y="27.6" width="20" height="7.4" rx="1.6" />
      <rect className="f-screen ns" x="15.4" y="28.8" width="17.2" height="5" rx="0.8" />
      <text className="tx f-gold" x="21" y="31.4" fontSize="3.6">z</text>
      <text className="tx f-gold" x="25.6" y="31" fontSize="4.6">Z</text>
      <path className="ln s-wood dt" d="M9 41h30" />
    </>
  ),

  lost_phone: () => (
    <>
      <Room desk={false} />
      <rect className="f-wood-2" y="48" width="64" height="16" />
      <rect className="f-roof" x="6" y="22" width="48" height="16" rx="4" />
      <rect className="f-roof" x="4" y="32" width="56" height="14" rx="4" />
      <rect className="f-roof-2" x="10" y="30" width="20" height="6" rx="3" />
      <rect className="f-roof-2" x="32" y="30" width="20" height="6" rx="3" />
      <path className="ln" d="M8 46v4M56 46v4" style={{ strokeWidth: 1.8 }} />
      <g transform="rotate(-18 24 31)">
        <rect className="f-tile-2" x="19" y="27" width="10" height="6" rx="1.2" />
        <rect className="f-glass ns" x="20" y="28" width="8" height="4" rx="0.6" />
      </g>
      <circle className="f-glass ns dt" cx="24" cy="29" r="6" opacity="0.25" />
      <Magnifier x={46} y={14} r={6} angle={30} />
    </>
  ),

  // ----------------------------------------------------------- the city
  bicycle: () => (
    <>
      <Backdrop far="city" />
      <path className="f-jade ns" d="M0 54h64v3H0z" opacity="0.6" />
      <Shadow rx={20} y={50} />
      <g>
        <circle className="ln" cx="18" cy="42" r="7.4" style={{ strokeWidth: 1.6 }} />
        <circle className="ln" cx="46" cy="42" r="7.4" style={{ strokeWidth: 1.6 }} />
        <path className="ln s-blue" d="M18 42l8 -12h14l6 12M26 30l6 12l8 -12M32 42h-14" style={{ strokeWidth: 2 }} />
        <path className="ln" d="M24 27h5M40 30l-1.6 -6h4" style={{ strokeWidth: 1.6 }} />
        <rect className="f-wood" x="40" y="18" width="9" height="6" rx="1" />
        <path className="ln s-wood dt" d="M42 18v6M45 18v6" />
      </g>
    </>
  ),

  taxi: () => (
    <>
      <Backdrop far="city" />
      <Shadow rx={24} y={49} />
      <path className="f-gold" d="M6 46v-6q0 -3 3 -3.4l7 -1l5 -7h20l7 7l8 1.4q2 0.4 2 3V46z" />
      <path className="f-glass" d="M22 30.4h8v5.6H17zM32 30.4h8l5 5.6H32z" />
      <rect className="f-tile-2 ns" x="6.6" y="41" width="51.4" height="2.4" />
      <rect className="f-paper" x="27" y="25" width="10" height="4.4" rx="1" />
      <text className="tx f-roof" x="32" y="27.4" fontSize="3">出租</text>
      <rect className="f-roof ns" x="54" y="38.4" width="3" height="1.6" rx="0.6" />
      <Wheel x={16} y={46} r={4} />
      <Wheel x={47} y={46} r={4} />
    </>
  ),

  driving: () => (
    <>
      <Backdrop far="hills" />
      <path className="ln s-paper" d="M0 55h10M18 55h10M36 55h10M54 55h10" style={{ strokeWidth: 1.6 }} />
      <Shadow rx={22} y={49} />
      <path className="f-blue" d="M8 46v-6q0 -3 3 -3.4l7 -1l5 -6h18l6 6l7 1.4q2 0.4 2 3V46z" />
      <path className="f-glass" d="M24 31h7v5H19zM33 31h7l4 5H33z" />
      <rect className="f-gold" x="25" y="38.4" width="7" height="6" rx="0.8" />
      <text className="tx f-roof-2" x="28.5" y="41.6" fontSize="4.4">学</text>
      <Wheel x={18} y={46} r={4} />
      <Wheel x={46} y={46} r={4} />
    </>
  ),

  lift: () => (
    <>
      <Room desk={false} />
      <rect className="f-wood-2" y="52" width="64" height="12" />
      <rect className="f-stone-2" x="12" y="10" width="40" height="42" />
      <rect className="f-stone" x="15" y="16" width="16.6" height="36" />
      <rect className="f-stone" x="32.4" y="16" width="16.6" height="36" />
      <path className="hl dt" d="M18 20v26M35.4 20v26" />
      <rect className="f-screen" x="25" y="3.4" width="14" height="5.4" rx="1" />
      <text className="tx f-gold" x="30.4" y="6.3" fontSize="3.6">12</text>
      <path className="f-gold ns" d="M35 7.2l1.6 -2.6l1.6 2.6z" />
      <rect className="f-stone" x="54" y="26" width="5" height="11" rx="1" />
      <circle className="f-gold" cx="56.5" cy="29.4" r="1.2" />
      <circle className="f-paper" cx="56.5" cy="33.6" r="1.2" />
    </>
  ),

  scooter: () => (
    <>
      <Backdrop far="city" sun={false} />
      <path className="ln s-water dt" d={range(8).map((i) => `M${4 + i * 8} ${8 + (i % 3) * 5}l-2 4`).join("")} style={{ strokeWidth: 1.1 }} />
      <Shadow rx={22} y={50} />
      <rect className="f-gold-2" x="8" y="22" width="16" height="13" rx="1.4" />
      <text className="tx f-paper" x="16" y="28.6" fontSize="4.2">外卖</text>
      <path className="f-jade" d="M8 44q0 -8 8 -8h18l6 -12h4l-4 14q6 2 6 6z" />
      <path className="ln" d="M42 24l4 -2" style={{ strokeWidth: 1.6 }} />
      <circle className="f-glass" cx="48" cy="22" r="1.6" />
      <Wheel x={14} y={46} r={4.2} />
      <Wheel x={44} y={46} r={4.2} />
    </>
  ),

  recycling: () => (
    <>
      <Backdrop far="city" />
      <Shadow rx={27} />
      {[[4, "blue"], [19, "roof"], [34, "jade"], [49, "stone-2"]].map(([x, tone]) => (
        <g key={x}>
          <path className={`f-${tone}`} d={`M${x + 1} 30h11l-1 18h-9z`} />
          <rect className={`f-${tone}`} x={x} y="27" width="13" height="3.4" rx="1" />
          <circle className="f-paper ns" cx={x + 6.5} cy="38" r="2.6" opacity="0.85" />
        </g>
      ))}
      <path className="f-glass" d="M8 18h3v6q0 1.4 -1.5 1.4T8 24z" />
      <path className="f-roof ns dt" d="M24 36.6l1.4 2.6h-2.8z" />
      <path className="f-leaf" d="M38 20q2 -4 5 -2q-1 4 -5 2z" />
      <path className="f-paper" d="M52 17h7v6h-7z" transform="rotate(10 55 20)" />
    </>
  ),

  // --------------------------------------------------------------- misc
  coins: () => (
    <>
      <Room />
      <rect className="f-jade" x="8" y="22" width="28" height="15" rx="1" transform="rotate(-8 22 30)" />
      <circle className="ln s-paper" cx="22" cy="29" r="3.6" transform="rotate(-8 22 30)" />
      <rect className="f-wood-2" x="12" y="30" width="28" height="16" rx="3" />
      <path className="f-wood" d="M12 34h28v6H12z" />
      <circle className="f-gold" cx="34" cy="37" r="1.4" />
      {[0, 1, 2, 3].map((i) => (
        <g key={i}>
          <ellipse className="f-gold-2" cx="50" cy={44 - i * 3} rx="7" ry="2.4" />
          <ellipse className="f-gold" cx="50" cy={43 - i * 3} rx="7" ry="2.4" />
        </g>
      ))}
      <text className="tx f-roof-2" x="50" y="34.2" fontSize="3.4">¥</text>
    </>
  ),

  candle: () => (
    <>
      <Room />
      <WallWindow x={8} y={8} w={16} h={16} />
      <rect className="f-screen ns" width="64" height="64" opacity="0.55" />
      <circle className="f-sun ns" cx="36" cy="22" r="14" opacity="0.28" />
      <circle className="f-sun ns" cx="36" cy="22" r="8" opacity="0.35" />
      <ellipse className="f-gold-2" cx="36" cy="45" rx="10" ry="2.6" />
      <rect className="f-paper" x="32" y="26" width="8" height="18" rx="1" />
      <path className="ln" d="M36 26v-2" />
      <path className="f-gold" d="M36 15q3.6 4.6 0 8.4q-3.6 -3.8 0 -8.4z" />
      <path className="f-roof ns" d="M36 18.4q1.6 2.4 0 4q-1.6 -1.6 0 -4z" />
    </>
  ),

  suitcase: () => (
    <>
      <Room desk={false} />
      <rect className="f-stone-2" y="44" width="64" height="20" />
      <path className="ln s-stone" d="M0 48h64M8 44v20M24 44v20M40 44v20M56 44v20" />
      {[[10, 0], [36, 1]].map(([x, odd]) => (
        <g key={x}>
          <path className="ln" d={`M${x + 6} 18v-5h6v5`} style={{ strokeWidth: 1.6 }} />
          <rect className="f-blue" x={x} y="18" width="18" height="26" rx="3" />
          <path className="ln s-blue dt" d={`M${x + 6} 18v26M${x + 12} 18v26`} />
          <path className="ln" d={`M${x + 14} 24l4 4`} />
          <rect className="f-paper" x={x + 15} y="27" width="6" height="8" rx="0.8" transform={`rotate(-12 ${x + 18} 31)`} />
          {odd ? <text className="tx f-roof" x={x + 18} y="31.4" fontSize="5" transform={`rotate(-12 ${x + 18} 31)`}>?</text> : null}
        </g>
      ))}
    </>
  ),

  old_key: () => (
    <>
      <Room />
      <path className="f-wood-2" d="M6 42l26 3l26 -3v-24l-26 3l-26 -3z" />
      <path className="f-paper" d="M8 40q12 -1 24 3V22q-12 -4 -24 -3z" />
      <path className="f-paper" d="M56 40q-12 -1 -24 3V22q12 -4 24 -3z" />
      <path className="ln dt" d="M12 25h16M12 29h16M12 33h12M36 25h16M36 29h16M36 33h12" />
      <g transform="rotate(-20 32 30)">
        <circle className="ln s-gold" cx="18" cy="30" r="4" style={{ strokeWidth: 2.2 }} />
        <path className="ln s-gold" d="M22 30h22M38 30v4M42 30v5" style={{ strokeWidth: 2.2 }} />
      </g>
    </>
  ),

  scroll: () => (
    <>
      <Room />
      <rect className="f-wall" x="10" y="38" width="22" height="8" transform="rotate(-6 20 42)" />
      <rect className="f-paper" x="12" y="35" width="22" height="8" transform="rotate(4 22 39)" />
      <rect className="f-paper" x="22" y="8" width="24" height="30" />
      <rect className="f-wood-2" x="19" y="6" width="30" height="3.4" rx="1.6" />
      <rect className="f-wood-2" x="19" y="37" width="30" height="3.4" rx="1.6" />
      <text className="tx f-ink" x="34" y="22" fontSize="14" style={{ fontWeight: 600 }}>纸</text>
      <rect className="f-roof ns" x="40" y="31" width="3" height="3" rx="0.4" />
      <g transform="translate(52 36) rotate(25)">
        <rect className="f-wood" x="-1" y="-12" width="2" height="12" rx="0.8" />
        <path className="f-ink" d="M-1.4 0h2.8q0 4 -1.4 6q-1.4 -2 -1.4 -6z" />
      </g>
    </>
  ),

  empty_frame: () => (
    <>
      <Room desk={false} />
      <rect className="f-wood-2" y="52" width="64" height="12" />
      <path className="f-sun ns" d="M32 0L14 50h36z" opacity="0.15" />
      <rect className="f-gold" x="13" y="10" width="38" height="30" rx="1" />
      <rect className="f-gold-2" x="16" y="13" width="32" height="24" />
      <rect className="f-room" x="18" y="15" width="28" height="20" />
      <circle className="f-tile-2" cx="32" cy="12" r="0.9" />
      <text className="tx f-roof" x="32" y="25.4" fontSize="12">?</text>
      {[10, 54].map((x) => (
        <g key={x}>
          <path className="ln" d={`M${x} 52V40`} style={{ strokeWidth: 1.6 }} />
          <circle className="f-gold" cx={x} cy="39" r="1.4" />
        </g>
      ))}
      <path className="ln s-roof" d="M10 42q22 8 44 0" style={{ strokeWidth: 1.6 }} />
    </>
  ),

  old_photo: () => (
    <>
      <Room />
      <g transform="rotate(-7 26 26)">
        <rect className="f-paper" x="8" y="8" width="34" height="32" rx="0.6" />
        <rect className="f-wall-2" x="11" y="11" width="28" height="22" />
        {[[17, 0], [25, 1], [33, 0]].map(([x, tall]) => (
          <g key={x} className="f-wood ns" opacity="0.75">
            <circle cx={x} cy={tall ? 20 : 21.4} r="2.2" />
            <path d={`M${x - 3} 33v-5q0 -3 3 -3t3 3v5z`} />
          </g>
        ))}
      </g>
      <g>
        <rect className="f-tile-2" x="40" y="32" width="18" height="12" rx="1.6" />
        <rect className="f-tile" x="43" y="29.4" width="6" height="3" rx="0.6" />
        <circle className="f-stone" cx="49" cy="38" r="4" />
        <circle className="f-screen ns" cx="49" cy="38" r="2.2" />
        <rect className="f-gold ns" x="54" y="34" width="2" height="1.4" />
      </g>
    </>
  ),

  opera: () => (
    <>
      <Room />
      <g className="f-roof">
        <circle cx="15" cy="34" r="2.6" /><circle cx="49" cy="34" r="2.6" />
      </g>
      <path className="ln" d="M17 30l-2 4M47 30l2 4" />
      <path className="f-gold" d="M16 14q16 -10 32 0l-2 4H18z" />
      <circle className="f-roof" cx="32" cy="11" r="2" />
      <path className="f-paper" d="M18 18h28q1 14 -5 20q-5 6 -9 6t-9 -6q-6 -6 -5 -20z" />
      <path className="f-roof ns" d="M19 24q4 -2 7 1q-1 6 -2 9q-4 -3 -5 -10zM45 24q-4 -2 -7 1q1 6 2 9q4 -3 5 -10z" />
      <path className="f-ink" d="M21 21q4 -3 9 0q-4 1 -9 0zM34 21q5 -3 9 0q-5 1 -9 0z" />
      <path className="f-ink" d="M24 26q2 -1.6 4 0q-2 1.4 -4 0zM36 26q2 -1.6 4 0q-2 1.4 -4 0z" />
      <path className="f-roof-2" d="M29 37q3 1.6 6 0q-3 3 -6 0z" />
      <path className="ln" d="M32 26v6" opacity="0.6" />
    </>
  ),

  name_seal: () => (
    <>
      <Room />
      <rect className="f-paper" x="14" y="6" width="26" height="38" rx="0.6" />
      <text className="tx f-ink" x="27" y="17" fontSize="10" style={{ fontWeight: 600 }}>王</text>
      <text className="tx f-ink" x="27" y="30" fontSize="10" style={{ fontWeight: 600 }}>明</text>
      <rect className="f-roof" x="30" y="36" width="6" height="6" rx="0.6" />
      <text className="tx f-paper" x="33" y="39.2" fontSize="3.6">印</text>
      <rect className="f-roof-2" x="46" y="28" width="8" height="12" rx="1" />
      <rect className="f-wood" x="47" y="18" width="6" height="10" rx="2" />
      <rect className="f-roof" x="44" y="40" width="12" height="3" rx="1" />
    </>
  ),

  // A story without its own cover yet: an open book with a ribbon.
  reading: () => (
    <>
      <Room />
      <path className="f-wood-2" d="M6 42l26 3l26 -3v-24l-26 3l-26 -3z" />
      <path className="f-paper" d="M8 40q12 -1 24 3V22q-12 -4 -24 -3z" />
      <path className="f-paper" d="M56 40q-12 -1 -24 3V22q12 -4 24 -3z" />
      <text className="tx f-ink" x="20" y="29" fontSize="7">书</text>
      <path className="ln dt" d="M36 25h16M36 29h16M36 33h12M12 35h14" />
      <path className="f-roof" d="M46 18v12l2 -2l2 2V18z" />
    </>
  ),
};

export function bookFallback() {
  return BOOK_ART.reading();
}
