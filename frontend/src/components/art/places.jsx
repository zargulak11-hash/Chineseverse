import {
  Awning, Backdrop, Bush, Columns, Door, Flag, Lantern, Magnifier, Notes, Pot, Roof, Shadow, Sign, Star, Steps,
  StreetLamp, Tree, Win, Wins, range,
} from "./kit.jsx";

// A white-walled water-town house with stepped "horse-head" gables and
// black tile copings (old_town).
function WaterHouse({ x, y, w, h }) {
  const s = w / 6;
  const tops = [[x, y - 3, s], [x + s, y - 6, s], [x + 2 * s, y - 9, 2 * s], [x + 4 * s, y - 6, s], [x + 5 * s, y - 3, s]];
  return (
    <g>
      <path className="f-wall" d={`M${x} ${y + h}V${y - 3}h${s}v-3h${s}v-3h${2 * s}v3h${s}v3h${s}V${y + h}z`} />
      {tops.map(([tx, ty, tw]) => <rect key={tx} className="f-tile-2" x={tx - 0.6} y={ty - 1} width={tw + 1.2} height="1.6" rx="0.4" />)}
      <rect className="f-tile-2" x={x - 1} y={y - 0.4} width={w + 2} height="1.8" rx="0.4" />
    </g>
  );
}

// The places of Живой китайский (services/world_places.py), one painting
// per place key, all from the shared kit. The signs carry the Chinese the
// learner will meet at that door (银行, 医院, 地铁 ...). A place added to
// the world without artwork here still gets the generic `building`.

