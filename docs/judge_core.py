"""Shared assessment engine for native Python and Pyodide."""

import contextlib
import io
import math
import time
import traceback
from numbers import Integral, Real


class BoundedLog(io.StringIO):
    def write(self, message):
        if self.tell() < 3000:
            super().write(message[:3000 - self.tell()])
        return len(message)


def error_text(error):
    if isinstance(error, SyntaxError):
        return f"第 {error.lineno} 行 · {error.msg}"
    frames = [frame for frame in traceback.extract_tb(error.__traceback__) if frame.filename == "<solution>"]
    location = f"第 {frames[-1].lineno} 行 · " if frames else ""
    return (f"{location}{type(error).__name__}: {error}")[:450]


def fixture_namespace(runtime):
    if runtime == "PyTorch":
        import torch
        torch.set_num_threads(1)

        def seq(*shape):
            values = torch.arange(math.prod(shape), dtype=torch.float32)
            return (values.remainder(17) - 8).reshape(shape) / 7

        return {"torch": torch, "seq": seq}
    if runtime == "NumPy":
        import numpy as np
        return {"np": np, "a": np.array}
    return {}


def compare(actual, expected, fixtures):
    if isinstance(expected, (tuple, list)):
        assert isinstance(actual, type(expected)) and len(actual) == len(expected), (
            f"返回值应为长度 {len(expected)} 的 {type(expected).__name__}。"
        )
        for left, right in zip(actual, expected):
            compare(left, right, fixtures)
        return
    torch = fixtures.get("torch")
    np = fixtures.get("np")
    if torch is not None and isinstance(expected, torch.Tensor):
        assert isinstance(actual, torch.Tensor), "返回值应为 torch.Tensor。"
        torch.testing.assert_close(actual, expected, atol=1e-6, rtol=1e-5, equal_nan=True)
    elif np is not None and isinstance(expected, np.ndarray):
        assert isinstance(actual, np.ndarray), "返回值应为 NumPy ndarray。"
        assert actual.shape == expected.shape, f"期望形状 {expected.shape}，得到 {actual.shape}。"
        if expected.dtype.kind in "biu":
            actual_kind, expected_kind = actual.dtype.kind, expected.dtype.kind
            assert actual_kind == expected_kind or {actual_kind, expected_kind} <= {"i", "u"}, "检查数组 dtype。"
            np.testing.assert_array_equal(actual, expected)
        else:
            np.testing.assert_allclose(actual, expected, atol=1e-7, rtol=1e-6, equal_nan=True)
    elif isinstance(expected, bool):
        assert isinstance(actual, (bool, np.bool_) if np is not None else bool) and actual == expected, f"期望 {expected!r}。"
    elif isinstance(expected, Integral):
        assert isinstance(actual, Integral) and actual == expected, f"期望整数 {expected!r}，得到 {str(actual)[:135]}。"
    elif isinstance(expected, Real):
        assert isinstance(actual, Real) and math.isclose(actual, expected, abs_tol=1e-7, rel_tol=1e-6), (
            f"期望 {expected!r}，得到 {str(actual)[:135]}。"
        )
    else:
        assert actual == expected, f"期望 {expected!r}，得到 {str(actual)[:135]}。"


def check(problem_id, solve, reference, case, fixtures):
    args = eval(case["arguments"], fixtures)
    reference_args = eval(case["arguments"], fixtures)
    actual = solve(*args)
    if problem_id == "gate-calibration":
        torch = fixtures.get("torch")
        logits, target = reference_args
        assert isinstance(actual, float) and math.isfinite(actual), "返回值应为有限的 Python float。"
        if torch is None:
            np = fixtures["np"]
            mean = np.exp(-np.logaddexp(0, -(logits + actual))).mean()
        else:
            mean = torch.sigmoid(logits + actual).mean().item()
        error = abs(mean - target)
        assert error <= 1e-7, f"目标均值为 {target:.8f}，绝对误差为 {error:.4g}。"
        return

    expected = eval(case["expected"], fixtures) if case.get("expected") else reference(*reference_args)
    compare(actual, expected, fixtures)
    if problem_id == "int8-quantization":
        assert actual[0].dtype == fixtures["np"].int8, "量化数组应为 np.int8。"
    if problem_id in {"slot-update", "kv-cache"}:
        for left, right in zip(args, reference_args):
            compare(left, right, fixtures)

    grad_inputs = [arg for arg in args if getattr(arg, "requires_grad", False)]
    if grad_inputs:
        torch = fixtures["torch"]
        assert actual.requires_grad, "返回值应保留输入的梯度。"
        reference_inputs = [arg for arg in reference_args if getattr(arg, "requires_grad", False)]
        actual_grad = torch.autograd.grad(actual, grad_inputs)
        expected_grad = torch.autograd.grad(expected, reference_inputs)
        compare(actual_grad, expected_grad, fixtures)


def evaluate(payload, problem):
    fixtures = fixture_namespace(problem["runtime"])
    submission = {"__name__": "submission"}
    reference = {"__name__": "reference"}
    exec(compile(problem["solution"], "<reference>", "exec"), reference)
    entry = next(name for name, value in reference.items() if getattr(value, "__module__", "") == "reference")
    try:
        exec(compile(payload["code"], "<solution>", "exec"), submission)
        solve = submission.get(entry)
        if not callable(solve):
            return {"error": f"找不到函数 {entry}。保留模板里的函数名和参数。"}
    except BaseException as error:
        return {"error": error_text(error)}

    cases = problem["cases"] if payload["mode"] == "submit" else problem["cases"][:2]
    results = []
    for case in cases:
        start = time.perf_counter()
        failure = None
        try:
            check(problem["id"], solve, reference[entry], case, fixtures)
        except BaseException as error:
            failure = error_text(error)
        results.append({"name": case["name"], "ok": failure is None, "error": failure,
                        "ms": round((time.perf_counter() - start) * 1000, 2)})
    return {"tests": results, "passed": sum(case["ok"] for case in results), "total": len(results)}


def assess(payload, problem):
    log = BoundedLog()
    with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        try:
            result = evaluate(payload, problem)
        except Exception as error:
            result = {"error": "判题进程错误 · " + error_text(error)}
    result["log"] = log.getvalue()
    return result
