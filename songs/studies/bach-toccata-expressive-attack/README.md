# Bach Toccata: selective electronic attacks

This separate original candidate responds to feedback that the [accepted integrated pulse motion](../bach-toccata-integrated-motion/README.md) remains subtle. It tests a bolder transformation inside the existing main lead. **Rejected in listening on 2026-10-14.** The design uses accepted Bach inputs and written intentions; no Gyruss binary, traces, extracted notes, audio or program was consulted.

- [Score](score.json): byte-identical to the accepted 45-event opening. No extra voice or score notes are added; source mapping remains in the [driven preparation](../bach-toccata-opening-driven/preparation.json).
- [Native recipe](hybrid.json): adds `lead-attack`, selected only for the existing statements at 0–0.8, 2.6–3.4 and 4.9–5.7 seconds. Each has two sawtooth body calls at +12 semitones, two at +7, two pulse calls at +3, then base-pitch pulse. The finite table ends there. These six attack calls deliberately deviate from the written lead pitch; the simultaneous bass anchors the written octave. First base pitch arrives at `startTick + 7`, approximately 0.14 seconds after the score onset.
- [Preparation](preparation.json): pins the accepted integrated reference and names every pitch/waveform deviation. The rapid passing notes, later holds, lead ADSR, [integrated pulse-width program](../bach-toccata-integrated-motion/preparation.json), accompanying voices and shared filter retain their definitions.

Target: one MOS8580 at `$D400`, PAL, A=440 Hz, pinned SID-Wizard 1.97 Extra at 1x. Native frame one retains TEST silence. This tests a brief electronic attack followed by the familiar Bach tone; it does not introduce a repeating background reply.

The [cached paired recipe](../../../config/listening/bach-toccata-expressive-attack.json) builds the accepted integrated opening and candidate, renders their full approximately 15.5-second spans, verifies that frame changes are confined to lead frequency, waveform and pulse width, and samples the standalone PRG in VICE:

```sh
python3 scripts/listening-package.py config/listening/bach-toccata-expressive-attack.json --output build/bach-expressive-attack
```

The [run receipt](../../../build/bach-expressive-attack/run.json) and [listening index](../../../build/bach-expressive-attack/listening.md) retain outputs. The [attack verification](../../../evidence/bach-expressive-attack/attack-verification.json) checks all 21 programmed body frames at ticks 1–7, 131–137 and 247–253 against their named MIDI offsets and control bytes. Each settles on the written pitch within one PAL frequency-register unit. All other frames equal the accepted integrated execution; pulse width, lead envelope, bass, harmony and filter equal it throughout all 779 calls. Native scheduling retains 45 note starts and the gate/volume stop at tick 726. The 15.503855-second mono PCM16 render has zero clipped samples, and standalone VICE checkpoints pass separately.

Listen to [expressive-attack.wav](../../../build/bach-expressive-attack-listening/expressive-attack.wav), the accepted [subtle-lead.wav](../../../build/bach-expressive-attack-listening/subtle-lead.wav), or [subtle-then-expressive.ab.wav](../../../build/bach-expressive-attack-listening/subtle-then-expressive.ab.wav), at unity gain with a half-second separator. Human review asks whether the three foreground transformations supply the bolder electronic character requested while preserving the accepted gestures. Model-assistance review: skip unvalidated musical-preference inference; reassess after paired human feedback. CPU, PCM and VICE checks establish bounded execution separately from acceptance.


## Listening rejection and next hypothesis

The listener rejected this variant: **“Not good. The expressive variant again just adds these odd short sounds.”** The [structured verdict](listening-review.json) pins the candidate. The earlier background replies and these foreground attacks share the failed strategy of using short pitched effects to represent a broader musical character. Moving the effect into the lead did not make it musically integrated for this listener. Neither correct execution nor unchanged score-event counts overrules that judgment; the sounding attack pitches were deliberately altered.

Retain the liked subtle pulse-motion version. The next experiment changes a longer running passage's accompaniment/articulation to test sustained game-like momentum while keeping the foreground recognisable. It does not add another chirp, sweep or noise accent. This is a new hypothesis, not a claim that rhythm alone explains the listener's Gyruss preference. Model-assistance review: skip unvalidated preference inference; explicit human feedback settles rejection, and the next paired phrase needs its own listening verdict.
