---
kind: frontend_style
name: Vanilla CSS Dark Theme with Design Tokens and Glassmorphism UI
category: frontend_style
scope:
    - '**'
source_files:
    - frontend/style.css
    - frontend/index.html
    - frontend/app.js
---

## What system/approach is used

The frontend uses a **vanilla HTML + CSS + JavaScript** stack with no CSS framework, preprocessor, or component library. Styling is centralized in a single `frontend/style.css` file and the layout lives in `frontend/index.html`. Fonts are loaded from Google Fonts (`Outfit` for body text, `JetBrains Mono` for monospace/numeric display). The visual style is a **dark-mode security dashboard** using glassmorphism (semi-transparent cards with `backdrop-filter: blur`) and ambient background glows.

## Key files and packages

- `frontend/style.css` — all styling, design tokens, responsive breakpoints, animations
- `frontend/index.html` — page structure; links to `/static/style.css` and `/static/app.js`
- `frontend/app.js` — client-side tab switching, form submission, result rendering (not styled directly but drives DOM state)

No build step, no CSS-in-JS, no Tailwind/Bootstrap/Sass — pure static assets served by the FastAPI backend.

## Architecture and conventions

### Design tokens via CSS custom properties
All colors, radii, and fonts are declared as `:root` variables at the top of `style.css`, forming a small design token system:
- Backgrounds: `--bg-main`, `--bg-card`
- Borders: `--border-color`, `--border-highlight`
- Text: `--text-main`, `--text-muted`
- Brand palette: `--primary`, `--primary-glow`, `--accent-cyan`, `--accent-emerald`
- Risk levels: `--risk-critical`, `--risk-high`, `--risk-medium`, `--risk-low`
- Spacing/radius: `--radius-lg`, `--radius-md`, `--radius-sm`
- Typography: `--font-main`, `--font-mono`

### Layout model
- A centered `.app-container` (max-width 1320px) holds header, main grid, and footer.
- The workspace is a two-column CSS Grid (`.main-grid`: `1fr 1.2fr`) that collapses to a single column below 960px.
- Cards use a shared `.card` class with glassmorphism (`background: var(--bg-card)`, `backdrop-filter: blur(16px)`, translucent border).

### Component-like classes
The stylesheet defines reusable UI primitives rather than strict components:
- `.badge` / `.badge-ai` / `.badge-status` — header status badges
- `.tabs` + `.tab-btn` + `.tab-content` — four-tab input switcher (Text/Screenshot/URL/Voice), toggled via JS adding/removing `.active`
- `.upload-zone` — dashed-border drag-and-drop area
- `.btn` + `.btn-primary` — gradient primary action button
- `.chip` — selectable preset chips
- `.gauge-circle`, `.risk-badge`, `.ind-chip` — result visualization primitives
- `.dos-card` / `.donts-card` — paired positive/negative action panels

### Responsive strategy
Breakpoints are minimal and functional:
- `@media (max-width: 960px)` — switches `.main-grid` to single-column
- `@media (max-width: 600px)` — stacks the `.actions-grid` into one column
No mobile-first media queries; the base styles target desktop and degrade downward.

### Visual theme details
- Dark background (`#0B0F19`) with two large blurred radial-gradient circles (`.bg-glow-1`, `.bg-glow-2`) fixed behind content for ambient glow.
- Primary accent is indigo (`#4F46E5`) with cyan (`#06B6D4`) highlights; risk severity maps to red/orange/yellow/green.
- Focus states highlight inputs with `border-color: var(--primary)` plus a glow shadow.
- Loading overlay uses a CSS-only radar spinner (`@keyframes spin`).

## Conventions and constraints

- **Single-file stylesheet**: All styles live in one `style.css`; there are no scoped/component-specific CSS files.
- **CSS custom properties for theming**: Colors, radii, and fonts are always referenced through `var(--*)` variables rather than hardcoded values, keeping the palette centralized.
- **Semantic BEM-ish naming**: Classes follow a flat, descriptive pattern (`card`, `card-header`, `tab-btn`, `upload-zone`, `results-card`) without a formal methodology like BEM or ITCSS.
- **JS-driven state, CSS-driven appearance**: Tab visibility, loading overlays, and result sections are toggled by adding/removing `.active` or inline `display` styles in `app.js`; the CSS only defines the visual states.
- **Responsive breakpoints are sparse**: Only two `@media` rules exist (960px and 600px); the rest of the layout relies on Flexbox/Grid auto-sizing.
- **No CSS framework or preprocessor**: No imports, no `@use`/`@import`, no build pipeline — the browser consumes plain CSS directly.
- **Fonts loaded externally**: `Outfit` and `JetBrains Mono` are pulled from Google Fonts via `<link>` in `<head>`; no local font files.