export const PLACE_ART = {
  // ---------------------------------------------------------------- home
  home: () => (
    <>
      <Backdrop far="hills" ground="grass" />
      <Shadow rx={20} />
      <Tree x={10.5} r={5} />
      <rect className="f-wall" x="17" y="30" width="30" height="18" />
      <rect className="f-wall-2 ns" x="17.6" y="30.6" width="28.8" height="2.2" />
      <Roof cx={32} y={31} hw={17} h={9} />
      <Win x={20.5} y={36} w={5} h={5} />
      <Win x={38.5} y={36} w={5} h={5} />
      <path className="ln" d="M23 36v5M20.5 38.5h5M41 36v5M38.5 38.5h5" />
      <Door x={28.5} y={38} w={7} h={10} tone="roof" double />
      <Sign x={29} y={32.4} w={6} h={4.6} text="家" />
      <Lantern x={18.4} y={31.6} />
      <Lantern x={45.6} y={31.6} />
      <Bush x={53} r={3.2} />
    </>
  ),

  word_garden: () => (
    <>
      <Backdrop far="hills" ground="grass" />
      <g className="dt">
        {range(9).map((i) => <rect key={i} className="f-wood" x={6 + i * 6.2} y="41" width="2" height="7" rx="0.6" />)}
        <path className="f-wood" d="M5 43h54v1.4H5z" />
      </g>
      <Shadow rx={14} />
      <path className="f-wood" d="M29.5 48c1-6 0.6-11-0.5-16h6c-1.1 5-1.5 10-0.5 16z" />
      <circle className="f-leaf" cx="32" cy="22" r="13" />
      <circle className="f-leaf" cx="21.5" cy="27" r="7" />
      <circle className="f-leaf" cx="42.5" cy="27" r="7" />
      <circle className="f-leaf-2 ns" cx="36" cy="27" r="7" opacity="0.6" />
      <circle className="f-leaf-2 ns" cx="22" cy="29" r="4" opacity="0.6" />
      {[[22, 22, "字"], [31, 29, "词"], [40, 21, "书"], [32, 14, "学"]].map(([x, y, ch]) => (
        <g key={ch}>
          <path className="ln s-gold" d={`M${x} ${y - 3}v2`} />
          <rect className="f-paper" x={x - 3} y={y - 1} width="6" height="6.4" rx="0.8" />
          <text className="tx f-roof" x={x} y={y + 2.3} fontSize="4.2">{ch}</text>
        </g>
      ))}
      <g className="dt">
        <circle className="f-pink" cx="12" cy="50" r="1.4" />
        <circle className="f-gold" cx="16" cy="52" r="1.2" />
        <circle className="f-pink" cx="49" cy="51" r="1.4" />
        <circle className="f-gold" cx="54" cy="49.6" r="1.1" />
      </g>
    </>
  ),

  cafe: () => (
    <>
      <Backdrop far="city" />
      <Shadow rx={20} />
      <rect className="f-wall" x="13" y="22" width="38" height="26" />
      <Sign x={11.5} y={18.5} w={41} h={5} text="咖啡馆" tone="wood" size={3.6} />
      <Awning x={13} y={25} w={38} n={8} h={4} />
      <Win x={16} y={33} w={18} h={11} />
      <path className="f-paper ns dt" d="M21.5 36.5h6l-0.7 4h-4.6z" opacity="0.9" />
      <path className="ln s-paper dt" d="M27.4 37.5a1.4 1.4 0 0 1 0 2.4" />
      <Door x={37} y={32} w={10} h={16} glass />
      <Pot x={10} />
      <Pot x={54} />
      <g>
        <path className="f-paper" d="M25 8h14l-1.6 8.4h-10.8z" />
        <rect className="f-wood ns" x="25.8" y="10.8" width="12.4" height="2.2" />
        <path className="ln" d="M38.4 10a2.6 2.6 0 0 1 0 4.8" />
        <ellipse className="f-paper" cx="32" cy="16.8" rx="9" ry="1.6" />
        <path className="ln dt" d="M29 6q-1-1.5 0-3M32 6.4q-1-1.6 0-3.4M35 6q-1-1.5 0-3" />
      </g>
    </>
  ),

  // -------------------------------------------------------------- campus
  university: () => (
    <>
      <Backdrop far="hills" ground="grass" />
      <Shadow rx={24} />
      <rect className="f-wall" x="8" y="30" width="48" height="18" />
      <rect className="f-wall-2 ns" x="8.6" y="30.6" width="46.8" height="1.6" />
      <Wins x={10.5} y={33} cols={3} rows={2} w={3} h={4} gx={1.8} gy={2.4} />
      <Wins x={39.5} y={33} cols={3} rows={2} w={3} h={4} gx={1.8} gy={2.4} />
      <rect className="f-wall" x="23" y="20" width="18" height="28" />
      <Roof cx={32} y={21} hw={11} h={6} tone="jade" />
      <Sign x={25.5} y={23} w={13} h={5} text="大学" />
      <circle className="f-paper" cx="32" cy="32" r="2.6" />
      <path className="ln" d="M32 30.4v1.6h1.2" />
      <Door x={28} y={37} w={8} h={11} double />
      <Steps cx={32} y={48} w={16} />
      <Flag x={32} y={13} h={8} />
      <Tree x={5} y={48} r={3.6} />
      <Tree x={59} y={48} r={3.6} />
    </>
  ),

  library: () => (
    <>
      <Backdrop far="city" />
      <Shadow rx={22} />
      <rect className="f-wall" x="12" y="24" width="40" height="22" />
      <rect className="f-wall-2" x="14" y="27" width="36" height="17" />
      <path className="f-stone" d="M9 24.5L32 12l23 12.5z" />
      <path className="f-wall-2 ns" d="M15.5 22.6L32 14.6l16.5 8z" />
      <circle className="f-gold" cx="32" cy="19.6" r="3.4" />
      <text className="tx f-roof-2" x="32" y="19.8" fontSize="4">书</text>
      <rect className="f-stone" x="11" y="24" width="42" height="3.4" />
      <text className="tx f-roof-2 dt" x="32" y="25.8" fontSize="2.6">图 书 馆</text>
      <Columns x={15} y={27.4} h={17} n={5} gap={8} />
      <Steps cx={32} y={48} w={44} />
      <g>
        <rect className="f-blue" x="5" y="44" width="12" height="3.6" rx="0.6" />
        <rect className="f-jade" x="6.4" y="40.4" width="10" height="3.6" rx="0.6" />
        <rect className="f-roof" x="5.6" y="36.8" width="11" height="3.6" rx="0.6" />
        <path className="ln s-paper dt" d="M7 45.8h8M8 42.2h6.4M7.4 38.6h7" />
      </g>
    </>
  ),

  bookstore: () => (
    <>
      <Backdrop far="city" />
      <Shadow rx={20} />
      <rect className="f-wall" x="13" y="22" width="38" height="26" />
      <Sign x={13} y={20} w={38} h={5.4} text="书店" tone="jade" />
      <Awning x={13} y={25.4} w={38} n={8} h={3.6} a="jade" />
      <rect className="f-wall-2" x="16" y="32" width="19" height="12" />
      {[[16.8, "roof"], [18.6, "blue"], [20.4, "gold"], [22.2, "jade"], [24, "roof-2"], [25.8, "paper"], [27.6, "blue"], [29.4, "gold-2"], [31.2, "roof"], [33, "jade"]]
        .map(([x, tone], i) => (
          <g key={i}>
            <rect className={`f-${tone} ns`} x={x} y={33} width="1.6" height="4.6" />
            <rect className={`f-${tone === "paper" ? "roof" : "paper"} ns dt`} x={x} y={38.8} width="1.6" height="4.6" opacity="0.9" />
          </g>
        ))}
      <path className="ln" d="M16 38.2h19" />
      <Door x={38.5} y={32} w={9} h={16} glass />
      <g>
        <path className="f-paper" d="M32 17Q26.5 12.6 20 13.4V8.4Q26.5 7.6 32 12zM32 17Q37.5 12.6 44 13.4V8.4Q37.5 7.6 32 12z" />
        <path className="ln dt" d="M22.4 10h6M22.4 11.6h5M35.6 10h6M36.6 11.6h5" />
      </g>
    </>
  ),

  // -------------------------------------------------------------- centre
  street: () => (
    <>
      <Backdrop far="none" />
      <rect className="f-stone" x="7" y="22" width="15" height="26" />
      <Wins x={9} y={25} cols={3} rows={3} w={2.6} h={3.4} gx={1.6} gy={2.6} />
      <rect className="f-blue" x="23" y="9" width="17" height="39" />
      <path className="ln s-paper dt" d="M23 15h17M23 21h17M23 27h17M23 33h17M23 39h17M28.6 9v39M34.3 9v39" opacity="0.6" />
      <Sign x={34.5} y={12} w={4} h={13} text="街市" vertical tone="roof" />
      <rect className="f-wall" x="41" y="19" width="15" height="29" />
      <Wins x={43} y={22} cols={3} rows={3} w={2.6} h={3.6} gx={1.6} gy={3} />
      <Awning x={41} y={39} w={15} n={4} h={3} />
      <g className="f-paper ns">
        {range(6).map((i) => <rect key={i} x={13 + i * 6.4} y="52" width="3.4" height="6" rx="0.4" />)}
      </g>
      <StreetLamp x={5} />
      <g>
        <path className="ln" d="M58.5 48V31" style={{ strokeWidth: 1 }} />
        <rect className="f-tile-2" x="55.8" y="22" width="5.4" height="10" rx="1.2" />
        <circle className="f-roof ns" cx="58.5" cy="24.4" r="1.1" />
        <circle className="f-gold ns" cx="58.5" cy="27" r="1.1" />
        <circle className="f-jade ns" cx="58.5" cy="29.6" r="1.1" />
      </g>
    </>
  ),

  shop: () => (
    <>
      <Backdrop far="city" />
      <Shadow rx={23} />
      <rect className="f-wall" x="10" y="24" width="44" height="24" />
      <Sign x={10} y={19} w={44} h={6} text="便利店" tone="jade" size={4.2} />
      <rect className="f-gold ns" x="10.6" y="25" width="42.8" height="1.4" />
      <rect className="f-roof ns" x="10.6" y="26.4" width="42.8" height="1.4" />
      <rect className="f-glass" x="13" y="30" width="38" height="18" />
      <path className="ln" d="M24 30v18M40 30v18M32 32v16" />
      <g className="dt">
        {[[15, "roof"], [17.4, "gold"], [19.8, "jade"], [42, "blue"], [44.4, "roof"], [46.8, "gold"]].map(([x, tone]) => (
          <g key={x}>
            <rect className={`f-${tone} ns`} x={x} y="35" width="1.8" height="2.6" />
            <rect className={`f-${tone} ns`} x={x + 0.4} y="40.4" width="1.8" height="2.6" />
          </g>
        ))}
        <path className="ln" d="M14 38h9M14 43.4h9M41 38h9M41 43.4h9" />
      </g>
      <circle className="f-gold" cx="50" cy="15" r="4" />
      <text className="tx f-roof-2" x="50" y="15.2" fontSize="3.4">24h</text>
    </>
  ),

  internet_cafe: () => (
    <>
      <Backdrop far="city" />
      <Shadow rx={20} />
      <rect className="f-tile" x="13" y="20" width="38" height="28" />
      <rect className="f-screen" x="16" y="23" width="32" height="15" rx="1" />
      <g className="ns">
        <path className="ln s-gold" d="M22 31.6a5 5 0 0 1 7 0M23.6 33.4a2.6 2.6 0 0 1 3.8 0" style={{ strokeWidth: 1.2 }} />
        <circle className="f-gold" cx="25.5" cy="35.2" r="0.9" />
      </g>
      <rect className="f-jade" x="31" y="25.4" width="13" height="4.4" rx="1.6" />
      <rect className="f-paper" x="33" y="31.4" width="12" height="4.4" rx="1.6" />
      <path className="ln s-paper dt" d="M33 27.6h8" />
      <path className="ln dt" d="M35 33.6h7" />
      <Door x={27.5} y={40} w={9} h={8} glass />
      <Sign x={26} y={13} w={12} h={6} text="网吧" tone="screen" />
      <path className="ln dt" d="M45 20v-5M45 15l-2.4-2M45 15l2.4-2" />
    </>
  ),

  detective: () => (
    <>
      <Backdrop far="city" />
      <Shadow rx={17} />
      <rect className="f-stone-2" x="17" y="17" width="28" height="31" />
      <path className="f-tile" d="M15 18L31 9l16 9z" />
      <path className="ln s-stone dt" d="M17 24h28M17 30h28M17 36h28M17 42h28" opacity="0.7" />
      <rect className="f-glass" x="20" y="19" width="22" height="11" rx="0.8" />
      {/* The detective at the window: shoulders, head, a brimmed hat. */}
      <g className="f-ink ns" opacity="0.88">
        <path d="M25.4 30q0-4 5.6-4t5.6 4z" />
        <circle cx="31" cy="24.4" r="2.1" />
        <rect x="26.6" y="22" width="8.8" height="1.1" rx="0.5" />
        <rect x="28.6" y="19.8" width="4.8" height="2.6" rx="0.6" />
      </g>
      <Sign x={24.5} y={32.5} w={13} h={4} text="侦探社" tone="wood" size={2.8} />
      <Door x={27} y={37.5} w={8} h={10.5} tone="roof" />
      <path className="ln" d="M45 25h5v2" style={{ strokeWidth: 1 }} />
      <Magnifier x={51} y={32} r={4} angle={-30} />
      <StreetLamp x={10} h={18} />
    </>
  ),

  sound_plaza: () => (
    <>
      <Backdrop far="city" />
      <ellipse className="f-pave-2 ns" cx="32" cy="50" rx="27" ry="5" />
      <Shadow rx={22} />
      <rect className="f-stone" x="11" y="40" width="42" height="8" />
      <path className="f-roof" d="M13 40Q13 19 32 17Q51 19 51 40z" />
      <path className="f-wall-2" d="M17.5 40Q18 23.5 32 22Q46 23.5 46.5 40z" />
      <path className="ln s-roof-2 dt" d="M21 39Q22 27 32 25.6Q42 27 43 39" />
      <Notes x={26} y={33} s={0.9} tone="roof" />
      <Notes x={34} y={30} s={0.9} tone="jade" />
      {[6, 50].map((x) => (
        <g key={x}>
          <rect className="f-tile-2" x={x} y="30" width="8" height="14" rx="1.2" />
          <circle className="f-stone" cx={x + 4} cy="34" r="2" />
          <circle className="f-stone" cx={x + 4} cy="40" r="2.6" />
        </g>
      ))}
      <path className="ln s-gold dt" d="M4 35q-2 3 0 6M60 35q2 3 0 6" style={{ strokeWidth: 1 }} />
      <g>
        <path className="ln" d="M24 14a8 8 0 0 1 16 0" style={{ strokeWidth: 2.4 }} />
        <path className="ln s-gold" d="M24 14a8 8 0 0 1 16 0" style={{ strokeWidth: 1 }} />
        <rect className="f-gold" x="21.4" y="12" width="4.4" height="6.4" rx="1.8" />
        <rect className="f-gold" x="38.2" y="12" width="4.4" height="6.4" rx="1.8" />
      </g>
    </>
  ),

  passport_office: () => (
    <>
      <Backdrop far="city" />
      <Shadow rx={23} />
      <rect className="f-wall" x="9" y="28" width="46" height="20" />
      <Wins x={11.5} y={31} cols={2} rows={2} w={3} h={4} gx={2} gy={2.6} />
      <Wins x={44.5} y={31} cols={2} rows={2} w={3} h={4} gx={2} gy={2.6} />
      <rect className="f-wall" x="21" y="20" width="22" height="28" />
      <Roof cx={32} y={21} hw={13} h={6} tone="tile" />
      <circle className="f-gold" cx="32" cy="25.6" r="3" />
      <path className="ln s-wood dt" d="M29 25.6h6M32 22.6v6M29.8 23.6q2.2 2 4.4 0M29.8 27.6q2.2 -2 4.4 0" />
      <Sign x={25} y={30} w={14} h={4.6} text="护照" />
      <Columns x={23.4} y={35} h={10} n={4} gap={5.2} w={2} />
      <Steps cx={32} y={48} w={22} />
      <g transform="translate(5 33) rotate(-8)">
        <rect className="f-roof-2" x="0" y="0" width="10" height="13.5" rx="1" />
        <circle className="ln s-gold" cx="5" cy="5.4" r="2.2" style={{ strokeWidth: 0.9 }} />
        <path className="ln s-gold dt" d="M2.6 10h4.8" />
      </g>
      <Flag x={55} y={28} h={10} />
    </>
  ),

  post_office: () => (
    <>
      <Backdrop far="city" />
      <Shadow rx={21} />
      <rect className="f-wall" x="12" y="22" width="40" height="26" />
      <Sign x={12} y={20} w={40} h={6} text="邮局" tone="jade" />
      <rect className="f-gold ns" x="12.6" y="26" width="38.8" height="1.2" />
      {[16, 38].map((x) => (
        <g key={x}>
          <path className="f-glass" d={`M${x} 42v-8a5 5 0 0 1 10 0v8z`} />
          <path className="ln" d={`M${x + 5} 29v13M${x} 36h10`} />
        </g>
      ))}
      <Door x={28} y={34} w={8} h={14} double />
      <g>
        <path className="f-jade" d="M47 48V39a4 4 0 0 1 8 0v9z" />
        <rect className="f-tile-2 ns" x="48.6" y="40" width="4.8" height="1" rx="0.4" />
        <circle className="f-gold" cx="51" cy="44.4" r="1.4" />
      </g>
      <g transform="translate(32 11) rotate(-8)">
        <rect className="f-paper" x="-7" y="-4.4" width="14" height="9" rx="0.8" />
        <path className="ln" d="M-7 -4.2l7 5l7 -5" />
        <rect className="f-roof" x="3" y="-3.4" width="3" height="3.4" />
      </g>
    </>
  ),

  bank: () => (
    <>
      <Backdrop far="city" />
      <Shadow rx={22} />
      <rect className="f-wall" x="13" y="25" width="38" height="20" />
      <rect className="f-wall-2" x="15" y="28" width="34" height="17" />
      <path className="f-stone" d="M10 25.4L32 12.4l22 13z" />
      <path className="f-wall-2 ns" d="M16.4 23.6L32 15l15.6 8.6z" />
      <circle className="f-gold" cx="32" cy="20.2" r="3.4" />
      <rect className="f-gold-2" x="30.6" y="18.8" width="2.8" height="2.8" />
      <rect className="f-stone" x="11.4" y="25" width="41.2" height="3.2" />
      <Columns x={16.4} y={28.2} h={16.8} n={5} gap={7.4} />
      <Sign x={25} y={31.2} w={14} h={4.8} text="银行" />
      <Steps cx={32} y={48.2} w={44} n={2} />
    </>
  ),

  police_station: () => (
    <>
      <Backdrop far="city" />
      <Shadow rx={23} />
      <rect className="f-wall" x="10" y="21" width="44" height="27" />
      <Sign x={10} y={20} w={44} h={6} text="警察" tone="blue" />
      <Wins x={13} y={29} cols={5} rows={1} w={4} h={4.4} gx={4.4} />
      <Door x={14} y={37} w={8} h={11} tone="blue" glass />
      <path className="f-blue" d="M32 7l6 2v4.6q0 4.4-6 6.6q-6-2.2-6-6.6V9z" />
      <Star x={32} y={13} r={2.4} />
      <g>
        <path className="f-paper" d="M27 49v-5.4q0-1.6 1.6-1.8L33 41l3-4.4h12l4 5 4.4 0.6q1.6 0.4 1.6 2V49z" />
        <path className="f-glass" d="M37.6 38h4.8v4h-7.4zM44 38h3.4l3 4H44z" />
        <rect className="f-blue ns" x="27.6" y="44.6" width="29" height="1.8" />
        <rect className="f-roof" x="40" y="34.2" width="3" height="2.2" rx="0.6" />
        <rect className="f-blue" x="43" y="34.2" width="3" height="2.2" rx="0.6" />
        <circle className="f-tile-2" cx="33" cy="49" r="2.8" />
        <circle className="f-tile-2" cx="50" cy="49" r="2.8" />
        <circle className="f-stone ns" cx="33" cy="49" r="1" />
        <circle className="f-stone ns" cx="50" cy="49" r="1" />
      </g>
    </>
  ),

  office: () => (
    <>
      <Backdrop far="city" />
      <Shadow rx={20} />
      <rect className="f-blue" x="17" y="7" width="20" height="41" />
      <path className="ln s-paper dt" d="M17 12h20M17 17h20M17 22h20M17 27h20M17 32h20M17 37h20M17 42h20M23.6 7v41M30.3 7v41" opacity="0.55" />
      <path className="hl dt" d="M19 9l6 0M19 9v10" />
      <rect className="f-wall" x="37" y="19" width="15" height="29" />
      <Wins x={39} y={22} cols={3} rows={4} w={2.6} h={3.2} gx={1.6} gy={2.6} />
      <Sign x={20.5} y={39} w={13} h={4.4} text="公司" tone="screen" />
      <Door x={23.5} y={43.6} w={7} h={4.4} glass />
      <g>
        <path className="ln" d="M8.6 39v-2h5v2" />
        <rect className="f-wood" x="5" y="39" width="12" height="9" rx="1.2" />
        <rect className="f-gold ns" x="10" y="41.6" width="2" height="1.6" />
        <path className="ln dt" d="M5 42.4h12" />
      </g>
    </>
  ),

  // -------------------------------------------------------------- health
  hospital: () => (
    <>
      <Backdrop far="city" />
      <Shadow rx={23} />
      <rect className="f-paper" x="9" y="22" width="46" height="26" />
      <Wins x={12} y={30} cols={2} rows={2} w={3.4} h={4} gx={2} gy={2.6} />
      <Wins x={43.2} y={30} cols={2} rows={2} w={3.4} h={4} gx={2} gy={2.6} />
      <Sign x={21} y={24} w={22} h={5} text="医院" tone="paper" />
      <rect className="f-paper" x="25" y="6" width="14" height="14" rx="2" />
      <path className="f-roof" d="M30 8.6h4v3.8h3.8v4H34v3.8h-4v-3.8h-3.8v-4H30z" transform="translate(0 -1.4)" />
      <rect className="f-blue" x="22" y="34" width="20" height="3" rx="0.6" />
      <path className="ln" d="M24 37v11M40 37v11" />
      <Door x={27} y={38} w={10} h={10} tone="glass" double />
      <Bush x={5} r={3} />
      <Bush x={56} r={3} />
    </>
  ),

  pharmacy: () => (
    <>
      <Backdrop far="city" />
      <Shadow rx={20} />
      <rect className="f-wall" x="13" y="22" width="36" height="26" />
      <Sign x={13} y={20} w={36} h={6} text="药店" tone="jade" />
      <rect className="f-glass" x="16" y="30" width="18" height="13" />
      <path className="ln" d="M16 37h18" />
      <g className="dt">
        <rect className="f-jade" x="18" y="32.6" width="3" height="4.4" rx="0.6" />
        <rect className="f-paper ns" x="18.2" y="31.6" width="2.6" height="1.2" />
        <rect className="f-gold" x="23" y="33.4" width="3" height="3.6" rx="0.6" />
        <rect className="f-roof" x="28" y="32" width="3.4" height="5" rx="0.6" />
      </g>
      <g transform="translate(25 40) rotate(-20)">
        <rect className="f-paper" x="-4.4" y="-1.5" width="8.8" height="3" rx="1.5" />
        <path className="f-roof" d="M0 -1.5h2.9a1.5 1.5 0 0 1 0 3H0z" />
      </g>
      <Door x={37.5} y={30} w={9} h={18} glass />
      <path className="ln" d="M49 17h5v3" style={{ strokeWidth: 1 }} />
      <rect className="f-jade" x="49.6" y="20" width="9" height="9" rx="1.6" />
      <path className="f-paper ns" d="M53 21.4h2.2v2.2h2.2v2.2h-2.2V28H53v-2.2h-2.2v-2.2H53z" />
    </>
  ),

  // ----------------------------------------------------------- transport
  metro: () => (
    <>
      <Backdrop far="city" />
      <Shadow rx={22} />
      <rect className="f-tile-2" x="15" y="33" width="34" height="15" />
      {/* Stairs going down: side walls closing in, steps narrowing, rails. */}
      <path className="f-stone-2 ns" d="M15 34L23 48H15zM49 34L41 48H49z" />
      <path className="ln s-paper" opacity="0.75"
            d={range(4).map((i) => {
              const y = 37 + i * 3;
              const inset = ((y - 34) / 14) * 8;
              return `M${15 + inset} ${y}H${49 - inset}`;
            }).join("")} />
      <path className="ln s-gold" d="M17.4 33.6L24.6 46M46.6 33.6L39.4 46" style={{ strokeWidth: 1 }} />
      <path className="f-stone" d="M12 34h4v14h-4zM48 34h4v14h-4z" />
      <path className="f-glass" d="M11 34Q32 18 53 34z" opacity="0.92" />
      <path className="ln" d="M11 34Q32 18 53 34M22 27.6V34M32 24.6V34M42 27.6V34" />
      <path className="hl dt" d="M18 29.6q6-4 12-5" />
      <rect className="f-stone" x="10" y="33.4" width="44" height="2" />
      <path className="ln" d="M10.5 48V18" style={{ strokeWidth: 1.2 }} />
      <rect className="f-blue" x="5" y="7" width="11" height="13" rx="1.6" />
      <text className="tx f-paper" x="10.5" y="10.8" fontSize="4.4">地</text>
      <text className="tx f-paper" x="10.5" y="16.2" fontSize="4.4">铁</text>
    </>
  ),

  train_station: () => (
    <>
      <Backdrop far="hills" />
      <rect className="f-wall" x="9" y="20" width="46" height="22" />
      {[12, 43].map((x) => <path key={x} className="f-glass" d={`M${x} 36v-7a4.5 4.5 0 0 1 9 0v7z`} />)}
      <rect className="f-wall" x="25" y="11" width="14" height="31" />
      <path className="f-roof" d="M23.5 12L32 6l8.5 6z" />
      <circle className="f-paper" cx="32" cy="16.4" r="4" />
      <path className="ln" d="M32 14.2v2.2l1.8 1" />
      <Sign x={21} y={22.6} w={22} h={5} text="火车站" />
      <rect className="f-stone ns" x="0" y="46" width="64" height="2" />
      <g>
        <path className="f-paper" d="M-2 38H44Q55.5 39 59 47.4H-2z" />
        <path className="f-blue ns" d="M-2 44H55.6Q57.4 45.4 58.2 46.4H-2z" />
        <path className="f-glass" d="M47 39.6q5 1 8.4 4H47z" />
        {range(5).map((i) => <rect key={i} className="f-glass" x={2 + i * 8.6} y="40.2" width="5.6" height="2.6" rx="0.6" />)}
        <path className="ln" d="M-2 47.4H59" />
      </g>
    </>
  ),

  bus_station: () => (
    <>
      <Backdrop far="city" />
      <Shadow cx={30} rx={24} />
      <g>
        <rect className="f-jade" x="40" y="17" width="20" height="2.6" rx="0.6" />
        <path className="ln" d="M42 19.6V48M58 19.6V48" />
        <rect className="f-glass" x="44" y="22" width="12" height="15" opacity="0.8" />
        <Sign x={44} y={11.6} w={12} h={4.8} text="公交" tone="jade" />
      </g>
      <g>
        <rect className="f-jade" x="5" y="23" width="44" height="21" rx="3.2" />
        <rect className="f-paper ns" x="5.6" y="36" width="42.8" height="5" />
        <rect className="f-screen" x="10" y="24.6" width="14" height="3" rx="0.6" />
        <text className="tx f-gold" x="17" y="26.2" fontSize="2.4">12路</text>
        {range(4).map((i) => <Win key={i} x={10 + i * 9} y={29} w={7.4} h={6} />)}
        <path className="f-glass" d="M5.4 27h2.6v9H5.4z" />
        <path className="ln" d="M5 36h44" />
        <rect className="f-gold ns" x="5.4" y="39.6" width="3" height="1.6" rx="0.6" />
        <circle className="f-tile-2" cx="15" cy="44.4" r="3.6" />
        <circle className="f-tile-2" cx="40" cy="44.4" r="3.6" />
        <circle className="f-stone ns" cx="15" cy="44.4" r="1.3" />
        <circle className="f-stone ns" cx="40" cy="44.4" r="1.3" />
      </g>
    </>
  ),

  airport: () => (
    <>
      <Backdrop far="none" clouds={false} />
      <Shadow rx={25} />
      <path className="f-paper" d="M6 36Q19 25 33 31Q46 36 58 28V37H6z" />
      <rect className="f-glass" x="7" y="36.4" width="50" height="11.6" />
      <path className="ln" d="M7 36.4h50M14 36.4v11.6M21 36.4v11.6M28 36.4v11.6M35 36.4v11.6M42 36.4v11.6M49 36.4v11.6" />
      <Sign x={36} y={29.6} w={14} h={4.4} text="机场" tone="blue" />
      <rect className="f-stone" x="10" y="17" width="4" height="19" />
      <path className="f-glass" d="M7 12h10l-1.4 5.4H8.4z" />
      <path className="f-tile" d="M8 11.4h8l-1-2h-6z" />
      <g transform="translate(40 14) rotate(-14)">
        <path className="f-paper" d="M-11 0q0-1.8 2-1.8h15l5 1.8l-5 1.8h-15q-2 0-2-1.8z" />
        <path className="f-blue" d="M-2 0l-4.6 7h2.6l6-7zM-2 -0.2l-3.6-5h2.2l4.6 5z" />
        <path className="f-roof" d="M-9.6 -1.6l-2.4-4.2h2l3.4 4.2z" />
        <path className="ln dt" d="M-6 0h8" />
      </g>
      <path className="ln s-paper dt" d="M24 21h-8M22 23.6h-6" opacity="0.8" />
    </>
  ),

  hotel: () => (
    <>
      <Backdrop far="city" />
      <Shadow rx={20} />
      <rect className="f-wall" x="16" y="11" width="32" height="37" />
      <rect className="f-wall-2 ns" x="16.6" y="11.6" width="30.8" height="2" />
      <Wins x={19.4} y={16} cols={4} rows={3} w={4} h={4.4} gx={3} gy={2.8} />
      <Sign x={21} y={5} w={22} h={6} text="酒店" />
      {[27.5, 30.5, 33.5, 36.5].map((x) => <Star key={x} x={x} y={13.6} r={1.1} />)}
      <rect className="f-roof" x="21" y="37" width="22" height="2.8" rx="0.6" />
      <path className="ln" d="M22.6 39.8V48M41.4 39.8V48" />
      <Door x={27} y={40} w={10} h={8} tone="glass" double />
      <Pot x={13} />
      <Pot x={51} />
    </>
  ),

  // ----------------------------------------------------------- riverside
  park: () => (
    <>
      <Backdrop far="hills" ground="grass" />
      <path className="f-pave-2 ns" d="M24 64Q28 54 37 50.5Q43 48.5 52 48l2 1.6Q45 50 40 52.4Q33 56 32 64z" />
      <ellipse className="f-water" cx="51" cy="56" rx="9" ry="3.6" />
      <Shadow cx={21} rx={11} />
      <path className="f-wood" d="M19.6 48q1.4-7-1.6-13l2.6-1q2.4 5 1.8 7q1.6-4 5-6l1.2 1.6q-4 3-4.2 6q-0.4 2.4 0.2 5.4z" />
      <circle className="f-pink" cx="20" cy="24" r="8" />
      <circle className="f-pink" cx="11.6" cy="30" r="5.4" />
      <circle className="f-pink" cx="29" cy="29" r="6" />
      <circle className="f-pink-2 ns" cx="24" cy="30" r="5" opacity="0.55" />
      <circle className="f-pink-2 ns" cx="13" cy="32" r="2.6" opacity="0.55" />
      <g className="f-paper ns dt">
        <circle cx="17" cy="21" r="0.8" /><circle cx="24" cy="25" r="0.8" /><circle cx="13" cy="28" r="0.7" />
        <circle cx="29" cy="27" r="0.7" /><circle cx="21" cy="29" r="0.7" />
      </g>
      <g className="f-pink ns dt">
        <circle cx="35" cy="34" r="0.8" /><circle cx="31" cy="40" r="0.7" /><circle cx="38" cy="41" r="0.6" />
      </g>
      <g>
        <rect className="f-wood" x="36" y="38" width="18" height="2" rx="0.6" />
        <rect className="f-wood" x="36" y="41.2" width="18" height="2" rx="0.6" />
        <path className="ln" d="M38 43.2v4.4M52 43.2v4.4M38 40v1.2M52 40v1.2" style={{ strokeWidth: 1.1 }} />
      </g>
      <Bush x={58} y={47} r={2.6} />
    </>
  ),

  riverside: () => (
    <>
      <Backdrop far="hills" ground="water" />
      <path className="f-grass" d="M0 46h12q-3 9-12 12zM64 46H52q3 9 12 12z" />
      <path className="f-stone" d="M2 47Q32 18 62 47v2.6H52Q32 28 12 49.6H2z" />
      <path className="ln s-stone dt" d="M7 42.6l3 2.6M57 42.6l-3 2.6M17 34.2l2 3M47 34.2l-2 3M27 29.6l0.8 3.4M37 29.6l-0.8 3.4" />
      <path className="ln" d="M4 44.6Q32 16 60 44.6" />
      {range(9).map((i) => {
        const x = 9 + i * 5.75;
        // The rail is a parabola (a symmetric quadratic curve) peaking at 30.3.
        const y = 44.6 - 14.3 * (1 - ((x - 32) / 28) ** 2);
        return <path key={i} className="ln" d={`M${x} ${y}v2.2`} style={{ strokeWidth: 0.9 }} />;
      })}
      <path className="ln s-water dt" d="M14 55Q32 42 50 55" style={{ strokeWidth: 1.1 }} opacity="0.8" />
      <g>
        <path className="f-wood" d="M5.4 46.4V30h1.6v16.4z" />
        <circle className="f-leaf" cx="6.2" cy="28" r="5" />
        <path className="ln s-leaf" d="M2.6 29q-1 7 0 12M5 31v11M8 31q1 6 0 10M10.4 29q1.4 6 0.4 10" style={{ strokeWidth: 0.9 }} />
      </g>
    </>
  ),

  sports_center: () => (
    <>
      <Backdrop far="city" />
      <Shadow rx={25} />
      <path className="f-paper" d="M7 48V35Q32 8 57 35v13z" />
      <path className="ln s-stone dt" d="M15 25.6Q20 32 20 48M32 21.4V48M49 25.6Q44 32 44 48" />
      <rect className="f-glass" x="7.6" y="38" width="48.8" height="6" />
      <path className="ln" d="M7 38h50M7 44h50" />
      <Sign x={22} y={39} w={20} h={4.6} text="体育馆" tone="jade" size={3.2} />
      <g transform="translate(32 24) rotate(-25)">
        <path className="f-paper" d="M-2.2 -1.4L-6 -9.6h12L2.2 -1.4z" />
        <path className="ln dt" d="M-4.4 -8.8l2.6 7M0 -9.6v8M4.4 -8.8l-2.6 7M-5 -6h10" />
        <path className="f-roof" d="M-2.6 -1.6h5.2v1.6a2.6 2.6 0 0 1 -5.2 0z" />
      </g>
      <Flag x={57} y={33} h={8} tone="jade" />
    </>
  ),

  bamboo_garden: () => (
    <>
      <Backdrop far="hills" ground="grass" />
      <rect className="f-wall" x="3" y="27" width="58" height="21" />
      <rect className="f-tile" x="1.6" y="24.4" width="60.8" height="3.4" rx="0.8" />
      <path className="ln s-tile dt" d="M5 24.6v3M9 24.6v3M13 24.6v3M17 24.6v3M47 24.6v3M51 24.6v3M55 24.6v3M59 24.6v3" />
      {/* Through the moon gate: the garden beyond, a path and a small tree. */}
      <circle className="f-sky-2" cx="32" cy="38.6" r="9" />
      <path className="f-grass ns" d="M23.2 40.4h17.6a9 9 0 0 1 -17.6 0z" />
      <path className="f-pave-2 ns" d="M30.6 40.4h2.8l2 7.2h-6.8z" />
      <circle className="f-leaf ns" cx="36.6" cy="35.4" r="3" />
      <rect className="f-wood ns" x="36.1" y="37.4" width="1" height="3" />
      <circle className="ln" cx="32" cy="38.6" r="9" style={{ strokeWidth: 1.6 }} />
      <circle className="ln s-tile dt" cx="32" cy="38.6" r="10.2" />
      {[[8, 7, 0.4], [12, 6, -0.3], [15.6, 9, 0.2], [49, 8, 0.3], [53, 5, -0.4]].map(([x, top, lean], i) => (
        <g key={i}>
          <path className="ln s-jade" d={`M${x} 49L${x + lean * 6} ${top}`} style={{ strokeWidth: 2.4 }} />
          <path className="ln s-jade" d={`M${x} 49L${x + lean * 6} ${top}`} style={{ strokeWidth: 1, stroke: "var(--art-jade)" }} />
          <path className="ln s-leaf dt" d={`M${x + lean * 2} ${top + 26}h1.6M${x + lean * 4} ${top + 14}h1.6`} />
          <path className="f-leaf ns" d={`M${x + lean * 6} ${top + 4}q4 -2 6 -1q-3 2 -6 1zM${x + lean * 4.4} ${top + 12}q-4 -1.6 -6 -0.4q3 1.8 6 0.4z`} />
        </g>
      ))}
      <g>
        <rect className="f-stone" x="54" y="43" width="5" height="5" />
        <rect className="f-stone" x="53" y="39.4" width="7" height="3.6" />
        <rect className="f-glass ns" x="55.2" y="40.2" width="2.6" height="2" />
        <path className="f-stone" d="M52.6 39.4l3.9 -2.6l3.9 2.6z" />
      </g>
    </>
  ),

  // ---------------------------------------------------------------- food
  restaurant: () => (
    <>
      <Backdrop far="city" />
      <Shadow rx={23} />
      <rect className="f-wall" x="11" y="27" width="42" height="21" />
      <rect className="f-roof" x="11" y="27" width="3" height="21" />
      <rect className="f-roof" x="50" y="27" width="3" height="21" />
      {[16.5, 38].map((x) => (
        <g key={x}>
          <rect className="f-glass" x={x} y="32" width="9.5" height="9" />
          <path className="ln s-wood" d={`M${x} 35h9.5M${x} 38h9.5M${x + 3.2} 32v9M${x + 6.3} 32v9`} style={{ strokeWidth: 0.9 }} />
        </g>
      ))}
      <Door x={28} y={35} w={8} h={13} double />
      <Roof cx={32} y={28} hw={22} h={9} />
      <Sign x={25} y={29.4} w={14} h={4.6} text="饭馆" tone="wood" />
      <Lantern x={18} y={28.4} />
      <Lantern x={46} y={28.4} />
      <g>
        <path className="ln s-wood" d="M35 4.6l-6 8M38 5.4l-7.6 7" style={{ strokeWidth: 1.1 }} />
        <path className="f-paper" d="M24 12h16a8 6 0 0 1 -16 0z" />
        <path className="f-roof ns" d="M24.6 14h14.8l-0.6 1.4H25.2z" />
        <path className="ln s-gold" d="M26.6 12q1.6-2 3 0t3 0t3 0t3 0" style={{ strokeWidth: 0.9 }} />
      </g>
    </>
  ),

  food_street: () => (
    <>
      <Backdrop far="city" />
      <path className="ln" d="M2 9Q32 18 62 9" style={{ strokeWidth: 0.8 }} />
      <Lantern x={12} y={11.6} s={0.8} />
      <Lantern x={25} y={13.8} s={0.8} />
      <Lantern x={39} y={13.8} s={0.8} />
      <Lantern x={52} y={11.6} s={0.8} />
      <Shadow rx={26} />
      <g>
        <path className="ln" d="M7 26v22M29 26v22" />
        <Awning x={5} y={22} w={26} n={6} h={4} />
        <rect className="f-wood" x="6" y="36" width="24" height="12" />
        <Sign x={10.5} y={38.6} w={15} h={4.6} text="小吃" />
        {[[10, 28.6], [10, 32], [20, 30.4], [20, 33.6]].map(([x, y]) => (
          <g key={`${x}${y}`}>
            <rect className="f-gold-2" x={x} y={y} width="7" height="3.4" rx="1" />
            <path className="ln s-wood dt" d={`M${x} ${y + 1.6}h7`} />
          </g>
        ))}
        <path className="ln dt" d="M12 26.6q-1-1.4 0-2.6M15 26.6q-1-1.4 0-2.6M23 28.4q-1-1.4 0-2.6" opacity="0.7" />
      </g>
      <g>
        <path className="ln" d="M36 26v22M58 26v22" />
        <Awning x={34} y={22} w={26} n={6} h={4} a="jade" />
        <rect className="f-wood" x="35" y="36" width="24" height="12" />
        {[40, 45, 50, 55].map((x) => (
          <g key={x}>
            <path className="ln s-wood" d={`M${x} 37V27`} style={{ strokeWidth: 0.8 }} />
            <circle className="f-roof" cx={x} cy="28.6" r="1.4" />
            <circle className="f-roof" cx={x} cy="31.2" r="1.4" />
            <circle className="f-roof" cx={x} cy="33.8" r="1.4" />
          </g>
        ))}
        <path className="ln dt" d="M38 42h18" />
      </g>
    </>
  ),

  market: () => (
    <>
      <Backdrop far="city" />
      <Shadow rx={25} />
      <path className="f-jade" d="M4 26L32 11l28 15z" />
      <path className="ln s-jade dt" d="M10 23h44" opacity="0.6" />
      <path className="ln" d="M7 26v22M57 26v22" />
      <Sign x={21} y={17.2} w={22} h={5} text="菜市场" size={3.4} />
      <rect className="f-wood" x="5" y="37" width="54" height="3.4" />
      <path className="ln" d="M9 40.4V48M55 40.4V48" />
      {[[8, "leaf"], [24, "gold-2"], [40, "roof"]].map(([x, tone]) => (
        <g key={x}>
          <rect className="f-wood" x={x} y="31" width="15" height="6" />
          <path className="ln s-wood dt" d={`M${x} 34h15`} />
          {tone === "gold-2"
            ? [0, 3.4, 6.8, 10.2].map((d) => (
              <g key={d}>
                <path className="f-gold-2" d={`M${x + 1.4 + d} 31.4l1.2 -5l1.2 5z`} />
                <path className="ln s-leaf" d={`M${x + 2.6 + d} 26.4l-0.8 -1.4M${x + 2.6 + d} 26.4l0.8 -1.4`} />
              </g>
            ))
            : [2.4, 6.4, 10.4].map((d, i) => (
              <circle key={d} className={`f-${tone}`} cx={x + d + 1} cy={30.4 - (i === 1 ? 1 : 0)} r={tone === "leaf" ? 2.6 : 2.1} />
            ))}
        </g>
      ))}
      <g className="dt">
        <ellipse className="f-gold-2" cx="14" cy="47" rx="4" ry="1.6" />
        <path className="f-wood" d="M10 47q4 4 8 0" />
        <circle className="f-leaf" cx="47" cy="45.6" r="2" />
        <circle className="f-roof" cx="51" cy="46" r="1.7" />
      </g>
    </>
  ),

  // ------------------------------------------------------------- culture
  tea_house: () => (
    <>
      <Backdrop far="hills" ground="grass" />
      <Shadow rx={22} />
      <rect className="f-wood" x="14" y="34" width="36" height="14" />
      {[16.5, 40].map((x) => (
        <g key={x}>
          <rect className="f-glass" x={x} y="37" width="7.5" height="7" />
          <path className="ln s-wood" d={`M${x + 3.75} 37v7M${x} 40.5h7.5`} style={{ strokeWidth: 0.9 }} />
        </g>
      ))}
      <Door x={28} y={37} w={8} h={11} tone="roof" double />
      <Roof cx={32} y={35} hw={20} h={7} />
      <rect className="f-wall" x="20" y="21" width="24" height="10" />
      <Win x={23} y={23.4} w={5} h={5} />
      <Win x={36} y={23.4} w={5} h={5} />
      <Sign x={29.4} y={22.6} w={5.2} h={6.4} text="茶" size={4.2} />
      <Roof cx={32} y={22} hw={14} h={7} />
      <Lantern x={15} y={33.6} s={0.85} />
      <Lantern x={49} y={33.6} s={0.85} />
      <g>
        <path className="ln s-wood" d="M6 48V8" style={{ strokeWidth: 1.2 }} />
        <path className="f-roof" d="M6.6 9h7v15l-3.5 -2l-3.5 2z" />
        <text className="tx f-gold" x="10.1" y="15" fontSize="5">茶</text>
      </g>
    </>
  ),

  calligraphy: () => (
    <>
      <Backdrop far="hills" ground="grass" />
      <Shadow rx={22} />
      <rect className="f-wall" x="10" y="22" width="44" height="26" />
      <Roof cx={32} y={23} hw={23} h={8} tone="tile" />
      <rect className="f-wood-2" x="21" y="23.4" width="22" height="1.8" rx="0.8" />
      <rect className="f-paper" x="22.4" y="25" width="19.2" height="19" />
      <rect className="f-roof ns dt" x="23.6" y="26.2" width="16.8" height="16.6" opacity="0.08" />
      <text className="tx f-ink" x="32" y="34.6" fontSize="12.5" style={{ fontWeight: 600 }}>永</text>
      <rect className="f-roof ns" x="37.4" y="39.6" width="2.6" height="2.6" rx="0.4" />
      <rect className="f-wood-2" x="21" y="43.8" width="22" height="1.8" rx="0.8" />
      <g transform="translate(50 30) rotate(18)">
        <rect className="f-wood" x="-1.2" y="-14" width="2.4" height="16" rx="1" />
        <rect className="f-gold" x="-1.4" y="-15" width="2.8" height="1.6" rx="0.6" />
        <path className="f-ink" d="M-1.6 2h3.2q0 4.6 -1.6 7q-1.6 -2.4 -1.6 -7z" />
      </g>
      <g>
        <rect className="f-tile-2" x="9" y="44.6" width="9" height="3.4" rx="1" />
        <ellipse className="f-ink ns" cx="13.5" cy="46" rx="2.8" ry="0.9" />
      </g>
    </>
  ),

  museum: () => (
    <>
      <Backdrop far="hills" />
      <Shadow rx={26} />
      <rect className="f-stone" x="5" y="41" width="54" height="7" />
      <rect className="f-stone-2" x="25" y="41" width="14" height="7" />
      <path className="ln s-stone" d="M25 43.4h14M25 45.8h14" />
      <rect className="f-roof" x="12" y="28" width="40" height="13" />
      <Columns x={13.6} y={30} h={11} n={6} gap={7.2} w={1.6} tone="roof-2" />
      <Sign x={23.5} y={31.4} w={17} h={4.8} text="博物馆" tone="wood" size={3.2} />
      <Roof cx={32} y={29} hw={24} h={10} tone="gold" />
      <g>
        <path className="f-jade-2" d="M5 33.4h9l-1 5.4h-7z" />
        <path className="ln" d="M7 38.8l-0.8 2.4M9.5 38.8v2.4M12 38.8l0.8 2.4" />
        <path className="ln" d="M6 33.4q0-2.6 1.6-2.6M13 33.4q0-2.6 -1.6-2.6" />
        <path className="ln s-gold dt" d="M6.4 35.6h7.2" />
      </g>
    </>
  ),

  temple: () => (
    <>
      <Backdrop far="hills" ground="grass" />
      <Shadow rx={18} />
      <path className="ln s-gold" d="M32 14V4.6" style={{ strokeWidth: 1.2 }} />
      <g className="f-gold">
        <ellipse cx="32" cy="11.4" rx="2.2" ry="0.7" />
        <ellipse cx="32" cy="9" rx="1.7" ry="0.6" />
        <ellipse cx="32" cy="6.8" rx="1.2" ry="0.5" />
        <circle cx="32" cy="4.2" r="1" />
      </g>
      <rect className="f-roof" x="23" y="38" width="18" height="10" />
      <Door x={29} y={41} w={6} h={7} tone="wood" />
      <Roof cx={32} y={38.6} hw={13} h={5} />
      <rect className="f-roof" x="25.4" y="29" width="13.2" height="7" />
      <Win x={30} y={30.6} w={4} h={4} />
      <Roof cx={32} y={29.6} hw={10} h={5} />
      <rect className="f-roof" x="27.4" y="20.6" width="9.2" height="6" />
      <Win x={30.6} y={21.8} w={2.8} h={3.4} />
      <Roof cx={32} y={21} hw={7} h={5} />
      <g>
        <path className="f-gold-2" d="M9 41h8l-1.2 4h-5.6z" />
        <path className="ln" d="M10 45l-0.6 3M16 45l0.6 3M13 45v3" />
        <path className="ln s-stone dt" d="M11.4 40q-1.6-3 0-5.4t0-5M14.4 40q1.4-2.6 0-5" />
      </g>
      <Tree x={53} r={4.4} tone="leaf" />
    </>
  ),

  hutong: () => (
    <>
      <Backdrop far="none" />
      <path className="f-pave-2 ns" d="M28 46h8l6 18H22z" />
      <rect className="f-stone" x="3" y="27" width="26" height="21" />
      <path className="ln s-stone dt" d="M3 31h26M3 35h26M3 39h26M3 43h26M8 27v4M18 27v4M13 31v4M23 31v4M8 35v4M18 35v4" opacity="0.8" />
      <rect className="f-tile" x="1.6" y="24.6" width="28.8" height="3" rx="0.6" />
      <rect className="f-wood" x="10" y="31" width="12" height="17" />
      <Door x={11.4} y={34} w={9.2} h={14} tone="roof" double studs />
      <Roof cx={16} y={31.4} hw={7.4} h={4} tone="tile" />
      <rect className="f-roof ns" x="8" y="34" width="1.6" height="10" />
      <rect className="f-roof ns" x="22.4" y="34" width="1.6" height="10" />
      <rect className="f-stone" x="36" y="29" width="25" height="19" />
      <path className="ln s-stone dt" d="M36 33h25M36 37h25M36 41h25M36 45h25M41 29v4M51 29v4M46 33v4M56 33v4" opacity="0.8" />
      <rect className="f-tile" x="34.6" y="26.6" width="27.8" height="3" rx="0.6" />
      <circle className="f-leaf" cx="52" cy="21" r="6" />
      <circle className="f-leaf-2 ns" cx="54" cy="23" r="3" opacity="0.6" />
      <g>
        <circle className="ln" cx="40" cy="45" r="3.2" style={{ strokeWidth: 1.1 }} />
        <circle className="ln" cx="51" cy="45" r="3.2" style={{ strokeWidth: 1.1 }} />
        <path className="ln s-roof" d="M40 45l4-6h6l1 6M44 39l1.6 6h-5.6M49.6 37.6h2.6M43.2 37.6h2" style={{ strokeWidth: 1.2 }} />
      </g>
    </>
  ),

  old_town: () => (
    <>
      <Backdrop far="hills" ground="water" />
      <WaterHouse x={29} y={22} w={30} h={24} />
      <WaterHouse x={5} y={27} w={24} h={19} />
      <Win x={9} y={31} w={5} h={5} tone="glass" />
      <Win x={19} y={31} w={5} h={5} tone="glass" />
      <Win x={33} y={27} w={5} h={6} />
      <Win x={50} y={27} w={5} h={6} />
      <Door x={40.5} y={33} w={7} h={13} />
      <Lantern x={40} y={22.6} s={0.75} />
      <Lantern x={48} y={22.6} s={0.75} />
      <rect className="f-stone" x="3" y="45" width="58" height="2.6" />
      <g>
        <path className="f-wood-2" d="M16 52h30q-2 4.4 -8 4.4H23q-5 0 -7 -4.4z" />
        <path className="f-tile-2" d="M24 52v-2.4a7 4 0 0 1 13 0V52z" />
        <path className="ln s-wood" d="M46 51.4l7 -7" style={{ strokeWidth: 1 }} />
      </g>
      <path className="ln s-water dt" d="M12 59h9M40 60h12" />
    </>
  ),

  // ------------------------------------------------------------ shopping
  shopping_district: () => (
    <>
      <Backdrop far="none" />
      <path className="f-pave-2 ns" d="M24 64L29 30h6l5 34z" />
      {[[10, "jade"], [42, "roof"]].map(([x, tone]) => (
        <g key={x}>
          <rect className="f-wall" x={x} y="28" width="12" height="20" />
          <Awning x={x} y={33} w={12} n={4} h={3} a={tone} />
          <rect className="f-glass" x={x + 2} y="38.6" width="8" height="7" />
        </g>
      ))}
      <rect className="f-roof" x="6" y="20" width="3.4" height="28" />
      <rect className="f-roof" x="54.6" y="20" width="3.4" height="28" />
      <rect className="f-roof-2" x="6" y="20" width="52" height="2.4" />
      <Roof cx={32} y={17} hw={24} h={6} tone="tile" />
      <Sign x={20} y={17.4} w={24} h={5} text="步行街" tone="wood" size={3.4} />
      <g>
        <path className="f-roof" d="M24 40h8l-0.6 8.4h-6.8z" />
        <path className="ln" d="M26 40v-1.6a2 2 0 0 1 4 0V40" />
        <path className="f-gold" d="M31 42h7.6l-0.6 6.4h-6.4z" />
        <path className="ln" d="M33 42v-1.4a1.8 1.8 0 0 1 3.6 0V42" />
      </g>
    </>
  ),

  mall: () => (
    <>
      <Backdrop far="city" />
      <Shadow rx={25} />
      <rect className="f-wall" x="7" y="17" width="50" height="31" />
      <rect className="f-glass" x="19" y="20" width="26" height="28" />
      <path className="ln" d="M19 27h26M19 34h26M19 41h26M28 20v28M36 20v28" opacity="0.7" />
      <path className="ln s-paper dt" d="M21 46l7-6M30 39l6-5" style={{ strokeWidth: 1 }} />
      <Sign x={21} y={10} w={22} h={6} text="商场" />
      {[[10, "roof"], [47.6, "gold"]].map(([x, tone]) => (
        <g key={x}>
          <rect className={`f-${tone}`} x={x} y="21" width="6.4" height="16" rx="0.6" />
          <path className="ln s-paper dt" d={`M${x + 1.6} 25h3.2M${x + 1.6} 28h3.2M${x + 1.6} 31h3.2`} />
        </g>
      ))}
      <Door x={27} y={42} w={10} h={6} tone="glass" double />
      <Pot x={13} />
      <Pot x={51} />
    </>
  ),

  cinema: () => (
    <>
      <Backdrop far="city" />
      <Shadow rx={23} />
      <rect className="f-roof-2" x="9" y="19" width="46" height="29" />
      <rect className="f-paper" x="12" y="24" width="40" height="8.6" rx="1" />
      <text className="tx f-roof" x="32" y="28.4" fontSize="4.6">电影院</text>
      <g className="f-gold ns dt">
        {range(11).map((i) => <circle key={`t${i}`} cx={13.6 + i * 3.68} cy="22.6" r="0.6" />)}
        {range(11).map((i) => <circle key={`b${i}`} cx={13.6 + i * 3.68} cy="34" r="0.6" />)}
      </g>
      {[13, 43].map((x, i) => (
        <g key={x}>
          <rect className="f-wood-2" x={x} y="36" width="8" height="11" />
          <rect className={`f-${i ? "jade" : "blue"} ns`} x={x + 1} y="37" width="6" height="9" />
          <circle className="f-gold ns" cx={x + 4} cy="40" r="1.6" />
        </g>
      ))}
      <Door x={26} y={36} w={12} h={12} tone="glass" double />
      <g transform="translate(32 11)">
        <rect className="f-tile-2" x="-8" y="-1.6" width="16" height="8" rx="0.8" />
        <path className="f-tile-2" d="M-8 -2.4l15 -4.6l0.8 2.4l-15 4.6z" />
        <path className="f-paper ns" d="M-5 -3.4l2.6 -0.8l-1 2.6l-2.6 0.8zM0.4 -5l2.6 -0.8l-1 2.6l-2.6 0.8z" />
        <path className="ln s-paper dt" d="M-5.6 1.6h11.2M-5.6 3.6h7" />
      </g>
    </>
  ),

  ktv: () => (
    <>
      <Backdrop far="city" />
      <Shadow rx={21} />
      <rect className="f-blue-2" x="12" y="16" width="40" height="32" />
      <rect className="f-screen" x="15" y="19" width="34" height="11.6" rx="1.6" />
      <text className="tx f-pink" x="32" y="25" fontSize="8.4" style={{ letterSpacing: "0.6px" }}>KTV</text>
      <rect className="ln s-pink dt" x="16.4" y="20.4" width="31.2" height="8.8" rx="1" />
      <Wins x={15} y={33} cols={4} rows={1} w={5.4} h={4} gx={4.2} tone="pink" />
      <Door x={27.5} y={39} w={9} h={9} tone="glass" double />
      <g transform="translate(55 32) rotate(18)">
        <rect className="f-tile-2" x="-1.4" y="0" width="2.8" height="11" rx="1.2" />
        <circle className="f-stone" cx="0" cy="-2.4" r="3.4" />
        <path className="ln s-stone dt" d="M-2.4 -2.4h4.8M0 -4.8v4.8" />
      </g>
      <Notes x={5} y={22} s={1} tone="pink" />
      <Notes x={50} y={10} s={0.8} tone="gold" />
    </>
  ),
};

// Any place without its own painting yet: a city building with a sign-less
// facade, so the map never falls back to an emoji.
export function building() {
  return (
    <>
      <Backdrop far="city" />
      <Shadow rx={18} />
      <rect className="f-wall" x="16" y="22" width="32" height="26" />
      <Roof cx={32} y={23} hw={17} h={7} />
      <Wins x={19.4} y={28} cols={4} rows={2} w={3.6} h={4} gx={3.2} gy={3} />
      <Door x={28} y={39} w={8} h={9} double />
    </>
  );
}
