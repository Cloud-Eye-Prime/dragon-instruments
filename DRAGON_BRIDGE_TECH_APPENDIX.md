# Dragon Bridge -- Technical Appendix

Companion reference for `public/tempo_mixer.html` (the mixer) and `deploy/grabber/app.py`
(the grabber). Anchors are function/variable NAMES (stable), not line numbers (which drift).
Authored 2026-07-07. Read `DRAGON_BRIDGE_CONDUCTOR_PLAN.md` for the build narrative and
`DRAGON_BRIDGE_WORKFLOW_PATTERNS.md` for the process that produced this.

## 0. Thesis: infinite variety = combinatorial certainty, not LLM improvisation
A 90-minute never-repeating set comes from deterministic engines multiplied together, NOT
from asking an LLM to improvise every move:
- a **self-avoiding Camelot key-walk** (harmonically legal, energy-directional),
- a **no-repeat track ledger** + a **recipe deck dealt without replacement**,
- **SoundTouch** stretch/key-shift turning one track into many usable neighbors.
The LLM (Conductor) is used ONLY pre-roll (plan the arc, name artists) and as a live
performer (AI DJ) -- never as the source of variety. Everything load-bearing is seeded and
reproducible (`mulberry32`).

## 1. Clock -- ONE lookahead scheduler (Phase 0)
`clockScheduler()` is the single Web-Audio lookahead loop (replaced two drifting
setIntervals). Globals: `SCHED_AHEAD` (0.15s), `SCHED_TICK` (25ms), `nextBeatTime`,
`beatCount`. `startClock()`/`stopClock()` manage the timer. Each tick advances beats while
`nextBeatTime < ctx.currentTime + SCHED_AHEAD`, and from ONE place drives: the dragon-bus
clock post, `djTick`, the conductor beds (`conductorStep` x2/beat), the key-walk advance,
`conductorCheckMovement`, live-loop capture, `loopFxTick` (per bar), and the ai-loop 16ths.
Never block the audio thread; all param writes are ramped (`setTargetAtTime`).

## 2. Layer 1 -- seeded synth beds
`startConductorBeds()`/`stopConductorBeds()` gate `conductor.bedsOn`; `conductorStep(when)`
schedules bed notes via `composerNote(ch,midi,vel,dur,when)` (oscillator voices from
`ensureComposer`). `mulberry32(seed)` + `bedWalk()` give a seeded, non-cyclic walk
(fixed the old `sc[bar%len]` repeat). `conductor.scale`/`conductor.root` set the key.

## 3. Layer 2 -- deterministic Camelot stepper
- Keys: `CAMELOT_TO_KEY`, `KEY_TO_CAMELOT`, `camelotParse`, `camelotToKeyName`,
  `keyNameToCamelot`.
- `camelotNeighbors(code)` returns `[stay, clockwise(+1h), counter(-1h), relative(maj/min)]`.
- `keyScore(a,b)` -> 0..100 harmonic gradient (100 same, 90 rel, 85 +/-1h, 70 rel+1h, 60
  +/-2h, 55 +/-5h dominant, else falls off; a clash scores low). Research-calibrated.
- `nextKey()` is ENERGY-DIRECTIONAL: clockwise/dominant when `conductor.energyDir>0`,
  counter-cw/subdominant when `<0`; self-avoiding via `stepper.visited` (VK ring), honors
  `conductor.keyBias` (A/B). `stepper.rng` seeds it.
- `RECIPES` (12 archetype names) + `nextRecipe()` deals without replacement; `stepper.deck`.
- Track ledger: `trackUsable(id)` / `markTrack(id)` (no-repeat).

## 4. Layer 3 -- corpus pool + curation
`pool` (bounded ~80). `manifestToRec(id,title,url,manifest)` normalizes a grabber manifest
to a pool record (tempo, camelot, density, loudness). `poolAdd(rec)` dedups by id.
`preFilter(camelot,densLo,densHi,n)` filters candidates to Camelot-legal (`keyScore>=55`,
clashes excluded) AND density-in-band AND fresh, then RANKS descending by `keyScore`.
`prefetchQueries(queries,n)` runs the grabber `q=` search lane and pools the results.

