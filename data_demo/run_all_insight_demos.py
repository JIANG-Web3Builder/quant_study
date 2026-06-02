#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smoke-test runner for the Insight demo files.

Credentials are read from the ignored local config written by
``save_insight_credentials.py``. Environment variables with the same names can
still override the local config when needed.

Examples:
  python data_demo/save_insight_credentials.py
  python data_demo/run_all_insight_demos.py --dry-run
  python data_demo/run_all_insight_demos.py --categories subscribe,playback,doc_extra --timeout 90
  python data_demo/run_all_insight_demos.py --one subscribe:subscribe_tick_by_id_demo
  python data_demo/run_all_insight_demos.py --compare-docs tools/insight/exports/insight_python_data_dictionary_raw.json --dry-run
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import datetime as dt
import importlib
import inspect
import io
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import traceback
from dataclasses import asdict, dataclass
from contextlib import redirect_stderr, redirect_stdout
from typing import Dict, Iterable, List, Optional, Tuple


ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA_DEMO_DIR = pathlib.Path(__file__).resolve().parent
REPORT_DIR = DATA_DEMO_DIR / "reports"

MODULES = {
    "subscribe": "subscribe_demo",
    "playback": "playback_demo",
    "doc_extra": "doc_extra_demo",
}

SECRET_ENV = ("INSIGHT_USER", "INSIGHT_PASSWORD", "INSIGHT_PASSWORD_DPAPI")
SYMBOL_RE = re.compile(r"\b(?:get|subscribe|playback)_[A-Za-z0-9_]+\s*\(")


@dataclass
class DemoCase:
    category: str
    module: str
    function: str
    line: int


@dataclass
class DemoResult:
    category: str
    module: str
    function: str
    status: str
    elapsed_sec: float
    return_code: Optional[int] = None
    stdout_tail: str = ""
    stderr_tail: str = ""
    error: str = ""


def _tail(text: str, limit: int = 4000) -> str:
    if not text:
        return ""
    return text[-limit:]


def _redact(text: str) -> str:
    redacted = text or ""
    for name in SECRET_ENV:
        value = os.environ.get(name)
        if value:
            redacted = redacted.replace(value, f"<{name}>")
    with contextlib.suppress(Exception):
        from insight_config import redact as redact_insight

        redacted = redact_insight(redacted)
    return redacted


def _output_indicates_failure(text: str) -> bool:
    markers = [
        "invalid data",
        "invalid request",
        "invalid error msg",
        "Unsuccessful login",
        "login failed",
        "failed!!! reason",
        "Subscribe failed",
        "queryfininfo failed",
        "Traceback",
    ]
    return any(marker in (text or "") for marker in markers)


def _ensure_import_path() -> None:
    for path in (str(DATA_DEMO_DIR), str(ROOT)):
        if path not in sys.path:
            sys.path.insert(0, path)


def discover_cases(categories: Iterable[str]) -> List[DemoCase]:
    cases = []
    for category in categories:
        module_name = MODULES[category]
        source_path = DATA_DEMO_DIR / (module_name + ".py")
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef):
                continue
            if not node.name.endswith("_demo"):
                continue
            cases.append(DemoCase(category, module_name, node.name, node.lineno))
    return sorted(cases, key=lambda case: (case.category, case.line, case.function))


def import_package_symbols() -> Tuple[Dict[str, List[str]], Dict[str, str]]:
    package_modules = {
        "subscribe": "insight_python.com.insight.subscribe",
        "playback": "insight_python.com.insight.playback",
    }
    symbols = {}
    errors = {}
    supported_versions = {(3, 6), (3, 7), (3, 8), (3, 9), (3, 10)}
    if sys.version_info[:2] not in supported_versions:
        message = (
            f"Skipped on Python {sys.version_info.major}.{sys.version_info.minor}; "
            "insight_python 6.1.2 includes native clients for Python 3.6 through 3.10."
        )
        return {category: [] for category in package_modules}, {
            category: message for category in package_modules
        }

    for category, module_name in package_modules.items():
        try:
            module = importlib.import_module(module_name)
        except Exception as exc:
            symbols[category] = []
            errors[category] = f"{type(exc).__name__}: {exc}"
            continue
        names = []
        for name, obj in inspect.getmembers(module):
            if name.startswith("_"):
                continue
            if category == "subscribe" and name.startswith("subscribe_") and callable(obj):
                names.append(name)
            elif category == "playback" and name.startswith("playback_") and callable(obj):
                names.append(name)
        symbols[category] = sorted(set(names))
    return symbols, errors


