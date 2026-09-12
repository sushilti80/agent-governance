# GitHub App authentication for governed repositories

The reusable governance workflow is executed in the caller repository context.

When this governance repository is **public**, callers do not need a GitHub App. The policy checkout can use the caller `GITHUB_TOKEN` (or the default unauthenticated public clone) because the workflow already falls back to `github.token` when no App token is minted.

When the governance source is **private**, GitHub can load a shared reusable workflow if Actions access is enabled, but the caller repository's `GITHUB_TOKEN` does not gain read access to the separate private `agent-governance` repository. Cross-repository callers then authenticate the policy checkout with an `agents-governance` GitHub App.

## GitHub App contract

The App should be installed only on the canonical `agent-governance` repository and should have only repository `Contents: Read` permission (plus GitHub-required metadata access). Consumer repositories receive the App client ID and private key through restricted organization Actions secrets.

The reusable workflow accepts optional secrets:

- `governance_app_client_id`
- `governance_app_private_key`

For cross-repository calls with those secrets present, it uses `actions/create-github-app-token@v3` to mint a short-lived installation token scoped to the `agent-governance` repository with `Contents: Read`. That token is used only for the policy checkout. The policy checkout still uses `job.workflow_repository` and `job.workflow_sha`, preserving the exact called-workflow identity as the policy source of truth.

For same-repository execution in `agent-governance`, and for public cross-repository calls without App secrets, no App token is generated; `github.token` is sufficient.

## Caller example

Public governance source:

```yaml
jobs:
  central-agent-governance:
    uses: sushilti80/agent-governance/.github/workflows/agent-governance.yml@<immutable-governance-sha>
```

Private governance source:

```yaml
jobs:
  central-agent-governance:
    uses: OWNER/agent-governance/.github/workflows/agent-governance.yml@<immutable-governance-sha>
    secrets:
      governance_app_client_id: ${{ secrets.AGENT_GOVERNANCE_APP_CLIENT_ID }}
      governance_app_private_key: ${{ secrets.AGENT_GOVERNANCE_APP_PRIVATE_KEY }}
```

The caller must pin the reusable workflow to a full approved commit SHA or immutable release tag. Do not pass a second governance ref.