## 5. Spine + movement
`auditSpine(plan)` normalizes the arc into blocks `{phase,bars,density,focus,queries}`.
`conductor.blocks/blockIdx/blockStarts/densLo/densHi/energyDir`. `conductorCheckMovement(setBar)`
advances at block boundaries: sets `energyDir` from density delta, updates the density band,
prefetches the NEXT block, and calls `conductorLoadNext()`. `conductorLoadNext()` pulls a
pre-filtered candidate, loads it (`addFileChannel` + `attachManifest`), and -- Feature 1 --
schedules a transition from `conductor.nowPlaying` when `dj.on`.

## 6. Genre spectrum (38 genres)
`GENRES[]` -- each `{n, k:[keyword patterns], bpm:[lo,hi], mode:'A'minor|'B'major|null,
ph:phraseBars, e:[start,peak,end 0..1], tr:[preferred transitions], half?:1}`. Specific
subgenres precede generics so `genresIn(text)` (all matches) / `genreFor(text)` (first)
resolve correctly. `half:1` marks written-fast/felt-slow genres (dubstep+subgenres, future
bass, DnB, hip-hop) -- the tempo-bridge flag. Wired in `conductorPlan`: mode->keyBias,
bpm-clamp, blend detection + half-time-bridge log.

## 7. Transition param-curves (Feature 1)
`TRANSITION_CURVES` -- 7 techniques (`bass_swap` 4b, `filter_fade` 8b, `echo_tail` 16b,
`double_drop` 16b, `loop_roll` 8b, `backspin` 2b, `half_time` 16b), each a list of bar-by-bar
moves `{bar, ch:'out'|'in'|'xf', param, to}` in KNOB semantics (0..1). `pickTechnique(energyDelta,
genre)` selects by an energy-band matrix (`ENERGY_TECH`), preferring a genre `.tr` that is a real
curve, with `nextRecipe()` variety (`RECIPE_TECH`). `scheduleTransition(outId,inId,technique,
startBar)` queues `djApplyMove`-shaped moves into `dj.plan` keyed by ABSOLUTE bar (matches
`djTick`), sets `dj.coolUntil` past the window so the AI DJ DEFERS (no fighting), bumps
`dj.plannedThrough`, and does NOT force `dj.on` (so a human grab is never re-hijacked).
`conductorLoadNext` gates the call on `dj.on` and starts the incoming fader at 0.03 so the
fade-in curves have silence to raise. KEY INVARIANT: `dj.plan` is keyed by
`Math.floor(beatCount/4)` (absolute), which is what `djTick(bar,beat)` reads.

