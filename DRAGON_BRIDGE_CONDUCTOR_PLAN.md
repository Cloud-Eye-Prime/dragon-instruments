# Dragon Bridge -- Conductor Build Plan (for Claude Code)

Author: Cloud-Eye Opus (Desktop), discovery-grounded against live source.
Two working trees:
- MIXER  = C:\Users\grego\Desktop\CloudEye\production\dragon-instruments\public\tempo_mixer.html  (single-file, vanilla JS, 527 lines)
- GRABBER = C:\Users\grego\Desktop\CloudEye\deploy\grabber  (FastAPI, app.py 109 lines, Dockerfile build)

Live facts (verified this session):
- Mixer served by Railway service heartbeat-pages (project Team-CoachAI), deployed by manual `railway up` from the dragon-instruments repo. NOT auto-deploy. HEAD 2368180.
- Grabber live at https://dragon-grabber-production.up.railway.app -- ffmpeg + ffprobe at /usr/bin, yt-dlp 2026.03.17. Deployed by manual `railway up` (Dockerfile builder).
- Mixer AI path is Anthropic-direct (api.anthropic.com/v1/messages, anthropic-dangerous-direct-browser-access), key in localStorage key `dragonbridge_ant_key`, model `dragonbridge_ant_model` (default claude-sonnet-4-6). Re-use this exact path for all new AI calls. Do NOT introduce a second provider.

## NON-NEGOTIABLE CONSTRAINTS (read first; every phase obeys these)
1. ASCII ONLY in all source. Use `--` for dashes, straight quotes. No em-dashes, curly quotes, or emoji in code. (Inherited-Unicode codebase law.)
2. Mixer stays a single self-contained HTML file with vanilla JS. The ONE allowed exception: a vendored library file under public/vendor/ loaded by <script src>. Do not add a build step, a framework, or npm to the mixer.
3. Browser-to-provider direct, BYO key, key never leaves localStorage; nothing auto-spends the key without a user gesture EXCEPT an explicitly engaged live mode (AI DJ / Conductor), which the user turns on and any console touch turns off. Re-use aiChat/parseAiJson/aiBusy single-flight.
4. All audio-param writes go through the existing ramped paths (applyKnob / recomputeGains / setTargetAtTime). NEVER block or compute on the audio thread. Live moves are scheduled bars ahead on the existing clock (the djTick/djApplyMove pattern).
5. Every AI/auto change is reversible: pushUndo() before apply, applyMixState() to revert. Keep the undo stack working across new features.
6. RIGHTS: copyrighted YouTube content is ACCEPTABLE at this stage. Do NOT add any rights/licensing filter or gate. Validation is QUALITY/INTEGRITY ONLY (decodes, not silent, music-vs-speech, beat/key confidence). The planner may name real artists/songs/albums and the grabber may fetch them. Tier-gates and legal posture are explicitly out of scope and deferred.
7. Verify the DEPLOYED artifact after each deploy (probe the live endpoint), not just the source. One concern per commit. After committing to dragon-instruments, the mixer must be deployed with `railway up` (it does not auto-deploy).
8. Backward compatibility: the current Console (manual rack + auto-mix + NL command + scenes + AI DJ) must keep working unchanged. New modes are additive.

## PRODUCT SHAPE: two clear modes, one engine
Same Web Audio graph and toolkit underneath; the modes differ only in who holds the wheel and which surface is foreground. A header segmented control switches them. The switch is STATEFUL -- never resets the graph or loaded channels.
- CONSOLE (Human-AI) = the current setup. Rack foreground; human drives; AI on tap (auto-mix, NL command, scenes, AI DJ).
- CONDUCTOR (Full AI) = chat foreground; the user types what artists / songs / albums / styles / moods they want; the AI acquires audio (YouTube via the grabber) plus optional synth beds, locks everything to a common BPM/key/bar frame, and live-mixes a set using the existing DJ engine, narrating moves. The rack recedes to a live "what the Dragon is doing" view.
- TRANSITION (the key primitive, already half-built): touching any console control yields control. Today every drag calls djStop('manual override'). Extend that so in Conductor a console touch drops to Console mode inheriting the exact live state, sound continuous. Console->Conductor hands the current channels to the planner as its starting state.