def symbols_from_docs(path: pathlib.Path) -> List[str]:
    if not path.exists():
        raise FileNotFoundError(path)
    text = path.read_text(encoding="utf-8", errors="ignore")
    if path.suffix.lower() == ".json":
        try:
            data = json.loads(text)
            text = json.dumps(data, ensure_ascii=False)
        except json.JSONDecodeError:
            pass
    return sorted(set(match.group(0)[:-1] for match in SYMBOL_RE.finditer(text)))


def compare_coverage(cases: List[DemoCase], docs_path: Optional[pathlib.Path]) -> Dict[str, object]:
    demo_functions = {
        case.function[:-5] if case.function.endswith("_demo") else case.function
        for case in cases
    }
    package_symbols, package_import_errors = import_package_symbols()
    package_flat = sorted({name for names in package_symbols.values() for name in names if not name.startswith("<")})

    coverage: dict[str, object] = {
        "demo_api_count": len(demo_functions),
        "demo_apis": sorted(demo_functions),
        "package_api_count": len(package_flat),
        "package_apis": package_flat,
        "package_import_errors": package_import_errors,
        "package_without_demo": sorted(set(package_flat) - demo_functions),
        "demo_not_found_in_package": sorted(demo_functions - set(package_flat)),
    }

    if docs_path:
        doc_symbols = symbols_from_docs(docs_path)
        coverage.update(
            {
                "docs_path": str(docs_path),
                "docs_api_count": len(doc_symbols),
                "docs_apis": doc_symbols,
                "docs_without_demo": sorted(set(doc_symbols) - demo_functions),
                "demo_not_found_in_docs": sorted(demo_functions - set(doc_symbols)),
            }
        )

    return coverage


def login_for_module(module_name: str):
    from insight_python.com.insight import common
    from insight_config import login as insight_login

    module = importlib.import_module(module_name)

    common.config(False, False, False)
    markets = module.insightmarketservice()
    result = insight_login(markets, common_module=common, login_log=False)
    print(f"[login] {result!r}")
    if result != "login success":
        raise RuntimeError(f"Insight login failed: {result}")
    return common


def run_child(module_name: str, function_name: str, wait_after: float) -> int:
    _ensure_import_path()
    common = None
    try:
        module = importlib.import_module(module_name)
        func = getattr(module, function_name)
        common = login_for_module(module_name)
        print(f"[run] {module_name}.{function_name}")
        result = func()
        if result is not None:
            print(f"[return] {type(result).__name__}: {result!r}")
        if wait_after > 0:
            print(f"[wait] {wait_after}s for async callbacks")
            time.sleep(wait_after)
        return 0
    except Exception:
        traceback.print_exc()
        return 1
    finally:
        if common is not None:
            with contextlib.suppress(Exception):
                common.fini()


