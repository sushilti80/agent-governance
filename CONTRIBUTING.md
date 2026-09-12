# Contributing

Feedback, issues, and pull requests are welcome. By contributing you agree that your work is licensed under the MIT License in `LICENSE`.

Maintainer and code owner: [@sushilti80](https://github.com/sushilti80)

## How to send feedback

- Use GitHub issues for design questions, false positives/negatives, and documentation gaps.
- Use a pull request for concrete policy, schema, script, or docs changes.
- Use the pull request template: observed failure, principle IDs, smallest-correct-layer, eval impact.
- Report vulnerabilities only through `SECURITY.md` (private advisory). Do not file public issues for those.

Do not over-claim maturity in docs or issues: semantic review is report-only; global evals are a governed catalog, not a full execution harness; runtime efficiency has no live telemetry yet.

## Before you change policy

- Keep deterministic gates blocking. An LLM must not waive schema, version, learning-firewall, or constitution checks.
- Prefer the smallest correct layer: code/tool, then skill, then repository policy, then agent, then global governance.
- Consumers of this repo should pin an immutable workflow ref (`@v2026.09.8` or a full commit SHA) and match `.agent/governance.yaml` `policy: agent-governance` and `version` to that pin.

## Local checks

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-governance.txt
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
.venv/bin/python scripts/governance_check.py --policy-root . --target-root .
```

Do not commit `.DS_Store`, `.venv/`, `.semantic-judge/`, credentials, or production logs.

## Semantic review in CI

Deterministic jobs run on every pull request, including forks.

The Copilot CLI semantic job runs only on pull requests from this repository, not from forks, because Copilot credentials are not available to fork workflows. It defaults to GPT-5.6 Luna; reusable-workflow callers and manual runs can set the `semantic_model` input to another Copilot-supported model. On the canonical repo it still needs Copilot CLI access (`copilot-requests: write` on `GITHUB_TOKEN`, or optional `COPILOT_GITHUB_TOKEN`). Semantic verdicts are report-only; judge or result-contract failures fail that job.

## Review

R4 paths (`principles/`, `schemas/`, `evals/global/`, `.github/workflows/`, `scripts/`, `tests/`, `VERSION`) require review from [@sushilti80](https://github.com/sushilti80) via `.github/CODEOWNERS`.

Maintainer setup so CODEOWNERS actually blocks merge:

1. GitHub → **Settings** → **Branches** → protect `main`.
2. Enable **Require a pull request before merging**.
3. Enable **Require review from Code Owners**.
4. Optionally require the `deterministic-governance` status check.

## Security

See [`SECURITY.md`](SECURITY.md). Enable **Private vulnerability reporting** under **Settings → Code security** so the advisory form works.
