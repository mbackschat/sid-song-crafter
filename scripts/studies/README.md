# Study-specific tools

These tools investigate pinned recordings or prepare fixed demonstrations. They are research/example entry points, not the general production interface. Use the [tool boundaries](../README.md) to find shared workflows and supported synthesis backends.

| Study | Tools | Owning findings |
| --- | --- | --- |
| DRAX | [Describe the score](drax/describe-drax-score.py), [bass intervention](drax/study-drax-bass.py), [bass in context](drax/context-drax-bass.py), [full recurring-theme reconstruction](drax/reconstruct-drax-full.py), [bass transfer](drax/transfer-drax-bass.py) | [Decoded bass](../../songs/studies/drax-bass-reconstruction/README.md), [recurring theme](../../songs/studies/drax-full-reconstruction/README.md) |
| Flashdance | [Describe the pinned score](flashdance/describe-flashdance-score.py) | [Flashdance study](../../docs/research/composition/flashdance-preparation.md) |
| Shades | [PWM intervention](shades/compare-shades-pwm.py), [familiar phrase preparation](shades/prepare-shades-elise.py) | [Shades study](../../docs/research/composition/shades-preparation.md) |
| Cybernoid II | [Source analysis](cybernoid/analyze-cybernoid.py), [title preparation](cybernoid/prepare-cybernoid-title.py), [familiar phrase preparation](cybernoid/prepare-cybernoid-elise.py) | [Cybernoid study](../../docs/research/composition/cybernoid-ii-preparation.md) |
| Monty on the Run | [Optional finite-ending preparation](monty/prepare-monty-title-ending.py), [familiar phrase preparation](monty/prepare-monty-elise.py) | [Monty study](../../docs/research/composition/monty-preparation.md) |
| Rambo | [Loader preparation](rambo/prepare-rambo-loader.py), [whole numeric player verification](rambo/check-rambo-player.py), [complete sound verification](rambo/check-rambo-programs.py), [familiar phrase preparation](rambo/prepare-rambo-elise.py), [fresh and retained recipes](../../docs/workflows/listening-package.md#verify-a-study-before-compiled-playback) | [Rambo study](../../docs/research/composition/rambo-preparation.md) |
| Arkanoid / Galway contrast | [Bounded executed comparison](arkanoid/check-arkanoid-contrast.py), [same-material drum diagnostic recipe](arkanoid/listening.json) | [Rambo/Arkanoid findings and limits](../../docs/research/composition/galway-contrast.md) |
| Ghouls ’n Ghosts | [Independent score-boundary proof](ghouls/score-probe.py), [numeric sound-boundary proof](ghouls/sound-probe.py) | [Ghouls score and sound contracts](../../docs/research/composition/ghouls-preparation.md#independent-score-and-sound-boundaries) |

Run commands from the repository root using these paths, for example `python3 scripts/studies/monty/prepare-monty-elise.py --check`. Current study documentation links the relocated tools; frozen JSON recipes and archived evidence preserve their historical provenance. The explicitly deferred untracked work remains at its original paths, untouched and unstaged.
