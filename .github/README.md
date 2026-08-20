# CI/CD

Two workflows live in `.github/workflows/`.

## `ci.yml` — Continuous Integration

Triggers: push to `main`/`master`, pull requests targeting them, and manual dispatch.
Concurrency: in-progress runs for the same ref are cancelled. Default permissions: `contents: read`.

| Job | What it does |
| --- | --- |
| `mule-build` | Temurin JDK 17 + Maven cache, `mvn -ntp -B clean verify` (this also runs MUnit tests once any exist). Uploads `target/*-mule-application.jar` and, if present, `target/surefire-reports` / `target/munit-reports`. |
| `node-bridge` | Node 18 (matches `heroku-web/package.json` `engines`), `npm ci` (falls back to `npm install` when no lockfile), `npm run lint --if-present` + `node --check server.js`, `npm test --if-present`, then boots `server.js` and curls `/` as a smoke test. |
| `config-lint` | `yamllint` (config: `.github/yamllint.yml`), JSON parse of every tracked `*.json`, `xmllint` well-formedness for `pom.xml` and the Mule XML configs. |
| `sql-check` | Spins up a `postgres:14` service container, creates the base tables documented in `README.md`, applies `database-setup.sql`, and asserts the expected tables/columns exist. |
| `shell-lint` | `shellcheck` over every tracked `*.sh`. |
| `dependency-scan` | `npm audit` for the bridge (advisory only) and a Trivy filesystem scan of the Maven/npm manifests, uploaded as SARIF to code scanning. |

### Optional secrets

| Secret | Used by | Notes |
| --- | --- | --- |
| `ANYPOINT_USERNAME` / `ANYPOINT_PASSWORD` | `mule-build` | Written into `~/.m2/settings.xml` for the `anypoint-exchange-v2` server. Placeholders are used when unset — the build works today because all dependencies resolve from public MuleSoft repositories. Required only if private Exchange assets are added. |

## `cd.yml` — Deployment (MOCKED for the demo)

**Nothing in this pipeline reaches real infrastructure.** It runs only on `workflow_dispatch`,
and every AWS-touching step is guarded by `DRY_RUN`, which defaults to `true`. Turning it off
requires both `dry_run: false` on the dispatch **and** the repository variable
`ALLOW_REAL_DEPLOY=true` (not set here). In dry-run the AWS CLI is never invoked; the steps
print the exact `aws ecr` / `aws ecs` commands they would run.

Flow: `build-images` → `deploy-staging` (environment `staging`) → `deploy-production`
(environment `production`, protected by required reviewers so it waits for approval).
`build-images` packages the Mule app with Maven, builds the Node bridge container from
`heroku-web/Dockerfile`, and mocks the Mule image build — a real Mule EE runtime base image
needs a MuleSoft licence, so only the application jar is staged. ECS rollout logic lives in
`.github/scripts/deploy-ecs.sh`.

AWS authentication uses OIDC role assumption (`permissions: id-token: write`,
`aws-actions/configure-aws-credentials`), skipped entirely in dry-run.

### Mocked placeholder values

| Name | Value |
| --- | --- |
| `AWS_ACCOUNT_ID` | `123456789012` |
| `AWS_REGION` | `us-east-1` |
| `ECR_REGISTRY` | `123456789012.dkr.ecr.us-east-1.amazonaws.com` |
| `ECR_REPOSITORY_MULE` / `ECR_REPOSITORY_BRIDGE` | `demo-employee-api/mule-app`, `demo-employee-api/node-bridge` |
| `ECS_CLUSTER` | `demo-employee-api` (suffixed `-staging` / `-production`) |
| `K8S_NAMESPACE` | `demo-employee-api` |
| `AWS_OIDC_ROLE_ARN` | `arn:aws:iam::123456789012:role/demo-employee-api-github-actions` |

Replace all of them with real values before pointing this at an actual account.

### Repository variables / environments

| Name | Type | Purpose |
| --- | --- | --- |
| `ALLOW_REAL_DEPLOY` | repo variable | Must be `"true"` (together with `dry_run: false`) for any AWS call to execute. Leave unset for the demo. |
| `staging`, `production` | GitHub environments | Create both; add required reviewers to `production`. |
| `ANYPOINT_CLIENT_ID` / `ANYPOINT_CLIENT_SECRET` | secrets | Only needed if the commented-out CloudHub 2.0 job at the bottom of `cd.yml` is enabled — CloudHub is the app's native target. |

## `dependabot.yml`

Weekly updates for `maven` (root), `npm` (`/heroku-web`), and `github-actions`.
