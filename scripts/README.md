# Deployment Scripts

This directory contains helper scripts for deploying the Code Review & Documentation Agent.

## Available Scripts

### 1. docker-deploy.sh

Quick deployment script for Docker-based deployments.

**Usage:**
```bash
./docker-deploy.sh [command]
```

**Commands:**
- `start` - Start the services
- `stop` - Stop the services
- `restart` - Restart the services
- `logs` - Show service logs
- `status` - Show service status
- `cleanup` - Stop services and remove all data
- `help` - Show help message

**Examples:**
```bash
# Start services
./docker-deploy.sh start

# View logs
./docker-deploy.sh logs

# Check status
./docker-deploy.sh status

# Restart services
./docker-deploy.sh restart

# Stop services
./docker-deploy.sh stop
```

**Prerequisites:**
- Docker installed
- Docker Compose installed
- `.env` file configured (script will create from `.env.example` if missing)

### 2. create-k8s-secrets.sh

Interactive script to create Kubernetes secrets for the Code Review Agent.

**Usage:**
```bash
./create-k8s-secrets.sh
```

The script will prompt you for:
- AWS credentials (for Amazon Bedrock)
- OpenAI API key (optional)
- Anthropic API key (optional)
- API authentication key (optional)

You can skip any secret by pressing Enter without providing a value.

**Prerequisites:**
- kubectl installed and configured
- Access to Kubernetes cluster
- Appropriate permissions to create secrets

**What it does:**
1. Checks if kubectl is installed
2. Creates namespace if it doesn't exist
3. Prompts for secret values
4. Creates Kubernetes secret
5. Shows secret details (without revealing values)

**After running:**
```bash
# Deploy the application
kubectl apply -f k8s-deployment.yaml

# Check deployment status
kubectl get pods -n code-review-agent

# View logs
kubectl logs -f deployment/code-review-agent -n code-review-agent
```

### 3. verify_setup.py

Python script to verify the installation and configuration.

**Usage:**
```bash
python scripts/verify_setup.py
```

**What it checks:**
- Python version
- Required dependencies
- Environment variables
- LLM provider configuration
- Database connectivity
- File system permissions

## Windows Users

On Windows, you can run these scripts using:

**Git Bash:**
```bash
bash scripts/docker-deploy.sh start
bash scripts/create-k8s-secrets.sh
```

**WSL (Windows Subsystem for Linux):**
```bash
./scripts/docker-deploy.sh start
./scripts/create-k8s-secrets.sh
```

**PowerShell (alternative):**
For Windows users without bash, you can use Docker Compose directly:
```powershell
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f

# Check status
docker-compose ps
```

## Troubleshooting

### Permission Denied

If you get "Permission denied" errors on Linux/Mac:

```bash
chmod +x scripts/*.sh
```

### Docker Not Found

Install Docker:
- **Linux**: Follow [Docker installation guide](https://docs.docker.com/engine/install/)
- **Mac**: Install [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/)
- **Windows**: Install [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)

### kubectl Not Found

Install kubectl:
```bash
# Linux
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/

# Mac
brew install kubectl

# Windows
choco install kubernetes-cli
```

### .env File Issues

If the `.env` file is not being read:
1. Ensure it's in the project root directory
2. Check file permissions: `chmod 644 .env`
3. Verify no extra spaces or special characters
4. Use `.env.example` as a template

### Services Won't Start

1. Check if ports are already in use:
   ```bash
   # Linux/Mac
   lsof -i :8000
   
   # Windows
   netstat -ano | findstr :8000
   ```

2. Check Docker logs:
   ```bash
   docker-compose logs api
   ```

3. Verify environment variables:
   ```bash
   docker-compose config
   ```

## Additional Resources

- [Deployment Guide](../docs/DEPLOYMENT.md) - Comprehensive deployment documentation
- [Docker Documentation](https://docs.docker.com/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)

## Support

For issues or questions:
1. Check the [Deployment Guide](../docs/DEPLOYMENT.md)
2. Review the [Troubleshooting section](../docs/DEPLOYMENT.md#troubleshooting)
3. Open an issue on GitHub
4. Contact the development team
