# CLAUDE.md -- dragon-instruments (Dragon Bridge mixer)

You are working on the Dragon Bridge tempo mixer. READ `DRAGON_BRIDGE_CONDUCTOR_PLAN.md` in this
repo root FIRST -- it is the authoritative build plan. This file is the quick orientation.

## What this repo is
Static site served by `serve public` (package.json). Only `public/` is served. Three pages:
- public/tempo_mixer.html  -- THE MIXER you are building (single-file vanilla JS, ~527 lines). This is the work.
- public/voidscale.html, public/ghatika.html -- sibling synth instruments (do not touch unless the plan says so).
- public/index.html -- the 3-tile landing menu.
Root files (README, package.json, this file, the PLAN) are NOT served -- harmless to commit.

## Your work is Phases 2-5 of the PLAN (Phase 1 is the grabber, a separate dir)
All mixer phases edit the SAME file (public/tempo_mixer.html) -- do them serially, never in parallel.

## NON-NEGOTIABLE constraints (full list in the PLAN; the load-bearing ones)
- ASCII ONLY in source. Use `--` for dashes, straight quotes. No em-dashes/curly quotes/emoji. Inherited-Unicode codebase.
- Mixer stays ONE self-contained HTML file with vanilla JS. The ONLY allowed extra file is a vendored library under public/vendor/ loaded by <script src>. No build step, no framework, no npm for the mixer.
- Reuse the EXISTING AI path for every new AI call: `aiChat(sys,usr,maxTok)` -> api.anthropic.com/v1/messages with header `anthropic-dangerous-direct-browser-access: true`, key from `localStorage.dragonbridge_ant_key`, model `dragonbridge_ant_model`. Do NOT add a second provider. Re-use `parseAiJson` and the `aiBusy` single-flight.
- NEVER block or compute on the audio thread. All param writes go through the ramped paths (`applyKnob` / `recomputeGains` / `setTargetAtTime`). Live moves schedule bars ahead on the existing clock (the `djTick`/`djApplyMove` pattern).
- Every AI/auto change is reversible: `pushUndo()` before apply, `applyMixState()` to revert. Keep undo working.
- RIGHTS: copyrighted YouTube content is ACCEPTABLE. Do NOT add any rights/licensing gate. Validation is integrity/quality only. The planner may name and fetch real artists/songs.
- Backward compat: the current Console (manual rack + auto-mix + NL command + scenes + AI DJ) must keep working unchanged. New modes are additive.
- One concern per commit. Verify the DEPLOYED artifact after deploy, not the source.

## Real anchors in public/tempo_mixer.html (edit against these names, not from memory)
- Model: `channels` (Map id->ch), `order` (array), `buildChannel(opt)`, channel types composer|capture|file.
  ch fields: id,type,name,fader,mute,solo,group(L|R|null),k{high,mid,low,filt,rev,dly,pan},timbre,audio,track,srcBPM,match,nodes{inGain,eqLow,eqMid,eqHigh,filter,chGain,panner,an,delay,fb,dlySend,conv,revSend},data,els.
- Sources: `captureSource()` (getDisplayMedia), `addFileChannel(url,name)` (Audio->MediaElementSource), `loadUrl()`,
  `grabYouTube()` -> fetches `$('grabBase').value` (default https://dragon-grabber-production.up.railway.app) `/grab?url=...&start=&end=`, then `addFileChannel(base+d.file,title)`.
- Clock/frame: `bpm()`, `startClock()/stopClock()`, `beatCount`, posts `{type:'clock',bpm,beat}` on `bc=new BroadcastChannel('dragon-bus')`; `doResync()`. dragon-bus consumer is `handleBus()` (hello/note/bye); composer voices via `ensureComposer`/`composerNote` (oscillators).
- Current tempo-match: `applyRate(ch)` uses pitch-preserved `playbackRate=bpm()/srcBPM` (file channels, toggled by `ch.match`). Phase 2 upgrades this to SoundTouch stretch+pitch-shift; keep applyRate as fallback.
- AI/state: `aiChat`,`parseAiJson`,`aiBusy`; `captureMixState()`/`applyMixState(st)`/`clampAiMix(json)`/`bandRead(c)`/`MIX_SCHEMA`/`pushUndo()`/`doUndo()`.
- Features to extend, not replace: `autoMix()`, `aiCommand()`, scenes (`scenes`,`sceneSave`,`sceneRecall`,`aiVibe`).
- AI DJ engine (reuse for Conductor performance): `dj` state, `DJ_SYS`, `DJ_LEAD=2`, `DJ_WINDOW=4`, `djTick(bar,beat)`, `djRequest(bar)`, `djApplyMove(mv)`, `animXfade(to,sec)`, `djStart()/djStop(reason)`.
- GRAB=YIELD primitive (the mode-transition spine, already wired): every console touch calls `djStop('manual override -- your hands win')` (in `startDrag`, the rack click handler, and the xfader pointerdown). Conductor mode reuses this: a touch drops to Console inheriting live state.

## Validate every edit before commit
- Extract the <script> and run it through `node --check` (or `new Function(src)`); fix any syntax error.
- Assert ZERO non-ASCII bytes in the file.
- Confirm the page loads with no console errors and the existing Console still works.

## Deploy (this service does NOT auto-deploy)
1. `railway status` here -> must print Service: heartbeat-pages (Team-CoachAI / production). If missing, re-link (see PLAN, Railway section).
2. commit (one concern), then `railway up` from this dir.
3. Probe https://heartbeat-pages-production.up.railway.app/tempo_mixer.html -> 200, and exercise the changed feature live. Verify the deployed artifact, not just the commit.

Wu ji nei gong. See it. Seize it. Secure it.
