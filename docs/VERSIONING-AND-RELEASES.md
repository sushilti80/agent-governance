# Versioning and Releases

## Two different versions

Agent Governance intentionally separates schema compatibility from policy release identity.

### `spec_version`

`spec_version` is the compatibility version of the governance manifest contract. It changes only when a breaking change makes existing governed repository manifests invalid or materially changes the interpretation of an existing manifest field.

The machine-readable policy is `principles/versioning-policy.yaml`. The current manifest schema must use the same `spec_version` declared there.

### Governance version

The governance release version identifies one immutable policy implementation. Its single authoritative source is the root `VERSION` file.

Governed repositories declare that exact version in `.agent/governance.yaml`:

```yaml
governance:
  policy: agent-governance
  version: "<contents-of-VERSION>"
```

The deterministic gate requires an exact match between the target manifest and the policy checkout. This prevents a repository from claiming one policy release while CI executes another.

Governance versions use calendar-style `YYYY.MM.PATCH` numbering. Compatible policy improvements may advance the governance version without changing `spec_version`.

## Release tag

The release tag is always:

```text
v<VERSION>
```

A governance tag is immutable. Never move, delete and recreate, or reuse a published governance tag. If a released policy requires correction, create a new governance version.

Organization/repository rules should protect `v*` tags from update or deletion after publishing.

## Release sequence

1. Change governance through a pull request.
2. Treat changes to `VERSION`, global principles, schemas, global evals, governance CI, validation scripts, or governance tests as R4.
3. Update `CHANGELOG.md` for the version in `VERSION`.
4. Pass deterministic governance and regression CI.
5. Obtain required governance-owner review.
6. Merge to `main`.
7. Confirm the merged `main` commit still passes governance CI.
8. Create tag `v<VERSION>` on that exact merged commit.
9. Allow the release guard workflow to verify the tag/version/changelog contract.
10. Publish the GitHub Release using the matching changelog entry.
11. Protect the published tag from mutation.
12. Only then onboard or upgrade governed repositories to that release.

## Breaking changes

A change requires a `spec_version` increment when it intentionally breaks the current governance manifest contract or changes the meaning of an existing field such that a previously valid repository would require migration.

A new principle, eval, validation rule, compatible schema addition, bug fix, or stronger implementation that preserves the manifest contract normally changes only the governance release version.

When `spec_version` changes, the PR must include migration guidance and explicit compatibility tests for the supported transition.