The grabber cannot generate a named artist; Conductor is the AI ORCHESTRATING the existing toolkit (grabber + synth voices + the mix engine) from a chat intent. Keep that honest in copy.

---

## PHASE 1 -- Grabber analysis manifest + keyword search (GRABBER, do first)
Goal: the grabber stops being a fetcher and becomes an ear. Every grab can return an analysis manifest; the grabber can also search YouTube by keyword so Conductor can fetch from a phrase.

Files: deploy/grabber/app.py, deploy/grabber/requirements.txt (Dockerfile already installs ffmpeg; no Dockerfile change needed unless a system lib is required by a pinned wheel).

Changes:
1. requirements.txt += analysis libs. Use a pin set known to build on python:3.12-slim with numba/llvmlite resolving cleanly. Suggested starting pins (claude_code must verify they import in the container and adjust if numba/llvmlite fight 3.12): `librosa>=0.10.2`, `soundfile>=0.12`, `pyloudnorm>=0.1.1`, `numpy<2.1`, `scipy`. If numba install is heavy/slow, that is acceptable (build time grows; runtime is fine).
2. Add `GET /grab` support for keyword search: accept optional `q` param; when present and `url` absent, fetch via yt-dlp `ytsearch1:<q>` (first result). Keep existing url path intact. Return the same shape plus the resolved title.
3. Add `analyze` query to `/grab`: when `analyze` in (1,true,yes), after the mp3 lands, run analyze() and include `"manifest": {...}` in the JSON response. Default off (so the existing mixer path is unchanged until the mixer opts in).
4. Add `GET /analyze?file=<name>` (analyze an already-grabbed /audio/<name>) returning the manifest alone -- useful for re-analysis and for files grabbed without analyze=1.
5. Implement analyze(path) -> manifest using librosa + pyloudnorm:
   - decode via librosa.load(path, sr=22050, mono=True) (ffmpeg/audioread backend present).
   - integrity: duration, rms dBFS, peak dBFS, spectral_flatness (librosa.feature.spectral_flatness mean), onset regularity; derive class in {music,speech,silence,noise} and music_confidence 0..1 (heuristic: high flatness + low harmonic ratio + sparse/irregular onsets => speech/noise; near-silence by LUFS => silence).
   - tempo: librosa.beat.beat_track -> bpm + beat frames (to seconds). Set tempo.confidence from beat strength consistency. If confidence low, set beatless=true, bpm=null, beat_grid_s=null. downbeats_s: leave null in Phase 1 (madmom/GPU is a later tier); do not fake them.
   - key: chroma_cqt mean -> correlate against Krumhansl-Schmuckler major/minor profiles -> tonic + scale + confidence; map to Camelot. If confidence low, key=null.
   - loudness: pyloudnorm integrated LUFS; gain_to_target_db = target(-16) - lufs (clamped to +/-12).
   - sections: onset/novelty + librosa.segment (agglomerative or spectral clustering) -> ordered segments; per section compute density 0..1 (normalized RMS energy), onset_rate, harmonic_ratio (from librosa.effects.hpss energy split), rms_dbfs; label heuristically intro|build|drop|break|drone|outro from density trajectory.
   - loops: find bar-aligned (if bpm) low-discontinuity regions; for beatless material, find a long low-variance region as a seamless drone loop; each loop {start_s,end_s,bars|null,seamless 0..1,kind rhythmic|drone}.
   - dynamics: crest_factor, max_transient_db, no_startle bool (true when max_transient modest and onset density low -- the yoga/tai-chi safety flag).
   - mix: stretchable bool, max_stretch_pct (suggest +/-12), recommended_use list drawn from class/sections (e.g. drum_bed, drop, yoga_bed, drone, accompaniment).
   - stems: {available:false} (GPU/Demucs deferred).
   - validation: status in {verified (musical + confident grid + key), ambient_only (usable but beatless/low-conf), rejected (silent/speech/decode-fail/too-short)} + reasons[]. NOTE: NO rights logic. Copyrighted music is verified normally.
