# CI/CD

Two GitHub Actions workflows: `.github/workflows/ci.yml` (validation) and
`.github/workflows/cd.yml` (build + deploy to AWS).

**This repository is a demo. Every AWS identifier in the CD pipeline is a mock
placeholder and all AWS-touching steps are guarded so they no-op or dry-run
until real values are configured.**

## CI (`ci.yml`)

Triggers: push to `main`, pull requests targeting `main`, manual dispatch.
Concurrency group cancels superseded runs; `permissions: contents: read`.

| Job | What it does |
| --- | --- |
| `mule-build` | JDK 17 (Temurin), `~/.m2` cache, `mvn clean package` + `mvn test` with `.github/ci/settings.xml`; uploads `target/*-mule-application.jar` |
| `node-bridge` | Node 18 with npm cache, `npm ci`, `npm run lint`, `npm test` (spawns `heroku-web/server.js` and hits `/health`, `/`, `/register`, `/authenticate`), advisory `npm audit` |
| `database-schema` | `postgres:14` service container; applies `.github/ci/schema-bootstrap.sql` then `database-setup.sql`, then asserts tables/columns/index/trigger via `.github/ci/schema-verify.sql` |
| `shell-scripts` | `shellcheck --severity=warning test-*.sh` |
| `workflow-lint` | YAML parse of all workflows + `actionlint` 1.7.7 |

### Anypoint / Exchange credentials

`pom.xml` declares the Anypoint Exchange repository, which requires MuleSoft
credentials that are not available here. `.github/ci/settings.xml` maps both
Mule server IDs to `ANYPOINT_USERNAME` / `ANYPOINT_PASSWORD`; when those secrets
are absent the workflow substitutes `mock-anypoint-user` /
`mock-anypoint-password`.

Everything the project depends on today is on Maven Central and the public
MuleSoft releases repository, so the build succeeds with mock credentials. If a
private Exchange artifact is ever added, the `Package Mule application` step is
allowed to fail **only in mock mode**: the job then emits a warning annotation
and falls back to offline validation of `pom.xml`, the Mule flow XML and
`mule-artifact.json`. Once `ANYPOINT_USERNAME` is set, mock mode turns off and
the Maven build becomes fail-fast.

MUnit: the pom declares no `munit-maven-plugin` and `src/test` contains no MUnit
suites, so `mvn test` is a no-op today. Adding suites under `src/test/munit`
(plus the plugin) makes the existing step run them with no workflow change.

## CD (`cd.yml`)

Triggers: push to `main` (staging → production), or manual dispatch with an
`environment` input (`staging` | `production`).

1. `build-images` — packages the Mule app, installs Node deps, builds two
   images with Buildx (`docker/Dockerfile.mule`, `heroku-web/Dockerfile`),
   tagged `<account>.dkr.ecr.<region>.amazonaws.com/<repo>:<sha12>`.
2. `deploy-staging` — GitHub Environment `demo-staging`, runs
   `.github/scripts/deploy.sh`.
3. `deploy-production` — GitHub Environment `demo-prod`, runs after staging.
   **Add required reviewers to the `demo-prod` environment** — that is the
   manual approval gate.

Credentials use GitHub OIDC only (`aws-actions/configure-aws-credentials@v4`
with `permissions: id-token: write`). There are no long-lived AWS keys anywhere
in these workflows.

### Mock-mode guard

`build-images` computes `mock_mode`:

```
mock_mode = false  iff  vars.AWS_OIDC_ROLE_ARN is set AND vars.AWS_ACCOUNT_ID != 123456789012
```

When `mock_mode == true`:

- the OIDC assume-role and ECR login steps are skipped entirely;
- images are built and loaded locally (`push: false`);
- `deploy.sh` prints every `aws`/`kubectl` command with a `[mock]` prefix
  instead of executing it, and skips `aws ecs wait services-stable`.

### Variables and secrets

All are GitHub **Actions variables** (`vars.*`) unless noted. Fake defaults are
baked into the workflow so the pipeline runs unconfigured.

| Name | Mock default | Notes |
| --- | --- | --- |
| `AWS_REGION` | `us-east-1` | |
| `AWS_ACCOUNT_ID` | `123456789012` | Non-placeholder value is half of the mock-mode switch |
| `AWS_OIDC_ROLE_ARN` | _(unset)_ | e.g. `arn:aws:iam::123456789012:role/demo-github-actions-deploy` |
| `MULE_ECR_REPOSITORY` | `demo/employee-service-api-mule` | |
| `NODE_ECR_REPOSITORY` | `demo/employee-service-auth-ui` | |
| `ECS_CLUSTER_STAGING` / `ECS_CLUSTER_PROD` | `demo-staging-cluster` / `demo-prod-cluster` | |
| `ECS_SERVICE_MULE_STAGING` / `_PROD` | `demo-staging-employee-api` / `demo-prod-employee-api` | |
| `ECS_SERVICE_NODE_STAGING` / `_PROD` | `demo-staging-auth-ui` / `demo-prod-auth-ui` | |
| `EKS_NAMESPACE_STAGING` / `_PROD` | `demo-staging` / `demo-prod` | Only used when `EKS_CLUSTER_NAME` is set |
| `EKS_CLUSTER_NAME` | _(unset)_ | Optional EKS path in `deploy.sh` |
| `ANYPOINT_USERNAME` / `ANYPOINT_PASSWORD` (secrets) | mock values | Enables private Exchange resolution and fail-fast Maven |

## Going from mock to real

1. Create the ECR repositories and the ECS cluster/services (or EKS
   deployments `employee-service-api` / `employee-auth-ui`).
2. Create an IAM role trusted by `token.actions.githubusercontent.com`, scoped
   to this repository, with ECR push + ECS/EKS deploy permissions; set
   `AWS_OIDC_ROLE_ARN` and the real `AWS_ACCOUNT_ID`.
3. Replace the remaining `demo-*` variables with real cluster/service names.
4. Create GitHub Environments `demo-staging` and `demo-prod` (rename as
   desired) and add required reviewers to the production one.
5. Swap the base image in `docker/Dockerfile.mule` for a licensed Mule 4.9
   runtime image and remove the placeholder `CMD` — the current image only
   stages the application archive on a plain JDK 17 base.
6. Optionally add `ANYPOINT_USERNAME` / `ANYPOINT_PASSWORD` secrets.

## Dependabot

`.github/dependabot.yml` watches Maven (`/`), npm (`/heroku-web`),
GitHub Actions (`/`), and Docker (`/docker`, `/heroku-web`) weekly.
