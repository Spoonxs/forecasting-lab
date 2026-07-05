# Sakura one-shot teardown — the landing-quality bar (2026-07-05)

*Reference: https://oneshot-sakura.vercel.app/ ("SAKURA — Ink & Bloom", a Fable
one-shot). Captures on disk: `sakura-01-fullpage.png` (full page),
`sakura-f1..f5.png` (hero motion + scroll positions),
`sakura-walkthrough.mp4` (stitched scroll-through). This is the quality bar for
OUR landing/marketing surfaces; the techniques below are what make it feel
expensive — all buildable with zero frameworks.*

## What actually creates the feel (verified from its DOM + CSS bundle)
1. **One full-viewport `<canvas>` particle layer** — drifting petals with
   physics (rotation, sway, depth-varied speed/size/alpha). THE aliveness.
   Ours: drifting **ticker glyphs / paper motes / tiny candlesticks** in the
   cream palette, ~60 particles, requestAnimationFrame, killed under
   prefers-reduced-motion.
2. **Film grain overlay** — `@keyframes grain` jittering a noise texture at low
   opacity over everything; makes flat color feel like paper/print.
3. **Editorial serif display pairing** — Cormorant Garamond + Shippori Mincho,
   huge thin-weight headlines. Ours: keep IBM Plex Mono for the app, allow a
   display serif ONLY on the landing hero (system fallback stack).
4. **Extreme tracked-out eyebrows** — letter-spacing .3–.7em uppercase micro
   labels (we already do a mild version; the landing pushes it).
5. **Vertical text accents** — `writing-mode:vertical-rl` rails on section
   edges. Ours: vertical "EST. 2026 · PAPER FIRST" rails.
6. **Warm paper ground** — rgb(242,236,223) ≈ #F2ECDF; ours is #FBF7EB. Same
   family; no change needed.
7. **Decisive easing** — everything moves on `cubic-bezier(.7,0,.2,1)` (fast
   out, soft land), scroll-triggered reveals with large translate+fade, a
   `scrollcue` pulse. Nothing uses default ease.
8. **backdrop-blur nav + mix-blend-multiply imagery** — glassy sticky nav;
   images multiply into the paper so they feel printed, not pasted.

## Local asset pipeline (operator hardware: RTX 4070 Ti, 12GB)
Generated art is for the LANDING/brand layer only — data surfaces stay
hand-rolled SVG. Recommended stack (all free, all local):
- **ComfyUI + Flux.1-dev fp8** (fits 12GB) for hero/section illustrations —
  prompt to match the skin: "warm cream paper, ink-brush financial motifs,
  muted green/brick accents, editorial print texture". Batch + pick.
- **Real-ESRGAN** upscale → export **WebP/AVIF** (≤200KB per hero).
- Short ambient loops (optional): **LTX-Video** (works on 12GB) or animated
  canvas instead — canvas is smaller, sharper, and reduced-motion-safe;
  prefer it over video for anything under 8s.
- Assets land in `site/assets/brand/`, committed (ours, not scraped), with
  generation prompts recorded beside them in `PROMPTS.md` for regeneration.

## Where it applies
- `landing.html` (new): the marketing/entry page — canvas particles, grain,
  display-serif hero ("Every recommendation carries its receipts"), scroll
  reveals, then hands off to the app (index).
- The app pages get the RESTRAINED versions only: grain at 2% opacity, the
  easing curve, reveal-on-scroll — never particles over data tables.
- All motion behind `prefers-reduced-motion`; content never JS-gated.
