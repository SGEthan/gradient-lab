import { loadPyodide } from "./pyodide/pyodide.mjs";

const PYODIDE_URL = new URL("./pyodide/", self.location.href).href;
let engine;
let pythonAssess;
let hasNumPy = false;

async function loadEngine() {
  const sourceRequest = fetch("./judge_core.py");
  const runtime = await loadPyodide({ indexURL: PYODIDE_URL });
  const source = await sourceRequest;
  if (!source.ok) throw new Error("judge source unavailable");
  const setup = (await source.text()) + `
import json as _json
def _assess_json(payload, problem):
    return _json.dumps(assess(_json.loads(payload), _json.loads(problem)), ensure_ascii=False)
`;
  const scope = runtime.runPython("dict()");
  runtime.runPython(setup, { globals: scope });
  pythonAssess = scope.get("_assess_json");
  return runtime;
}

self.onmessage = async ({ data }) => {
  const {payload, problem} = data;
  try {
    engine ??= await loadEngine();
    if (problem.runtime === "NumPy" && !hasNumPy) {
      await engine.loadPackage("numpy");
      hasNumPy = true;
    }
    self.postMessage({ phase: "ready" });
    const result = JSON.parse(pythonAssess(JSON.stringify(payload), JSON.stringify(problem)));
    self.postMessage({ result });
  } catch (error) {
    self.postMessage({ error: "网页判题环境出错。\n" + (error.message || String(error)).slice(0, 350) });
    console.error(error);
  }
};
