---
name: chineseverse-frontend-design
description: The ChineseVerse "Ink & Jade" frontend design system — layout widths, page shapes, spacing, typography, color/theme tokens, cards, buttons, forms, navigation, icons, motion, breakpoints, accessibility and the World map's rules. Use automatically whenever creating, editing, fixing or reviewing anything visual in frontend/ — React pages or components (frontend/src/pages, frontend/src/components), frontend/src/index.css, responsive/mobile layout, animations, hover/focus states, UI redesigns or frontend bug fixes — so every page looks like part of one application. Use together with the `chineseverse` project skill.
---

# ChineseVerse frontend design system ("Ink & Jade")

This skill describes the design system that **already exists** in `frontend/src/index.css` and the shared components. It does not introduce a new one. The goal is consistency, not redesign: reuse what is there, and add the smallest reusable piece only when nothing fits.

The general project rules (api.js, i18n workflow, `useApi`, `useDashboard`, git workflow) live in the `chineseverse` skill. Follow both.

## 0. Workflow for every frontend change

**Before writing code**

1. Read the page or component you are changing, plus the CSS rules for the classes it uses (`grep -n "\.classname" frontend/src/index.css`).
2. For every visual need, walk the reuse ladder and stop at the first step that works:
   1. an **existing class or component** (sections 3–9, `components/ui.jsx`, `Icon.jsx`);
   2. an existing **modifier** on it (`.card.hover`, `.btn.small.ghost`, `.page.wide`, …);
   3. a **token** (`var(--space-4)`, `var(--text-sm)`, …) in a new class;
   4. a **new class in `index.css`**, built only from tokens and placed beside its related section.
   Ask yourself each time: *"Does an existing ChineseVerse class, component or token already solve this?"*
3. Touch only what the task needs. Don't restyle neighbouring sections because you prefer another look, and don't migrate a legacy page to a new shape unless the user asked for it (section 16).

**After writing code**, run the quality check in section 14.

## 1. Tokens: the single source of truth

All tokens are defined at the top of `frontend/src/index.css`, with theme values on `:root, [data-theme="ink"]` (dark, deep navy) and `[data-theme="paper"]` (light, parchment).

- Tokens use the names below, **not** a `--cv-*` prefix. Never create parallel aliases such as `--cv-radius-md`; that would split the system in two.
- Never hardcode a value that a token covers.
- Add a new token only when a value is genuinely reused in 3 or more places and matches the existing scale. Add it in the matching block (theme-dependent values go in **both** theme blocks).

| Group | Tokens |
|---|---|
| Surfaces | `--bg`, `--surface-1` (cards), `--surface-2` (inputs, chips, kpis, secondary buttons), `--surface-3` (hover/raised), `--glass-bg` (sticky bars) |
| Lines | `--border`, `--border-strong` |
| Text | `--text`, `--text-dim` (secondary), `--text-faint` (labels, hints, placeholders) |
| Accent (brass → gold) | `--accent`, `--accent-strong`, `--accent-soft`, `--accent-gradient`, `--accent-dim` (tinted bg), `--accent-border`, `--on-accent` (text on accent), `--accent-glow`, `--ring-accent` |
| Semantic | `--good` / `--good-dim` (jade), `--bad` / `--bad-dim` (cinnabar), `--seal` |
| Type | `--font-ui`, `--font-display` (both Manrope + Noto Sans SC; no serif anywhere) |
| Type scale | `--text-2xs` 11.5 · `--text-xs` 13 · `--text-sm` 14.5 · `--text-base` 16 · `--text-md` 18.5 · `--text-lg` 22 · `--text-xl` 29 · `--text-2xl` 38 · `--text-3xl` clamp(42–66) · `--text-hero` clamp(48–92) |
| Spacing | `--space-1` 4 · `-2` 8 · `-3` 12 · `-4` 16 · `-5` 24 · `-6` 32 · `-7` 48 · `-8` 64 |
| Radius | `--radius-sm` 8 · `--radius-md` 12 · `--radius-lg` 18 · `--radius-full` 999 |
| Shadow | `--shadow-sm` (resting card), `--shadow-md` (hover / popover / map), `--shadow-lg` (drawer / overlay) |
| Motion | `--dur-fast` .12s · `--dur-base` .22s · `--dur-slow` .42s · `--ease-out` · `--ease-spring` |

