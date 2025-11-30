#!/usr/bin/env python3
"""
Validation script for deployment configuration files.
Checks YAML syntax and Docker/Kubernetes configuration validity.
"""

import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("❌ PyYAML not installed. Install with: pip install pyyaml")
    sys.exit(1)


def validate_yaml_file(file_path: Path) -> bool:
    """Validate YAML file syntax."""
    try:
        with open(file_path, 'r') as f:
            if file_path.name == 'k8s-deployment.yaml':
                # Multiple YAML documents
                list(yaml.safe_load_all(f))
            else:
                yaml.safe_load(f)
        print(f"✓ {file_path.name}: Valid YAML syntax")
        return True
    except yaml.YAMLError as e:
        print(f"✗ {file_path.name}: Invalid YAML syntax")
        print(f"  Error: {e}")
        return False
    except FileNotFoundError:
        print(f"⚠ {file_path.name}: File not found")
        return False


def validate_docker_compose(file_path: Path) -> bool:
    """Validate Docker Compose configuration."""
    try:
        with open(file_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Check required fields
        if 'version' not in config:
            print(f"⚠ {file_path.name}: Missing 'version' field")
        
        if 'services' not in config:
            print(f"✗ {file_path.name}: Missing 'services' field")
            return False
        
        # Check API service
        if 'api' not in config['services']:
            print(f"✗ {file_path.name}: Missing 'api' service")
            return False
        
        api_service = config['services']['api']
        
        # Check required service fields
        if 'build' not in api_service and 'image' not in api_service:
            print(f"✗ {file_path.name}: API service missing 'build' or 'image'")
            return False
        
        if 'ports' not in api_service:
            print(f"⚠ {file_path.name}: API service missing 'ports'")
        
        print(f"✓ {file_path.name}: Valid Docker Compose configuration")
        return True
        
    except Exception as e:
        print(f"✗ {file_path.name}: Validation error")
        print(f"  Error: {e}")
        return False


def validate_kubernetes(file_path: Path) -> bool:
    """Validate Kubernetes configuration."""
    try:
        with open(file_path, 'r') as f:
            docs = list(yaml.safe_load_all(f))
        
        if not docs:
            print(f"✗ {file_path.name}: No Kubernetes resources found")
            return False
        
        # Check for required resource types
        resource_types = {doc.get('kind') for doc in docs if doc}
        
        required_types = {'Namespace', 'Deployment', 'Service'}
        missing_types = required_types - resource_types
        
        if missing_types:
            print(f"⚠ {file_path.name}: Missing resource types: {missing_types}")
        
        # Check Deployment
        deployments = [doc for doc in docs if doc and doc.get('kind') == 'Deployment']
        if deployments:
            deployment = deployments[0]
            spec = deployment.get('spec', {})
            
            if 'replicas' not in spec:
                print(f"⚠ {file_path.name}: Deployment missing 'replicas'")
            
            if 'selector' not in spec:
                print(f"✗ {file_path.name}: Deployment missing 'selector'")
                return False
            
            template = spec.get('template', {})
            if 'spec' not in template:
                print(f"✗ {file_path.name}: Deployment template missing 'spec'")
                return False
        
        print(f"✓ {file_path.name}: Valid Kubernetes configuration ({len(docs)} resources)")
        return True
        
    except Exception as e:
        print(f"✗ {file_path.name}: Validation error")
        print(f"  Error: {e}")
        return False


def validate_dockerfile(file_path: Path) -> bool:
    """Validate Dockerfile."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for required instructions
        required_instructions = ['FROM', 'WORKDIR', 'COPY', 'EXPOSE']
        missing_instructions = []
        
        for instruction in required_instructions:
            if instruction not in content:
                missing_instructions.append(instruction)
        
        if missing_instructions:
            print(f"⚠ {file_path.name}: Missing instructions: {missing_instructions}")
        
        # Check for best practices
        if 'HEALTHCHECK' not in content:
            print(f"⚠ {file_path.name}: Missing HEALTHCHECK instruction (recommended)")
        
        if 'USER' not in content:
            print(f"⚠ {file_path.name}: Missing USER instruction (recommended for security)")
        
        print(f"✓ {file_path.name}: Valid Dockerfile")
        return True
        
    except FileNotFoundError:
        print(f"⚠ {file_path.name}: File not found")
        return False
    except Exception as e:
        print(f"✗ {file_path.name}: Validation error")
        print(f"  Error: {e}")
        return False


def main():
    """Main validation function."""
    print("🔍 Validating Deployment Configuration Files")
    print("=" * 50)
    print()
    
    project_root = Path(__file__).parent.parent
    all_valid = True
    
    # Validate Dockerfile
    print("📦 Docker Configuration:")
    dockerfile = project_root / "Dockerfile"
    all_valid &= validate_dockerfile(dockerfile)
    print()
    
    # Validate docker-compose.yml
    docker_compose = project_root / "docker-compose.yml"
    all_valid &= validate_yaml_file(docker_compose)
    all_valid &= validate_docker_compose(docker_compose)
    print()
    
    # Validate Kubernetes deployment
    print("☸️  Kubernetes Configuration:")
    k8s_deployment = project_root / "k8s-deployment.yaml"
    all_valid &= validate_yaml_file(k8s_deployment)
    all_valid &= validate_kubernetes(k8s_deployment)
    print()
    
    # Validate nginx.conf (basic check)
    print("🌐 Nginx Configuration:")
    nginx_conf = project_root / "nginx.conf"
    if nginx_conf.exists():
        print(f"✓ {nginx_conf.name}: File exists")
    else:
        print(f"⚠ {nginx_conf.name}: File not found")
    print()
    
    # Validate .env.example
    print("⚙️  Environment Configuration:")
    env_example = project_root / ".env.example"
    if env_example.exists():
        with open(env_example, 'r') as f:
            env_content = f.read()
        
        # Check for required variables
        required_vars = [
            'AWS_REGION',
            'BEDROCK_MODEL_ID',
            'LOG_LEVEL',
            'API_PORT'
        ]
        
        missing_vars = []
        for var in required_vars:
            if var not in env_content:
                missing_vars.append(var)
        
        if missing_vars:
            print(f"⚠ .env.example: Missing variables: {missing_vars}")
        else:
            print(f"✓ .env.example: All required variables present")
    else:
        print(f"✗ .env.example: File not found")
        all_valid = False
    print()
    
    # Summary
    print("=" * 50)
    if all_valid:
        print("✅ All deployment configurations are valid!")
        return 0
    else:
        print("❌ Some deployment configurations have issues")
        print("   Please review the warnings and errors above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
