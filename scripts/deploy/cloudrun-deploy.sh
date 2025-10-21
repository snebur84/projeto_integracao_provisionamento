#!/bin/bash
# Google Cloud Run deployment script
# This script deploys the application to Cloud Run

set -euo pipefail

# Check required environment variables
: "${GCP_PROJECT:?Environment variable GCP_PROJECT is required}"
: "${GCP_REGION:?Environment variable GCP_REGION is required}"
: "${GCP_REPOSITORY:?Environment variable GCP_REPOSITORY is required}"
: "${IMAGE_TAG:?Environment variable IMAGE_TAG is required}"
: "${CLOUD_RUN_SERVICE:?Environment variable CLOUD_RUN_SERVICE is required}"

echo "=========================================="
echo "Cloud Run Deployment Script"
echo "=========================================="
echo "Project: ${GCP_PROJECT}"
echo "Region: ${GCP_REGION}"
echo "Service: ${CLOUD_RUN_SERVICE}"
echo "Image: ${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/${GCP_REPOSITORY}/provision-app:${IMAGE_TAG}"
echo "=========================================="

# Full image URI
IMAGE_URI="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/${GCP_REPOSITORY}/provision-app:${IMAGE_TAG}"

# Set the project
echo "Setting GCP project..."
gcloud config set project "${GCP_PROJECT}"

# Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy "${CLOUD_RUN_SERVICE}" \
  --image="${IMAGE_URI}" \
  --platform=managed \
  --region="${GCP_REGION}" \
  --allow-unauthenticated \
  --port=8000 \
  --cpu=1 \
  --memory=1Gi \
  --min-instances=1 \
  --max-instances=10 \
  --timeout=300 \
  --concurrency=80 \
  --cpu-throttling \
  --no-cpu-boost \
  --execution-environment=gen2 \
  --service-account="${CLOUD_RUN_SERVICE_ACCOUNT:-default}" \
  --set-env-vars="DJANGO_SETTINGS_MODULE=provision.settings,PYTHONUNBUFFERED=1,ENVIRONMENT=${ENVIRONMENT:-production}" \
  --update-secrets="SECRET_KEY=django-secret-key:latest,DB_PASSWORD=db-password:latest,PROVISION_API_KEY=provision-api-key:latest,MONGO_URI=mongo-uri:latest" \
  --quiet

# Get the service URL
echo ""
echo "=========================================="
echo "Deployment completed successfully!"
echo "=========================================="
SERVICE_URL=$(gcloud run services describe "${CLOUD_RUN_SERVICE}" \
  --platform=managed \
  --region="${GCP_REGION}" \
  --format='value(status.url)')

echo "Service URL: ${SERVICE_URL}"
echo "=========================================="
echo "Monitor deployment with:"
echo "gcloud run services describe ${CLOUD_RUN_SERVICE} --platform=managed --region=${GCP_REGION}"
echo "=========================================="