Back-compat aliases `--accent2`, `--indigo`, `--warn`, `--radius` and `--shadow` exist only so old code keeps working. **Don't use them in new code**; use `--text-dim`, `--surface-3`, `--accent`, `--radius-md` and `--shadow-md`.

## 2. Layout

**App shell** (`components/Layout.jsx`): `.shell` = `.sidebar` (252px, collapsed 78px) + `.shell-main` (sticky `.topbar` + `<main class="page route-reveal">`). Every authenticated page renders inside `<Layout>`. Never build a second header, sidebar or page wrapper inside a page.

**Content width and padding** come from `.page` only:
- `max-width: min(1360px, 94vw)`, padding `36px 24px 90px`; at ≤720px it is `20px 14px 64px`.
- `.page.wide` (`min(1600px, 96vw)`) exists for genuinely wide tools.
- Pages don't set their own max-width or side padding. Narrow, focused content uses an existing narrow container: `.formcard` (420px) for auth-style forms, `.modal .card` (480px) for dialogs.

**The two page shapes in use.** Pick the one that matches the page; don't invent a third.

*A. Workspace shape* (Achievements, Assistant, Practice, Roadmap). Use it for feature pages that have a summary and a supporting side panel.
```jsx
<Layout>
  <header className="page-head">
    <div>
      <div className="page-eyebrow"><Icon name="award" size={13} /> {t("…")}</div>
      <h1 className="h1">{t("…title")}</h1>
      <p className="sub">{t("…subtitle")}</p>
    </div>
    <div className="kpi-row">
      <div className="kpi"><span className="kpi-value">…</span><span className="kpi-label">{t("…")}</span></div>
    </div>
  </header>
  <div className="ws">
    <div className="ws-main">
      <h2 className="h2 section-title">{t("…")}</h2>
      …cards / grids…
    </div>
    <aside className="ws-side">
      <div className="card side-card"><p className="side-title">{t("…")}</p>…</div>
    </aside>
  </div>
</Layout>
```

*B. Simple shape* (Vocabulary, Lessons, Settings, World, most older pages). Use it for list or utility pages.
```jsx
<Layout>
  <h1 className="h1">{t("…title")}</h1>
  <p className="sub">{t("…subtitle")}</p>
  <div className="grid cards" style={{ marginTop: 16 }}>…</div>
</Layout>
```

**Spacing rhythm.** Inline spacing numbers must be on the scale (4, 8, 12, 16, 24, 32, 48, 64).

| Where | Value |
|---|---|
| Title block → first content block | 16px (`--space-4`). Existing 14 or 18 values are legacy; don't churn them. |
| Between major sections, and `page-head` → `.ws` | 24px (`--space-5`) |
| Grid / card gaps (`.grid`, `.ach-grid`, `.ws-main`, `.ws-side`) | 16px (`--space-4`) |
| Inside a row of controls (`.row`, `.col`) | 12px (`--space-3`); tight clusters use 8px |
| Card padding | `.card` 26px, `.side-card` 20px, dense grid cards 18px (e.g. `.ach-grid .card`). Don't invent other paddings; reuse one of these. |

**Grids:** use `.grid` (gap 16), `.grid.grid-2` (two columns, one column at ≤640), `.grid.cards` (auto-fill, min 268px), `.bento` for the dashboard and `.row` / `.row.spread` / `.col` for flex. Any custom multi-column grid must collapse at an existing breakpoint (section 11).

## 3. Typography

Use the classes, not ad-hoc `fontSize` values.

