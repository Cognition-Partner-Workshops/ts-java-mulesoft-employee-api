#!/usr/bin/env bash
# Mocked Amazon ECS deployment for the demo pipeline.
# Every identifier used here is a placeholder (see .github/workflows/cd.yml);
# when DRY_RUN=true the AWS CLI is never invoked.
set -euo pipefail

: "${DRY_RUN:=true}"
: "${IMAGE_TAG:?IMAGE_TAG is required}"
: "${ENV_SUFFIX:?ENV_SUFFIX is required}"
: "${AWS_REGION:?AWS_REGION is required}"
: "${ECR_REGISTRY:?ECR_REGISTRY is required}"
: "${ECS_CLUSTER:?ECS_CLUSTER is required}"
: "${ECS_SERVICE_MULE:?ECS_SERVICE_MULE is required}"
: "${ECS_SERVICE_BRIDGE:?ECS_SERVICE_BRIDGE is required}"

cluster="${ECS_CLUSTER}-${ENV_SUFFIX}"

for service in "$ECS_SERVICE_MULE" "$ECS_SERVICE_BRIDGE"; do
  echo "Deploying ${service} (${IMAGE_TAG}) to cluster ${cluster} in ${AWS_REGION}"
  if [ "$DRY_RUN" = "true" ]; then
    echo "MOCK: aws ecs update-service --cluster ${cluster} --service ${service}-${ENV_SUFFIX} --force-new-deployment"
    echo "MOCK: aws ecs wait services-stable --cluster ${cluster} --services ${service}-${ENV_SUFFIX}"
    continue
  fi
  aws ecs update-service \
    --cluster "$cluster" \
    --service "${service}-${ENV_SUFFIX}" \
    --force-new-deployment \
    --region "$AWS_REGION"
  aws ecs wait services-stable \
    --cluster "$cluster" \
    --services "${service}-${ENV_SUFFIX}" \
    --region "$AWS_REGION"
done

echo "Deployment to ${ENV_SUFFIX} complete (DRY_RUN=${DRY_RUN})"
