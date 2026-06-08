# QueAI Design Tokens

This is the **single source of truth** for the look & feel of the kernel and the official plugins. Each plugin is independent and **embeds its own copy** of these tokens; it does not load CSS from the kernel. When the tokens change here, they're manually replicated to the 3 official plugins (OCR, STT, TTS).

## Why

- Plugins are published as standalone containers and have to look just as good inside the kernel (iframe) or opened directly at their URL.
- Sharing CSS over HTTP across different domains pulls in CORS issues and breaks the "plugin = black-box Docker" contract.
- Deliberate duplication > coupling to the kernel.

## Palette

```css
:root {
    /* Background */
    --bg:            #141414;  /* page */
    --bg-card:       #1c1c1c;  /* cards, panels */
    --surface:       #262626;  /* card hover, active pills */
    --surface2:      #2c2c2c;  /* inputs, modals */

    /* Lines */
    --border:        #2a2a2a;  /* default border */
    --border-subtle: #1f1f1f;  /* subtle separators */

    /* Text */
    --text:          #eaeae6;  /* primary */
    --text-muted:    #909090;  /* descriptions */
    --text-dim:      #707070;  /* labels, monospace values */

    /* Brand */
    --red:           #e8180c;  /* CTA, brand, focus */
    --red-soft:      rgba(232,24,12,0.10);  /* error bg */
    --ok:            #4ade80;  /* success, running state */
    --warn:          #f5c042;
    --danger:        #ff5d5d;

    /* Geometry */
    --radius:        14px;     /* cards, panels */
    --radius-sm:     9px;      /* buttons, pills, inputs */
}
```

## Typography

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
```

```css
body {
    font-family: 'DM Sans', system-ui, sans-serif;
    font-size: 15px;
    -webkit-font-smoothing: antialiased;
}
/* Monospace for versions, IDs, metrics, labels */
.mono, code, kbd { font-family: 'DM Mono', monospace; }
```

## Visual principles

1. **Flat, no glassmorphism.** No `backdrop-filter`, no radial background gradients. Only flat layers (`--bg`, `--bg-card`, `--surface`).
2. **No aggressive shadows.** At most `box-shadow: 0 8px 24px rgba(0,0,0,0.3)` on modals. Cards don't float.
3. **Edges, not elevation.** Separation between surfaces is marked with `1px solid var(--border)`, not shadows.
4. **Red is used sparingly.** Only for primary CTAs, focus, brand. Never as a card background.
5. **Uppercase with `letter-spacing: 0.08em`** for monospace labels (status, eyebrows). Body copy never goes in uppercase.

## Core components

### Primary button (CTA)

```css
.btn-primary {
    background: var(--red);
    color: #fff;
    border: 1px solid var(--red);
    border-radius: var(--radius-sm);
    padding: 10px 22px;
    font-family: inherit;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: opacity 0.15s;
}
.btn-primary:hover { opacity: 0.92; }
.btn-primary:disabled { opacity: 0.6; cursor: progress; }
```

### Ghost button (secondary action)

```css
.btn-ghost {
    background: var(--bg-card);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 10px 22px;
    font-family: inherit;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.15s, border-color 0.15s;
}
.btn-ghost:hover { background: var(--surface); border-color: #484848; }
```

### Card / panel

```css
.card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px;
}
```

### Input

```css
input[type=text], input[type=password], textarea {
    background: var(--surface2);
    border: 1px solid var(--border);
    color: var(--text);
    border-radius: var(--radius-sm);
    padding: 10px 14px;
    font-family: inherit;
    font-size: 14px;
    outline: none;
    transition: border-color 0.15s;
}
input:focus, textarea:focus { border-color: var(--red); }
```

### Spinner (for loading buttons)

```css
.btn-spinner {
    display: inline-block;
    width: 12px; height: 12px;
    border: 2px solid currentColor;
    border-right-color: transparent;
    border-radius: 50%;
    margin-right: 4px;
    vertical-align: -2px;
    animation: btn-spin 0.7s linear infinite;
}
@keyframes btn-spin { to { transform: rotate(360deg); } }
```

## What we don't use

- Radial or linear background gradients (don't match the flat aesthetic).
- `backdrop-filter: blur(...)`.
- Colored shadows (rgba with red/blue/etc. tint).
- Border radii larger than 14px (except 9999px pills for circular tags).
- More than 3 surface layers (bg, bg-card, surface).
- Serif or cursive typefaces.
