# GitHub App authentication for governed repositories

The reusable governance workflow is executed in the caller repository context. GitHub can load a shared private reusable workflow when Actions access is enabled, but the caller repository's `GITHUB_TOKEN` does not gain read access to the separate private `agent-governance` repository.

Cross-repository callers therefore authenticate the policy checkout with the organization-owned `agents-governance` GitHub App.

## GitHub App contract

The App should be installed only on `Aya-DevOpsTeam/agent-governance` and should have only repository `Contents: Read` permission (plus GitHub-required metadata access). Consumer repositories receive the App client ID and private key through restricted organization Actions secrets.

The reusable workflow accepts:

- `governance_app_client_id`
- `governance_app_private_key`

For cross-repository calls it uses `actions/create-github-app-token@v3` to mint a short-lived installation token scoped to the `agent-governance` repository with `Contents: Read`. That token is used only for the policy checkout. The policy checkout still uses `job.workflow_repository` and `job.workflow_sha`, preserving the exact called-workflow identity as the policy source of truth.

For same-repository execution in `agent-governance`, no App token is generated; the normal `github.token` is sufficient.

## Caller example

```yaml
jobs:
  central-agent-governance:
    uses: Aya-DevOpsTeam/agent-governance/.github/workflows/agent-governance.yml@<immutable-governance-sha>
    secrets:
      governance_app_client_id: ${{ secrets.AGENT_GOVERNANCE_APP_CLIENT_ID }}
      governance_app_private_key: ${{ secrets.AGENT_GOVERNANCE_APP_PRIVATE_KEY }}
```

The caller must pin the reusable workflow to a full approved commit SHA or immutable release tag. Do not pass a second governance ref.
