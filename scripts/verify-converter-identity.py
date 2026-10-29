"""Require the working tree's native converter to match an earlier Git ref byte for byte on every recipe."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
RECIPE_ROOTS = ("songs", "config", "tests/fixtures")
RECIPE_MARKER = b'"sidwizard-arrangement-v1"'
OUTPUT_PLACEHOLDER = b"<output>"


def discover_recipes(root=ROOT):
    return [path for base in RECIPE_ROOTS for path in sorted((root / base).rglob("*.json")) if RECIPE_MARKER in path.read_bytes()]


def export_baseline(ref, destination):
    """Materialize the converter sources of `ref` under `destination`, keeping the layout its ROOT-relative imports expect."""
    archive = subprocess.run(["git", "-C", str(ROOT), "archive", ref, "scripts"], check=True, capture_output=True).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
        bundle.extractall(destination)
    return Path(destination) / "scripts/arrange-sidwizard.py"


def stand_in_score(recipe):
    """One note per voice at the start of each section.

    Several recipes name scores that are kept out of Git because their rights are unknown; this still exercises every
    instrument encoding and section mapping of such a recipe, which is where converter changes can alter bytes.
    """
    names = list(recipe["sections"][0]["voices"])
    sections = recipe["sections"]
    return {
        "title": "Stand-in", "composer": "Stand-in", "quarterBpm": 120, "totalBeats": sections[-1]["endBeat"], "tailTicks": 3, "volume": 15,
        "voices": [{"name": name, "events": [{"startBeat": section["startBeat"], "durationBeats": min(1, section["endBeat"] - section["startBeat"]), "midi": 48 + 7 * index} for section in sections]} for index, name in enumerate(names)],
    }


def usable_recipe(recipe_path, scratch):
    """Return the recipe to convert and whether a stand-in score replaced a missing one."""
    recipe = json.loads(recipe_path.read_text())
    if (recipe_path.parent / recipe["score"]).is_file():
        return recipe_path, False
    stand_in = Path(scratch) / f"{hashlib.sha256(str(recipe_path).encode()).hexdigest()[:12]}.score.json"
    stand_in.write_text(json.dumps(stand_in_score(recipe)))
    patched = stand_in.with_suffix(".recipe.json")
    patched.write_text(json.dumps(dict(recipe, score=str(stand_in))))
    return patched, True


def convert(script, recipe, clock):
    """Run one conversion in a scratch directory and return its exit code, normalized streams and output files."""
    with tempfile.TemporaryDirectory() as scratch:
        output = Path(scratch).resolve() / "out"
        command = [sys.executable, str(script), str(recipe), "--output-dir", str(output)] + (["--clock", clock] if clock else [])
        finished = subprocess.run(command, capture_output=True)
        # The converter embeds its resolved output directory in the manifest and its summary line.
        normalize = lambda data: data.replace(str(output).encode(), OUTPUT_PLACEHOLDER)
        files = {str(path.relative_to(output)): normalize(path.read_bytes()) for path in sorted(output.rglob("*")) if path.is_file()} if output.exists() else {}
        return finished.returncode, normalize(finished.stdout), normalize(finished.stderr), files


def differences(baseline, current):
    """List the observable differences between two `convert` results."""
    found = [label for index, label in ((0, "exit code"), (1, "stdout"), (2, "stderr")) if baseline[index] != current[index]]
    for name in sorted(set(baseline[3]) | set(current[3])):
        if name not in baseline[3] or name not in current[3]:
            found.append(f"{name} only in {'current' if name in current[3] else 'baseline'}")
        elif baseline[3][name] != current[3][name]:
            found.append(f"{name} bytes")
    return found


def verify(ref, recipes, clocks, jobs):
    """Compare every recipe and clock; return (recipe, clock, stand_in, converted, differences) rows."""
    with tempfile.TemporaryDirectory() as scratch:
        baseline_script = export_baseline(ref, scratch)
        current_script = ROOT / "scripts/arrange-sidwizard.py"

        usable = {recipe: usable_recipe(recipe, scratch) for recipe in recipes}

        def compare(case):
            recipe, clock = case
            path, stand_in = usable[recipe]
            baseline, current = convert(baseline_script, path, clock), convert(current_script, path, clock)
            return recipe, clock, stand_in, current[0] == 0, differences(baseline, current)

        with ThreadPoolExecutor(max_workers=jobs) as pool:
            return list(pool.map(compare, [(recipe, clock) for recipe in recipes for clock in clocks]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recipes", nargs="*", type=Path, help="Recipes to compare; default: every native arrangement recipe under songs/, config/ and tests/fixtures/")
    parser.add_argument("--baseline-ref", default="HEAD", help="Git ref whose converter defines the expected output (default: HEAD)")
    parser.add_argument("--clock", action="append", choices=("pal", "ntsc"), help="Convert for this target clock (repeatable); default: each recipe's own clock")
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()
    recipes = [path.resolve() for path in args.recipes] or discover_recipes()
    started = time.monotonic()
    rows = verify(args.baseline_ref, recipes, args.clock or [None], args.jobs)
    failures = [row for row in rows if row[4]]
    for recipe, clock, _, _, found in failures:
        print(f"DIFFERS {recipe.relative_to(ROOT) if recipe.is_relative_to(ROOT) else recipe} clock={clock or 'recipe'}: {', '.join(found)}")
    # An identical failure proves nothing about output bytes, so it is counted apart from identical conversions.
    converted = sum(1 for row in rows if row[3] and not row[4])
    stood_in = sum(1 for row in rows if row[2] and row[3] and not row[4])
    unconverted = sum(1 for row in rows if not row[3] and not row[4])
    print(f"Compared {len(rows)} conversions of {len(recipes)} recipes against {args.baseline_ref} in {time.monotonic() - started:.1f} s: "
          f"{converted} identical ({stood_in} with a stand-in score), {unconverted} failed identically, {len(failures)} differ")
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
