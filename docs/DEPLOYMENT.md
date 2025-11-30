# Deployment Guide

This guide covers various deployment options for the Code Review & Documentation Agent, from local development to production cloud deployments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Local Development](#local-development)
- [Docker Deployment](#docker-deployment)
- [AWS Deployment](#aws-deployment)
- [Google Cloud Deployment](#google-cloud-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Environment Configuration](#environment-configuration)
- [Health Checks and Monitoring](#health-checks-and-monitoring)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required

- Python 3.11 or higher
- Docker and Docker Compose (for containerized deployment)
- Git (for version control integration)

### LLM Provider (choose one)

- **Amazon Bedrock** (recommended for Amazon employees)
  - AWS account with Bedrock access
  - AWS credentials configured
  - Nova Pro or Nova Lite model access enabled

- **OpenAI**
  - OpenAI API key
  - GPT-4 or GPT-3.5-turbo access

- **Anthropic Claude**
  - Anthropic API key
  - Claude 3 access via Bedrock or direct API

- **Local LLM (Ollama)**
  - Ollama installed locally
  - Llama 3.1, Mistral, or CodeLlama model downloaded

## Local Development

### 1. Clone the Repository

```bash
git clone <repository-url>
cd code-review-documentation-agent
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

Copy the example environment file and configure your settings:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```bash
# AWS Bedrock Configuration (if using Bedrock)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
BEDROCK_MODEL_ID=amazon.nova-pro-v1:0

# Or use OpenAI
# OPENAI_API_KEY=your_openai_key

# Application settings
LOG_LEVEL=INFO
MAX_PARALLEL_FILES=4
API_PORT=8000
```

### 5. Run the Application

**CLI Mode:**
```bash
code-review-agent analyze --path ./your-codebase --output ./reports
```

**API Mode:**
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Access the API documentation at: http://localhost:8000/docs

## Docker Deployment

### Quick Start with Docker Compose

1. **Configure Environment**

Create a `.env` file with your configuration (see `.env.example`).

2. **Build and Start Services**

```bash
docker-compose up -d
```

This will:
- Build the Docker image
- Start the API service
- Create persistent volumes for data
- Expose the API on port 8000

3. **Check Service Health**

```bash
curl http://localhost:8000/health
```

4. **View Logs**

```bash
docker-compose logs -f api
```

5. **Stop Services**

```bash
docker-compose down
```

### Custom Docker Build

**Build the image:**
```bash
docker build -t code-review-agent:latest .
```

**Run the container:**
```bash
docker run -d \
  --name code-review-agent \
  -p 8000:8000 \
  -e AWS_REGION=us-east-1 \
  -e AWS_ACCESS_KEY_ID=your_key \
  -e AWS_SECRET_ACCESS_KEY=your_secret \
  -e BEDROCK_MODEL_ID=amazon.nova-pro-v1:0 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/your-codebase:/workspace:ro \
  code-review-agent:latest
```

### Docker Compose with PostgreSQL

For production deployments, use PostgreSQL instead of SQLite:

1. **Uncomment PostgreSQL service** in `docker-compose.yml`

2. **Update environment variables:**

```bash
DATABASE_URL=postgresql://codereviewer:changeme@postgres:5432/code_review_agent
POSTGRES_USER=codereviewer
POSTGRES_PASSWORD=your_secure_password
```

3. **Start services:**

```bash
docker-compose up -d
```

## AWS Deployment

### Option 1: AWS ECS (Elastic Container Service)

#### Prerequisites
- AWS CLI configured
- ECS cluster created
- ECR repository for Docker images

#### Steps

1. **Build and Push Docker Image to ECR**

```bash
# Authenticate Docker to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build image
docker build -t code-review-agent:latest .

# Tag image
docker tag code-review-agent:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/code-review-agent:latest

# Push image
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/code-review-agent:latest
```

2. **Create ECS Task Definition**

Create `ecs-task-definition.json`:

```json
{
  "family": "code-review-agent",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "code-review-agent",
      "image": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/code-review-agent:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "AWS_REGION",
          "value": "us-east-1"
        },
        {
          "name": "BEDROCK_MODEL_ID",
          "value": "amazon.nova-pro-v1:0"
        },
        {
          "name": "LOG_LEVEL",
          "value": "INFO"
        }
      ],
      "secrets": [
        {
          "name": "API_KEY",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:<account-id>:secret:code-review-api-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/code-review-agent",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "python -c 'import httpx; httpx.get(\"http://localhost:8000/health\", timeout=5.0)' || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

3. **Register Task Definition**

```bash
aws ecs register-task-definition --cli-input-json file://ecs-task-definition.json
```

4. **Create ECS Service**

```bash
aws ecs create-service \
  --cluster your-cluster-name \
  --service-name code-review-agent \
  --task-definition code-review-agent \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}" \
  --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:...,containerName=code-review-agent,containerPort=8000"
```

### Option 2: AWS Lambda (Serverless)

For lightweight deployments, you can deploy as a Lambda function with API Gateway.

1. **Create Lambda Deployment Package**

```bash
# Install dependencies to a directory
pip install -r requirements.txt -t lambda_package/

# Copy application code
cp -r agents api config models storage tools lambda_package/

# Create deployment package
cd lambda_package
zip -r ../lambda_deployment.zip .
cd ..
```

2. **Create Lambda Function**

```bash
aws lambda create-function \
  --function-name code-review-agent \
  --runtime python3.11 \
  --role arn:aws:iam::<account-id>:role/lambda-execution-role \
  --handler api.lambda_handler.handler \
  --zip-file fileb://lambda_deployment.zip \
  --timeout 900 \
  --memory-size 2048 \
  --environment Variables="{AWS_REGION=us-east-1,BEDROCK_MODEL_ID=amazon.nova-pro-v1:0}"
```

3. **Create API Gateway**

Use AWS Console or CLI to create an API Gateway that triggers the Lambda function.

### Option 3: AWS App Runner

AWS App Runner provides a simple way to deploy containerized applications.

1. **Create App Runner Service**

```bash
aws apprunner create-service \
  --service-name code-review-agent \
  --source-configuration '{
    "ImageRepository": {
      "ImageIdentifier": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/code-review-agent:latest",
      "ImageRepositoryType": "ECR",
      "ImageConfiguration": {
        "Port": "8000",
        "RuntimeEnvironmentVariables": {
          "AWS_REGION": "us-east-1",
          "BEDROCK_MODEL_ID": "amazon.nova-pro-v1:0"
        }
      }
    },
    "AutoDeploymentsEnabled": true
  }' \
  --instance-configuration '{
    "Cpu": "1 vCPU",
    "Memory": "2 GB"
  }' \
  --health-check-configuration '{
    "Protocol": "HTTP",
    "Path": "/health",
    "Interval": 10,
    "Timeout": 5,
    "HealthyThreshold": 1,
    "UnhealthyThreshold": 5
  }'
```

## Google Cloud Deployment

### Cloud Run Deployment

1. **Build and Push to Google Container Registry**

```bash
# Configure Docker for GCR
gcloud auth configure-docker

# Build image
docker build -t gcr.io/<project-id>/code-review-agent:latest .

# Push image
docker push gcr.io/<project-id>/code-review-agent:latest
```

2. **Deploy to Cloud Run**

```bash
gcloud run deploy code-review-agent \
  --image gcr.io/<project-id>/code-review-agent:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8000 \
  --memory 2Gi \
  --cpu 2 \
  --set-env-vars "LOG_LEVEL=INFO,MAX_PARALLEL_FILES=4" \
  --set-secrets "OPENAI_API_KEY=openai-key:latest"
```

### Google Kubernetes Engine (GKE)

See [Kubernetes Deployment](#kubernetes-deployment) section below.

## Kubernetes Deployment

### Prerequisites

- Kubernetes cluster (EKS, GKE, AKS, or local)
- kubectl configured
- Docker image pushed to a registry

### Deployment Files

1. **Create Namespace**

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: code-review-agent
```

2. **Create ConfigMap**

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: code-review-agent-config
  namespace: code-review-agent
data:
  LOG_LEVEL: "INFO"
  MAX_PARALLEL_FILES: "4"
  API_HOST: "0.0.0.0"
  API_PORT: "8000"
  AWS_REGION: "us-east-1"
  BEDROCK_MODEL_ID: "amazon.nova-pro-v1:0"
```

3. **Create Secret**

```bash
kubectl create secret generic code-review-agent-secrets \
  --from-literal=aws-access-key-id=your_key \
  --from-literal=aws-secret-access-key=your_secret \
  --from-literal=api-key=your_api_key \
  -n code-review-agent
```

4. **Create Deployment**

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: code-review-agent
  namespace: code-review-agent
spec:
  replicas: 2
  selector:
    matchLabels:
      app: code-review-agent
  template:
    metadata:
      labels:
        app: code-review-agent
    spec:
      containers:
      - name: code-review-agent
        image: <your-registry>/code-review-agent:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: code-review-agent-config
        env:
        - name: AWS_ACCESS_KEY_ID
          valueFrom:
            secretKeyRef:
              name: code-review-agent-secrets
              key: aws-access-key-id
        - name: AWS_SECRET_ACCESS_KEY
          valueFrom:
            secretKeyRef:
              name: code-review-agent-secrets
              key: aws-secret-access-key
        - name: API_KEY
          valueFrom:
            secretKeyRef:
              name: code-review-agent-secrets
              key: api-key
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
        volumeMounts:
        - name: data
          mountPath: /app/data
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: code-review-agent-pvc
```

5. **Create Service**

```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: code-review-agent
  namespace: code-review-agent
spec:
  type: LoadBalancer
  selector:
    app: code-review-agent
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
```

6. **Create PersistentVolumeClaim**

```yaml
# pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: code-review-agent-pvc
  namespace: code-review-agent
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

7. **Apply Configuration**

```bash
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f pvc.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
```

8. **Check Deployment Status**

```bash
kubectl get pods -n code-review-agent
kubectl get svc -n code-review-agent
kubectl logs -f deployment/code-review-agent -n code-review-agent
```

## Environment Configuration

### Required Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `AWS_REGION` | AWS region for Bedrock | `us-east-1` | If using Bedrock |
| `AWS_ACCESS_KEY_ID` | AWS access key | - | If using Bedrock |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | - | If using Bedrock |
| `BEDROCK_MODEL_ID` | Bedrock model ID | `amazon.nova-pro-v1:0` | If using Bedrock |
| `OPENAI_API_KEY` | OpenAI API key | - | If using OpenAI |
| `ANTHROPIC_API_KEY` | Anthropic API key | - | If using Anthropic |

### Optional Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LOG_LEVEL` | Logging level | `INFO` |
| `MAX_PARALLEL_FILES` | Max parallel file processing | `4` |
| `DATABASE_URL` | Database connection string | `sqlite:///./memory_bank.db` |
| `API_HOST` | API host address | `0.0.0.0` |
| `API_PORT` | API port | `8000` |
| `API_KEY` | API authentication key | None (disabled) |
| `DEFAULT_ANALYSIS_DEPTH` | Default analysis depth | `standard` |
| `COMPLEXITY_THRESHOLD` | Complexity threshold | `10` |

## Health Checks and Monitoring

### Health Check Endpoints

The application provides three health check endpoints:

1. **`/health`** - Overall health status
   - Returns health status of all components
   - Used by Docker health checks
   - Returns 200 if healthy, 503 if unhealthy

2. **`/health/ready`** - Readiness check
   - Indicates if the application is ready to accept requests
   - Used by Kubernetes readiness probes
   - Returns 200 if ready, 503 if not ready

3. **`/health/live`** - Liveness check
   - Indicates if the application is alive
   - Used by Kubernetes liveness probes
   - Always returns 200 unless the application is completely down

### Example Health Check Response

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "0.1.0",
  "components": {
    "memory_bank": "healthy",
    "session_manager": "healthy",
    "active_analyses": 2
  }
}
```

### Monitoring with Prometheus

The application exposes metrics that can be scraped by Prometheus:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'code-review-agent'
    static_configs:
      - targets: ['code-review-agent:8000']
    metrics_path: '/metrics'
```

### Logging

The application uses structured JSON logging. Logs can be collected using:

- **AWS CloudWatch**: Configure CloudWatch Logs agent
- **Google Cloud Logging**: Automatically collected in Cloud Run/GKE
- **ELK Stack**: Use Filebeat to ship logs to Elasticsearch
- **Datadog**: Use Datadog agent for log collection

Example log entry:

```json
{
  "event": "analysis_started",
  "session_id": "abc-123",
  "path": "/workspace/myproject",
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "info"
}
```

## Troubleshooting

### Common Issues

#### 1. Container Fails to Start

**Symptom**: Container exits immediately after starting

**Solutions**:
- Check logs: `docker logs <container-id>`
- Verify environment variables are set correctly
- Ensure AWS credentials are valid (if using Bedrock)
- Check if required ports are available

#### 2. Health Check Failures

**Symptom**: Health check endpoint returns 503 or times out

**Solutions**:
- Check if Memory Bank database is accessible
- Verify database file permissions
- Ensure sufficient disk space
- Check application logs for errors

#### 3. Out of Memory Errors

**Symptom**: Container is killed due to OOM

**Solutions**:
- Increase container memory limit
- Reduce `MAX_PARALLEL_FILES` setting
- Use `quick` analysis depth instead of `deep`
- Process smaller codebases or use file filters

#### 4. Slow Analysis Performance

**Symptom**: Analysis takes too long to complete

**Solutions**:
- Increase `MAX_PARALLEL_FILES` for more parallelism
- Use faster LLM model (e.g., Nova Lite instead of Nova Pro)
- Exclude unnecessary files with `exclude_patterns`
- Use `quick` analysis depth for faster results

#### 5. API Authentication Errors

**Symptom**: 401 or 403 errors when calling API

**Solutions**:
- Verify `API_KEY` environment variable is set
- Include `X-API-Key` header in requests
- Check if API key matches configured value

#### 6. LLM API Errors

**Symptom**: Errors related to LLM provider (Bedrock, OpenAI, etc.)

**Solutions**:
- Verify API credentials are correct
- Check if you have access to the specified model
- Ensure sufficient API quota/credits
- Check network connectivity to LLM provider

### Getting Help

If you encounter issues not covered here:

1. Check the application logs for detailed error messages
2. Review the [GitHub Issues](https://github.com/your-repo/issues)
3. Consult the [API Documentation](http://localhost:8000/docs)
4. Contact the development team

## Security Best Practices

### Production Deployment Checklist

- [ ] Use strong, unique API keys
- [ ] Store secrets in a secure secret manager (AWS Secrets Manager, HashiCorp Vault)
- [ ] Enable HTTPS/TLS for all API endpoints
- [ ] Use IAM roles instead of access keys when possible
- [ ] Implement rate limiting on API endpoints
- [ ] Enable audit logging for all API requests
- [ ] Regularly update dependencies and base images
- [ ] Use read-only file system mounts for codebase access
- [ ] Implement network policies to restrict traffic
- [ ] Enable container scanning for vulnerabilities
- [ ] Use non-root user in Docker containers
- [ ] Implement proper backup strategy for Memory Bank data

### Network Security

- Use VPC/private networks for internal communication
- Implement firewall rules to restrict access
- Use API Gateway or reverse proxy for public endpoints
- Enable DDoS protection (AWS Shield, Cloudflare)
- Implement request validation and sanitization

### Data Security

- Encrypt data at rest (database encryption)
- Encrypt data in transit (TLS/HTTPS)
- Implement data retention policies
- Regularly backup Memory Bank and session data
- Sanitize code snippets before sending to LLM providers

## Scaling Considerations

### Horizontal Scaling

The application is designed to be stateless (except for Memory Bank and session data), making it suitable for horizontal scaling:

- Use load balancer to distribute traffic across multiple instances
- Share Memory Bank database across instances (use PostgreSQL)
- Use shared storage for session data (S3, NFS)
- Configure auto-scaling based on CPU/memory usage

### Vertical Scaling

For large codebases, consider vertical scaling:

- Increase container memory (2-4 GB recommended)
- Increase CPU allocation (2-4 cores recommended)
- Adjust `MAX_PARALLEL_FILES` based on available resources

### Performance Optimization

- Use caching for frequently analyzed codebases
- Implement incremental analysis (PR mode)
- Use faster LLM models for quick analyses
- Optimize database queries and indexes
- Use connection pooling for database access

## Cost Optimization

### AWS Bedrock

- Use Nova Lite for simpler analyses (lower cost)
- Use Nova Pro only for complex code analysis
- Implement request batching to reduce API calls
- Cache LLM responses for similar code patterns

### Infrastructure

- Use spot instances for non-critical workloads
- Implement auto-scaling to match demand
- Use reserved instances for predictable workloads
- Monitor and optimize resource utilization
- Use serverless options (Lambda, Cloud Run) for low-traffic scenarios

## Backup and Disaster Recovery

### Backup Strategy

1. **Memory Bank Database**
   - Daily automated backups
   - Retention: 30 days
   - Store in S3 or equivalent

2. **Session Data**
   - Backup active sessions hourly
   - Retention: 7 days
   - Store in S3 or equivalent

3. **Configuration**
   - Version control all configuration files
   - Store secrets in secret manager with versioning

### Disaster Recovery

1. **Database Corruption**
   - Restore from latest backup
   - Verify data integrity
   - Resume active sessions

2. **Service Outage**
   - Deploy to secondary region/zone
   - Update DNS/load balancer
   - Restore from backups if needed

3. **Data Loss**
   - Restore from point-in-time backup
   - Re-run failed analyses
   - Notify affected users

## Maintenance

### Regular Maintenance Tasks

- Update dependencies monthly
- Review and rotate API keys quarterly
- Clean up old session data weekly
- Optimize database indexes monthly
- Review and update security policies quarterly
- Test backup and restore procedures monthly

### Monitoring Metrics

- API response times
- Analysis completion rates
- Error rates by category
- Resource utilization (CPU, memory, disk)
- LLM API costs and usage
- Active session counts
- Database query performance

## Conclusion

This deployment guide covers various deployment scenarios from local development to production cloud deployments. Choose the deployment option that best fits your requirements, infrastructure, and scale.

For additional help, refer to:
- [API Documentation](./api/README.md)
- [CLI Usage Guide](./CLI_USAGE.md)
- [Quick Start Guide](./QUICK_START.md)
- [Project README](../README.md)
