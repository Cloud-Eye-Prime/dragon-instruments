# Ghatika -- the embryonic breath

A single-file breath-and-entrainment sequencer built on React and Tone.js (both
loaded from a CDN, compiled in-page by Babel standalone). Everything below lives
in `public/ghatika.html`. One clock drives the whole thing.

## The breath cycle and the five elements

A breath is 8 beats = 32 sixteenth-notes. The breath is divided into four phases,
each mapped to an element of the Wu Xing cycle:

| Phase  | Element | Glyph |
|--------|---------|-------|
| Inhale | Water   | shui  |
| Pause  | Metal   | jin   |
| Exhale | Fire    | huo   |
| Rest   | Earth   | tu    |

At a given BPM the breath rate is BPM/8 breaths per minute (so 96 BPM is 12
breaths per minute). Every layer below is optional and rides this one clock.

## Entrainment

A drone tuned to a target beat frequency, in three modes:

- **Binaural:** two oscillators (carrier +/- beat/2) panned hard left and right;
  the beat is perceived from the difference between the ears.
- **Monaural:** the same two oscillators summed into one channel.
- **Isochronic:** a single oscillator amplitude-gated by an LFO at the beat rate.

Two ways to move through frequencies:

- **Journey:** a scripted arc over time -- Arrive (10 Hz) -> Soften (7) ->
  Descend (5) -> Deep still (2.5) -> Return (6) -> Quicken (40) -> Integrate (10).
- **Hold a band:** pin one band -- Delta 2.5, Theta 6, Alpha 10, Beta 18,
  Gamma 40, or Hypergamma 100 Hz.

Entrainment effects are subjectively reported, not clinically established.

## Generative rhythm styles

Rhythm styles are stackable and **labeled honestly as structural homages -- not
anyone's sacred repertoire.** They borrow a feel, not a recording:

- **Icaro . chacapa** -- Amazonian medicine-song pulse; leaf-rattle ostinato
- **Aka . hocket** -- Central African interlocking
- **Baka . water+clap** -- airy water-drum and claps
- **Mbuti . forest** -- minimal forest heartbeat
- **Trance . pulse** -- steady driving journey-drum
- **Hip-hop . boom-bap** -- kick-snare backbeat

Drum voices (kick, frame, conga, snare, clap, shaker, wood/tek) map to General
MIDI drum numbers for export.

## Melody, scales, and ragas

A melodic voice plays patterns -- scale run, arpeggio, melody, circle of fifths,
raga ornament -- over a chosen scale. Available scales include the seven Western
modes (major, minor, dorian, phrygian, lydian, mixolydian, locrian), pentatonics
and blues, chromatic, and four ragas (Bhairav, Yaman, Bhairavi, Kafi), each
defined as semitone intervals from a chosen root. The melodic timbre is swappable
(triangle, FM, pluck, saw, square, AM).

## Effects rack

A master chain wet-mixes four effects, with delay and reverb as parallel sends so
they do not choke the dry signal:

```
filter (lowpass) -> drive (crossfade clean/distorted)
                 -> delay (ping-pong)   [parallel send]
                 -> reverb              [parallel send]
```

Each effect amount is a 0..1 control.

## Export -- real MIDI and WAV

Both exporters are full renders (not placeholders):

- **MIDI:** a hand-written Standard MIDI File at 480 PPQ, with drums on GM
  channel 10 and melody on channel 1.
- **WAV:** a deterministic offline bounce (`Tone.Offline`) of an 8-bar take in
  the current voice -- the active AI phrase if one is loaded, otherwise a fresh
  generative take.

## Live MIDI out

Over the Web MIDI API, Ghatika can send a 24-PPQN clock plus notes to an external
device. This works on a normally hosted or local page; a chat-preview sandbox
blocks Web MIDI, and the UI says so honestly when access is denied.

## The AI -- compose and DJ

Both AI features call **Anthropic directly from the browser**
(`https://api.anthropic.com/v1/messages`, model `claude-sonnet-4-20250514`),
using a bring-your-own-key entered in the top key bar. The key is held only in
that tab's memory for the session -- never stored to disk or committed here.

- **AI compose** asks for one strict-JSON **8-bar phrase** (notes + drums,
  diatonic to the active scale and root), parses it defensively, and loads it as
  a playable take you can then export.

- **AI DJ** is a live director. It is told the current state and asked to write
  the **next few measures ahead** as JSON: sparse control changes (styles,
  density, scale, root, instrument, BPM, and the four FX amounts) plus notes and
  drums, landing transitions on measure boundaries. A scheduler reads that plan
  buffer measure by measure and **drives the controls live.** It runs in an
  autonomous "arc" mode or a "journey" mode that follows the breath score, and
  it prints a short readout of what it is doing and why.

## Honesty

All audio is synthesized. Entrainment is subjectively reported, not established.
The rhythm styles are structural homages, not anyone's sacred repertoire. This is
not a medical device. The page deploys nothing and calls out only to your chosen
AI provider when you ask it to.
