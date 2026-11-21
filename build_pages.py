"""Build a static GitHub Pages site. No packages are required for the build."""

import argparse
import hashlib
import json
import shutil
import tarfile
import urllib.request
from dataclasses import asdict
from io import BytesIO
from pathlib import Path

from problems import PROBLEMS, catalog, load_sets

ROOT = Path(__file__).resolve().parent
WASM_RELEASE = "314.0.8"
NUMPY_WHEEL = "numpy-2.4.6-cp314-cp314-pyemscripten_2026_0_wasm32.whl"
PYODIDE_FILES = ["pyodide.mjs", "pyodide.asm.mjs", "pyodide.asm.wasm", "pyodide-lock.json", "python_stdlib.zip"]
ARTIFACTS = {
    "pyodide-core.tar.bz2": (f"https://github.com/pyodide/pyodide/releases/download/{WASM_RELEASE}/pyodide-core-{WASM_RELEASE}.tar.bz2",
                            "ff3e5f9d9bc8e98ff30b99515535fc24d375994f47a978c61975d653e162ca37"),
    NUMPY_WHEEL: (f"https://cdn.jsdelivr.net/pyodide/v{WASM_RELEASE}/full/{NUMPY_WHEEL}",
                  "a292c1f5d7d8a2208cd5e94fc467604c131cabcd2fc14fed6eefde121e7fabdf"),
    "LICENSE-pyodide": (f"https://raw.githubusercontent.com/pyodide/pyodide/{WASM_RELEASE}/LICENSE",
                        "1f256ecad192880510e84ad60474eab7589218784b9a50bc7ceee34c2b91f1d5"),
    "LICENSE-cpython": ("https://raw.githubusercontent.com/python/cpython/v3.14.2/LICENSE",
                        "b0e25a78cffb43f4d92de8b61ccfa1f1f98ecbc22330b54b5251e7b6ba010231"),
}


def web_questions():
    variants = {p["id"]: p for p in load_sets([ROOT / "web_variants.txt"])}
    torch_ids = {p["id"] for p in PROBLEMS if p["runtime"] == "PyTorch"}
    if variants.keys() != torch_ids:
        raise ValueError("Every native PyTorch problem needs a browser variant.")
    return [variants.get(p["id"], p) for p in PROBLEMS]


def fetch_artifact(name, cache):
    path = cache / name if cache is not None else None
    url, checksum = ARTIFACTS[name]
    if path is not None and path.is_file():
        data = path.read_bytes()
    else:
        with urllib.request.urlopen(url, timeout=40) as response:
            data = response.read()
    if hashlib.sha256(data).hexdigest() != checksum:
        raise ValueError(f"Checksum mismatch for {name}")
    return data


def build_runtime(output, cache):
    runtime = output / "pyodide"
    runtime.mkdir(exist_ok=True)
    stamp = runtime / "VERSION"
    if (stamp.is_file() and stamp.read_text() == WASM_RELEASE
            and all((runtime / name).is_file() for name in (*PYODIDE_FILES, NUMPY_WHEEL, "LICENSE-pyodide", "LICENSE-cpython"))):
        return
    archive = fetch_artifact("pyodide-core.tar.bz2", cache)
    with tarfile.open(fileobj=BytesIO(archive), mode="r:bz2") as contents:
        for name in PYODIDE_FILES:
            with contents.extractfile("pyodide/" + name) as source, (runtime / name).open("wb") as target:
                shutil.copyfileobj(source, target)
    for name in (NUMPY_WHEEL, "LICENSE-pyodide", "LICENSE-cpython"):
        (runtime / name).write_bytes(fetch_artifact(name, cache))
    stamp.write_text(WASM_RELEASE)
    (runtime / "SOURCES.md").write_text(
        f"Pyodide {WASM_RELEASE} source: https://github.com/pyodide/pyodide/tree/{WASM_RELEASE}\n"
        "CPython 3.14.2 source: https://github.com/python/cpython/tree/v3.14.2\n"
        "NumPy 2.4.6 source: https://github.com/numpy/numpy/tree/v2.4.6\n"
        "The NumPy wheel includes its license notices.\n", encoding="utf-8",
    )


def build(output, cache):
    output.mkdir(parents=True, exist_ok=True)
    for name in ["style.css", "app.js", "judge-worker.js"]:
        shutil.copyfile(ROOT / "static" / name, output / name)
    source = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
    (output / "index.html").write_text(source.replace('data-judge="native"', 'data-judge="browser"'), encoding="utf-8")
    shutil.copyfile(ROOT / "judge_core.py", output / "judge_core.py")
    problems = web_questions()
    data = [
        dict(summary, cases=[asdict(case) for case in problem["cases"]])
        for summary, problem in zip(catalog(problems), problems)
    ]
    (output / "questions.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    build_runtime(output, cache)
    (output / ".nojekyll").touch()
    print(f"Built {len(data)} questions in {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "docs")
    parser.add_argument("--runtime-cache", type=Path)
    args = parser.parse_args()
    build(args.out.resolve(), args.runtime_cache)
