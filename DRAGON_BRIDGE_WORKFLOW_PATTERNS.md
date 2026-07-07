# Dragon Bridge -- Workflow Patterns That Worked

The process (not the product) that built the Dragon Bridge mixer + conductor. These patterns
are reusable for any single-file, audio, or headless-browser build in this codebase. Companion
to `DRAGON_BRIDGE_TECH_APPENDIX.md`. Captured 2026-07-07.

## 1. The validation chain, made concrete for a single HTML file
OBSERVE -> HYPOTHESIZE -> ACT -> VALIDATE -> DECLARE. For `tempo_mixer.html` every edit ran:
1. **Syntax**: extract the LAST inline `<script>` block and `node --check` it. Extraction
   must handle multiple script tags -- take the last `<script>` open to the last `</script>`,
   NOT a non-greedy match (which truncates at an in-string or earlier tag).
2. **Bytes**: `LC_ALL=C grep -c '[^ -~\t]'` must be 0 (ASCII-only house rule).
3. **Behavior**: extract the real functions and unit-test them in Node with mocked browser
   globals (see pattern 3). Syntax passing is necessary but NOT sufficient.
4. **Artifact**: load the DEPLOYED (or locally served) page in a real headless browser, confirm
   symbols defined + zero console errors, then probe the live URL for the new symbols.

## 2. Edit single-file HTML via a Python patch script, not heredocs
Git-Bash heredocs mangle regex/backslashes/quotes. Write a `*.py` patch with a list of
`(old, new)` string pairs, `assert s.count(old)==1` for each (uniqueness = safety), then
`replace`. ASCII rule: NO apostrophes inside single-quoted JS string literals ("does not",
not "doesn't"); glyphs as `\u`. Use Python RAW strings for `new` blocks containing regex.

## 3. Verify by running the REAL functions, not a re-implementation
The highest-signal test: slice the actual function source out of the file (by string markers),
paste it into a Node harness with minimal mocked globals (`$`, `ctx`, `channels`, `rec`,
`_rng`, ...), and assert real behavior. This caught bugs `node --check` cannot:
- transition moves keyed to a WRONG bar origin (walk-relative vs the absolute bar `djTick`
  reads) -> would never fire;
- a WAV header verified by actually parsing the RIFF/WAVE bytes a live render produced.
Stub `Blob`/`DataView` when the function returns them. This beats re-implementing the logic
(which drifts from the real code).

## 4. Delegate, then ADVERSARIALLY verify -- never trust a self-report
When a subagent (or forge/claude-code) returns "F1 OK / F2 OK", treat it as a claim to be
refuted. Read the diff, run the behavioral tests, and check INTEGRATION, not just syntax. On
the 3-feature vision build the delegate produced plausible-but-wrong code: wrong bar origin
(feature dead), pin tripping the GRAB=YIELD stop (killed the whole set), two systems writing
`dj.plan` with no arbitration. All four surfaced only under review. Surgical fixes I did
inline at frontier quality rather than round-tripping another uncertain delegation.

## 5. Forge / headless-agent reality
`forge_dispatch -> claude_code` TIMED OUT at 300s (exit 1) with permission errors -- headless
claude-code could not get file-write permission. For file-writing tasks in this environment
it is not viable; build inline. `forge_status` confirms availability but availability != a
working headless run. (Recorded in the global memory as a standing note.)

## 6. Design decisions via a judge panel, load-bearing claims verified against code
For "how to achieve infinite variety", a Workflow generated N independent architectures ->
adversarial critique -> synthesis ("Seeded Spine + Pre-filtered Curator", harness pre-roll
only). EVERY load-bearing claim in the synthesis was then re-checked against the actual file
before acting. A panel is worth it when the solution space is wide; always ground its claims.

## 7. Cheap-model exemplars via a blind bake-off
To teach cheap models (gpt-4o-mini, gemma, qwen) the DJ/auto-mix JSON, run a bake-off:
generate exemplars from several strong models (Opus/Fable/Sonnet via OpenRouter), blind-judge,
embed the winner's exemplars as few-shot in the system prompt, then VERIFY transfer (the cheap
model generalized a breakdown from a drop exemplar; restraint held: 0 moves when the mix works
vs 9-12 when building). Few-shot beats prose instruction for format+taste.

## 8. Research -> encodable spec -> build (dual-stream, grounded)
Two research streams (a Tentacle agent + a web-search Workflow) returned an ENCODABLE spec
(transition automation curves, generative-looper design, genre taxonomy + blend scoring, the
half-time flag). Pattern: dispatch research async, keep building, integrate the LOAD-BEARING
finding first (the half-time flag was the one mechanism that makes wild blends beat-match).
Record the full spec in memory so later builds self-serve.

## 9. The headless true-render pipeline (real audio out of a browser, no device)
Proven: a headless preview browser RUNS Web Audio in real time (`ctx.state==='running'` with no
user gesture) and a ScriptProcessor CAPTURES the master. To render real mixes to disk:
1. **Same-origin audio**: grab YouTube via the grabber, download the mp3s into `public/` so the
   page fetches them SAME-ORIGIN (sidesteps CORS tainting -> silence).
2. **Upload sink**: a tiny Node HTTP server (CORS `*`) receives a POSTed WAV and writes it to
   disk -- the page `fetch`-POSTs its `encodeWAV` Blob (avoids exfiltrating MBs through eval).
3. **Self-driving render fn**: define `window.renderGenre(cfg)` (mixer vars ARE window globals
   ON `tempo_mixer.html`, but ONLY after navigating to it). It self-cleans (`removeChannel`
   all + clear timers), loads the track + beds + ai-loop + swing, runs a `setTimeout` energy
   arc, `recStart`s, and at ~122s `encodeWAV` -> POST. It persists across genres (no reload).
4. **eval budget**: preview_eval times out ~30s. Long grabs/renders must be FIRE-AND-FORGET +
   polled (background bash waits for the file), never awaited in one eval.
Result: 6 x 2-min genre mixes (real tracks + real synth voices + swing) rendered + verified.

## 10. Per-phase deploy + verify-the-deployed-artifact
One concern per commit; `railway up --detach`; poll the deployment id to SUCCESS; then
`curl` the LIVE `/tempo_mixer` and grep for the new symbols. The house rule is explicit:
verify the DEPLOYED artifact, not just the commit. Static render audio + temp files are
`.gitignore`d so they never reach the deploy.

## 11. Persist the non-obvious in memory + Librarian
Each milestone updated the auto-memory (`dragon-instruments-music-rooms.md`) with what was
built, the hazards, and the reproduction steps -- plus feedback memories (e.g. the forge
delegation lesson) with Why + How-to-apply. Save what is NOT derivable from the code: the
research spec, the pipeline recipe, the process feedback. Not line numbers (they drift).
