import { afterAll, test } from "bun:test";
import assert from "node:assert/strict";
import { readFile, writeFile, mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { buildArrangement, compileScore, PAL_TICKS_PER_SECOND, type Score } from "../scripts/build-arrangement.ts";

const instrument = { waveform: 16, attackDecay: 2, sustainRelease: 0x92 };
const fixture: Score = {
  title: "Three voice timing fixture",
  composer: "Test fixture",
  quarterBpm: 72,
  totalBeats: 151,
  tailTicks: 25,
  volume: 15,
  voices: [
    { instrument, events: Array.from({ length: 300 }, (_, i) => ({ startBeat: i / 2, durationBeats: 0.5, midi: i % 2 ? 75 : 76 })) },
    { instrument, events: [{ startBeat: 0, durationBeats: 1, midi: 45 }, { startBeat: 1, durationBeats: 1, midi: 45 }, { startBeat: 5, durationBeats: 0.125, midi: 48 }] },
    { instrument, events: [{ startBeat: 4, durationBeats: 1, midi: 57 }] },
  ],
};
const directories: string[] = [];

async function fixtureOutput() {
  const output = await mkdtemp(join(tmpdir(), "fuer-elise-player-"));
  directories.push(output);
  const source = join(output, "score.json");
  await writeFile(source, JSON.stringify(fixture));
  return { output, source, name: "arrangement" };
}

afterAll(async () => {
  await Promise.all(directories.map(path => rm(path, { recursive: true, force: true })));
});

test("absolute beat quantization supports three voices, over 255 notes and over a minute", () => {
  const compiled = compileScore(fixture);
  const melody = compiled.events.filter(event => event.voice === 0);
  assert.equal(melody.length, 300);
  assert.ok(compiled.durationSeconds > 120);
  for (let i = 0; i < melody.length; i++) {
    assert.equal(melody[i].startTick, Math.round(i / 2 * 60 / 72 * PAL_TICKS_PER_SECOND));
    assert.equal(melody[i].frequencyWord, i % 2 ? 0x2964 : 0x2bda);
  }
  const fast = compiled.events.find(event => event.voice === 1 && event.startBeat === 5)!;
  assert.equal(fast.durationTicks, 5);
  assert.equal(fast.gateOffTick, fast.startTick + 4);
  assert.equal(compiled.scoreTicks, Math.round(151 * 60 / 72 * PAL_TICKS_PER_SECOND));
  assert.equal(compiled.totalTicks, compiled.scoreTicks + 25);
});

test("repeated notes get gate gaps, while rests and later voice starts stay silent", () => {
  const score = structuredClone(fixture);
  score.voices[1].events.splice(2, 0, { startBeat: 2, durationBeats: 1, midi: null });
  const compiled = compileScore(score);
  const bass = compiled.events.filter(event => event.voice === 1);
  assert.ok(bass[0].gateOffTick! < bass[1].startTick);
  assert.equal(bass[2].gateOffTick, null);
  assert.equal(bass[2].frequencyWord, 0);
  const bassOn = compiled.writes.filter(write => write.address === 0xd40b && write.value === 0x11);
  assert.deepEqual(bassOn.map(write => write.tick), [0, 42, 209]);
  const harmonyOn = compiled.writes.filter(write => write.address === 0xd412 && write.value === 0x11);
  assert.deepEqual(harmonyOn.map(write => write.tick), [167]);
  assert.deepEqual(compiled.writes.slice(-4), [
    { tick: compiled.totalTicks, address: 0xd404, value: 16 },
    { tick: compiled.totalTicks, address: 0xd40b, value: 16 },
    { tick: compiled.totalTicks, address: 0xd412, value: 16 },
    { tick: compiled.totalTicks, address: 0xd418, value: 0 },
  ]);
});

test("invalid pitches, overlaps, unrepresentable timing and bounds fail explicitly", () => {
  const change = (mutate: (score: Score) => void) => { const score = structuredClone(fixture); mutate(score); return score; };
  assert.throws(() => compileScore(change(score => score.voices[0].events[0].midi = 128)), /midi/);
  assert.throws(() => compileScore(change(score => score.voices[0].events[1].startBeat = 0.25)), /overlap/);
  assert.throws(() => compileScore(change(score => score.voices[0].events[0].durationBeats = 0.001)), /one PAL tick/);
  assert.throws(() => compileScore(change(score => score.totalBeats = 1)), /totalBeats/);
  assert.throws(() => compileScore(change(score => score.voices.pop())), /three voices/);
  assert.throws(() => compileScore(change(score => score.voices[0].instrument.waveform = 128)), /waveform/);
  assert.throws(() => compileScore(change(score => score.totalBeats = 100000)), /16-bit delay/);
});

test("a one-frame grace note retains its pitch and retriggers before the next note", () => {
  const score = structuredClone(fixture);
  score.voices[0].events = [{ startBeat: 0, durationBeats: 1 / 48, midi: 76 }, { startBeat: 1 / 48, durationBeats: 0.25, midi: 75 }];
  const compiled = compileScore(score);
  const grace = compiled.voices[0].events[0];
  assert.equal(grace.durationTicks, 1);
  assert.equal(grace.gateOffTick, 1);
  const controls = compiled.writes.filter(write => write.address === 0xd404 && write.tick === 1);
  assert.deepEqual(controls.map(write => write.value), [16, 17]);
});

test("PSID v2 PAL 8580 and BASIC PRG share the bounded callable payload", async () => {
  const options = await fixtureOutput();
  const manifest = await buildArrangement(options);
  const sid = await readFile(join(options.output, "arrangement.sid"));
  const prg = await readFile(join(options.output, "arrangement.prg"));
  assert.equal(sid.toString("ascii", 0, 4), "PSID");
  assert.equal(sid.readUInt16BE(4), 2);
  assert.equal(sid.readUInt16BE(6), 0x7c);
  assert.equal(sid.readUInt16BE(8), 0x1000);
  assert.equal(sid.readUInt16BE(10), 0x1000);
  assert.equal(sid.readUInt16BE(12), 0x1003);
  assert.equal(sid.readUInt16BE(14), 1);
  assert.equal(sid.readUInt16BE(16), 1);
  assert.equal(sid.readUInt32BE(18), 0);
  assert.equal(sid.readUInt16BE(118), 0x24);
  assert.deepEqual([...sid.subarray(120, 124)], [0, 0, 0, 0]);
  assert.equal(prg.readUInt16LE(0), 0x0801);
  assert.equal(prg.toString("ascii", 7, 11), "2064");
  assert.equal(manifest.symbols.standalone, 0x0810);
  assert.equal(manifest.symbols.init, 0x1000);
  assert.equal(manifest.symbols.play, 0x1003);
  assert.ok(manifest.payloadEndAddress <= 0xa000);
  assert.equal(manifest.payloadEndAddress, 0x1000 + sid.length - 0x7c);
  assert.deepEqual(sid.subarray(0x7c), prg.subarray(2 + 0x1000 - 0x0801));
});

test("builds produce identical binaries, assembly and manifests", async () => {
  const first = await fixtureOutput();
  const second = await fixtureOutput();
  await buildArrangement(first);
  await buildArrangement(second);
  for (const name of ["sid", "prg", "asm", "events.json"]) {
    assert.deepEqual(await readFile(join(first.output, `arrangement.${name}`)), await readFile(join(second.output, `arrangement.${name}`)));
  }
});

test("an oversized register stream fails before writing a PRG hidden by BASIC ROM", async () => {
  const options = await fixtureOutput();
  const score = structuredClone(fixture);
  score.totalBeats = 1250;
  score.voices[0].events = Array.from({ length: 2500 }, (_, i) => ({ startBeat: i / 2, durationBeats: 0.5, midi: 60 }));
  await writeFile(options.source, JSON.stringify(score));
  await assert.rejects(buildArrangement(options), /fit below BASIC ROM/);
  await assert.rejects(readFile(join(options.output, "arrangement.prg")), { code: "ENOENT" });
});

test("the same exporter builds an unrelated tempo, timbre and metadata without source edits", async () => {
  const options = await fixtureOutput();
  const second: Score = {
    title: "Another arrangement",
    composer: "Someone else",
    quarterBpm: 120,
    totalBeats: 2,
    tailTicks: 5,
    volume: 11,
    voices: [
      { instrument: { waveform: 32, attackDecay: 0x03, sustainRelease: 0x62 }, events: [{ startBeat: 0, durationBeats: 1, midi: 60 }] },
      { instrument: { waveform: 64, attackDecay: 0x03, sustainRelease: 0x62, pulseWidth: 0x600 }, events: [{ startBeat: 0.5, durationBeats: 1, midi: 36 }] },
      { instrument, events: [{ startBeat: 1, durationBeats: 1, midi: 67 }] },
    ],
  };
  await writeFile(options.source, JSON.stringify(second));
  const manifest = await buildArrangement({ ...options, name: "other-piece" });
  const sid = await readFile(join(options.output, "other-piece.sid"));
  assert.equal(sid.toString("ascii", 22, 22 + second.title.length), second.title);
  assert.equal(sid.toString("ascii", 54, 54 + second.composer.length), second.composer);
  assert.equal(manifest.quarterBpm, 120);
  assert.equal(manifest.scoreTicks, Math.round(PAL_TICKS_PER_SECOND));
  assert.deepEqual(manifest.voices.map(voice => voice.instrument.waveform), [32, 64, 16]);
  assert.equal(manifest.voices[1].instrument.pulseWidth, 0x600);
});
