#!/bin/bash
# Script to create Kubernetes secrets for Code Review Agent
# Usage: ./create-k8s-secrets.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Code Review Agent - Kubernetes Secrets Setup${NC}"
echo "=============================================="
echo ""

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}Error: kubectl is not installed${NC}"
    exit 1
fi

# Check if namespace exists
NAMESPACE="code-review-agent"
if ! kubectl get namespace $NAMESPACE &> /dev/null; then
    echo -e "${YELLOW}Namespace $NAMESPACE does not exist. Creating...${NC}"
    kubectl create namespace $NAMESPACE
fi

echo "This script will help you create Kubernetes secrets for the Code Review Agent."
echo "You can skip any secret by pressing Enter without providing a value."
echo ""

# Function to read secret value
read_secret() {
    local prompt=$1
    local secret_value
    read -sp "$prompt: " secret_value
    echo ""
    echo "$secret_value"
}

# Function to read non-secret value
read_value() {
    local prompt=$1
    local default=$2
    local value
    read -p "$prompt [$default]: " value
    echo "${value:-$default}"
}

# Collect secrets
echo -e "${YELLOW}AWS Credentials (for Amazon Bedrock)${NC}"
AWS_ACCESS_KEY_ID=$(read_secret "AWS Access Key ID (or press Enter to skip)")
AWS_SECRET_ACCESS_KEY=$(read_secret "AWS Secret Access Key (or press Enter to skip)")
echo ""

echo -e "${YELLOW}Alternative LLM Providers${NC}"
OPENAI_API_KEY=$(read_secret "OpenAI API Key (or press Enter to skip)")
ANTHROPIC_API_KEY=$(read_secret "Anthropic API Key (or press Enter to skip)")
echo ""

echo -e "${YELLOW}API Authentication${NC}"
API_KEY=$(read_secret "API Key for authentication (or press Enter to skip)")
echo ""

# Build kubectl command
SECRET_CMD="kubectl create secret generic code-review-agent-secrets --namespace=$NAMESPACE"

# Add secrets if provided
if [ -n "$AWS_ACCESS_KEY_ID" ]; then
    SECRET_CMD="$SECRET_CMD --from-literal=aws-access-key-id=$AWS_ACCESS_KEY_ID"
fi

if [ -n "$AWS_SECRET_ACCESS_KEY" ]; then
    SECRET_CMD="$SECRET_CMD --from-literal=aws-secret-access-key=$AWS_SECRET_ACCESS_KEY"
fi

if [ -n "$OPENAI_API_KEY" ]; then
    SECRET_CMD="$SECRET_CMD --from-literal=openai-api-key=$OPENAI_API_KEY"
fi

if [ -n "$ANTHROPIC_API_KEY" ]; then
    SECRET_CMD="$SECRET_CMD --from-literal=anthropic-api-key=$ANTHROPIC_API_KEY"
fi

if [ -n "$API_KEY" ]; then
    SECRET_CMD="$SECRET_CMD --from-literal=api-key=$API_KEY"
fi

# Check if secret already exists
if kubectl get secret code-review-agent-secrets --namespace=$NAMESPACE &> /dev/null; then
    echo -e "${YELLOW}Secret 'code-review-agent-secrets' already exists.${NC}"
    read -p "Do you want to delete and recreate it? (y/N): " confirm
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        kubectl delete secret code-review-agent-secrets --namespace=$NAMESPACE
        echo -e "${GREEN}Existing secret deleted.${NC}"
    else
        echo -e "${YELLOW}Skipping secret creation.${NC}"
        exit 0
    fi
fi

# Create secret
echo ""
echo -e "${GREEN}Creating Kubernetes secret...${NC}"
eval $SECRET_CMD --dry-run=client -o yaml | kubectl apply -f -

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Secret created successfully!${NC}"
    echo ""
    echo "You can now deploy the application using:"
    echo "  kubectl apply -f k8s-deployment.yaml"
else
    echo -e "${RED}✗ Failed to create secret${NC}"
    exit 1
fi

# Show secret info (without values)
echo ""
echo "Secret details:"
kubectl describe secret code-review-agent-secrets --namespace=$NAMESPACE

echo ""
echo -e "${GREEN}Setup complete!${NC}"
