# ReproKit

A tiny Codex skill and Python CLI for checking regression tests. **Same test,
buggy code fails, fixed code passes, evidence saved.**

This is a working MVP for local code you trust. Codex writes the test through the
included skill; the CLI executes and checks it. No API key is required by the CLI.

## Try it

Requires Python 3.10+.

```sh
git clone https://github.com/vcet7333-sketch/reprokit.git
cd reprokit
python -m pip install -r requirements.txt
python reprokit.py verify --before examples/before --after examples/after --test examples/test_discount.py --out evidence/demo --trust-code
```

Expected: `verified_regression`. Open `evidence/demo/report.md`.
The bundled example checks that a 20% discount on 200 is 160. The buggy function
subtracts 20 directly and returns 180. This is a synthetic example, not an upstream
bug or an adoption claim. Choose a fresh `--out` folder for each run.

## Use with Codex

Open this repository in Codex and ask:

> Use skills/reprokit/SKILL.md. Read examples/issue.md and examples/before. Write a
> regression test and verify it against examples/after. Save the evidence.

This repo also includes a `.codex-plugin/plugin.json` manifest for plugin packaging.
The skill is usable directly without installing a marketplace entry. It doesn't
call another agent or model itself: the active Codex session generates the test.

## Check your own fix

```sh
python reprokit.py verify --before ./buggy --after ./fixed --test ./test_bug.py --out ./evidence/run-1 --trust-code
```

Use two code directories containing the modules your test imports. Dependencies
must already be installed in your Python environment. The CLI copies the code
into temporary folders, disables project pytest configuration, conftest files,
and automatic third-party pytest plugins, then runs the same test in both copies.
Only the supplied test file runs; this is not a full project test suite.

| Result | Meaning |
|---|---|
| `verified_regression` | Assertion failure before; identical test cases pass after |
| `not_reproduced` | The test already passes before the fix |
| `still_failing` | Test fails before and after |
| `environment_error` | Import, collection, execution, or pytest error |
| `inconclusive` | Skipped tests or different collected test cases |
| `timeout` | A revision exceeded `--timeout` seconds (default 30) |

Exit code 0 means verified, 1 means not verified, and 2 means invalid invocation.
Evidence contains Markdown, JSON, both pytest logs, a copy of the test, and its hash.
Check that the failing assertion actually represents the issue; matching execution
results alone cannot establish the test's semantic correctness.

## Limits

**Not a sandbox.** Tests execute with your current user's permissions and environment.
Only run trusted code. A temporary copy protects against ordinary accidental edits,
not malicious code. Timeout bounds the direct pytest process, not a malicious process
tree. Review logs before sharing; application output can contain private information.
This MVP has no hosted service, automatic issue fetching, Docker runner, automatic
fixing, billing, API spending controls, or external users claimed.

## Development

```sh
python -m unittest discover -s tests -v
```

Small bug fixes and clear reproductions are welcome. Open an issue with the command,
Python version, expected result, and redacted logs. MIT licensed. Independent project;
not affiliated with or endorsed by OpenAI.
