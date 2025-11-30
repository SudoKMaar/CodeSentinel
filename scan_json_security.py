"""
Simple security scanner for JSON files.
Checks for hardcoded secrets, passwords, API keys, etc.
"""

import json
import re
import os
from pathlib import Path

# Security patterns to detect
SECURITY_PATTERNS = {
    'password': r'(?i)(password|passwd|pwd)\s*[:=]\s*["\']([^"\']{8,})["\']',
    'api_key': r'(?i)(api[_-]?key|apikey)\s*[:=]\s*["\']([^"\']{20,})["\']',
    'secret': r'(?i)(secret|token)\s*[:=]\s*["\']([^"\']{8,})["\']',
    'aws_key': r'(?i)(aws[_-]?access[_-]?key|aws[_-]?secret)\s*[:=]\s*["\']([^"\']{16,})["\']',
    'private_key': r'(?i)(private[_-]?key|priv[_-]?key)\s*[:=]\s*["\']([^"\']{20,})["\']',
}

def scan_json_file(file_path):
    """Scan a JSON file for security issues."""
    issues = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check for security patterns
        for pattern_name, pattern in SECURITY_PATTERNS.items():
            matches = re.finditer(pattern, content)
            for match in matches:
                issues.append({
                    'file': file_path,
                    'type': pattern_name,
                    'line': content[:match.start()].count('\n') + 1,
                    'severity': 'HIGH',
                    'description': f'Potential {pattern_name.replace("_", " ")} detected'
                })
        
        # Try to parse as JSON
        try:
            data = json.loads(content)
            # Check for suspicious keys in JSON structure
            issues.extend(check_json_structure(file_path, data))
        except json.JSONDecodeError as e:
            issues.append({
                'file': file_path,
                'type': 'json_error',
                'line': e.lineno,
                'severity': 'MEDIUM',
                'description': f'JSON parsing error: {e.msg}'
            })
    
    except Exception as e:
        issues.append({
            'file': file_path,
            'type': 'read_error',
            'line': 0,
            'severity': 'LOW',
            'description': f'Error reading file: {str(e)}'
        })
    
    return issues

def check_json_structure(file_path, data, path=''):
    """Recursively check JSON structure for sensitive data."""
    issues = []
    
    if isinstance(data, dict):
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            
            # Check for suspicious keys
            if any(keyword in key.lower() for keyword in ['password', 'secret', 'token', 'api_key', 'private_key']):
                if isinstance(value, str) and len(value) > 5:
                    issues.append({
                        'file': file_path,
                        'type': 'sensitive_key',
                        'line': 0,
                        'severity': 'HIGH',
                        'description': f'Sensitive key "{current_path}" contains value'
                    })
            
            # Recurse into nested structures
            issues.extend(check_json_structure(file_path, value, current_path))
    
    elif isinstance(data, list):
        for i, item in enumerate(data):
            current_path = f"{path}[{i}]"
            issues.extend(check_json_structure(file_path, item, current_path))
    
    return issues

def scan_directory(directory_path):
    """Scan all JSON files in a directory."""
    all_issues = []
    json_files = list(Path(directory_path).glob('*.json'))
    
    print(f"\n🔍 Scanning {len(json_files)} JSON files in: {directory_path}\n")
    
    for json_file in json_files:
        print(f"Scanning: {json_file.name}...")
        issues = scan_json_file(str(json_file))
        all_issues.extend(issues)
    
    return all_issues

def print_report(issues):
    """Print security scan report."""
    if not issues:
        print("\n✅ No security issues found!\n")
        return
    
    print(f"\n⚠️  Found {len(issues)} potential security issues:\n")
    print("=" * 80)
    
    # Group by severity
    by_severity = {'HIGH': [], 'MEDIUM': [], 'LOW': []}
    for issue in issues:
        by_severity[issue['severity']].append(issue)
    
    for severity in ['HIGH', 'MEDIUM', 'LOW']:
        if by_severity[severity]:
            print(f"\n{severity} SEVERITY ({len(by_severity[severity])} issues):")
            print("-" * 80)
            for issue in by_severity[severity]:
                print(f"  📄 File: {Path(issue['file']).name}")
                print(f"  📍 Line: {issue['line']}")
                print(f"  🔍 Type: {issue['type']}")
                print(f"  💬 Description: {issue['description']}")
                print()

if __name__ == "__main__":
    target_dir = r"C:\QAL\Week 48\Optimus Agent Evaluation Workflow"
    
    if not os.path.exists(target_dir):
        print(f"❌ Directory not found: {target_dir}")
        exit(1)
    
    issues = scan_directory(target_dir)
    print_report(issues)
    
    # Save report to file
    report_file = "security_scan_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(issues, f, indent=2)
    
    print(f"📊 Detailed report saved to: {report_file}\n")
