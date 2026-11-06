# Vidravo website

A motion-graphics library for YouTube videos, Shorts and Reels.

## What's inside

| Path | What it is |
| --- | --- |
| `index.html` | The whole website: pages, styles and code in one file |
| `logo.png` | Your Vidravo logo |
| `mg/` | Every animation: preview `.mp4`, poster `.jpg`, and for overlays a transparent `-alpha.webm` and a `-green.mp4` |
| `animation-source/` | Python scripts that generated the animations |

**ProRes 4444 files** come in the separate `vidravo-prores.zip`. Copy its `mg/*.mov` files into this `mg/` folder before uploading. The site shows a "ProRes 4444 MOV" button automatically when the file is there.

## Download formats and editors

| Format | Best for |
| --- | --- |
| ProRes 4444 `.mov` (transparent) | Premiere Pro, DaVinci Resolve, Final Cut Pro, After Effects |
| Green screen `.mp4` | CapCut, phone editors, anything with chroma key |
| MP4 | Every editor |
| Transparent WebM | Web and browser-based editors |
| PNG sequence `.zip` (from Customize text) | Premiere Pro, After Effects, DaVinci Resolve |

## Customize text

15 templates have a **Customize text** panel on their page (lower thirds, titles, handles, captions, Part 2, Wait for it, reply comment, milestone notification and more). Pro and Studio members type their own words, preview live, then export:

- **Transparent PNG sequence (.zip)**, 25 fps, rendered in the browser
- **Green-screen video** (MP4 in Chrome and Safari, WebM in Firefox), recorded in real time

To add a new editable template, add an entry to the `CUST` object in `index.html` with its size, length, fields and a `draw()` function.

## Put it online

Any static host works: Netlify or Vercel (drag the folder in), GitHub Pages, or upload to `public_html` on Hostinger/cPanel.
For large ProRes files, a CDN such as Bunny or Cloudflare R2 is cheaper; point the `.mov` links at it.

To try it locally: `python3 -m http.server` inside the folder, then open http://localhost:8000.

## Before taking real money

This version keeps accounts and plans in each visitor's browser, and checkout charges nothing.

1. **Accounts**: Supabase Auth (or Clerk), so sign-ins and plans live on a server.
2. **Payments**: Lemon Squeezy (supports sellers in Pakistan). Point Subscribe at your checkout link and update plans from its webhook.
3. **Protect paid files**: serve Pro and Studio files through signed links (Supabase Storage, Bunny or R2).
4. **Vidravo AI**: on your own host, add a server route that calls the Claude API with your key and returns the same JSON, and point `getSample()` at it.

## Re-render animations

Needs Python 3, Pillow, NumPy, ffmpeg, the Poppins font and `global-land-mask`:

```bash
pip install pillow numpy global-land-mask
python3 render.py  ../mg subscribe-bell
MOV=1 python3 render2.py ../mg lower-third-gradient      # MOV=1 also writes ProRes 4444
ORIENT=v python3 render3.py ../mg captions-pop          # Shorts & Reels (9:16)
```
