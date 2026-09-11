"""Small, local regression-test verifier. Run only code you trust."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

VERSION = "0.1.0"


def run_case(source: Path, test: Path, timeout: int) -> dict:
    """Copy a trusted code tree, add the same test, and collect pytest evidence."""
    with tempfile.TemporaryDirectory(prefix="reprokit-") as temp:
        root = Path(temp) / "code"
        shutil.copytree(source, root, ignore=shutil.ignore_patterns(
            ".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".env"))
        target = root / "_reprokit_test.py"
        if target.exists():
            raise ValueError("Source contains reserved file _reprokit_test.py")
        shutil.copyfile(test, target)
        xml_path = Path(temp) / "result.xml"
        # Ignore project configuration and auto-loaded plugins; keep setup explicit.
        config = Path(temp) / "pytest.ini"
        config.write_text("[pytest]\n", encoding="utf-8")
        command = [sys.executable, "-m", "pytest", "-q", "--tb=short",
                   "-c", str(config), "--confcutdir", str(root),
                   "--noconftest", f"--junitxml={xml_path}", str(target)]
        env = os.environ.copy()
        env.pop("PYTEST_ADDOPTS", None)
        env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        env["PYTHONPATH"] = str(root)
        try:
            proc = subprocess.run(command, cwd=root, env=env, capture_output=True,
                                  text=True, encoding="utf-8", errors="replace", timeout=timeout)
            result = {"exit_code": proc.returncode, "log": proc.stdout + proc.stderr}
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "exit_code": None, "log": "Time limit exceeded", "cases": []}
        cases = []
        if xml_path.exists():
            for case in ET.parse(xml_path).iter("testcase"):
                failure, error = case.find("failure"), case.find("error")
                status = "passed"
                message = ""
                if error is not None:
                    status, message = "error", error.get("message", "")
                elif failure is not None:
                    message = (failure.get("message", "") + "\n" + (failure.text or ""))
                    status = "assertion_failed" if "AssertionError" in message or "assert " in message else "error"
                elif case.find("skipped") is not None:
                    status = "skipped"
                cases.append({"id": case.get("classname", "") + "::" + case.get("name", ""),
                              "status": status, "message": message})
        result["cases"] = cases
        if proc.returncode not in (0, 1) or not cases or any(c["status"] == "error" for c in cases):
            result["status"] = "environment_error"
        elif any(c["status"] == "skipped" for c in cases):
            result["status"] = "inconclusive"
        elif proc.returncode == 0 and all(c["status"] == "passed" for c in cases):
            result["status"] = "passed"
        elif proc.returncode == 1 and any(c["status"] == "assertion_failed" for c in cases):
            result["status"] = "failed"
        else:
            result["status"] = "inconclusive"
        return result


def classify(before: dict, after: dict) -> str:
    statuses = (before["status"], after["status"])
    if "timeout" in statuses:
        return "timeout"
    if "environment_error" in statuses:
        return "environment_error"
    if "inconclusive" in statuses:
        return "inconclusive"
    if sorted(c["id"] for c in before["cases"]) != sorted(c["id"] for c in after["cases"]):
        return "inconclusive"
    if statuses == ("failed", "passed"):
        return "verified_regression"
    if before["status"] == "passed":
        return "not_reproduced"
    return "still_failing"


def verify(before: Path, after: Path, test: Path, out: Path, timeout: int = 30) -> dict:
    before, after, test, out = (p.resolve() for p in (before, after, test, out))
    if not before.is_dir() or not after.is_dir() or not test.is_file():
        raise ValueError("Before/after must be directories; test must be an existing Python file")
    if test.suffix != ".py":
        raise ValueError("Test must be a .py file")
    if out.exists():
        raise ValueError("Output already exists; choose a new directory to preserve evidence")
    if out.is_relative_to(before) or out.is_relative_to(after):
        raise ValueError("Output must be outside the input code directories")
    data = {"version": VERSION, "test_sha256": hashlib.sha256(test.read_bytes()).hexdigest(),
            "before": run_case(before, test, timeout), "after": run_case(after, test, timeout)}
    data["status"] = classify(data["before"], data["after"])
    out.mkdir(parents=True)
    shutil.copyfile(test, out / "test_regression.py")
    for side in ("before", "after"):
        (out / f"{side}.log").write_text(data[side]["log"], encoding="utf-8")
    (out / "result.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    summary = (f"# ReproKit result: {data['status']}\n\n"
               f"| Revision | Result |\n|---|---|\n| Before | {data['before']['status']} |\n"
               f"| After | {data['after']['status']} |\n\n"
               f"Test SHA-256: `{data['test_sha256']}`\n\n"
               "See `before.log`, `after.log`, `test_regression.py`, and `result.json`.\n\n"
               "A verified regression means the same test failed an assertion before and passed after. "
               "A maintainer must still check that the assertion matches the reported bug. "
               "This is a local trusted-code tool, not a security sandbox.\n")
    (out / "report.md").write_text(summary, encoding="utf-8")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=VERSION)
    subs = parser.add_subparsers(dest="command", required=True)
    check = subs.add_parser("verify", help="Verify the same pytest test before and after a fix")
    check.add_argument("--before", type=Path, required=True)
    check.add_argument("--after", type=Path, required=True)
    check.add_argument("--test", type=Path, required=True)
    check.add_argument("--out", type=Path, required=True)
    check.add_argument("--timeout", type=int, default=30)
    check.add_argument("--trust-code", action="store_true", help="Acknowledge local execution without sandboxing")
    args = parser.parse_args()
    if not args.trust_code:
        parser.error("Only run trusted code. Pass --trust-code to acknowledge local execution.")
    if not 1 <= args.timeout <= 300:
        parser.error("Timeout must be between 1 and 300 seconds per revision")
    try:
        result = verify(args.before, args.after, args.test, args.out, args.timeout)
    except (ValueError, OSError, ET.ParseError) as exc:
        print(f"ReproKit: {exc}", file=sys.stderr)
        return 2
    print(f"{result['status']}\nReport: {args.out.resolve() / 'report.md'}")
    return 0 if result["status"] == "verified_regression" else 1


if __name__ == "__main__":
    raise SystemExit(main())
