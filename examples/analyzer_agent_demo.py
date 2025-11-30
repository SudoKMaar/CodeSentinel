"""
Demo script for the Analyzer Agent.

This script demonstrates the capabilities of the AnalyzerAgent including:
- Cyclomatic complexity calculation
- Code duplication detection
- Security vulnerability detection
- Error handling detection
- Parallel file processing
"""

from agents.analyzer_agent import AnalyzerAgent


def demo_complexity_analysis():
    """Demonstrate complexity analysis."""
    print("=" * 60)
    print("DEMO: Complexity Analysis")
    print("=" * 60)
    
    # Simple function with low complexity
    simple_code = """def calculate_sum(a, b):
    return a + b
"""
    
    # Complex function with high complexity
    complex_code = """def process_data(data, options):
    if not data:
        return None
    
    result = []
    for item in data:
        if item > 0:
            if options.get('double'):
                result.append(item * 2)
            elif options.get('triple'):
                result.append(item * 3)
            else:
                result.append(item)
        elif item < 0:
            if options.get('abs'):
                result.append(abs(item))
            else:
                result.append(0)
        else:
            result.append(item)
    
    return result
"""
    
    analyzer = AnalyzerAgent()
    
    print("\n1. Simple function:")
    result = analyzer.analyze_file("simple.py", simple_code)
    if result:
        for func in result.functions:
            print(f"   Function: {func.name}")
            print(f"   Complexity: {func.complexity}")
    
    print("\n2. Complex function:")
    result = analyzer.analyze_file("complex.py", complex_code)
    if result:
        for func in result.functions:
            print(f"   Function: {func.name}")
            print(f"   Complexity: {func.complexity}")
        
        print(f"\n   Issues found: {len(result.issues)}")
        for issue in result.issues:
            print(f"   - {issue.severity}: {issue.description}")


def demo_security_analysis():
    """Demonstrate security vulnerability detection."""
    print("\n" + "=" * 60)
    print("DEMO: Security Vulnerability Detection")
    print("=" * 60)
    
    # Code with SQL injection vulnerability
    sql_injection_code = """def get_user(user_id):
    query = "SELECT * FROM users WHERE id = %s" % user_id
    cursor.execute(query)
    return cursor.fetchone()
"""
    
    # Code with hardcoded secrets
    hardcoded_secrets_code = """def connect_to_api():
    api_key = "PLACEHOLDER_API_KEY_HERE"  # DEMO ONLY
    password = "super_secret_password_123"
    return authenticate(api_key, password)
"""
    
    analyzer = AnalyzerAgent()
    
    print("\n1. SQL Injection vulnerability:")
    result = analyzer.analyze_file("sql.py", sql_injection_code)
    if result:
        security_issues = [i for i in result.issues if i.category == 'security']
        print(f"   Security issues found: {len(security_issues)}")
        for issue in security_issues:
            print(f"   - {issue.severity}: {issue.description}")
            print(f"     Suggestion: {issue.suggestion}")
    
    print("\n2. Hardcoded secrets:")
    result = analyzer.analyze_file("secrets.py", hardcoded_secrets_code)
    if result:
        security_issues = [i for i in result.issues if i.category == 'security']
        print(f"   Security issues found: {len(security_issues)}")
        for issue in security_issues:
            print(f"   - {issue.severity}: {issue.description}")


def demo_error_handling_analysis():
    """Demonstrate error handling detection."""
    print("\n" + "=" * 60)
    print("DEMO: Error Handling Detection")
    print("=" * 60)
    
    # Code without error handling
    no_error_handling = """def read_config(path):
    with open(path, 'r') as f:
        return f.read()
"""
    
    # Code with proper error handling
    with_error_handling = """def read_config(path):
    try:
        with open(path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"Error reading config: {e}")
        return None
"""
    
    analyzer = AnalyzerAgent()
    
    print("\n1. Without error handling:")
    result = analyzer.analyze_file("no_error.py", no_error_handling)
    if result:
        error_issues = [i for i in result.issues if i.category == 'error_handling']
        print(f"   Error handling issues: {len(error_issues)}")
        for issue in error_issues:
            print(f"   - {issue.description}")
            print(f"     Suggestion: {issue.suggestion}")
    
    print("\n2. With proper error handling:")
    result = analyzer.analyze_file("with_error.py", with_error_handling)
    if result:
        error_issues = [i for i in result.issues if i.category == 'error_handling']
        print(f"   Error handling issues: {len(error_issues)}")


def demo_parallel_processing():
    """Demonstrate parallel file processing."""
    print("\n" + "=" * 60)
    print("DEMO: Parallel File Processing")
    print("=" * 60)
    
    files = [
        ("file1.py", "def func1():\n    return 1\n"),
        ("file2.py", "def func2():\n    return 2\n"),
        ("file3.py", "def func3():\n    return 3\n"),
        ("file4.py", "def func4():\n    return 4\n"),
        ("file5.py", "def func5():\n    return 5\n"),
    ]
    
    analyzer = AnalyzerAgent(max_workers=3)
    
    print(f"\n   Processing {len(files)} files in parallel...")
    results = analyzer.analyze_files_parallel(files)
    
    print(f"   Successfully analyzed: {len(results)} files")
    for result in results:
        print(f"   - {result.file_path}: {len(result.functions)} function(s)")


def demo_metrics_calculation():
    """Demonstrate metrics calculation."""
    print("\n" + "=" * 60)
    print("DEMO: Code Metrics Calculation")
    print("=" * 60)
    
    code = """# This is a well-documented module
# It demonstrates metrics calculation

def calculate_average(numbers):
    \"\"\"Calculate the average of a list of numbers.\"\"\"
    if not numbers:
        return 0
    
    total = sum(numbers)
    count = len(numbers)
    return total / count


def find_max(numbers):
    \"\"\"Find the maximum value in a list.\"\"\"
    if not numbers:
        return None
    
    max_val = numbers[0]
    for num in numbers:
        if num > max_val:
            max_val = num
    
    return max_val
"""
    
    analyzer = AnalyzerAgent()
    result = analyzer.analyze_file("metrics.py", code)
    
    if result:
        print("\n   File Metrics:")
        print(f"   - Lines of code: {result.metrics.lines_of_code}")
        print(f"   - Comment ratio: {result.metrics.comment_ratio:.2%}")
        print(f"   - Cyclomatic complexity: {result.metrics.cyclomatic_complexity}")
        print(f"   - Maintainability index: {result.metrics.maintainability_index:.2f}")
        
        print(f"\n   Functions found: {len(result.functions)}")
        for func in result.functions:
            print(f"   - {func.name}: complexity={func.complexity}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("ANALYZER AGENT DEMONSTRATION")
    print("=" * 60)
    
    demo_complexity_analysis()
    demo_security_analysis()
    demo_error_handling_analysis()
    demo_parallel_processing()
    demo_metrics_calculation()
    
    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)
