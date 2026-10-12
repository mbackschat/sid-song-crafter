import { afterAll, test } from "bun:test";
import assert from "node:assert/strict";
import { readFile, mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { buildSong, compileEvents } from "../scripts/build-song.ts";

const score = JSON.parse(await readFile(new URL("../songs/fuer-elise-opening.json", import.meta.url), "utf8"));
const temporaryDirectories: string[] = [];

async function temporaryOutput(prefix: string): Promise<string> {
  const path = await mkdtemp(join(tmpdir(), prefix));
  temporaryDirectories.push(path);
  return path;
}

afterAll(async () => {
  await Promise.all(temporaryDirectories.map(path => rm(path, { recursive: true, force: true })));
});

test("the manual transcription keeps the pickup, opening bar, and A eighth", () => {
  assert.deepEqual(score.notes.map((note: { pitch: string }) => note.pitch), ["E5", "D#5", "E5", "D#5", "E5", "B4", "D5", "C5", "A4"]);
  assert.deepEqual(score.notes.map((note: { sixteenths: number }) => note.sixteenths), [1, 1, 1, 1, 1, 1, 1, 1, 2]);
});

test("absolute PAL quantization preserves pitch, duration, gate gaps, and a silent tail", () => {
  const events = compileEvents(score);
  assert.deepEqual(events.map(event => event.startTick), [0, 10, 21, 31, 42, 52, 63, 73, 84, 104]);
  assert.deepEqual(events.map(event => event.durationTicks), [10, 11, 10, 11, 10, 11, 10, 11, 20, 25]);
  assert.deepEqual(events.slice(0, -1).map(event => event.frequencyWord), [0x2bda, 0x2964, 0x2bda, 0x2964, 0x2bda, 0x20da, 0x2711, 0x22ce, 0x1d44]);
  assert.deepEqual(events.slice(0, -1).map(event => event.gateOffTick), [8, 19, 29, 40, 50, 61, 71, 82, 102]);
  assert.equal(events.at(-1)!.frequencyWord, 0);
  assert.equal(events.at(-1)!.gateOffTick, null);
  for (const event of events.slice(0, -1)) {
    const midi = { E5: 76, "D#5": 75, B4: 71, D5: 74, C5: 72, A4: 69 }[event.pitch!];
    const hz = 440 * 2 ** ((midi! - 69) / 12);
    const actualHz = event.frequencyWord * (17734475 / 18) / 2 ** 24;
    assert.ok(Math.abs(1200 * Math.log2(actualHz / hz)) < 0.12);
  }
});

test("a longer valid excerpt retains events after 255 total ticks", () => {
  const longer = { ...score, notes: Array.from({ length: 6 }, () => score.notes).flat() };
  const events = compileEvents(longer);
  assert.equal(events.length, 55);
  assert.ok(events.at(-1)!.startTick > 600);
  assert.equal(events[9].pitch, "E5");
});

test("invalid note spelling and impossible articulation fail instead of becoming a fallback pitch", () => {
  assert.throws(() => compileEvents({ ...score, notes: [{ pitch: "-", sixteenths: 1 }] }), /pitch/);
  assert.throws(() => compileEvents({ ...score, quarterBpm: 2000 }), /release/);
});

test("PSID v2 exports a PAL 8580 VBI player and the same callable payload as the PRG", async () => {
  const output = await temporaryOutput("c64-song-test-");
  const result = await buildSong({ output });
  const sid = await readFile(join(output, "fuer-elise-opening.sid"));
  const prg = await readFile(join(output, "fuer-elise-opening.prg"));
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
  assert.equal(result.symbols.init, 0x1000);
  assert.equal(result.symbols.play, 0x1003);
  assert.equal(result.symbols.standalone, 0x0810);
  assert.deepEqual(sid.subarray(0x7c), prg.subarray(2 + 0x1000 - 0x0801));
  assert.equal(sid[0x7c], 0x4c);
  assert.equal(sid[0x7f], 0x4c);
  assert.equal(prg.toString("ascii", 7, 11), "2064");
});

test("builds produce identical binary bytes and event manifests", async () => {
  const first = await temporaryOutput("c64-song-test-a-");
  const second = await temporaryOutput("c64-song-test-b-");
  await buildSong({ output: first });
  await buildSong({ output: second });
  for (const file of ["fuer-elise-opening.sid", "fuer-elise-opening.prg", "fuer-elise-opening.events.json", "fuer-elise-opening.asm"]) {
    assert.deepEqual(await readFile(join(first, file)), await readFile(join(second, file)));
  }
});