def run_parent_case(case: DemoCase, timeout: int, wait_after: float, python_executable: str) -> DemoResult:
    start = time.monotonic()
    cmd = [
        python_executable,
        str(pathlib.Path(__file__).resolve()),
        "--_child",
        case.module,
        case.function,
        "--wait-after",
        str(wait_after),
    ]
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            timeout=timeout,
            env=os.environ.copy(),
        )
        elapsed = time.monotonic() - start
        combined_output = f"{completed.stdout}\n{completed.stderr}"
        status = "PASS" if completed.returncode == 0 and not _output_indicates_failure(combined_output) else "FAIL"
        return DemoResult(
            category=case.category,
            module=case.module,
            function=case.function,
            status=status,
            elapsed_sec=round(elapsed, 3),
            return_code=completed.returncode,
            stdout_tail=_redact(_tail(completed.stdout)),
            stderr_tail=_redact(_tail(completed.stderr)),
        )
    except subprocess.TimeoutExpired as exc:
        elapsed = time.monotonic() - start
        stdout = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout or b"").decode(errors="ignore")
        stderr = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr or b"").decode(errors="ignore")
        return DemoResult(
            category=case.category,
            module=case.module,
            function=case.function,
            status="TIMEOUT",
            elapsed_sec=round(elapsed, 3),
            stdout_tail=_redact(_tail(stdout)),
            stderr_tail=_redact(_tail(stderr)),
            error=f"Timed out after {timeout}s",
        )


def run_reuse_login_cases(cases: List[DemoCase], wait_after: float) -> List[DemoResult]:
    _ensure_import_path()
    results: List[DemoResult] = []
    grouped: Dict[str, List[DemoCase]] = {}
    for case in cases:
        grouped.setdefault(case.module, []).append(case)

    for module_name, module_cases in grouped.items():
        common = None
        module = None
        try:
            module = importlib.import_module(module_name)
            common = login_for_module(module_name)
        except Exception:
            error = traceback.format_exc()
            for case in module_cases:
                results.append(
                    DemoResult(
                        category=case.category,
                        module=case.module,
                        function=case.function,
                        status="FAIL",
                        elapsed_sec=0.0,
                        stderr_tail=_redact(_tail(error)),
                    )
                )
            continue

        try:
            for case in module_cases:
                start = time.monotonic()
                stdout_buffer = io.StringIO()
                stderr_buffer = io.StringIO()
                status = "PASS"
                error = ""
                with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                    try:
                        print(f"[run] {case.module}.{case.function}")
                        result = getattr(module, case.function)()
                        if result is not None:
                            print(f"[return] {type(result).__name__}: {result!r}")
                        if wait_after > 0:
                            print(f"[wait] {wait_after}s for async callbacks")
                            time.sleep(wait_after)
                    except Exception:
                        status = "FAIL"
                        error = traceback.format_exc()
                        print(error, file=sys.stderr)

                combined_output = f"{stdout_buffer.getvalue()}\n{stderr_buffer.getvalue()}"
                if status == "PASS" and _output_indicates_failure(combined_output):
                    status = "FAIL"

                results.append(
                    DemoResult(
                        category=case.category,
                        module=case.module,
                        function=case.function,
                        status=status,
                        elapsed_sec=round(time.monotonic() - start, 3),
                        stdout_tail=_redact(_tail(stdout_buffer.getvalue())),
                        stderr_tail=_redact(_tail(stderr_buffer.getvalue())),
                        error=_redact(_tail(error)),
                    )
                )
        finally:
            if common is not None:
                with contextlib.suppress(Exception):
                    common.fini()

    return results


def parse_categories(value: str) -> List[str]:
    categories = [item.strip() for item in value.split(",") if item.strip()]
    unknown = sorted(set(categories) - set(MODULES))
    if unknown:
        raise argparse.ArgumentTypeError(f"Unknown categories: {', '.join(unknown)}")
    return categories


def parse_one(value: str) -> Tuple[str, str]:
    if ":" not in value:
        raise argparse.ArgumentTypeError("Use CATEGORY:FUNCTION, for example subscribe:subscribe_tick_by_id_demo")
    category, function = value.split(":", 1)
    if category not in MODULES:
        raise argparse.ArgumentTypeError(f"Unknown category: {category}")
    if not function.endswith("_demo"):
        raise argparse.ArgumentTypeError("Function should be a *_demo function")
    return category, function


