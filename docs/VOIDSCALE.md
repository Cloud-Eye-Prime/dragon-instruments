# V0ID_SCALE Labs

A single-file browser instrument built on the Web Audio API. No framework, no
build step, no backend. Everything below lives in `public/voidscale.html`.

## The synth

Every note is generated live -- nothing is sampled. Pitched voices use
equal temperament (`freq = 440 * 2^((midi - 69) / 12)`) and a short gain
envelope, and the timbre now depends on the active instrument:

- **Piano** -- a triangle oscillator, slightly longer decay.
- **Synth** -- a sawtooth oscillator through a resonant low-pass filter that
  tracks the note's pitch, for a brighter, filtered tone.
- **Hirajoshi / Just** -- a clean sine, the original default voice.
- **Drums** -- a small percussion synth (not a pitched oscillator): note 36 is
  a pitch-swept kick, 38/40 a filtered-noise snare with a body tone, 49/51/53/55
  bright noise cymbals, and the rest short noise hats (46 is the open hat).

The single voice generator (`triggerVoice` / `triggerDrum`) takes an audio
context, a destination, and a start time, so the live transport and the offline
export render produce identical sound. All voices sum into one master gain,
which the volume slider and mute button act on.

## The 8-pad scale grid and instrument maps

There are 8 pads. Switching the instrument swaps which MIDI notes the pads play:

| Map        | MIDI notes                          | Notes |
|------------|-------------------------------------|-------|
| Piano      | 60 62 64 65 67 69 71 72             | C major run, 8 pads |
| Synth      | 36 38 40 42 44 45 47 48             | low cluster, 8 pads |
| Drums      | 36 38 42 46 49 51 53 55             | General MIDI drum numbers, 8 pads |
| Hirajoshi  | 60 61 65 67 72                      | Japanese pentatonic, 5 pads |
| Just       | 60 66 70 72 80                      | a "just" set, 5 pads |

The Hirajoshi and Just maps define only 5 notes. On those maps the three extra
pads are disabled (dimmed and unclickable) instead of playing stale notes, and
they re-enable when you switch back to an 8-note map.

## Euclidean rhythm

A density and a length field generate a true Euclidean rhythm via the
**Bjorklund algorithm** -- the pulses are spread as evenly as possible across
the steps (so density 3, length 8 gives `x..x..x.`, density 5/8 gives
`x.xx.xx.`). The pattern is drawn as a row of lit / unlit cells **and** it
sonifies: each lit step fires a kick when the transport runs, and the cell under
the playhead lights up as it passes. The "Cycle Length" field also sets the
length of the step sequencer (see below).

## Ouroboros breath visual

A canvas animation -- a ring with a pulse traveling around it on a roughly
four-second cycle. It is ambient; it is not wired to the transport.

## Looper and transport

The transport is a real looping **step sequencer**. Its length is the Euclidean
"Cycle Length", and each step's duration comes from the tempo and the Note
Division control (e.g. eighth notes at 96 BPM = 0.3125 s/step). A lookahead
scheduler ("a tale of two clocks") queues events slightly ahead on the audio
clock for steady timing.

- **Play** starts and stops the loop. While running, the Euclidean kicks and
  every armed loop play together, and the playhead sweeps the Euclidean row.
- **Record** captures live pad / MIDI input into a take; toggling it off saves
  the take as a loop.
- **Stop** halts the transport and clears the playhead.

Each saved loop remembers the instrument it was recorded with and is **armed**
by default. Click a loop to toggle it between ARMED and MUTED -- muted loops stay
in the list but drop out of playback and export. When the grid is built, a
loop's notes are quantized by their real elapsed time onto the current step grid,
so a loop recorded at one tempo still lands sensibly at another. AI-summoned
phrases are added as armed loops too.

## Master volume and mute

A range slider sets the master gain (default low, around 25%). Mute toggles the
master output off and on.

## WAV / MIDI export

Both exporters are now **real renders of the current grid** (the Euclidean kicks
plus every armed loop), bounced for two cycles of the loop:

- **WAV** renders through an `OfflineAudioContext` using the exact same voice
  generators as live playback, then encodes the result as a 16-bit PCM WAV
  (`RIFF`/`WAVE`). The status line reports the rendered length.
- **MIDI** writes a real Standard MIDI File: 480 PPQ, a tempo meta event from
  the current BPM, drums on channel 10 and melodic notes on channel 1, with
  variable-length delta times. It opens with `MThd` and carries one `MTrk`.

If the grid is empty (no armed loop and zero Euclidean density), export reports
that there is nothing to render instead of writing a silent file.

## Web MIDI input

If the browser grants Web MIDI access, incoming MIDI notes are routed to the
synth, so an external controller can play the pads.

## "The Shadow" -- the AI Summon

The Summon button (`generateAI`) asks a language model for a short phrase that
is locked to whatever scale is active, then plays it and saves it as a loop.

How it works, step by step:

1. **Vibe prompt.** You type a mood ("dark ambient", etc.). The instrument
   builds a system prompt that demands **raw JSON only** in the schema
   `{"steps":[{"note":int,"vel":int}]}`, up to 16 steps, and tells the model the
   note **must** come from the active map's exact MIDI set. Tempo and the
   current instrument are passed in the user message.

2. **The call.** It POSTs to `https://openrouter.ai/api/v1/chat/completions`
   with your key as a Bearer token, `temperature` 0.9, and the default model
   `openai/gpt-4o-mini` (editable in the AI Model field).

3. **Defensive parse.** The reply is stripped of any markdown fences, the JSON
   object is sliced out and parsed, and steps with non-finite notes are dropped.

4. **Snap to scale.** Any note the model returns that is **not** in the active
   set is snapped back into it by index (`map[((n % len) + len) % len]`), and
   velocity is clamped to 1..127. So the result can never leave the scale.

5. **Crystallize.** The phrase is committed as a new loop in the list **and**
   played immediately.

### Bring-your-own-key and the fallback

- The key is entered in the AI Key field and saved in `localStorage`
  (`voidscale_or_key`); the model string is saved too (`voidscale_or_model`).
  The key is sent only to OpenRouter and is never stored in this repo.
- **No key, no problem.** If the AI Key field is empty, Summon falls back to a
  local random walk over the active map -- 16 random in-scale notes -- so the
  button always does something, and a notice suggests adding a key for real AI.
- On an HTTP or provider error, the status line shows the provider's message;
  nothing is silently swallowed.