6. Manifest envelope: include `"schema":"dragon-mix-manifest/1"` and `"source":{file,title,query,duration_s,analyzed_at}`.

Verify (terminal conditions):
- `/grab?url=<4/4 dance clip>&analyze=1` -> status verified, bpm within +/-2 of truth, key plausible (allow relative major/minor), sections non-empty with density in [0,1], lufs present; completes < ~10s for a 90s section.
- `/grab?q=<artist phrase>&analyze=1` -> resolves a video, returns audio + manifest.
- `/analyze?file=<name>` on a spoken-word clip -> status rejected. On an ambient drone -> ambient_only + beatless=true + a long seamless drone loop.
- `/diag` and the legacy `/grab?url=...` (no analyze) still behave exactly as before.
- Container builds; librosa+numba import at runtime (check the deploy/build log).

Deploy: `railway up` to the dragon-grabber service (confirm the service link first; mirror the dragon-instruments deploy posture). Then probe live: /diag, a live /grab?analyze=1, a live /analyze. Confirm the manifest shape on the deployed artifact.

---

## PHASE 2 -- Mixer ingests the manifest + true time-stretch (MIXER)
Goal: grabbed tracks arrive analyzed and lock to the master tempo and session key without pitch artifacts.

Changes:
1. Vendor SoundTouchJS as public/vendor/soundtouch.min.js (committed -- sovereign, offline) and load it from tempo_mixer.html via <script src="vendor/soundtouch.min.js"></script>. This is the ONE allowed second file. If integrating SoundTouch as a live filter node is too costly, an acceptable v1 is: pre-render the stretched/shifted buffer once on load (offline) and play that buffer; re-render on master-bpm/key change (debounced). Keep the existing playbackRate path (applyRate) as the fallback when SoundTouch or a manifest is absent.
2. Extend the channel object (buildChannel opt + ch fields): add ch.manifest (null default), and use it. In grabYouTube(): call the grabber with `&analyze=1`, read d.manifest, attach to the channel; if manifest.tempo.bpm, set ch.srcBPM from it and set ch.match=true; apply manifest.loudness.gain_to_target_db to the initial fader/inGain so levels arrive sane.
3. Replace the file-channel tempo behavior: when a manifest with bpm exists and SoundTouch is available, stretch to master bpm() and pitch-shift by the semitone delta to the session key (see Phase 3); align playback start to the nearest downbeat/beat. Keep applyRate (playbackRate) as fallback.
4. Store sections on the channel for later use (Conductor + a manual "jump to section" affordance is optional here).

Verify: grab a known track -> manifest attached, channel tempo-matched to master bpm with no chipmunk/pitch artifact (SoundTouch), gain reasonable on arrival. Console, auto-mix, scenes, AI DJ all still work. File loads, ASCII clean, no console errors. Commit one concern; `railway up`; probe the live mixer loads and a grab still works end to end.

---

## PHASE 3 -- Common frame: tempo + key + bar, so everything plays together (MIXER)
Goal: grabs, internal synth voices, and (optionally) the sibling instruments share ONE musical frame, enabling live accompaniment.

Changes:
1. Session frame state: master bpm (exists via bpm()/clock), add sessionKey (string, e.g. "A:minor"/Camelot), and the bar grid (beatCount exists). Default sessionKey from the first verified grab's manifest.key; expose a small selector to override.
2. Every file channel with a manifest stretches to bpm() and shifts to sessionKey (delta semitones from manifest.key to sessionKey). Re-apply (debounced) when bpm or sessionKey changes.
3. Internal synth accompaniment: the mixer already has composer channels (ensureComposer/composerNote, oscillator voices). Add a helper to spawn an internal synth bed (a composer channel) and drive notes on the bar grid in sessionKey -- this is the rights-clean synth path, no external dependency. Conductor (Phase 4) uses it.
4. Optional (defer or include if cheap): add a dragon-bus SENDER to voidscale.html and ghatika.html (postMessage hello/note/bye on BroadcastChannel('dragon-bus')) so the mixer's existing handleBus auto-join finally has a sender and the instruments appear as composer strips. This touches the two instrument files; keep each as its own commit. The bus path re-synthesizes notes (MIDI-style), it is NOT the instrument's real timbre -- for real timbre, tab-capture remains the path. Document this.