| Role | Use | Spec |
|---|---|---|
| Hero greeting (Dashboard only, one per page) | `.hero-greeting` | `--text-hero`, 600 |
| Page title | `h1.h1` | `--text-xl` (29), 800, -0.015em |
| Section title | `h2.h2` (+ `.section-title` for the rule-line variant in workspaces) | `--text-md` (18.5), 800 |
| Eyebrow above a title | `.page-eyebrow` | `--text-2xs`, 800, uppercase, 0.08em, `--accent-strong` |
| Panel / field label | `.side-title`, `.field label` | `--text-2xs`, 700–800, uppercase, `--text-faint` |
| Body | inherited | `--text-base` (16), line-height 1.55 |
| Secondary / subtitle | `.sub`, `.muted` | `--text-sm` (14.5) `--text-dim` / colour only |
| Caption / meta | new class with `--text-xs` (13) or `--text-2xs` (11.5) | |
| Key numbers | `.kpi-value` | `--text-lg`, 800 |
| Buttons | `.btn` / `.btn.small` | `--text-sm` / `--text-xs`, 700 |
| Nav | `.sidebar-link` / `.navlink` | `--text-sm` / `--text-xs`, 600 |
| Chinese glyph as content | `.practice-hanzi` (clamp 40–64) or `--text-2xl` / `--text-3xl` | 800 |

- **Weights:** use 600 for nav, 700 for buttons, labels and badges, and 800 for headings and numbers. Body text stays at the default.
- **Never add a new pixel font size.** If nothing fits, use the nearest token. An inline `fontSize: 12` should become `var(--text-xs)` (or a class) whenever you are already editing that line.
- Use semantic headings: one `h1` per page, with `h2` for sections. Don't skip levels just to get a size; use the class for size and the tag for meaning.

## 4. Color and theme

- Every color must come from a token so that **both Ink and Paper themes work**. Test both themes; the toggle is in the topbar and in Settings.
- **Accent is rare:** use it for primary actions, the active nav state, key numbers and the "next" or highlighted item. It is not decoration, and there is never more than one primary button per action group.
- Use `--good` for success or correct, `--bad` for errors or wrong, and badge tones `.badge.good`, `.badge.bad` and `.badge.accent` (`.warn` is the same as accent). Don't add blue, purple or orange UI states.
- Content differentiation (animals, locations, question types) comes from **shape, icon and type, not new hues**.
- **Overlays:** the modal backdrop is `rgba(4, 4, 5, 0.75)` with a 6px blur, and the drawer backdrop is `rgba(4, 4, 5, 0.55)`. Reuse these by reusing `.modal` or `.sidebar-backdrop`.

## 5. Cards and surfaces

- Base is `.card`: `--surface-1`, a 1px `--border`, `--radius-lg`, 26px padding and `--shadow-sm`.
- Variants are defined in the system; use these instead of inline overrides:
  - `.card.hover` (clickable): lifts by `translateY(-3px)`, `--border-strong`, `--shadow-md`;
  - `.card.flat` (no shadow, for nested or grouped cards);
  - `.side-card` (20px padding);
  - `.page-head` (accent radial wash);
  - `.dna-hero-card`;
  - `.kpi` (surface-2, `--radius-md`).
- **Highlighting a card** (due, selected, recommended): use `border-color: var(--accent-border)` or `var(--accent)` with an accent badge. Never use `border: 0`, which collapses the card's edge and breaks the grid's rhythm.
- **Radius:** use `--radius-lg` for cards, panels and the map; `--radius-md` for buttons, kpis, tooltips and prompt chips; `--radius-sm` for inputs, small buttons and skeletons; `--radius-full` for pills, badges, chips and bars; `50%` for avatars and dots only.
- A **clickable card** must be a `<button>` or a `<Link>` (as Vocabulary and Lessons do), never a `<div onClick>`.

## 6. Buttons

There is one button family, `.btn`. Don't create page-specific button classes.

| Need | Class |
|---|---|
| Default / secondary | `.btn` |
| Primary (one per group) | `.btn.primary` |
| Low emphasis, toggles, "unselected" segment | `.btn.ghost` |
| Destructive | `.btn.danger` |
| Compact (filters, segmented controls, tool rows) | add `.small` |
| Disabled | the `disabled` attribute (styled by `.btn:disabled`); never fake it with opacity |
| Loading | `disabled` plus a translated "…ing" label (e.g. the existing `pages.onboarding.saving`; add a key in your own section) or an inline `.spinner`; keep the button width stable |
| Icon-only | `.icon-btn` with an `aria-label={t(...)}` |

