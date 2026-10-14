import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("render_audio_test", ROOT / "tests/render_audio_test.py")
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
renderer = ROOT / ".local/bin/render-sid"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render(sid, output, clock):
    command = [str(renderer), str(sid), str(output), "1.2", "--clock", clock]
    result = subprocess.run(command, capture_output=True, text=True, timeout=20, check=True)
    return {"command": command, "receipt": result.stdout.strip(), "input_sha256": sha256(sid),
            "output_sha256": sha256(output), "registers_sha256": sha256(Path(str(output) + ".registers.tsv"))}


report = {"renderer_sha256": sha256(renderer), "rate_hz": fixture.RATE, "duration_seconds": 1.2,
          "subtune": 1, "chip_addresses": ["0xd400", "0xd420"], "compatibility": [], "ntsc": []}
for name, clock, before in (("mono-pal", "pal", "mono-pal-before"),
                            ("dual-pal", "pal", "dual-pal-before"),
                            ("mono-ntsc", "ntsc", "mono-ntsc-traceprobe")):
    sid = OUTPUT / f"{name}.sid"
    output = OUTPUT / f"{name}-after.wav"
    record = render(sid, output, clock)
    record["wav_matches_before"] = output.read_bytes() == (OUTPUT / f"{before}.wav").read_bytes()
    record["registers_match_before"] = Path(str(output) + ".registers.tsv").read_bytes() == (OUTPUT / f"{before}.wav.registers.tsv").read_bytes()
    assert record["wav_matches_before"] and record["registers_match_before"]
    report["compatibility"].append(record)

cpu_clock, frame_cycles = 14318181.82 / 14, 263 * 65
for model in ("8580", "6581"):
    sid, output = OUTPUT / f"dual-ntsc-{model}.sid", OUTPUT / f"dual-ntsc-{model}.wav"
    fixture.write_two_sid_fixture(sid, clock="ntsc", model=model, counter=True)
    record = render(sid, output, "ntsc")
    frames, left, right = fixture.read_stereo_samples(output)
    assert frames == round(1.2 * fixture.RATE)
    record.update(model=model, channels=2, frames=frames, measured_duration_seconds=frames / fixture.RATE,
                  left_hz=fixture.frequency(left[fixture.RATE // 4:fixture.RATE]),
                  right_hz=fixture.frequency(right[fixture.RATE // 4:fixture.RATE]),
                  left_rms=fixture.rms(left[fixture.RATE // 4:fixture.RATE]),
                  right_rms=fixture.rms(right[fixture.RATE // 4:fixture.RATE]))
    assert abs(record["left_hz"] - 440) < 3 and abs(record["right_hz"] - 660) < 3
    assert record["left_rms"] > 100 and record["right_rms"] > 100
    rows = [line.split("\t") for line in Path(str(output) + ".registers.tsv").read_text().splitlines()[1:]]
    start, end = rows[4], rows[-1]
    elapsed_ms = int(end[0]) - int(start[0])
    expected = elapsed_ms * cpu_clock / (1000 * frame_cycles)
    observed = [bytes.fromhex(end[chip])[2] - bytes.fromhex(start[chip])[2] for chip in (1, 2)]
    assert all(abs(count - expected) < 1.1 for count in observed)
    record.update(elapsed_emulation_ms=elapsed_ms, expected_vbi_updates=expected,
                  observed_vbi_updates=observed, expected_vbi_hz=cpu_clock / frame_cycles)
    report["ntsc"].append(record)
(OUTPUT / "receipt.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
