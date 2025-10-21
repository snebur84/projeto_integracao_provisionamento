# Deployment Guide: AWS ECS Fargate & Google Cloud Run

This guide provides comprehensive instructions for deploying the provision application to AWS ECS Fargate and Google Cloud Run using the automated CI/CD pipeline.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [AWS ECS Fargate Setup](#aws-ecs-fargate-setup)
4. [Google Cloud Run Setup](#google-cloud-run-setup)
5. [GitHub Secrets Configuration](#github-secrets-configuration)
6. [CI/CD Workflow](#cicd-workflow)
7. [Manual Deployment](#manual-deployment)
8. [Monitoring and Troubleshooting](#monitoring-and-troubleshooting)

---

## Overview

The CI/CD pipeline builds a Docker image and deploys it to both AWS ECS Fargate and Google Cloud Run. The workflow is triggered on:
- Push to `feature/full-infra-deploy-ecs-fargate-cloudrun` branch
- Pull requests to `main` branch (build only, no deploy)

### Architecture

```
┌─────────────────┐
│  GitHub Actions │
│   CI/CD Pipeline│
└────────┬────────┘
         │
    ┌────┴────┐
    │  Build  │
    │  Image  │
    └────┬────┘
         │
    ┌────┴──────────────┐
    │                   │
┌───▼────┐       ┌──────▼─────┐
│  AWS   │       │   Google   │
│  ECR   │       │  Artifact  │
│        │       │  Registry  │
└───┬────┘       └──────┬─────┘
    │                   │
┌───▼────────┐   ┌──────▼────────┐
│ ECS Fargate│   │  Cloud Run    │
│  Service   │   │   Service     │
└────────────┘   └───────────────┘
```

---

## Prerequisites

### General Requirements
- GitHub account with repository access
- Docker installed locally (for testing)
- Git CLI
- Basic knowledge of AWS and GCP services

### AWS Requirements
- AWS Account with appropriate permissions
- AWS CLI installed and configured
- Access to create/manage:
  - ECR repositories
  - ECS clusters and services
  - IAM roles and policies
  - Systems Manager Parameter Store / Secrets Manager

### GCP Requirements
- GCP Project with billing enabled
- Google Cloud SDK (`gcloud`) installed
- Access to create/manage:
  - Artifact Registry repositories
  - Cloud Run services
  - Secret Manager
  - IAM service accounts

---

## AWS ECS Fargate Setup

### 1. Create ECR Repository

Create a repository to store Docker images:

```bash
# Set your AWS region
export AWS_REGION="us-east-1"

# Create ECR repository
aws ecr create-repository \
  --repository-name provision-app \
  --region ${AWS_REGION}

# Note the repository URI from the output
# Format: <account-id>.dkr.ecr.<region>.amazonaws.com/provision-app
```

### 2. Create ECS Cluster

```bash
# Create Fargate cluster
aws ecs create-cluster \
  --cluster-name provision-cluster \
  --region ${AWS_REGION}
```

### 3. Create IAM Roles

#### Task Execution Role

This role allows ECS to pull images and write logs:

```bash
# Create trust policy file
cat > ecs-task-execution-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create execution role
aws iam create-role \
  --role-name ecsTaskExecutionRole \
  --assume-role-policy-document file://ecs-task-execution-trust-policy.json

# Attach required policies
aws iam attach-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# Add permission to access secrets
aws iam attach-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/SecretsManagerReadWrite
```

#### Task Role

This role is assumed by the application container:

```bash
# Create task role trust policy
cat > ecs-task-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create task role
aws iam create-role \
  --role-name ecsTaskRole \
  --assume-role-policy-document file://ecs-task-trust-policy.json
```

### 4. Create CloudWatch Log Group

```bash
aws logs create-log-group \
  --log-group-name /ecs/provision-app \
  --region ${AWS_REGION}
```

### 5. Store Secrets in AWS

#### Using SSM Parameter Store

```bash
# Store Django secret key
aws ssm put-parameter \
  --name "/provision/SECRET_KEY" \
  --value "YOUR_DJANGO_SECRET_KEY_HERE" \
  --type "SecureString" \
  --region ${AWS_REGION}

# Store API key
aws ssm put-parameter \
  --name "/provision/PROVISION_API_KEY" \
  --value "YOUR_API_KEY_HERE" \
  --type "SecureString" \
  --region ${AWS_REGION}
```

#### Using Secrets Manager

```bash
# Store database password
aws secretsmanager create-secret \
  --name "provision/DB_PASSWORD" \
  --secret-string "YOUR_DB_PASSWORD_HERE" \
  --region ${AWS_REGION}
```

### 6. Create ECS Service

First, update the task definition template `infra/ecs/task-definition.json` with your values:
- Replace `TASK_DEFINITION_FAMILY_PLACEHOLDER` with your task family name
- Replace `ECS_EXECUTION_ROLE_ARN_PLACEHOLDER` with the execution role ARN
- Replace `ECS_TASK_ROLE_ARN_PLACEHOLDER` with the task role ARN
- Replace placeholder values for database, MongoDB, etc.

Then create the service:

```bash
# Register the task definition (after replacing placeholders)
aws ecs register-task-definition \
  --cli-input-json file://infra/ecs/task-definition.json \
  --region ${AWS_REGION}

# Create the service
aws ecs create-service \
  --cluster provision-cluster \
  --service-name provision-service \
  --task-definition provision-app \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxxxx],securityGroups=[sg-xxxxx],assignPublicIp=ENABLED}" \
  --region ${AWS_REGION}
```

---

## Google Cloud Run Setup

### 1. Enable Required APIs

```bash
# Set your GCP project
export GCP_PROJECT="your-project-id"
export GCP_REGION="us-central1"

gcloud config set project ${GCP_PROJECT}

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  sqladmin.googleapis.com
```

### 2. Create Artifact Registry Repository

```bash
# Create repository for Docker images
gcloud artifacts repositories create provision-app \
  --repository-format=docker \
  --location=${GCP_REGION} \
  --description="Docker repository for provision application"

# Verify repository creation
gcloud artifacts repositories list --location=${GCP_REGION}
```

### 3. Create Service Account

```bash
# Create service account for Cloud Run
gcloud iam service-accounts create cloud-run-provision \
  --display-name="Cloud Run Provision Service Account"

# Get the service account email
SA_EMAIL="cloud-run-provision@${GCP_PROJECT}.iam.gserviceaccount.com"

# Grant necessary permissions
gcloud projects add-iam-policy-binding ${GCP_PROJECT} \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding ${GCP_PROJECT} \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/cloudsql.client"
```

### 4. Create Service Account Key for GitHub Actions

```bash
# Create key for GitHub Actions
gcloud iam service-accounts keys create github-actions-key.json \
  --iam-account=${SA_EMAIL}

# Encode to base64 for GitHub Secret
cat github-actions-key.json | base64 -w 0 > github-actions-key-base64.txt

# Store this value in GitHub Secrets as GCP_SA_KEY
echo "Store the content of github-actions-key-base64.txt in GitHub Secret: GCP_SA_KEY"

# Clean up local files (IMPORTANT!)
rm github-actions-key.json github-actions-key-base64.txt
```

### 5. Store Secrets in Secret Manager

```bash
# Create secrets
echo -n "YOUR_DJANGO_SECRET_KEY" | gcloud secrets create django-secret-key \
  --replication-policy="automatic" \
  --data-file=-

echo -n "YOUR_DB_PASSWORD" | gcloud secrets create db-password \
  --replication-policy="automatic" \
  --data-file=-

echo -n "YOUR_API_KEY" | gcloud secrets create provision-api-key \
  --replication-policy="automatic" \
  --data-file=-

echo -n "mongodb+srv://user:pass@host/db" | gcloud secrets create mongo-uri \
  --replication-policy="automatic" \
  --data-file=-
```

### 6. Create Cloud SQL Instance (if needed)

```bash
# Create MySQL instance
gcloud sql instances create provision-db \
  --database-version=MYSQL_8_0 \
  --tier=db-f1-micro \
  --region=${GCP_REGION}

# Create database
gcloud sql databases create provision \
  --instance=provision-db

# Create user
gcloud sql users create provision-user \
  --instance=provision-db \
  --password=YOUR_PASSWORD_HERE
```

---

## GitHub Secrets Configuration

Configure the following secrets in your GitHub repository (Settings → Secrets and variables → Actions → New repository secret):

### Required Secrets for AWS

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `AWS_ACCESS_KEY_ID` | AWS access key for authentication | `AKIAIOSFODNN7EXAMPLE` |
| `AWS_SECRET_ACCESS_KEY` | AWS secret access key | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` |
| `AWS_REGION` | AWS region for deployment | `us-east-1` |
| `AWS_ECR_REPOSITORY` | Name of ECR repository | `provision-app` |
| `ECS_CLUSTER_NAME` | Name of ECS cluster | `provision-cluster` |
| `ECS_SERVICE_NAME` | Name of ECS service | `provision-service` |
| `ECS_TASK_FAMILY` | Task definition family name | `provision-app` |

### Required Secrets for GCP

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `GCP_PROJECT` | GCP project ID | `my-project-12345` |
| `GCP_SA_KEY` | Service account key JSON (base64 encoded) | `ewogICJ0eXBlIjog...` |
| `GCP_REGION` | GCP region for deployment | `us-central1` |
| `GCP_ARTIFACT_REGISTRY_REPOSITORY` | Artifact Registry repository name | `provision-app` |
| `CLOUD_RUN_SERVICE_NAME` | Name of Cloud Run service | `provision-app` |

### Steps to Add Secrets

1. Go to your GitHub repository
2. Navigate to Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Enter the secret name and value
5. Click "Add secret"
6. Repeat for all required secrets

---

## CI/CD Workflow

### Workflow Triggers

The workflow is automatically triggered on:
- **Push** to `feature/full-infra-deploy-ecs-fargate-cloudrun` branch → Builds and deploys
- **Pull Request** to `main` branch → Builds only (no deployment)

### Workflow Jobs

#### 1. Build Job
- Builds Docker image
- Tags with short SHA (first 7 characters)
- Pushes to both AWS ECR and GCP Artifact Registry
- Tags images with both SHA and `latest`

#### 2. Deploy to ECS Job
- Runs only on push to feature branch
- Retrieves current task definition
- Updates image reference
- Registers new task definition
- Updates ECS service

#### 3. Deploy to Cloud Run Job
- Runs only on push to feature branch
- Deploys new image to Cloud Run
- Configures secrets and environment variables
- Sets resource limits and scaling parameters

### Monitoring Workflow Execution

1. Go to the "Actions" tab in your GitHub repository
2. Select the workflow run to view details
3. Click on individual jobs to see logs
4. Check for any errors or warnings

---

## Manual Deployment

### Deploy to AWS ECS Manually

```bash
# Authenticate to AWS
aws configure

# Login to ECR
aws ecr get-login-password --region ${AWS_REGION} | \
  docker login --username AWS --password-stdin ${ECR_REGISTRY}

# Build and push image
docker build -t provision-app:manual .
docker tag provision-app:manual ${ECR_REGISTRY}/provision-app:manual
docker push ${ECR_REGISTRY}/provision-app:manual

# Deploy using the script
export ECR_REGISTRY="123456789012.dkr.ecr.us-east-1.amazonaws.com"
export ECR_REPOSITORY="provision-app"
export IMAGE_TAG="manual"
export AWS_REGION="us-east-1"
export ECS_CLUSTER="provision-cluster"
export ECS_SERVICE="provision-service"
export TASK_DEFINITION_FAMILY="provision-app"

./scripts/deploy/ecs-deploy.sh
```

### Deploy to Google Cloud Run Manually

```bash
# Authenticate to GCP
gcloud auth login
gcloud config set project ${GCP_PROJECT}

# Configure Docker for Artifact Registry
gcloud auth configure-docker ${GCP_REGION}-docker.pkg.dev

# Build and push image
docker build -t provision-app:manual .
docker tag provision-app:manual ${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/provision-app/provision-app:manual
docker push ${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/provision-app/provision-app:manual

# Deploy using the script
export GCP_PROJECT="my-project-12345"
export GCP_REGION="us-central1"
export GCP_REPOSITORY="provision-app"
export IMAGE_TAG="manual"
export CLOUD_RUN_SERVICE="provision-app"

./scripts/deploy/cloudrun-deploy.sh
```

---

## Monitoring and Troubleshooting

### AWS ECS Monitoring

#### View Service Status
```bash
aws ecs describe-services \
  --cluster provision-cluster \
  --services provision-service \
  --region ${AWS_REGION}
```

#### View Running Tasks
```bash
aws ecs list-tasks \
  --cluster provision-cluster \
  --service-name provision-service \
  --region ${AWS_REGION}
```

#### View CloudWatch Logs
```bash
# Get log stream names
aws logs describe-log-streams \
  --log-group-name /ecs/provision-app \
  --region ${AWS_REGION}

# View logs
aws logs tail /ecs/provision-app --follow --region ${AWS_REGION}
```

### GCP Cloud Run Monitoring

#### View Service Status
```bash
gcloud run services describe provision-app \
  --platform=managed \
  --region=${GCP_REGION}
```

#### View Logs
```bash
gcloud logs read \
  --project=${GCP_PROJECT} \
  --filter='resource.type="cloud_run_revision" AND resource.labels.service_name="provision-app"' \
  --limit=50
```

#### View Metrics in Console
Visit: https://console.cloud.google.com/run/detail/${GCP_REGION}/provision-app/metrics

### Common Issues and Solutions

#### Issue: Task fails health check
**Solution**: Check application logs, verify database connectivity, ensure environment variables are set correctly

#### Issue: Image pull authentication failure
**Solution**: 
- AWS: Verify ECR repository permissions and execution role
- GCP: Check Artifact Registry permissions and service account

#### Issue: Service not receiving traffic
**Solution**:
- AWS: Check security group rules and target group health
- GCP: Verify Cloud Run service has `--allow-unauthenticated` flag if needed

#### Issue: Database connection timeout
**Solution**:
- AWS: Check VPC configuration and security group rules
- GCP: Verify Cloud SQL connection name and VPC connector

#### Issue: Out of memory errors
**Solution**: Increase memory allocation in task definition (ECS) or service configuration (Cloud Run)

---

## Security Best Practices

1. **Never commit secrets** to the repository
2. **Use Secret Manager** (GCP) or Secrets Manager/SSM (AWS) for sensitive data
3. **Rotate secrets regularly**
4. **Use least-privilege IAM policies**
5. **Enable VPC for database connections**
6. **Use HTTPS** for all external communication
7. **Enable audit logging** in both AWS and GCP
8. **Review security groups and firewall rules** regularly

---

## Additional Resources

### AWS Documentation
- [Amazon ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [Amazon ECR Documentation](https://docs.aws.amazon.com/ecr/)
- [AWS Fargate Documentation](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html)

### GCP Documentation
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Artifact Registry Documentation](https://cloud.google.com/artifact-registry/docs)
- [Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)

### GitHub Actions
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Encrypted Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)

---

## Support and Contributions

For issues, questions, or contributions:
1. Open an issue in the GitHub repository
2. Submit a pull request with improvements
3. Contact the repository maintainers

---

**Last Updated**: 2025-10-21