Verify: two grabbed tracks plus one internal synth bed play beat-locked and key-compatible; crossfading between sections lands on the grid.

---

## PHASE 4 -- The two modes: Console (current) + Conductor (full-AI chat) (MIXER)
Goal: a clean mode toggle and a Conductor mode that turns a chat intent into a live, self-driven set.

Changes:
1. Header segmented control: Console | Conductor. State `mode`. Switching is stateful -- never tears down ctx/channels.
2. Conductor surface (shown only in Conductor mode): a chat input ("what do you want to hear? artists, songs, moods...") + a scrolling narration log; the rack visually recedes (dim/compact) into a live status view. Console controls remain present but de-emphasized.
3. conductorPlan(intent): one aiChat call with a CONDUCTOR_SYS schema returning ONLY JSON:
   {"queries":[string youtube search phrases], "synth_beds":[{"key":string,"role":string}], "arc":[{"phase":string,"bars":int,"focus":string}], "session_key":string, "session_bpm":int, "note":string}
   The model may name real artists/songs/albums in queries (rights are not filtered).
4. Execute the plan: set sessionKey/bpm; for each query call the grabber `/grab?q=<query>&analyze=1`, load each result as a file channel (Phase 2 ingest), reject only on validation.status=="rejected" (auto-skip + narrate), spawn synth_beds as internal composer beds (Phase 3). While audio acquires, start an immediate synth pad so there is never dead air; narrate "fetching ...".
5. Perform: reuse the AI DJ engine (djRequest/djApplyMove/djTick machinery) seeded by the Conductor arc to live-mix across the loaded channels -- section-aware (open on an intro, crossfade into a drop, sweep filters on transitions). One request in flight; bars-ahead scheduling; the same setTargetAtTime ramps.
6. Stateful switch + grab=yield: extend the existing djStop('manual override') hook so that, in Conductor, any console touch sets mode=Console and inherits the live state (sound continuous, AI performance paused). Console->Conductor passes current channels to conductorPlan as starting context ("continue from here: more energy").
7. Guardrails: one acquisition in flight, a sane cap on number of queries per plan, a visible cost reminder (uses the key), and the existing panic stops everything.

Verify: in Conductor, an intent like "moody downtempo, Bonobo and Tycho, slow build" -> planner emits queries -> grabber fetches+analyzes -> tracks load and frame-lock -> AI performs a live evolving set, narrating -> touching a fader drops to Console with sound continuous. Console mode unchanged. Commit per concern; `railway up`; verify on the deployed mixer.

---

## PHASE 5 -- Use-case modes: breath-led (yoga/tai chi) + Listener (musician)
Goal: bind the two named use cases. These are additive; the Listener can be deferred as its own dispatch.

Changes:
1. Time-authority selector (in Conductor): Session-led (AI picks bpm) | Human-led (Listener) | Breath-led (beatless).
2. Breath-led (yoga / tai chi): no bpm lock. The arc is class phase -- center, warm, flow, peak, cool, rest -- and the planner targets section density per phase. Transitions are slow gain/filter ramps over SECONDS (never hard cuts). Prefer manifests with validation.status=="ambient_only" and dynamics.no_startle, and seamless drone loops. Can run synth-only (rights-clean, and aesthetically right for class) or with grabbed ambient. Optional breath period (e.g. 6s inhale/exhale) drives synth swells instead of musical bpm. The cardinal failure to avoid: forcing a beat onto beatless material.
3. Listener (live musician) -- its own sub-module, may be a separate dispatch: startListener() via navigator.mediaDevices.getUserMedia({audio:true}) (parallels captureSource but mic/instrument input). Real-time: onset envelope autocorrelation -> tempo + downbeat phase; YIN/autocorrelation -> pitch -> key. It EMITS the session frame (bpm, key, bar phase) that grabs + synth beds lock to. It does NOT synthesize audio chasing the player; it cues pre-analyzed material to the player's grid (this is why Phase 2 stretchability is the prerequisite). Latency discipline: track phase, never render on the audio thread. A visible "following you" indicator.

