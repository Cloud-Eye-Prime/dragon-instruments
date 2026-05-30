# V0ID_SCALE Labs

A single-file browser instrument built on the Web Audio API. No framework, no
build step, no backend. Everything below lives in `public/voidscale.html`.

## The synth

Every pad and every note plays through one **sine oscillator** per voice.
Pitch is equal temperament (`freq = 440 * 2^((midi - 69) / 12)`), and each note
gets a short gain envelope that decays over about half a second. All voices sum
into a single master gain, which is what the volume slider and mute button act
on. There is no sampling and no per-instrument timbre -- the "instruments" below
are different note sets fed to the same oscillator, not different sounds.

## The 8-pad scale grid and instrument maps

There are 8 pads. Switching the instrument swaps which MIDI notes the pads play:

| Map        | MIDI notes                          | Notes |
|------------|-------------------------------------|-------|
| Piano      | 60 62 64 65 67 69 71 72             | C major run, 8 pads |
| Synth      | 36 38 40 42 44 45 47 48             | low cluster, 8 pads |
| Drums      | 36 38 42 46 49 51 53 55             | General MIDI drum numbers, 8 pads |
| Hirajoshi  | 60 61 65 67 72                      | Japanese pentatonic, 5 pads |
| Just       | 60 66 70 72 80                      | a "just" set, 5 pads |

The Hirajoshi and Just maps define only 5 notes. With 8 pads on screen, the pads
past the fifth currently fall back to stale notes -- a known rough edge.

## Euclidean rhythm visualizer

A density and a length field generate a Euclidean pattern (evenly spread hits
across the steps) and draw it as a row of lit / unlit cells. This is a
**visualizer**: it shows the pattern but does not yet drive the audio engine.

## Ouroboros breath visual

A canvas animation -- a ring with a pulse traveling around it on a roughly
four-second cycle. It is ambient; it is not wired to the transport.

## Looper and transport

The loop list holds phrases (including ones the AI creates). Play / Stop /
Record are present: Record captures live pad input into a take, Stop clears the
playing/recording flags. Play currently toggles state but does not yet sequence
the saved loops back -- full playback sequencing is future work.

## Master volume and mute

A range slider sets the master gain (default low, around 25%). Mute toggles the
master output off and on.

## WAV / MIDI export

The export buttons download a file, but in this build the V0ID_SCALE exporters
are **simplified placeholders** -- a minimal fixed WAV and a minimal MIDI header
rather than a true render of your session. (Ghatika's exporters are full; see
its doc.) A real V0ID_SCALE render is on the roadmap.

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