- **Segmented choice** (theme, language, HSK level): a `.row` of `.btn.small`, where the selected one is `.primary` and the rest are `.ghost` (see Settings and Vocabulary).
- **Press feedback** is global. `buttonFx.js` animates every element matching `PRESSABLE`. Don't add per-button press animations; if a new pressable class needs the effect, add it to `PRESSABLE`.
- Always set `type="button"` on non-submit buttons inside forms.

## 7. Inputs and forms

- Wrap each control in `.field`, which holds a `label` (uppercase 2xs) and the control, with a 15px bottom gap.
- Controls use `.input` (works on `input`, `textarea` and `select`): `--surface-2`, 1px `--border`, `--radius-sm`, padding 11×13, `--text-base`.
  - Hover: `--border-strong`.
  - Focus: `--accent` border with a `0 0 0 3px var(--accent-dim)` ring.
- Show errors with `.formerr` (bad colour plus a shake). Show the API's `detail` there and never `alert()`.
- Use `.switch` / `.toggle-row` for toggles (Settings) and `.divider` for an "or" separator.
- Every control needs a visible `<label>` or an `aria-label` from `t()`. Placeholders are not labels.

## 8. Navigation

- The sidebar `GROUPS` (`components/Sidebar.jsx`) and topbar `NAV_INDEX` (`components/Topbar.jsx`) are the only primary navigation.
- **Active state** is accent text and icon plus the brush mark (sidebar) or the gradient underline (`.navlink`, landing only). It is not a filled chip.
- **In-page tabs or filters:** use the segmented `.btn.small` pattern from section 6.
- **Back actions:** use a `.btn.ghost` link back (`<Link to={backTo} className="btn ghost">{t("…back")}</Link>`, as in Practice). The quieter `.sub.duel-back` text link is only for the in-game DuelBattle header.
- **Dropdowns and popovers** (search, notifications) use `--surface-1`, `--border-strong`, `--radius-md`, `--shadow-md` and z-index 60.
- **Z-index layers:**
  - 1–5: local stacking
  - 40: topbar
  - 44 / 45: drawer backdrop / sidebar
  - 50: landing appbar
  - 60: popovers
  - 100: modal
  - 110: toast
  - 200: celebration
  Fit new layers into this scale.

## 9. Icons

- Use only `components/Icon.jsx`: `<Icon name="…" size={…} />`. These are 24×24 line icons with a 1.8 stroke, round caps and `currentColor`.
  - Sizes: 13 inside chips, eyebrows and small buttons; 15–17 inside cards and rows; 18 is the default.
  - Icons are `aria-hidden`, so the button or link must carry the text or an `aria-label`.
- **Missing icon:** add one path to `PATHS` in the same style. Don't add an icon library, and don't mix filled or emoji icons into UI chrome.
- **Allowed emoji:** Celebration icons and data-driven content (location `icon`, companion art). Legacy chrome emoji such as `⏰` and `🔒` exist; replace them with an `Icon` only when you are already editing that line.

## 10. Motion

The motion system is small on purpose. Use these pieces and add nothing that competes with them.

- **Page entrance:** `PageReveal` in `Layout.jsx` animates the page's direct children automatically. A section with its own entrance sets `data-self-animate="true"` so the two never stack.
- **Card entrance:** `.grid > .card` and `.col > .card` already fade up with a stagger. Don't add another entrance to them.
- **Keyframes to reuse:** `fadeInUp`, `fadeIn`, `scaleIn`, `shimmer` (skeleton), `spin` (spinner) and `shake` (error). Don't write new keyframes for the same effect.
- **Durations:**
  - `--dur-fast` for hover colour and border changes;
  - `--dur-base` for cards, popovers and entrances;
  - `--dur-slow` for progress bars and theme swaps.
