#!/bin/bash
# ECS Fargate deployment script
# This script registers a new task definition and updates the ECS service

set -euo pipefail

# Check required environment variables
: "${ECR_REGISTRY:?Environment variable ECR_REGISTRY is required}"
: "${ECR_REPOSITORY:?Environment variable ECR_REPOSITORY is required}"
: "${IMAGE_TAG:?Environment variable IMAGE_TAG is required}"
: "${AWS_REGION:?Environment variable AWS_REGION is required}"
: "${ECS_CLUSTER:?Environment variable ECS_CLUSTER is required}"
: "${ECS_SERVICE:?Environment variable ECS_SERVICE is required}"
: "${TASK_DEFINITION_FAMILY:?Environment variable TASK_DEFINITION_FAMILY is required}"

echo "=========================================="
echo "ECS Deployment Script"
echo "=========================================="
echo "Cluster: ${ECS_CLUSTER}"
echo "Service: ${ECS_SERVICE}"
echo "Task Family: ${TASK_DEFINITION_FAMILY}"
echo "Image: ${ECR_REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}"
echo "=========================================="

# Full image URI
IMAGE_URI="${ECR_REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}"

# Get the current task definition
echo "Fetching current task definition..."
TASK_DEF_ARN=$(aws ecs describe-services \
  --cluster "${ECS_CLUSTER}" \
  --services "${ECS_SERVICE}" \
  --region "${AWS_REGION}" \
  --query 'services[0].taskDefinition' \
  --output text)

if [ -z "${TASK_DEF_ARN}" ] || [ "${TASK_DEF_ARN}" = "None" ]; then
  echo "ERROR: Could not fetch current task definition for service ${ECS_SERVICE}"
  echo "Will attempt to register task definition from template..."
  
  # Use the template file if it exists
  if [ -f "infra/ecs/task-definition.json" ]; then
    echo "Using task definition template from infra/ecs/task-definition.json"
    TASK_DEF_JSON=$(cat infra/ecs/task-definition.json)
  else
    echo "ERROR: Template file infra/ecs/task-definition.json not found"
    exit 1
  fi
else
  echo "Current task definition: ${TASK_DEF_ARN}"
  
  # Download the current task definition
  TASK_DEF_JSON=$(aws ecs describe-task-definition \
    --task-definition "${TASK_DEF_ARN}" \
    --region "${AWS_REGION}" \
    --query 'taskDefinition' \
    --output json)
fi

# Update the image in the task definition
echo "Updating image to: ${IMAGE_URI}"
NEW_TASK_DEF=$(echo "${TASK_DEF_JSON}" | jq --arg IMAGE "${IMAGE_URI}" '
  .containerDefinitions[0].image = $IMAGE |
  del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .compatibilities, .registeredAt, .registeredBy)
')

# Register the new task definition
echo "Registering new task definition..."
NEW_TASK_DEF_ARN=$(aws ecs register-task-definition \
  --cli-input-json "${NEW_TASK_DEF}" \
  --region "${AWS_REGION}" \
  --query 'taskDefinition.taskDefinitionArn' \
  --output text)

echo "New task definition registered: ${NEW_TASK_DEF_ARN}"

# Update the ECS service with the new task definition
echo "Updating ECS service..."
aws ecs update-service \
  --cluster "${ECS_CLUSTER}" \
  --service "${ECS_SERVICE}" \
  --task-definition "${NEW_TASK_DEF_ARN}" \
  --force-new-deployment \
  --region "${AWS_REGION}" \
  --no-cli-pager

echo "=========================================="
echo "Deployment initiated successfully!"
echo "=========================================="
echo "Monitor deployment status with:"
echo "aws ecs describe-services --cluster ${ECS_CLUSTER} --services ${ECS_SERVICE} --region ${AWS_REGION}"
echo "=========================================="