## 8. AI-mode looper -- covers ANY style (Feature 2)
`AILOOP_STYLES[]` maps keyword sets -> `{scale, pat, oct, dens, timbre}` (repurposed from the
ghatika engine's scales/ragas x melodic patterns). `aiLoopStyleFor()` picks from the chat
intent or conductor genre (falls back to the session scale). `aiMelSeq(pat,scLen,n,R)`
generates degrees for pat in {scale, raga, arp, melody, fifths}. `aiLoopSeed(style,sc)` lays a
sparse in-scale 16-step pattern. `aiLoopStart/aiLoopStop`. `aiLoopEvolve()` Markov-mutates by
scale degree (0.4 stay / 0.2 +1 / 0.2 -1 / 0.2 +/-2) + velocity nudge + add/drop, bounded to
<=16 notes. `aiLoopTick(when,step16,barAbs)` plays matching-step notes via `composerNote`,
follows `conductor.root`, and evolves every `evolveBars` (the genre phrase). Toggled by `#llAI`;
it is a composer channel -> mixable, FX-able (Feature: per-loop FX), pinnable.

## 9. Swing (natural groove)
`SWING` (0.50 straight .. 0.72). Model (MPC/Ableton): swing delays the 2nd 16th of each
8th-note pair by `(2*S-1) * sixteenth`. Applied in `clockScheduler`: the ai-loop off-16ths
(odd `_i`) are delayed, and the conductor beds off-8th by `(S-0.5)*spb`. `#swingIn` slider;
`conductorPlan` auto-sets a genre default (house/hip/garage ~57, jazz/blues ~62, trance
straight). Real audio tracks keep their own groove -- swing shapes the SYNTH layer.

## 10. Per-loop FX, pin/modify, half-time bridge
- **Per-loop FX** (`loopFxTick`): each channel with `ch.fxAuto` (set on loop + ai-loop
  channels, seeded by `ch.fxSeed`) gets its OWN filter+reverb LFO once per bar, independent
  of the AI DJ. A pinned loop is skipped.
- **Pin** (`ch.pinned`): `djApplyMove` returns early for a pinned strip (xfade with
  `strip:null` still applies). The rack click handler toggles pin BEFORE the GRAB=YIELD
  `djStop` (with early return) so pinning protects one channel without stopping the set.
  `scheduleTransition`/`conductorLoadNext` never target pinned or loop channels.
- **Half-time bridge** (`conductor.halfBridge`): set in `conductorPlan`'s genre block when a
  blend mixes a `half:1` genre with a non-half one -- there it anchors session tempo to the
  SLOWEST non-half genre (via `_slow.reduce`) and sets `conductor.halfBridge=true`.
  SEPARATELY, `conductorLoadNext` reads that flag and sets `ch.match=true` (then
  `syncStretch`/`applyRate`) so the fast incoming track sits at ~half tempo under the anchor.

## 11. Live-loop human/AI + latency calibration
`liveIn = {stream,src,proc,sink,armed,bars,capturing,L,R,target,mode,cal,calSec}`.
`liveLoopInput` opens the mic; `armLoopCapture`/`beginLoopCapture`/`finishLoopCapture` capture
exactly N bars on a downbeat (never routed to master -> no feedback). `#llAI` flips
`liveIn.mode` (human capture vs `aiLoopStart`). `calibrateLatency()` clicks through master,
captures the mic (cal branch in `onaudioprocess`), and `finishCalibration()` finds the click
peak -> `liveIn.calSec`; `finishLoopCapture` trims by `calSec` (falls back to
`ctx.baseLatency+ctx.outputLatency`). `#llCal` button.

## 12. WAV recording
`recStart()` taps `masterLim` (the master limiter -- see 18.6, post-fader/post-limiter so the
recording matches what is heard) with a ScriptProcessor into `rec.L/rec.R`; `recStop()` flattens,
`encodeWAV(L,R,sr)` writes a valid 16-bit PCM stereo RIFF/WAVE Blob, and downloads it. `#recBtn`.
(`encodeWAV` uses `ctx.sampleRate`, so headless 48kHz renders are valid.)

## 13. Chat / Conductor
- `conductorPlan()` -- the chat entry. Detects URLs (`extractUrls`), grabs them
  (`grabLinksToPool` -> pool), strips them from the intent, then plans via `aiChat(CONDUCTOR_SYS,
  ...)` when descriptive text + a key/beta exist, else `defaultPlanFromPool(descr)` (keyless:
  key/bpm from freshest pooled track + rising 4-block arc + pad/bass beds + pooled titles as
  queries). Applies the plan (key, bpm, beds, spine), prefetches block 0, and `djStart()`s.
- **Autonomous lookup**: `CONDUCTOR_SYS` instructs naming real artists/songs in per-block
  `queries` -> `prefetchQueries` -> grabber `q=` -> pool. `conductorSteer()` (Phase 7) nudges
  the remaining spine mid-set with no LLM call.
- `aiChat(sys,usr,maxTok)`: local Anthropic key (`localStorage.dragonbridge_ant_key`) OR the
  grabber `/ai` relay (OpenRouter house key, beta-gated via `X-Dragon-Beta`). `parseAiJson`,
  `aiBusy` single-flight.
- **GRAB=YIELD**: any performance touch (`startDrag`, rack `.tog/.grp/.mini` click, xfader
  pointerdown) calls `djStop('manual override')` -> drops to Console, beds keep sounding, the
  human inherits the live mix. Pin is exempt (handled before the djStop reflex).

## 14. DJ engine
`dj = {on,plan,plannedThrough,intents,requesting,coolUntil}`; `DJ_LEAD=2`, `DJ_WINDOW=4`.
`djTick(bar,beat)` applies `dj.plan[bar]` on the downbeat and, when the horizon is short and
not cooling, calls `djRequest(bar)` -> `aiChat(DJ_SYS,...)` -> queues moves. `djApplyMove(mv)`
applies `{bar,strip,param,to,beats}` via `applyKnob`/`recomputeGains`/`animXfade` (pinned
skipped). `DJ_SYS` carries 3 few-shot exemplars (craft, restraint, section-aware entry).

## 15. Grabber (`deploy/grabber/app.py`, Railway `dragon-grabber`, python:3.12-slim)
- `/grab?url=|q=&start=&end=&analyze=` -- yt-dlp fetch (url or ytsearch) -> mp3 under
  `/audio/{id}.mp3`; `analyze=1` runs librosa -> `dragon-mix-manifest/1` (tempo+beatgrid,
  Camelot key, LUFS, density sections, class/music-confidence).
- `/ai` -- provider-aware relay (OpenRouter chat/completions normalized to Anthropic
  `{content:[{type:text,text}]}`), beta-gated (`X-Dragon-Beta`), model allowlist (`AI_MODELS`).
- `/audio`, `/health`, `/diag`, `/analyze`. Env: `OPENROUTER_KEY`, `ANTHROPIC_KEY`, `AI_MODEL`,
  `AI_MODELS`, `BETA_TOKEN`, `YT_COOKIES_B64`, `COOKIES_FILE`.
- CORS caveat: cross-origin browser audio needs ACAO; the true-render pipeline sidesteps it by
  serving grabbed mp3s SAME-ORIGIN from `public/_mixaudio/` (temp, gitignored).

## 16. Deploy
- Mixer/site: Railway service `heartbeat-pages` (static `serve public`).
  `railway up` from repo root; probe `https://heartbeat-pages-production.up.railway.app/tempo_mixer`.
- Grabber: Railway `dragon-grabber` (its OWN repo/source -- do not cross-deploy).
- NON-NEGOTIABLE: ASCII-only source; single self-contained mixer file (+ vendored SoundTouch
  under `public/vendor/`); reuse the existing AI/undo/clock paths; verify the DEPLOYED artifact.

## 17. Files
- `public/tempo_mixer.html` -- the mixer (all of the above; ~1100 lines, one inline `<script>`
  + a SoundTouch `<script type=module>`).
- `public/voidscale.html`, `public/ghatika.html` -- sibling instruments (ghatika is the source
  of the scale/rhythm/melody library repurposed by the looper).
- `public/conductor.html` -- the split shell (left chat / right mixer iframe, postMessage).
- `public/index.html` -- 3-tile landing.
- `deploy/grabber/app.py` -- the grabber (separate repo/service).

---

## 18. Addendum (2026-07-07): real-loop lead, voice, search-ranking, length-on-command

Post-original-appendix work. The through-line: the oscillator synth is demoted to ambience;
the musical lead is now REAL curated audio; search is ranked; sets can be any length on command.

### 18.1 AI instrument voice (composerNote) -- refined, and demoted to ambience
`composerNote(ch,midi,vel,dur,when)` was a single raw oscillator with an instant-onset gain
(a click per note) and no filter -- it read as "video-game synth." Now it is a proper voice:
soft ADSR (no click), a per-note lowpass that opens on attack then eases (warmth + movement),
a sub sine for body, and REAL synthesis per timbre -- fm = sine carrier + decaying modulator,
pluck = tri+saw + fast filter decay, saw = detuned supersaw pair + sub, square/reed = square
softened by a triangle. BUG fixed: timbres 'saw'/'fm'/'pluck'/'am' are INVALID OscillatorType
values (only sine/square/sawtooth/triangle are legal) -- they threw, so those styles' loops were
silently failing. Per Architect direction the oscillator voice is now for **ambient beds only**,
never the lead.

### 18.2 Real-loop LEAD mode (`lead`, OPT-IN) -- the melodic lead is real audio
`lead={on,pool,every,startBar,chId,phraseCount}`. The lead is a melodic layer built from REAL
recorded loops, not oscillators -- the DJ engine applied to a topline:
- `leadStart(intent)` grabs short real phrases via the grabber, using per-genre MUSICAL queries
  (`LEAD_QUERIES`: raga->sitar/bansuri, jazz->sax lick, deep house->soulful vocal chop, trance->
  pluck/arp, dubstep->vocal chop/future-bass lead, ambient->pad, ...; generic fallback).
- `leadLoad()` loads a pool loop as a channel, **key-shifts it to the session key + tempo-locks**
  via `syncStretch` (SoundTouch, `keyDeltaSemitones`, bounded +/-6 st) -- not tempo-only -- sits
  it UNDER the main track via `leadFader()` (rides the current block density 0.26..0.54 + jitter,
  soft 1.2s entrance), and places it in the mix (mild high-cut filt 0.42 + rev 0.14).
- `leadPhrase()` (scheduler, every `lead.every` bars = the genre phrase, min 16) rotates the loop
  and RESTS every 3rd phrase so the lead BREATHES like a real topline instead of droning.
- OPT-IN: `#llLead` toggle; the Conductor engages it only when the chat asks for a
  lead/melody/solo/riff. Default stays DJ-mixing real audio; oscillator synth = ambience only.

### 18.3 Grabber: ranked search (search wisely)
`deploy/grabber/app.py` q-lane now RANKS N candidates instead of `ytsearch1`. `_flat_search`
(yt-dlp `--flat-playlist -J`, no download) -> `_score` = log(views) + duration-fit-per-kind
(`_duration_band`: loop 4-30s / track 90-420s / set 20-90min) + AI-slop penalty (suno/udio/aiva/
"ai generated"/...) + non-music penalty (reaction/interview/tutorial/...) -> grabs the BEST.
New params `kind=`(loop|track|set|inferred via `_infer_kind`) + `rank=`; response gains
`picked{views,duration,uploader,considered,kind}`. Legacy `url=`/`rank=0`/`/audio`/`/health`
unchanged. NOTE: YouTube exposes views/duration/uploader via yt-dlp but NO machine
AI-generated flag -- that disclosure is a self-reported UI label, so slop is heuristic-only.
The mixer passes `kind=track` for conductor tracks and `kind=loop` for lead loops.

### 18.4 Length on command
`parseLength(t)` reads a target from the chat ("45 min" / "1 hour" / "90 min" / "half an hour",
capped 90). `conductorPlan` prompts ONCE if no length is given (`conductor.pendingIntent`), then
defaults to **24 min** on the reply (or a bare number). The spine is SCALED to fill
`conductor.targetSec` at the session bpm (block bars * targetBars/sumBars), and the set ENDS at
the target via `conductorStop`. So the Conductor makes a mix of any length under 90 minutes on
command.

### 18.5 Access
The grabber `/ai` relay and beta-gated features use header `X-Dragon-Beta` = the `BETA_TOKEN`
Railway var (the shareable beta code held server-side; never the OpenRouter/Anthropic key).

## 19. Addendum (2026-07-08): master limiter, agentic /conduct, premium models, deep plan

### 19.1 Master-bus limiter
`startAudio()` inserts `masterLim = ctx.createDynamicsCompressor()` (threshold -3 dBFS, knee 0,
ratio 20, attack 3 ms, release 250 ms) right after the `master` gain. EVERY downstream tap now hangs
off `masterLim`, not `master`: the analyser->destination (audible), the `streamDest` (webm), the loop
`proc`, and the WAV `rec.proc`. So what you hear AND what is recorded are both limited. It is transparent
above -3 dBFS (clean mixes untouched) and only clamps when two loud masters sum past full scale during a
transition -- which was producing digital clipping before (a hot techno render measured rms 0.554/peak 1.0).

### 19.2 Agentic conductor planning -- grabber `POST /conduct`
A tool-use loop (OpenRouter) that gives the planning model search tools so it verifies + adjusts track
picks against real YouTube availability before the set. Tools: `search_tracks` (flat-search + score ->
candidates with title/uploader/views/duration/fit/studio_likely) and `finalize_plan` (the arc). Returns
the SAME plan shape `conductorPlan` consumes (`{session_key,session_bpm,arc:[{phase,bars,density,focus,
queries}],note}`) plus a search `trace`. Beta-gated; `max_steps` + a per-plan search cap bound cost. This
fixes the failure where a niche/unfindable request silently produced no tracks -- the model now sees
availability and pivots. The grabber `_score`/`_LIVE_WORDS` also down-rank single-song LIVE recordings and
visualizer/festival uploads (glastonbury/coachella/kexp/boiler room/unplugged/...) for `kind=track`, so
the studio master wins.

### 19.3 Premium models
`anthropic/claude-opus-4.8` and `anthropic/claude-sonnet-5` are in the `AI_MODELS` allowlist -- added in
CODE (`app.py`), not the Railway var, because a var change triggers a rebuild from the connected GitHub
source. They shine on `/conduct` (deep planning taste). Opt-in; the tool loop on a premium model is the
priciest path (shared OpenRouter key) -- watch spend.

### 19.4 Deep-plan toggle (mixer)
The Conductor bar has a `deep` toggle (`#cvDeep`) + a planning-model `<select>` (`#cvModel`, populated
live from grabber `/diag`, so Opus 4.8 / Sonnet 5 are selectable). When deep is on, `conductorPlan` routes
to `conductorDeepPlan()` -> `POST /conduct` with the selected model and falls back to the quick one-shot
`aiChat` plan on any failure. Both controls are hidden in `?embed` (the shell has its own). Opt-in; the
default stays the fast one-shot plan.
