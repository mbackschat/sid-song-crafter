"""Assemble callable-RAM 6502 sources without score or instrument assumptions."""


BRANCHES = {"BCC", "BCS", "BEQ", "BMI", "BNE", "BPL", "BVC", "BVS"}


def data_directive(statement):
    parts = statement.split(None, 1)
    if parts[0] not in (".byte", ".word"):
        return None
    if len(parts) != 2:
        raise ValueError("Data directive requires values")
    values = [value.strip() for value in parts[1].split(",")]
    if not all(values):
        raise ValueError("Data directive requires values")
    return (1 if parts[0] == ".byte" else 2), values


def assemble(source, constants=None, load=0x1000):
    """Return payload bytes, resolved symbols and a listing for a 6502 source.

    Labels occupy their own lines; .byte and little-endian .word directives may
    reference labels or constants. Numbers follow py65's hexadecimal default,
    with a leading + selecting decimal. Payloads must fit RAM $0400–$9fff.
    """
    from py65.assembler import Assembler
    from py65.devices.mpu6502 import MPU
    from py65.utils.addressing import AddressParser

    if type(load) is not int or not 0x0400 <= load < 0xa000:
        raise ValueError("Payload must remain in callable RAM")
    symbols = dict(constants or {})
    if not all(type(value) is int and 0 <= value <= 65535 for value in symbols.values()):
        raise ValueError("Constants must be 16-bit integers")
    statements = [line.split(";", 1)[0].strip() for line in source.splitlines()]
    statements = [line for line in statements if line]
    for line in statements:
        if line.endswith(":"):
            name = line[:-1]
            if name in symbols:
                raise ValueError(f"Duplicate label {name}")
            symbols[name] = load

    assembler = Assembler(MPU(), AddressParser(labels=symbols))
    pc = load
    for line in statements:
        if line.endswith(":"):
            symbols[line[:-1]] = pc
        else:
            directive = data_directive(line)
            pc += directive[0] * len(directive[1]) if directive else len(assembler.assemble(line, pc=pc))
    if not load < pc <= 0xa000:
        raise ValueError("Payload must remain in callable RAM")

    parser = AddressParser(labels=symbols)
    assembler = Assembler(MPU(), parser)
    pc, payload, listing = load, bytearray(), []
    for line in statements:
        if line.endswith(":"):
            continue
        directive = data_directive(line)
        if directive:
            width, values = directive
            encoded = []
            for token in values:
                value = parser.number(token)
                if not 0 <= value < 1 << (width * 8):
                    raise ValueError(f"Data directive must contain {width}-byte values")
                encoded.extend(value.to_bytes(width, "little"))
        else:
            if line.split(None, 1)[0].upper() in BRANCHES:
                target = parser.number(line.split(None, 1)[1])
                if not -128 <= target - pc - 2 <= 127:
                    raise ValueError(f"Branch out of range: {line}")
            encoded = assembler.assemble(line, pc=pc)
        listing.append(f"{pc:04x}  {bytes(encoded).hex():<12} {line}")
        payload.extend(encoded)
        pc += len(encoded)
    return bytes(payload), symbols, "\n".join(listing) + "\n"