- **Easing:** `--ease-out` by default. Use `--ease-spring` only for small playful accents such as the nav underline or a toggle.
- **JS motion** uses anime.js through the helpers in `anime.js` (`ELASTIC_POP`, `OUT_EXPO`, …). Use framer-motion only for AnimatePresence mount/unmount (`motion.js` `popIn`). Use `<Celebration>` for wins and level-ups. Don't add a new animation library.
- **Hover** may change only `transform` (`.btn` lifts 1px, `.card.hover` lifts 3px), `opacity`, `color`, `background`, `border-color`, `box-shadow` and `filter`. Never animate `width`, `height`, `padding`, `margin`, `top` or `font-size` on hover, because that shifts layout.
- **Stability rules.** These came from real bugs; don't reintroduce them.
  - A hover transform must never move the element out from under the cursor. Keep scale ≤ 1.15 and translate ≤ 3px.
  - **SVG:** any CSS transform on an SVG child needs `transform-box: fill-box; transform-origin: center;`. Without them the origin is the viewBox, so the element jumps and the hover flickers (this was the World map jitter fixed in `226930f`).
  - **SVG:** never put a CSS transform on an element that already has a `transform=` attribute (such as the positioned `<g>`). Transform its children instead.
  - Don't stack two animations on the same element's opacity or transform (PageReveal plus your own, React StrictMode double effects). Cancel or revert in effect cleanup.
  - After an anime.js animation finishes, clear any inline `transform` or `boxShadow` it left behind (as `buttonFx.js` does) so CSS `:hover` keeps working.
