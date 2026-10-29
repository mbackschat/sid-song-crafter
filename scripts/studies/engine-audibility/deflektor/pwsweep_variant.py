"""Compile Deflektor descriptions with SID-Wizard 1.97 Extra's PWSWEEP pulse arithmetic.

Study-local wrapper around the supported Deflektor backend: it swaps the one
pulse-interpolation step in both the numeric model and the 6502 player for the
duration of a ``with pwsweep_arithmetic():`` block and changes nothing else.
"""

from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'scripts'))
import deflektor_compiler
import deflektor_programs
from deflektor_programs import PulseState, cell

PWSWEEP_SOURCE = '.tools/sid-wizard-1.97/native/sources/include/player.asm'

# Deflektor's tail of df_pwm_interpolate: only the low byte moves, so a
# downward segment wraps the low byte upward and keeps the high byte.
EXACT_ASM = """  CMP df_pulse_word_hi,X
  BEQ df_pwm_done
  BCC df_pwm_subtract
  LDA df_pulse_word_lo,X
  CLC
  ADC df_pwm_step,X
  STA df_pulse_word_lo,X
  RTS
df_pwm_subtract:
  LDA df_pulse_word_lo,X
  SEC
  SBC df_pwm_step,X
  STA df_pulse_word_lo,X
df_pwm_done:
  RTS
"""

# PWSWEEP (player.asm 2332-2347) adds a signed amount to the low byte and
# carries or borrows into the high byte ("dec PWHIGHO" before a negative add,
# "inc PWHIGHO" on carry). Deflektor chooses the direction by comparing the
# next target's high nibble with the current high byte; that comparison would
# stop the sweep after the first borrow reaches the target nibble, which no
# fixed-amount PWSWEEP row does. A nonzero low byte at a target-equal high
# byte therefore still means the word lies above the target and keeps falling,
# which equals one signed row per segment while interval * step < 256.
PWSWEEP_ASM = """  CMP df_pulse_word_hi,X
  BEQ df_pwm_equal_high
  BCC df_pwm_subtract
  LDA df_pulse_word_lo,X
  CLC
  ADC df_pwm_step,X
  STA df_pulse_word_lo,X
  BCC df_pwm_done
  INC df_pulse_word_hi,X
  RTS
df_pwm_equal_high:
  LDA df_pulse_word_lo,X
  BEQ df_pwm_done
df_pwm_subtract:
  LDA df_pulse_word_lo,X
  SEC
  SBC df_pwm_step,X
  STA df_pulse_word_lo,X
  BCS df_pwm_done
  DEC df_pulse_word_hi,X
df_pwm_done:
  RTS
"""


def pwsweep_interpolation(program, elapsed, position, value, table):
    """Move the 16-bit pulse word toward the next target with signed carry/borrow."""
    target = cell(table, (program.table_base + (position & 127)) & 255) & 15
    high, low = value >> 8, value & 255
    if target < high or target == high and low:
        value = (value - program.low_step) & 0xffff
    elif target > high:
        value = (value + program.low_step) & 0xffff
    return PulseState(elapsed, position, value)


def player_source():
    original = deflektor_compiler.PLAYER
    if original.count(EXACT_ASM) != 1:
        raise ValueError('Deflektor player no longer contains the expected pulse interpolation tail once')
    return original.replace(EXACT_ASM, PWSWEEP_ASM)


def require_no_overshoot(description):
    """Reject patches whose one-segment travel could reach the next high nibble.

    interval * step < 256 keeps a segment inside one nibble, which makes the
    target comparison above equal to a fixed signed sweep per segment.
    """
    for record in description['score']['recordTable']['records']:
        interval, step = record['fields'][0] & 15, record['fields'][6]
        if interval * step > 255:
            raise ValueError(f"Record {record['recordOffset']} travels {interval * step} per segment; "
                             'PWSWEEP equivalence requires at most 255')


@contextmanager
def pwsweep_arithmetic():
    """Patch the numeric model and the assembled player, restoring both on exit."""
    model, player = deflektor_programs.pulse_interpolation, deflektor_compiler.PLAYER
    patched = player_source()
    deflektor_programs.pulse_interpolation = pwsweep_interpolation
    deflektor_compiler.PLAYER = patched
    try:
        yield
    finally:
        deflektor_programs.pulse_interpolation = model
        deflektor_compiler.PLAYER = player


def build(variant_path, output):
    """Compile the variant descriptor's base description and append study provenance."""
    variant_path, output = Path(variant_path), Path(output)
    variant = json.loads(variant_path.read_text())
    if variant['schemaVersion'] != 'engine-audibility-deflektor-variant-v1' or variant['pulseArithmetic'] != 'sid-wizard-1.97-pwsweep':
        raise ValueError('Unsupported variant descriptor')
    base = ROOT / variant['base']
    description = json.loads(base.read_text())
    require_no_overshoot(description)
    with pwsweep_arithmetic():
        deflektor_compiler.run(base, output)
    path = output / 'verification.json'
    report = json.loads(path.read_text())
    report['variant'] = dict(
        descriptor=str(variant_path.resolve()), descriptorSha256=hashlib.sha256(variant_path.read_bytes()).hexdigest(),
        pulseArithmetic=variant['pulseArithmetic'], basePath=variant['base'],
        pwsweepSource=PWSWEEP_SOURCE, pwsweepSourceSha256=hashlib.sha256((ROOT / PWSWEEP_SOURCE).read_bytes()).hexdigest(),
        moduleSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        playerAsmHasPwsweepTail='df_pwm_equal_high:' in (output / 'player.asm').read_text())
    path.write_text(json.dumps(report, indent=2) + '\n')
    return report
