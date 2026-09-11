---
name: reprokit
description: Turn a Python bug report into a small pytest regression test, then use ReproKit to verify that the identical test fails before a fix and passes afterward. Use for local trusted Python code with before and after directories.
---

# ReproKit

Read the issue and the buggy Python code. Identify the expected public behavior.
Write the smallest useful pytest test for that behavior in a separate file. Do not
modify the test after looking at the fixed implementation just to obtain a pass.

Use the CLI in this plugin's root directory (two directories above this skill).
Install its requirements if necessary: `python -m pip install -r requirements.txt`.

Run from the plugin root:

```sh
python reprokit.py verify --before /path/to/buggy --after /path/to/fixed --test /path/to/test_regression.py --out /path/to/new-evidence --trust-code
```

Execute only code the user trusts. The CLI runs locally with the current user's
permissions; it is not a sandbox. For arbitrary third-party code, stop and explain
that an isolated execution environment is outside this MVP's scope.

If the fixed version is absent, explain that paired verification needs one. You
may draft a candidate fix in a separate directory when the user requests it.
Do not overwrite their buggy copy. No automatic downloads or account access.

Read `result.json` and the logs. Link the report and the generated test. Describe
`not_reproduced`, `environment_error`, `inconclusive`, `timeout`, and `still_failing`
honestly. Even `verified_regression` still needs human review of the assertion's
meaning. Never claim the test is a security audit or proves the whole project.