Verify: breath-led runs a multi-minute synth-only arc with no startling transitions and no forced beat; Listener locks a grabbed loop to a live metronome/instrument tempo and key.

---

## ADVERSARIAL REVIEW (where this bites -- bake these in)
- Latency vs live: keyword->plan->grab->analyze->load is many seconds. Always open with an instant synth pad and narrate; the bars-ahead scheduler hides the gap. Never await in an audio callback.
- Detection error: beat/key on rubato/ambient/live material is unreliable. Confidence-gate everything; low confidence -> beatless/ambient_only, used as texture, never beat-locked. Relative major/minor confusion -> harmonic match is guidance, overridable.
- Stretch quality: SoundTouch artifacts at large ratios; cap to ~+/-12% and prefer choosing a closer-BPM grab over over-stretching.
- Hallucinated setlists: the planner will name tracks that mis-resolve on YouTube. Treat each grab as untrusted until its manifest lands; auto-skip rejected; one-tap replace; narrate what was actually loaded.
- Engine divergence: do NOT build a second audio path for Conductor. It drives the SAME graph and the SAME dj engine, or the modes rot apart.
- Cost: Conductor fires LLM calls continuously plus grabs. Debounce, cap, single-flight, show it spends the key, never auto-loop without a go. Any console touch stops it.
- Mode confusion: the toggle state and "who is driving" must be unmistakable; record/performance state loud (the B3 glanceable work already pushed this).
- Grabber disk is ephemeral (/tmp/grab wiped on redeploy) and CPU analysis is a few seconds; acceptable. Demucs stems + madmom downbeats are a later GPU tier (forge-compute), explicitly out of scope here.
- Single-file rule bends once (vendored soundtouch.min.js). That is the only allowed exception; justify it in a comment.

