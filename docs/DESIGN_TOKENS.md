# QueAI Design Tokens

Esta es la **fuente única de verdad** para el look & feel del kernel y los
plugins oficiales. Cada plugin es independiente y **embebe su propia copia**
de estos tokens; no carga CSS del kernel. Cuando estos tokens cambian aquí,
se replican manualmente a los 3 plugins oficiales (OCR, STT, TTS).

## Por qué

- Los plugins se publican como contenedores autónomos y deben verse igual de
  bien estando dentro del kernel (iframe) o abiertos directos en su URL.
- Compartir CSS por HTTP entre dominios distintos genera CORS y rompe el
  contrato de "plugin = caja negra Docker".
- Duplicación deliberada > acoplamiento al kernel.

## Paleta

```css
:root {
    /* Fondo */
    --bg:            #141414;  /* página */
    --bg-card:       #1c1c1c;  /* tarjetas, paneles */
    --surface:       #262626;  /* hover sobre cards, pills activos */
    --surface2:      #2c2c2c;  /* inputs, modales */

    /* Líneas */
    --border:        #2a2a2a;  /* borde por defecto */
    --border-subtle: #1f1f1f;  /* separadores discretos */

    /* Texto */
    --text:          #eaeae6;  /* primario */
    --text-muted:    #909090;  /* descripciones */
    --text-dim:      #707070;  /* etiquetas, valores monospace */

    /* Marca */
    --red:           #e8180c;  /* CTA, brand, focus */
    --red-soft:      rgba(232,24,12,0.10);  /* error bg */
    --ok:            #4ade80;  /* éxito, estado running */
    --warn:          #f5c042;
    --danger:        #ff5d5d;

    /* Geometría */
    --radius:        14px;     /* tarjetas, paneles */
    --radius-sm:     9px;      /* botones, pills, inputs */
}
```

## Tipografía

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
/* Monospace para versiones, IDs, métricas, etiquetas */
.mono, code, kbd { font-family: 'DM Mono', monospace; }
```

## Principios visuales

1. **Plano, no glassmorphism.** Sin `backdrop-filter`, sin gradientes
   radiales de fondo. Solo capas planas (`--bg`, `--bg-card`, `--surface`).
2. **Sin sombras agresivas.** Como mucho `box-shadow: 0 8px 24px
   rgba(0,0,0,0.3)` en modales. Las tarjetas no flotan.
3. **Borde, no elevación.** La separación entre superficies se marca con
   `1px solid var(--border)`, no con sombras.
4. **El rojo se usa con cuidado.** Solo CTAs principales, foco, marca. Nunca
   como fondo de tarjeta.
5. **Mayúsculas con `letter-spacing: 0.08em`** para etiquetas
   monospace (status, eyebrows). El cuerpo normal nunca va en mayúsculas.

## Componentes core

### Botón primario (CTA)

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

### Botón ghost (acción secundaria)

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

### Spinner (para botones de carga)

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

## Lo que NO usamos

- Gradientes radiales o lineales de fondo (no encajan con el flat).
- `backdrop-filter: blur(...)`.
- Sombras coloreadas (rgba con tinte rojo, azul, etc.).
- Bordes redondeados >14px (excepto pills 9999px para etiquetas circulares).
- Más de 3 capas de superficie (bg, bg-card, surface).
- Tipografías serif o cursivas.
