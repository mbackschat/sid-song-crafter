# Composition tools and player implementations

Study both the editor and the exported driver: their relationship determines what can actually sound on a C64. Return to the [research index](../README.md).

- [Composition-tool assessment](composition-tools.md): GoatTracker, SID-Wizard, SID Factory II, custom engines, and the fit for this project.
- [SID-Wizard headless export trial](sid-wizard-trial.md): pinned native SID-Maker execution, Extra exports, provenance and tested limits.
- [Tool overview](overview.md): editors, converters, players, and inspection utilities.
- [Source-code studies](source-studies.md): player, converter, and emulator implementation findings.
- [Skills and integrations](skills-and-integrations.md): installed skills, c64bridge capabilities, and inspected compiler limitations.
- [Local setup](../../local-setup.md): installed versions and dependency pins.
- [Headless execution and audio](../../audio-workflow.md): reproducible rendering and VICE operation.
- [Native PSID driver audit](../../psid-audit.md): bounded CPU execution and ordered register evidence without our score compiler's assumptions.
- [Audio comparisons](../../audio-comparisons.md): original-preserving A/B files with recorded gain and signal measurements.

Keep author claims, source inspection, successful builds, and tested exports distinct. A desktop editor can be useful even when our automation and verification remain headless; do not assume it has a command-line exporter without checking.