- **Reduced motion:** CSS is neutralised globally by `@media (prefers-reduced-motion: reduce)`. Every JS animation must check `prefersReducedMotion()` and jump to the end state.
- **Infinite loops** are only for small ambient signals (the map's "next" pulse, glows, the spinner). Never loop motion on text or controls the user is reading or using.

## 11. Responsive

Use the existing breakpoints, all of them `max-width`:

| Breakpoint | Meaning |
|---|---|
| **1080** | workspace collapses: `.page-head` and `.ws` go to one column, and `.ws-side` becomes an auto-fit grid |
| **980** | sidebar becomes an off-canvas drawer (`.mobile-open`), topbar search and date hide |
| **760** | tablet: `.page-head` padding is 18, `.kpi-row` is two columns |
| **720** | phone page padding (`.page` 20/14/64) |
| **640** | phone: `.grid-2` goes to one column, topbar is compact, logo is smaller |
| **480** | small phone tweaks |

- 900, 860, 560 and the `min-width: 760` breakpoints exist in older sections. Don't add more one-off widths; pick the nearest canonical breakpoint.
- Every new layout wider than one column needs a rule at one of these breakpoints. Prefer intrinsic layouts (`auto-fill`/`auto-fit` with `minmax(…)`, `minmax(0, 1fr)`, `flex-wrap`) that need no breakpoint at all.
- **No horizontal page scroll at 360px.** Give flex and grid children that hold text `min-width: 0`, use `overflow-wrap: anywhere` for user content, and clip decorative overflow (`overflow-x: clip`, as `.ach-grid` does).
- **Touch targets** must be at least about 36px. Hover-only information (tooltips) also needs a tap or focus path; the World map nodes navigate on click.
- Test at about 1440, about 1024 and about 375 px wide.

## 12. Accessibility

- **Semantic HTML:** one `h1`, `header`, `main` (provided by Layout), `aside`, `nav`, `button` for actions, `Link` for navigation. Don't use a `div onClick`, or a `<button>` inside a `<Link>` in new code.
- **Keyboard:** every interactive element is reachable and works with Enter or Space. Custom controls with `role="button"` (map nodes, switches) also need `tabIndex={0}` and an `onKeyDown` handler for Enter/Space.
- **Focus must stay visible.**
  - The app has no global `:focus-visible` style yet, so buttons and links rely on the browser outline. Never write `outline: none` without a replacement.
  - The `.input:focus` ring is the house style for inputs.
  - For other new controls, add `:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }`.
- **Contrast:** body text uses `--text` or `--text-dim`. `--text-faint` is only for labels and hints, never for body copy or for disabled text that still carries meaning. Text on accent uses `--on-accent`.
- **Labels and status:** icon-only buttons need a translated `aria-label`. Use `aria-pressed` for toggles and `aria-live` for async status (chat, grading feedback).

## 13. Page-specific rules

**World page** (`pages/WorldMap.jsx`, `.worldmap-*` and `.wm-*` in index.css):
- It is an SVG illustration, not a dashboard. Don't put cards, grids or `.page-head` on the map.
- **Keep:** `.worldmap-wrap` (square, `min(880px, 100%)`, `--radius-lg`, `--shadow-md`), the dashed road, the `wm-pulse` on the "next" node, node hover scale 1.15 with `transform-box: fill-box`, and the `.wm-tooltip` (surface-1, border-strong, radius-md, shadow-md, `fadeInUp` 0.15s).
- **Must still follow ChineseVerse:**
  - the title uses `h1.h1` + `.sub`;
  - tooltip text uses existing classes and badges;
  - buttons and overlays near the map use `.btn` and `.modal`;
  - all strings go through `t()`;
  - the map stays usable at 375px.
- **Known drift:** the SVG hardcodes the old zinc palette (`#18181b`, `#09090b`, `#2a2a2e`, `#e9e6df`, `#eab244`), so it doesn't follow the Paper theme.
  - Don't change it opportunistically.
  - When asked to work on the map's visuals, move those fills into CSS classes that use tokens (`fill: var(--surface-2)`, `stroke: var(--accent)`, …) and keep the geometry and animation identical.

**Dashboard** owns the only `.hero-greeting`, the `.hero-banner`, `.bento` and `.quick-actions`. Don't copy these onto other pages.

**Data visualisation:** Progress, the activity heatmap, the DNA rings and the Landing illustrations carry their own fixed category palettes. They are allowed there and must not spread into UI chrome.

## 14. Localization (EN / RU / TG / ZH)

- No visible string is hardcoded, including `aria-label`, `title`, `placeholder`, `alt`, button labels and empty states. Use `t()` and add the key to all four locale files (see the `chineseverse` skill for the safe way to edit them).
- Text length varies a lot: Russian and Tajik run about 30% longer than English, and Chinese is shorter. Layouts must allow wrapping. Don't use fixed-width buttons or labels, and don't truncate a label as a substitute for wrapping.
- Chinese content (hanzi, pinyin) is never translated and uses the same fonts. Pinyin uses `.sub`, not a new color.

## 15. Quality check (run every time)

1. **Audit the diff for design drift:**
   ```
   python .claude/skills/chineseverse-frontend-design/scripts/design_audit.py          # your uncommitted changes
   python .claude/skills/chineseverse-frontend-design/scripts/design_audit.py <file>…  # whole files
   ```
   It flags the following; fix them, or justify each one:
   - raw colors;
   - pixel font sizes and radii;
   - durations that don't use the tokens;
   - non-canonical breakpoints;
   - `outline: none`;
   - likely hardcoded English text.
2. **Visual consistency:** the page uses one of the two page shapes, the spacing rhythm, the typography classes, the card and button variants, and works in both themes.
3. **Responsive:** check about 1440, 1024 and 375 px. There is no horizontal scroll, and the sidebar drawer works.
4. **Interaction:** hover, focus-visible, disabled and loading states all exist. Nothing shifts, jitters or flickers on hover, especially SVG. Reduced motion is respected.
5. **i18n:** run `python frontend/scripts/check_i18n_keys.py`, then view the page in RU (the longest strings) and ZH.
6. **Build and console:** `cd frontend && npm run build` passes, and the browser console has no errors or React key warnings on the changed page.
7. **No regressions** in HSK 1–9, Vocabulary, Lessons, Practice, Review, Hanzi, Grammar, Learning DNA, Achievements, Companion, Assistant, Notifications, World, auth (including Google), localization and mobile layout. For any page whose shared classes you edited in index.css, re-check every page that uses those classes (`grep -rn "classname" frontend/src`).

## 16. Known legacy drift: don't copy it

Older pages contain patterns that predate the tokens. Leave them alone unless you are already editing those lines, and never use them as a template.

- Inline `fontSize: 12` (or 11, 12.5, 13, …) and `style={{ … }}` spacing that isn't on the scale. The Vocabulary, Lessons, Settings, Achievements and Profile pages have many.
- About 130 raw hex colours in JSX, mostly the Dashboard, Landing and Progress data palettes and the World SVG.
- Old-palette `rgba(238,106,103,…)` and `rgba(107,207,143,…)` borders on `.btn.danger`, `.badge.bad` and `.badge.good`. If you touch them, use `--bad` / `--good`-based values.
- `border: 0` on highlighted Vocabulary cards.
- One-off breakpoints at 900, 860 and 560.
- Emoji used as UI icons (`⏰`, `🔒`, `📍` fallback).
