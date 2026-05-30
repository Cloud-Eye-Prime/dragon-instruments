# Dragon Instruments

Two standalone browser instruments -- **V0ID_SCALE Labs** and **Ghatika** --
with optional, bring-your-own-key AI. No build step, no backend, no account.
Each instrument is a single HTML file you can open, host, or download and fork.

**Live:** https://heartbeat-pages-production.up.railway.app
( [V0ID_SCALE Labs](https://heartbeat-pages-production.up.railway.app/voidscale.html)
. [Ghatika](https://heartbeat-pages-production.up.railway.app/ghatika.html) )

---

## What it is

Two self-contained instruments that run entirely in the browser:

- **V0ID_SCALE Labs** (`public/voidscale.html`) -- a vanilla Web Audio
  pad/scale instrument. An 8-pad grid plays a swappable set of MIDI notes
  through a single sine oscillator. It has an Euclidean-rhythm visualizer, an
  ouroboros breath visual, a loop list, a master volume and mute, Web MIDI
  input, and an AI "Summon" that asks a language model for a short phrase
  locked to the active scale. One file, no dependencies, no build.

- **Ghatika** (`public/ghatika.html`) -- a breath-and-entrainment sequencer
  built on React + Tone.js (both loaded from a CDN). It runs a single clock
  where an 8-beat breath maps to the five-element cycle, layers binaural /
  monaural / isochronic entrainment tones, stacks generative rhythm styles,
  plays a swappable melodic voice through modes / pentatonics / ragas, and
  routes everything through a filter / drive / delay / reverb rack. It exports
  real MIDI and WAV, can send live MIDI out over the Web MIDI API, and has two
  AI features: an "AI compose" phrase and an "AI DJ" director that writes
  measures ahead and drives the controls live.

See [docs/VOIDSCALE.md](docs/VOIDSCALE.md) and [docs/GHATIKA.md](docs/GHATIKA.md)
for the concepts behind each instrument.

---

## AI integration (read this -- it is the trust model)

Both instruments use **bring-your-own-key** AI. The call is made **directly
from your browser** to the AI provider. There is no server in between, and this
repository never contains a key.

- **V0ID_SCALE Labs -> OpenRouter.** The browser POSTs to
  `https://openrouter.ai/api/v1/chat/completions` with your key as a Bearer
  token. The default model is `openai/gpt-4o-mini` and is editable in the
  "AI Model" field. Your key is entered in the "AI Key" field and saved in the
  browser's `localStorage` (so it survives a reload on that browser). With no
  key set, the Summon button still works -- it generates a local random pattern
  instead of calling the model.

- **Ghatika -> Anthropic.** The browser POSTs to
  `https://api.anthropic.com/v1/messages` with your key in the `x-api-key`
  header (model `claude-sonnet-4-20250514`). Your key is entered in the top key
  bar and held **only in that tab's memory** for the session -- it is not saved
  to disk or `localStorage`, so closing the tab clears it.

In both cases the key is **entered by you, stored only in your own browser, and
sent only to the AI provider.** It is never committed to this repo and never
passes through any server we run. The page source contains only placeholder
strings (`sk-or-...`, `sk-ant-...`).

### Trying the AI by hand

The AI features cannot be tested automatically (they need a paid key), so verify
them yourself:

- **V0ID_SCALE:** open the page, paste an OpenRouter key (`sk-or-...`) into
  "AI Key", optionally change the model, type a vibe into the prompt, and click
  Summon. Expect a "Summoning..." status, then "Summoned N notes", a new entry
  in the loop list, and audible playback. With no key, Summon produces a local
  random pattern and a "add an OpenRouter key for real AI" notice.

- **Ghatika:** open the page, paste an Anthropic key (`sk-ant-...`) into the top
  bar, click "set key" (status becomes "key set for this session"), then use
  "AI compose" for an 8-bar phrase or start the "AI DJ" to have it steer the
  controls live. Live MIDI out and the AI both require a real hosted/local page
  (a chat-preview sandbox blocks them).

---

## Run locally

These are static single files. Two ways to run them:

1. **Just open the file.** Open `public/index.html` (a small menu) or either
   instrument directly in a browser. Ghatika pulls React, Tone.js, and Babel
   from a CDN, so it needs an internet connection on first load.

2. **Serve the folder.** The `start` script runs `serve public -l $PORT`:

   ```sh
   npm install
   PORT=3000 npm start        # then visit http://localhost:3000
   ```

   On Windows PowerShell: `$env:PORT=3000; npm start`.

## Deploy

The repo is a static site (`package.json` + `public/`). To put your own copy
on Railway:

```sh
railway up
```

(The maintainer deploys to an existing Railway service with
`railway up --service <service> --environment production --detach`.)

## Download / fork a single file

Each instrument has a button that downloads its own complete HTML
(V0ID_SCALE: "DOWNLOAD .HTML"; Ghatika: "download .html"). The downloaded file
is the whole instrument -- open it, edit it, or host it anywhere.

---

## Repo layout

```
README.md
package.json            static-serve config (serve public -l $PORT)
.gitignore
public/index.html       two-link landing menu
public/voidscale.html   V0ID_SCALE Labs (one file)
public/ghatika.html     Ghatika (one file)
docs/VOIDSCALE.md       what V0ID_SCALE does and how its AI works
docs/GHATIKA.md         what Ghatika does and how its AI works
```

---

## Known limitations / roadmap

These are honest current gaps, listed so nobody is surprised:

- **V0ID_SCALE transport is partial.** Play / Stop / Record toggle state, but
  Play does not yet sequence the saved loops, and the Euclidean panel is a
  visualizer that is not yet sonified. Recording captures live pad input.

- **V0ID_SCALE WAV/MIDI export is simplified.** It currently downloads a minimal
  placeholder file rather than a full render of your audio. By contrast,
  **Ghatika's MIDI and WAV export are full**: a hand-written Standard MIDI File
  (drums on GM channel 10, melody on channel 1) and a deterministic offline
  audio bounce.

Full sequencing and a real V0ID_SCALE render are intentional future work; they
need a human ear and are out of scope for this release.

---

## Honesty and safety

All audio is **synthesized** -- nothing here is a recording or a sample pack.
Entrainment effects (binaural / monaural / isochronic) are **subjectively
reported, not clinically established.** Ghatika's rhythm styles are **structural
homages, not anyone's sacred repertoire.** This is **not a medical device.**
