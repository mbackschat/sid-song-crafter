# Project Instructions

Follow [Repository Guidelines](AGENTS.md) for musical priorities, knowledge retrieval, project layout and workflows. The testing policy below is the project-specific exception to the global requirement to use red/green TDD for every feature or fix.

## Choose validation that answers the question

Use judgment: red/green TDD is a tool, not a required ceremony for every change. Define the intended outcome and the evidence that can establish it before substantial implementation.

- **Reusable software and bug fixes:** prefer red/green tests for parsers, formats, scheduling, conversion, export, provenance, output protection and validation logic. Reproduce a defect and guard its mechanism when practical. Tests should reject meaningful wrong behavior rather than restate the implementation.
- **SID research and reverse engineering:** begin with bounded experiments, actual instruction/register traces, source inspection and independent emulator comparisons. Exploratory probes do not require unit tests first. Add focused tests when turning a probe into a reusable tool, especially for trace interpretation and evidence claims.
- **Music, instrument programs and arrangements:** use reproducible exports, relevant register/timing checks and short listening comparisons. Preserve source material and declare intentional arrangement differences. Do not require test-first development for changing timbre, groove or phrasing; passing software checks does not establish musical quality.
- **Documentation, indexes and routine configuration:** use proportionate checks such as link validation, configuration parsing or a smoke run. Do not add tests solely to satisfy a process rule.

Retain editable inputs, relevant tool/chip settings and reproduction commands. Document reusable findings and bounded listening judgments; keep raw traces in ignored build output rather than writing a diary. State what the evidence does and does not establish. Once relevant checks pass, repeat or broaden them only when changes or unresolved risks justify it.
