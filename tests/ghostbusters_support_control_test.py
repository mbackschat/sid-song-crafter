"""Guard the single-byte, cycle-preserving held-support causal control."""

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('gb_support_control_tests', ROOT / 'scripts/studies/ghostbusters/prepare-support-control.py')
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)


def fixture():
    data = bytearray(126 + 0x1000)
    data[:10] = bytes.fromhex('52534944 0003 007c 0000')
    data[118:126] = bytes.fromhex('0058 0000 4200 0108')
    address = 0x1100
    offset = 126 + address - 0x0801
    data[offset:offset + len(control.CONTEXT)] = control.CONTEXT
    build = dict(profile=dict(clock='ntsc', sidModel='MOS6581', sidBases=[0xd400,0xd420]),
        arrangement=dict(support=dict(patch=dict(control=0x41))),
        stereoSupport=dict(controlOnsetAddress=address), loadAddress=0x0801, streamAddress=0x1800)
    return bytes(data), build, offset


class GhostbustersSupportControlTest(unittest.TestCase):
    def test_only_gate_immediate_changes_and_following_overwrite_is_retained(self):
        data, build, offset = fixture()
        patched, receipt = control.patch_image(data, build, control.sha(data))
        self.assertEqual(patched[:offset + 1], data[:offset + 1])
        self.assertEqual(patched[offset + 1], 0x40)
        self.assertEqual(patched[offset + 2:], data[offset + 2:])
        self.assertEqual(receipt['changedBytes'], 1)
        self.assertEqual(receipt['originalSha256'], control.sha(data))
        self.assertEqual(receipt['diagnosticSha256'], control.sha(patched))

    def test_wrong_symbol_opcode_context_and_source_fingerprint_fail(self):
        data, build, offset = fixture()
        for delta in (0,2,3,5,6):
            changed = bytearray(data)
            changed[offset + delta] ^= 1
            with self.subTest(delta=delta), self.assertRaisesRegex(ValueError, 'instruction/context'):
                control.patch_image(bytes(changed), build, control.sha(changed))
        build['stereoSupport']['controlOnsetAddress'] += 1
        with self.assertRaisesRegex(ValueError, 'instruction/context'):
            control.patch_image(data, build, control.sha(data))
        with self.assertRaisesRegex(ValueError, 'verification receipt'):
            control.patch_image(data, build, '0' * 64)

    def test_duplicate_instruction_context_and_speech_address_are_rejected(self):
        data, build, offset = fixture()
        changed = bytearray(data)
        changed[offset + 32:offset + 32 + len(control.CONTEXT)] = control.CONTEXT
        with self.assertRaisesRegex(ValueError, 'not unique'):
            control.patch_image(bytes(changed), build, control.sha(changed))
        build['stereoSupport']['controlOnsetAddress'] = build['streamAddress']
        with self.assertRaisesRegex(ValueError, 'escapes generated music'):
            control.patch_image(data, build, control.sha(data))


if __name__ == '__main__':
    unittest.main()