## RAILWAY DEPLOY -- LINKS RESOLVED (confirmed 2026-06-12)
Both working dirs are already `railway link`ed per-directory (verified independent -- linking one does not change the other). Claude Code on this machine/user inherits these links; no flags needed.
- deploy\grabber                  -> Team-CoachAI / production / dragon-grabber  (service 841cfbb4-5c89-4faf-9726-b083bf27c8c1, Dockerfile builder, https://dragon-grabber-production.up.railway.app)
- production\dragon-instruments   -> Team-CoachAI / production / heartbeat-pages (service 7de1006c-a9d4-4c89-824f-0ac9ad21606c, `serve public`, https://heartbeat-pages-production.up.railway.app)
- Project Team-CoachAI = f9a827e0-3416-4493-bf77-b67798fe32d2 ; environment production = ae89fd0d-e9b7-47cf-b157-285c58fd2a19.
GUARD before any deploy: run `railway status` in the dir and confirm the expected Service prints. Only then `railway up`. If a session runs under a different OS user/home and the link is missing, re-link non-interactively:
  railway link --project f9a827e0-3416-4493-bf77-b67798fe32d2 --environment production --service <dragon-grabber|heartbeat-pages>
NEITHER service auto-deploys from git. Mixer flow: commit to the dragon-instruments repo, THEN `railway up` from production\dragon-instruments. Grabber flow: edit deploy\grabber, THEN `railway up` from deploy\grabber (not a git repo). After deploy, probe the live domain (verify the deployed artifact, not the source).

## DISPATCH STRATEGY (how to deliver this to Claude Code)
- Two trees, so prefer working_directory = C:\Users\grego\Desktop\CloudEye and let absolute paths route. Or run as two dispatches: (A) GRABBER Phase 1 in deploy\grabber; (B) MIXER Phases 2-5 in production\dragon-instruments.
- Order: Phase 1 (grabber) must land and deploy before Phase 2 can be verified end to end (the mixer needs live manifests). Phases 2->3->4 are sequential (each builds on the last). Phase 5 can be a follow-on dispatch; the Listener is independently deferrable.
- All mixer phases edit the SAME file (tempo_mixer.html) -- serialize, do not parallel-dispatch them (collision).
- Each phase = its own commit(s), one concern each, with the verification run before commit. After the grabber commit: `railway up` to dragon-grabber + live probe. After mixer commits: `railway up` to heartbeat-pages (from production\dragon-instruments) + live probe of /tempo_mixer.html.
- Validate every edit: node --check the extracted <script>, assert zero non-ASCII bytes, confirm the file still loads with no console errors before committing.

## SUGGESTED FIRST DISPATCH
Claude Code, working_directory C:\Users\grego\Desktop\CloudEye\deploy\grabber, mode execute:
"Implement Phase 1 of DRAGON_BRIDGE_CONDUCTOR_PLAN.md (one dir up at ..\DRAGON_BRIDGE_CONDUCTOR_PLAN.md): add librosa/pyloudnorm analysis, the dragon-mix-manifest/1, ytsearch via q=, and analyze=1 on /grab, per the schema and verification there. Obey the NON-NEGOTIABLE CONSTRAINTS. Do not deploy; stop at green local verification and report the pin set that built."

Then Greg deploys the grabber and dispatches the mixer phases.

-- End of plan. The grabber becomes an ear; the mixer gains a second posture; the same engine serves a DJ set, a yoga class, and a live duet. Wu ji nei gong.

---

## ADDENDUM 2026-07-06 -- INSTRUMENT INTEGRATION LAYER (Cloud-Eye, in-repo, verified live)

Context: the two LXR-5 "music rooms" (backend/lxr/lxr_metal.py) were room specs only --
personas + tool_manifest + ui_skin, with NO instrument bodies. The DJ Room already has its
body here (tempo_mixer = dual decks + AI-DJ + Conductor mode). The Sound Lab had no body.
This addendum gives the Sound Lab a body and wires the standalone instruments into the
conductor's clock, WITHOUT touching the mixer engine (additive, backward-compatible).

DONE + verified in the browser preview (serve public, no deploy):
1. public/soundlab.html -- the Aleia "soundlab" room, self-contained (pure Web Audio, no
   Tone.js, no external host, zero non-ASCII bytes, node --check clean). 8x8 clip launcher:
   8 Wu-Xing-mapped voice rows (Kick/Bass/Snare/Hat/Crash/Tom/Pad/Lead) x 8 eighth-note
   columns = 1 bar at 96 BPM. Lookahead Web-Audio scheduler; live "throw" (tap a row name)
   lands quantized to the next 16th, per the room spec.
2. dragon-bus integration (the same BroadcastChannel('dragon-bus') the mixer already uses):
   - Sound Lab LISTENS for {type:'clock',bpm,beat} -> adopts the conductor bpm and realigns
     its phase to the downbeat (beat 1 -> column 0). Falls back to standalone after 1.5s of
     silence. This is the ghatika_sync contract, honored over the existing bus.
   - Sound Lab EMITS {type:'hello'|'note'|'bye'}. The mixer's handleBus() already maps
     note -> ensureComposer + composerNote, so every Lab hit is voiced as a live channel
     INSIDE the conductor's mix. Verified: posting a clock locked the Lab to 120 bpm and the
     Lab emitted note:Sound Lab back on the bus.
   - heartbeat.html: added a light, additive bus listener -- the five-element drone's core
     flashes on each conductor beat (drone stays free-running otherwise). Verified core
     r 47 -> 54 on a clock tick.
3. public/index.html -- unified launcher reordered with the Tempo Mixer named "(the
   conductor)" first, then Sound Lab, Heartbeat, Ghatika, V0ID_SCALE, Git Cosmos.

The result: opening the Tempo Mixer (Console or Conductor mode) and the Sound Lab in two
tabs gives one shared clock and one shared mix -- the conductor drives tempo, the Lab feeds
voices, the Heartbeat breathes along. The "unified ui-chat-conductor" now has clocked
instrument satellites.

REMAINING (unchanged, Architect-gated -- deploys + keys, NOT done here):
- Phases 1-5 of this plan (grabber librosa manifest, SoundTouch time-stretch, the Conductor
  full-AI chat mode, breath-led + Listener modes) still stand as specced. They edit the
  grabber + tempo_mixer.html and require `railway up` + live probes; not auto-run.
- Deploy of THIS addendum's files: `railway up` from production\dragon-instruments to
  heartbeat-pages, then probe /soundlab.html + /heartbeat.html live. (The instruments are
  verified on the local server; they are NOT yet on the live domain.)

## ADDENDUM 2026-07-06b -- PHASE 4 CONDUCTOR CHAT MODE (core, in-repo, verified)

Built additively in tempo_mixer.html (Console preserved, no engine teardown):
- Header segmented control Console | Conductor (body.conductor recedes the rack + AI bar).
- Conductor surface: intent input + scrolling narration log (#cvLog).
- conductorPlan(): one aiChat call, CONDUCTOR_SYS -> JSON {queries, synth_beds, arc,
  session_key, session_bpm, note}. Sets session key+bpm; spawns synth_beds as internal
  composer voices (ensureComposer/composerNote) driven by a bar-grid bed engine in the
  session key (rights-clean, immediate, no dead air); reuses the AI DJ engine seeded by
  the arc to perform.
- Grab=yield: a console touch (the existing 'manual override' djStop hook) drops to Console
  with beds STILL sounding and the AI performance paused -- sound continuous, human inherits.
- Verified live (serve public): mode toggle, panel, key parse (F#:dorian -> root 66), 3 beds
  spawned + ticking, yield keeps beds alive, Console unchanged, zero console errors.
HONEST GATING: the live aiChat plan needs the user's Anthropic key (BYO, click-fired); the
external-track acquisition calls the grabber q=/analyze= lane (Phase 1, deploy-gated) and
degrades honestly to synth-beds-only when it 404s. Phases 2/3/5 (SoundTouch stretch, full
key-frame re-pitch of grabs, breath-led + Listener modes) remain as specced.

## ADDENDUM 2026-07-06c -- PHASE 1 DEPLOYED + PHASE 2 INGEST LIVE (verified on the artifacts)

PHASE 1 (grabber) DEPLOYED: railway up to dragon-grabber, build SUCCESS (47 wheels incl.
numba/llvmlite -- the declared risk retired). One real fault found by live probe and fixed:
yt-dlp 2026.07 requires a JS runtime for YouTube; added deno to the Dockerfile (deno:
/usr/local/bin/deno on /diag). B4 done: dead nixpacks.toml + Procfile deleted.
LIVE VERIFY (deployed artifact): music url-grab + analyze=1 -> status verified, bpm 116.51
with a 130-beat grid, LUFS -17.86 / gain +1.86, 5 sections (densities in [0,1]), an 8-bar
rhythmic loop seam 0.827, key honestly null (unconfident); spoken-word -> rejected
(non_musical: speech); /analyze?file= -> manifest alone; legacy /grab shape unchanged
(id/title/file, no manifest). Analysis ~+15s on a 90s section.
GATED (Architect): YouTube itself bot-checks Railway's datacenter IP ("Sign in to confirm
you're not a bot") -- BOTH url= and q= lanes, all videos tried. The code path is proven via
direct-URL grabs (archive.org). Options are user-supplied cookies (--cookies) or a different
egress; deliberately NOT worked around here. Non-YouTube http(s) audio grabs work today.

PHASE 2 INGEST LIVE in tempo_mixer.html: grabYouTube() now requests &analyze=1 and
attachManifest(ch,man) applies it -- srcBPM from the analyzed grid + match ON (tempo-locks
via the existing pitch-preserved applyRate), arrival gain from LUFS gain_to_target_db,
sections kept on ch.manifest for the Conductor, status narrates verdict/bpm/camelot. The
Conductor's acquisition path attaches manifests too and auto-skips validation.status
rejected (narrated). Verified end-to-end in the browser against the LIVE grabber:
srcBPM 116.51 / match on / playbackRate 0.858 (= master 100 / 116.51) / fader 0.966.
STILL OPEN in Phase 2: SoundTouch true time-stretch (vendoring a third-party lib into
public/vendor -- held for the Architect's nod), key-shift to sessionKey (Phase 3).

## ADDENDUM 2026-07-06d -- PHASES 2/3/5 COMPLETE (SoundTouch, session key, breath + Listener)

PHASE 2 COMPLETE: SoundTouchJS 0.3.0 vendored VERBATIM (LGPL-2.1) at public/vendor/
soundtouch.js, exposed by a module shim. Manifest'd file channels offline-render a
stretched + key-shifted buffer (chunked async, generation-tokened) and swap the media
element for a looped buffer source; re-render debounced on bpm/key change; applyRate
remains the fallback. VERIFIED live vs the deployed grabber: a 121.16-bpm grab rendered
90s -> 108.6s at master 100 (exact tempo ratio, pitch preserved), re-rendered to 90.6s
at 120, +5 st on a D-minor reselect.

PHASE 3 COMPLETE: sessionKey selector in the clock bar (auto = adopt the first analyzed
grab's key -- VERIFIED: A:minor conf 0.806 auto-adopted; Conductor plans adopt on auto
too); semitone delta wraps +/-6 into the stretch render; conductor synth beds follow the
key (root 62 on D-minor). Optional voidscale/ghatika bus senders NOT done (soundlab.html
is the sibling-sender exemplar; the two graduated instruments stay untouched per repo law).

PHASE 5 BUILT: time-authority segmented control in the Conductor bar.
- Breath-led: beatless by construction -- stops clock/DJ/grid-beds, spawns pad+drone beds
  if none, slow linear-attack swells (attack 0.45x / release 1.3x the breath period,
  default 6s/side, 3-20s). VERIFIED: beds spawn, swells run, clock stays OFF, clean exit.
- Listener: mic via getUserMedia (click-fired), analyser on rAF (never the audio thread,
  mic NOT routed to master), onset -> median IOI -> tempo folded 60-180, session bpm
  follows (restretch included), "following you: N bpm" indicator. Mic-denied degrades
  narrated to Session (VERIFIED -- headless preview). Key-follow DEFERRED (tempo only,
  stated honestly). Real-mic tempo lock needs the Architect's hands + a metronome.

INCIDENT (Architect action needed): the dragon-grabber Railway service's GitHub source is
misconnected to the dragon-instruments REPO -- the 11:34:47 push of the Phase 2 ingest
commit auto-deployed a static `serve` build ONTO dragon-grabber (grabber 404'd; restored
by railway up 39a3eba3). Until the dashboard source is fixed (dragon-grabber service ->
Settings -> Source -> Cloud-Eye-Prime/dragon-grabber), dragon-instruments commits are
held LOCAL (cae7645 + this one) and deploys go by railway up only. After the fix, push.

## ADDENDUM 2026-07-06e -- SOURCE HAZARD RESOLVED + THE LANE IS FULLY OPEN

- Architect reconnected dragon-grabber's dashboard GitHub source to
  Cloud-Eye-Prime/dragon-grabber. PROVEN by the failing test: a dragon-instruments push
  (ad5f713) no longer touches the grabber; Railway's initial deploy from the corrected
  source (016adc61) serves the true app (deno + cookies:true + q= functional). Both repos
  push-safe; the grabber auto-deploys from its own repo now.
- YT_COOKIES_B64 live (another session; adversarially verified). The mixer grab box accepts
  a plain SEARCH PHRASE (non-URL -> /grab?q=). End-to-end from the UI: phrase -> YouTube ->
  manifest -> session-key adoption -> SoundTouch true-stretch. The conductor pipeline that
  this plan describes is now open at every stage; remaining human-gated items are the BYO
  Anthropic key at perform-time and the Listener real-mic tempo lock test.