def write_report(results: List[DemoResult], coverage: Optional[Dict[str, object]]) -> pathlib.Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORT_DIR / f"insight_demo_smoke_{stamp}.json"
    payload = {
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "total": len(results),
            "pass": sum(1 for item in results if item.status == "PASS"),
            "fail": sum(1 for item in results if item.status == "FAIL"),
            "timeout": sum(1 for item in results if item.status == "TIMEOUT"),
        },
        "results": [asdict(result) for result in results],
        "coverage": coverage,
    }
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return report_path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run Insight demo smoke tests.")
    parser.add_argument("--categories", type=parse_categories, default=parse_categories("subscribe,playback,doc_extra"))
    parser.add_argument("--one", type=parse_one, help="Run one demo, formatted as CATEGORY:FUNCTION.")
    parser.add_argument("--timeout", type=int, default=90, help="Seconds allowed for each demo subprocess.")
    parser.add_argument("--wait-after", type=float, default=3.0, help="Seconds to wait after async subscribe/playback calls.")
    parser.add_argument("--reuse-login", action="store_true", help="Login once per module and run cases in-process.")
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable used for live child processes. Insight usually requires Python 3.6 or 3.7.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Only list demos and coverage; do not login or call Insight.")
    parser.add_argument("--compare-docs", type=pathlib.Path, help="Optional exported Insight JSON/Markdown to compare against demos.")
    parser.add_argument("--_child", nargs=2, metavar=("MODULE", "FUNCTION"), help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    if args._child:
        return run_child(args._child[0], args._child[1], args.wait_after)

    if args.one:
        category, function = args.one
        categories = [category]
    else:
        function = None
        categories = args.categories

    cases = discover_cases(categories)
    if function:
        cases = [case for case in cases if case.function == function]
        if not cases:
            raise SystemExit(f"No demo found for {args.one[0]}:{function}")

    coverage_cases = discover_cases(parse_categories("subscribe,playback,doc_extra"))
    coverage = compare_coverage(coverage_cases, args.compare_docs)

    print(f"Discovered {len(cases)} demo cases:")
    for case in cases:
        print(f"  - {case.category}:{case.function} ({case.module}.py:{case.line})")

    print("\nCoverage summary:")
    print(f"  demo APIs: {coverage['demo_api_count']}")
    print(f"  installed package APIs: {coverage['package_api_count']}")
    if coverage["package_import_errors"]:
        print("  package import warnings:")
        for category, error in coverage["package_import_errors"].items():
            print(f"    - {category}: {error}")
    print(f"  package APIs without demo: {len(coverage['package_without_demo'])}")
    if args.compare_docs:
        print(f"  docs APIs: {coverage['docs_api_count']}")
        print(f"  docs APIs without demo: {len(coverage['docs_without_demo'])}")

    if args.dry_run:
        report = write_report([], coverage)
        print(f"\nDry run complete. Report: {report}")
        return 0

    _ensure_import_path()
    try:
        from insight_config import load_config

        load_config(require_credentials=True)
    except Exception as exc:
        print(_redact(str(exc)), file=sys.stderr)
        return 2

    supported_versions = {(3, 6), (3, 7), (3, 8), (3, 9), (3, 10)}
    if sys.version_info[:2] not in supported_versions and args.python == sys.executable:
        print(
            "Warning: current Python is "
            f"{sys.version_info.major}.{sys.version_info.minor}. "
            "Insight 6.1.2 includes native clients for Python 3.6 through 3.10. "
            "Use --python PATH_TO_COMPATIBLE_PYTHON if available.",
            file=sys.stderr,
        )

    if args.reuse_login:
        print("\nRunning with one login per module.")
        results = run_reuse_login_cases(cases, args.wait_after)
        for index, result in enumerate(results, start=1):
            print(f"\n[{index}/{len(results)}] {result.category}:{result.function}")
            print(f"  -> {result.status} ({result.elapsed_sec}s)")
    else:
        results = []
        for index, case in enumerate(cases, start=1):
            print(f"\n[{index}/{len(cases)}] {case.category}:{case.function}")
            result = run_parent_case(case, args.timeout, args.wait_after, args.python)
            results.append(result)
            print(f"  -> {result.status} ({result.elapsed_sec}s)")

    report = write_report(results, coverage)
    print(f"\nReport: {report}")
    failed = [result for result in results if result.status != "PASS"]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
