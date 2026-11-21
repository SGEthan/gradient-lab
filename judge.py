"""Sandboxed subprocess adapter for the native judge."""

import importlib.util
import json
import resource
import sys
from dataclasses import asdict
from pathlib import Path


def load_module(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    resource.setrlimit(resource.RLIMIT_FSIZE, (2_000_000, 2_000_000))
    payload = json.load(sys.stdin)
    problems = load_module("problems")
    judge = load_module("judge_core")
    problem = dict(problems.BY_ID[payload["id"]])
    problem["cases"] = [asdict(case) for case in problem["cases"]]
    print(json.dumps(judge.assess(payload, problem), ensure_ascii=False))


if __name__ == "__main__":
    main()
