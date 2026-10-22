#!/usr/bin/env bash
# Deploys the Mule app and the Node bridge images to Amazon ECS (and, if an
# EKS cluster is configured, applies the same tag to the k8s deployments).
#
# DEMO GUARD: when MOCK_MODE=true (placeholder AWS account / no OIDC role, see
# .github/workflows/cd.yml) every AWS call is printed instead of executed, and
# ECS updates use --no-force-new-deployment style dry runs. Nothing can reach a
# real AWS account with mock credentials.
set -euo pipefail

: "${MOCK_MODE:?MOCK_MODE must be set}"
: "${IMAGE_TAG:?IMAGE_TAG must be set}"
: "${AWS_REGION:?AWS_REGION must be set}"
: "${AWS_ACCOUNT_ID:?AWS_ACCOUNT_ID must be set}"
: "${ECS_CLUSTER:?ECS_CLUSTER must be set}"
: "${ECS_SERVICE_MULE:?ECS_SERVICE_MULE must be set}"
: "${ECS_SERVICE_NODE:?ECS_SERVICE_NODE must be set}"

REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
MULE_IMAGE="${REGISTRY}/${MULE_ECR_REPOSITORY:-demo/employee-service-api-mule}:${IMAGE_TAG}"
NODE_IMAGE="${REGISTRY}/${NODE_ECR_REPOSITORY:-demo/employee-service-auth-ui}:${IMAGE_TAG}"

echo "cluster=${ECS_CLUSTER} namespace=${EKS_NAMESPACE:-<unset>}"
echo "mule image=${MULE_IMAGE}"
echo "node image=${NODE_IMAGE}"

run() {
  if [ "${MOCK_MODE}" = "true" ]; then
    echo "[mock] $*"
  else
    "$@"
  fi
}

for service in "${ECS_SERVICE_MULE}" "${ECS_SERVICE_NODE}"; do
  run aws ecs update-service \
    --cluster "${ECS_CLUSTER}" \
    --service "${service}" \
    --force-new-deployment \
    --region "${AWS_REGION}"
done

if [ "${MOCK_MODE}" != "true" ]; then
  for service in "${ECS_SERVICE_MULE}" "${ECS_SERVICE_NODE}"; do
    aws ecs wait services-stable \
      --cluster "${ECS_CLUSTER}" \
      --services "${service}" \
      --region "${AWS_REGION}"
  done
fi

# Optional EKS path: only used when an EKS cluster name is configured.
if [ -n "${EKS_CLUSTER_NAME:-}" ]; then
  run aws eks update-kubeconfig --name "${EKS_CLUSTER_NAME}" --region "${AWS_REGION}"
  run kubectl -n "${EKS_NAMESPACE:-demo-staging}" set image \
    deployment/employee-service-api "employee-service-api=${MULE_IMAGE}"
  run kubectl -n "${EKS_NAMESPACE:-demo-staging}" set image \
    deployment/employee-auth-ui "employee-auth-ui=${NODE_IMAGE}"
fi

if [ "${MOCK_MODE}" = "true" ]; then
  echo "::notice title=Dry run::Mock AWS identifiers in use; no deployment was performed."
fi
