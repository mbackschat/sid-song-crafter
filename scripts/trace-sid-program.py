"""Link bounded callable-PSID execution, RAM operands and ordered SID writes."""

import argparse
from enum import Enum
import hashlib
import importlib.util
import json
from pathlib import Path

from psid_audit import audit_psid
from verify_player import require


class TraceProfile(str, Enum):
    STRICT = 'strict'
    PAL_BANKED = 'pal-banked'
    FLASHDANCE_DIAGNOSTIC = 'flashdance-diagnostic'


def load_reference():
    spec = importlib.util.spec_from_file_location('sid_trace_reference', Path(__file__).with_name('study-drax-references.py'))
    reference = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reference)
    return reference


def audit_trace(data, calls, profile, observer, subtune=None):
    if profile in (TraceProfile.STRICT, TraceProfile.PAL_BANKED):
        report, writes = audit_psid(data, calls, observer=observer, profile=profile.value, subtune=subtune)
        return report, writes, None
    require(profile is TraceProfile.FLASHDANCE_DIAGNOSTIC, 'Unknown trace profile')
    require(subtune is None, 'The pinned Flashdance diagnostic does not accept subtune selection')
    reference = load_reference()
    reference.verify_reference('flashdance', data)
    diagnostic = reference.load_script('psid_audit.py', 'sid_trace_flashdance_audit')
    memories = []

    def memory_factory(sid_bases):
        memory = reference.FlashdanceDiagnosticMemory(sid_bases)
        memories.append(memory)
        return memory

    diagnostic.AuditMemory = memory_factory
    report, writes = diagnostic.audit_psid(data, calls, observer=observer)
    ignored = memories[0].ignored_writes
    require(ignored == [{'phase': 'init', 'tick': None, 'address': address, 'value': 0}
                        for address in (0xd419, 0xd41a)], 'Pinned Flashdance init paddle-write sequence changed')
    return report, writes, {
        'classification': 'Pinned Flashdance diagnostic adapter; not a production-auditor pass',
        'ignoredInitPaddleWrites': ignored,
        'boundary': 'Only the two pinned zero init paddle writes are excluded; all other audit guards remain active.',
    }


def operand_address(mode, operands, cpu, memory):
    def word(address):
        return memory[address] | memory[(address + 1) & 255] << 8

    if mode in ('abs', 'abx', 'aby'):
        address = int.from_bytes(operands, 'little')
        index = cpu.x if mode == 'abx' else cpu.y if mode == 'aby' else 0
        return (address + index) & 65535
    if mode in ('zpg', 'zpx', 'zpy'):
        index = cpu.x if mode == 'zpx' else cpu.y if mode == 'zpy' else 0
        return (operands[0] + index) & 255
    if mode == 'inx':
        return word((operands[0] + cpu.x) & 255)
    if mode == 'iny':
        return (word(operands[0]) + cpu.y) & 65535
    return None


def trace_program(data, *, first_call, last_call, profile='strict', subtune=None):
    """Observe instructions without altering execution under the RAM-only audit contract.

    Operand values are pre-instruction RAM snapshots, not a bus-access trace.
    The py65 observer runs before each instruction; its cycle is consequently
    an instruction-start cycle relative to the play call, not a SID bus cycle.
    Initialization sound-register writes are retained separately. The optional
    Flashdance diagnostic profile requires the canonical reference hash and
    excludes only its recorded two zero initialization paddle writes. The
    pal-banked profile requires an explicit one-based subtune and uses the
    CPU auditor's declared raster-host entry state with BASIC RAM exposed.
    """
    require(type(first_call) is int and type(last_call) is int and 0 <= first_call <= last_call < 100000 and last_call - first_call < 512, 'Select an inclusive window of 1..512 calls within 0..99999')
    require(profile in tuple(TraceProfile), 'Unknown trace profile')
    profile = TraceProfile(profile)
    from py65.disassembler import Disassembler

    instructions, stores = [], {}
    disassembler = None
    memory_operations = {'LDA', 'LDX', 'LDY', 'STA', 'STX', 'STY', 'ADC', 'SBC', 'AND', 'ORA', 'EOR', 'CMP', 'CPX', 'CPY', 'BIT', 'INC', 'DEC', 'ASL', 'LSR', 'ROL', 'ROR'}

    def observe(cpu, memory):
        nonlocal disassembler
        if memory.phase != 'play' or not first_call <= memory.tick <= last_call:
            return
        if disassembler is None:
            disassembler = Disassembler(cpu)
        pc = cpu.pc
        size, assembly = disassembler.instruction_at(pc)
        encoded = bytes(memory.data[pc:pc + size])
        mnemonic, mode = cpu.disassemble[encoded[0]]
        row = {'tick': memory.tick, 'instructionStartCycle': memory.instruction_cycle, 'pc': pc, 'bytes': encoded.hex(), 'assembly': assembly, 'a': cpu.a, 'x': cpu.x, 'y': cpu.y, 'status': cpu.p, 'sp': cpu.sp}
        if mnemonic in memory_operations:
            address = operand_address(mode, encoded[1:], cpu, memory.data)
            if address is not None:
                row.update(operandAddress=address, operandValueBefore=memory.data[address])
                if mnemonic in ('STA', 'STX', 'STY'):
                    stores[(memory.tick, memory.instruction_cycle, address)] = pc
        instructions.append(row)

    audited, writes, diagnostic = audit_trace(data, last_call + 1, profile, observe, subtune)
    selected = []
    for write in writes:
        if write['phase'] != 'play' or not first_call <= write['tick'] <= last_call:
            continue
        key = (write['tick'], write['instructionStartCycle'], write['address'])
        require(key in stores, 'SID write lacks an observed store instruction')
        selected.append(dict(write, instructionPc=stores[key]))
    result = {'schemaVersion': 1, 'sourceSha256': hashlib.sha256(data).hexdigest(), 'firstCall': first_call, 'lastCallInclusive': last_call, 'profile': profile.value, 'audit': audited, 'instructions': instructions, 'sidWrites': selected, 'initSidWrites': [row for row in writes if row['phase'] == 'init'], 'limitations': 'RAM-only callable PAL player; execution begins at init, records only the requested play-call window plus initialization SID-port writes (subject to the selected profile). Cycles are instruction starts relative to each call. Operand values are backing-memory snapshots, not bus reads or readable SID state. No CIA/VIC scheduling, bus-cycle or audible-quality claim.'}
    if diagnostic is not None:
        result['diagnostic'] = diagnostic
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sid', type=Path)
    parser.add_argument('--first-call', type=int, required=True)
    parser.add_argument('--last-call', type=int, required=True, help='Inclusive, zero-based')
    parser.add_argument('--profile', choices=[profile.value for profile in TraceProfile], default=TraceProfile.STRICT.value,
                        help='Strict audit by default; pal-banked exposes BASIC RAM with explicit subtune selection; Flashdance diagnostic requires pinned bytes')
    parser.add_argument('--subtune', type=int, help='One-based selection required by pal-banked')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists() and not args.output.is_symlink(), 'Choose a new output file')
    result = trace_program(args.sid.read_bytes(), first_call=args.first_call, last_call=args.last_call, profile=args.profile, subtune=args.subtune)
    result['sourcePath'] = str(args.sid.resolve())
    result['toolSha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as output:
        json.dump(result, output, indent=2)
        output.write('\n')
    print(f"Traced {len(result['instructions'])} instructions and {len(result['sidWrites'])} SID writes: {args.output}")


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        raise SystemExit(f'SID program trace failed: {error}')
