# CLI Usage Guide

The Code Review & Documentation Agent provides a comprehensive command-line interface for analyzing codebases, managing analysis sessions, and viewing results.

## Installation

After installing the package, the CLI is available as the `code-review` command:

```bash
pip install -e .
```

Or run directly with Python:

```bash
python -m api.cli
```

## Quick Start

Analyze a codebase with default settings:

```bash
code-review analyze --path ./src
```

## Commands

### analyze

Analyze a codebase for quality issues and generate documentation.

**Usage:**
```bash
code-review analyze --path <path> [OPTIONS]
```

**Options:**
- `--path PATH` (required): Path to codebase to analyze
- `--config FILE`: Path to configuration file (YAML or JSON)
- `--output DIR`: Output directory for reports (default: ./demo_docs)
- `--depth CHOICE`: Analysis depth: quick, standard, or deep (default: standard)
- `--parallel/--no-parallel`: Enable/disable parallel processing (default: enabled)
- `--file-patterns PATTERN`: File patterns to include (can be specified multiple times)
- `--exclude-patterns PATTERN`: Patterns to exclude (can be specified multiple times)
- `--project-id ID`: Project identifier for Memory Bank patterns

**Examples:**

Basic analysis:
```bash
code-review analyze --path ./src
```

With configuration file:
```bash
code-review analyze --path ./src --config analysis.yaml
```

Deep analysis with custom output:
```bash
code-review analyze --path ./src --depth deep --output ./reports
```

Filter specific files:
```bash
code-review analyze --path ./src \
  --file-patterns "*.py" \
  --file-patterns "*.js" \
  --exclude-patterns "tests/**"
```

### status

Check the status of an analysis session.

**Usage:**
```bash
code-review status <session-id> [OPTIONS]
```

**Options:**
- `--verbose`: Show detailed status information

**Examples:**

Basic status:
```bash
code-review status abc123-def456-ghi789
```

Detailed status:
```bash
code-review status abc123-def456-ghi789 --verbose
```

### pause

Pause a running analysis session.

**Usage:**
```bash
code-review pause <session-id> [OPTIONS]
```

**Options:**
- `--force`: Force pause even if session is not running

**Examples:**

Pause analysis:
```bash
code-review pause abc123-def456-ghi789
```

Force pause:
```bash
code-review pause abc123-def456-ghi789 --force
```

### resume

Resume a paused analysis session.

**Usage:**
```bash
code-review resume <session-id> [OPTIONS]
```

**Options:**
- `--project-id ID`: Project identifier for Memory Bank patterns

**Examples:**

Resume analysis:
```bash
code-review resume abc123-def456-ghi789
```

Resume with project ID:
```bash
code-review resume abc123-def456-ghi789 --project-id my-project
```

### history

Show history of previous analyses.

**Usage:**
```bash
code-review history [OPTIONS]
```

**Options:**
- `--status-filter CHOICE`: Filter by status: running, paused, completed, or failed
- `--limit N`: Maximum number of sessions to display (default: 20)
- `--verbose`: Show detailed information for each session

**Examples:**

Show all history:
```bash
code-review history
```

Show only completed analyses:
```bash
code-review history --status-filter completed
```

Show detailed history:
```bash
code-review history --verbose --limit 10
```

### examples

Show usage examples and help.

**Usage:**
```bash
code-review examples
```

## Configuration Files

The CLI supports both YAML and JSON configuration files for advanced settings.

### YAML Configuration Example

```yaml
# analysis.yaml
target_path: ./src

file_patterns:
  - "*.py"
  - "*.js"
  - "*.ts"

exclude_patterns:
  - "node_modules/**"
  - "venv/**"
  - "__pycache__/**"

coding_standards:
  max_complexity: 10
  max_line_length: 100
  min_maintainability: 65
  
  naming:
    functions: "snake_case"
    classes: "PascalCase"
    constants: "UPPER_CASE"
  
  security:
    check_sql_injection: true
    check_hardcoded_secrets: true
    check_unsafe_deserialization: true
  
  documentation:
    require_docstrings: true
    require_type_hints: true

analysis_depth: standard
enable_parallel: true
```

### JSON Configuration Example

```json
{
  "target_path": "./src",
  "file_patterns": ["*.py", "*.js", "*.ts"],
  "exclude_patterns": ["node_modules/**", "venv/**"],
  "coding_standards": {
    "max_complexity": 10,
    "max_line_length": 100
  },
  "analysis_depth": "standard",
  "enable_parallel": true
}
```

## Analysis Depth Options

### Quick
- Fast analysis with basic checks
- Suitable for rapid feedback during development
- Checks: basic syntax, simple complexity metrics

### Standard (Default)
- Balanced analysis with comprehensive checks
- Recommended for most use cases
- Checks: complexity, duplication, security, naming conventions

### Deep
- Comprehensive analysis with all checks
- Best for thorough code reviews
- Checks: all standard checks plus advanced pattern detection

## Output and Reports

Analysis results are displayed in the terminal with:
- Summary statistics (files analyzed, issues found, quality score)
- Issue breakdown by severity
- Top improvement suggestions

When using the `--output` option, a detailed JSON report is saved containing:
- Complete file analyses
- All identified issues with locations
- Suggestions with code examples
- Quality metrics and trends
- Documentation artifacts

## Session Management

The CLI supports pause/resume functionality for long-running analyses:

1. **Start an analysis:**
   ```bash
   code-review analyze --path ./large-codebase
   # Returns: Session ID: abc123-def456-ghi789
   ```

2. **Check progress:**
   ```bash
   code-review status abc123-def456-ghi789
   ```

3. **Pause if needed:**
   ```bash
   code-review pause abc123-def456-ghi789
   ```

4. **Resume later:**
   ```bash
   code-review resume abc123-def456-ghi789
   ```

The system automatically detects files modified during the pause and re-analyzes them.

## Project Tracking

Use the `--project-id` option to enable consistent pattern tracking across analyses:

```bash
code-review analyze --path ./src --project-id my-project
```

This allows the Memory Bank to:
- Learn project-specific conventions
- Provide consistent recommendations
- Track quality trends over time
- Prioritize project patterns over generic best practices

## Tips and Best Practices

### Performance Optimization

1. **Use file patterns to focus analysis:**
   ```bash
   code-review analyze --path ./src --file-patterns "*.py"
   ```

2. **Exclude unnecessary directories:**
   ```bash
   code-review analyze --path . \
     --exclude-patterns "node_modules/**" \
     --exclude-patterns "venv/**" \
     --exclude-patterns "build/**"
   ```

3. **Enable parallel processing (default):**
   ```bash
   code-review analyze --path ./src --parallel
   ```

### Configuration Management

1. **Create project-specific configs:**
   ```bash
   # Save as .code-review.yaml in project root
   code-review analyze --path ./src --config .code-review.yaml
   ```

2. **Use different configs for different scenarios:**
   ```bash
   # Quick check during development
   code-review analyze --path ./src --config quick.yaml
   
   # Thorough review before release
   code-review analyze --path ./src --config thorough.yaml
   ```

### Session Management

1. **Always save session IDs for long analyses:**
   ```bash
   code-review analyze --path ./large-codebase > analysis.log
   # Extract session ID from log for later use
   ```

2. **Use history to find previous sessions:**
   ```bash
   code-review history --status-filter completed
   ```

3. **Clean up old sessions periodically:**
   The system automatically manages session cleanup, but you can manually review:
   ```bash
   code-review history --verbose
   ```

## Troubleshooting

### Command Not Found

If `code-review` command is not found after installation:

```bash
# Use Python module syntax instead
python -m api.cli --help

# Or reinstall in editable mode
pip install -e .
```

### Configuration File Errors

If configuration file fails to load:

1. Check file format (YAML or JSON)
2. Validate syntax using online validators
3. Ensure all required fields are present
4. Check file permissions

### Analysis Failures

If analysis fails:

1. Check that the target path exists and is accessible
2. Verify file patterns match actual files
3. Ensure sufficient disk space for reports
4. Check logs for specific error messages

### Session Not Found

If a session cannot be found:

1. Verify the session ID is correct
2. Check if session was cleaned up (old sessions are auto-deleted)
3. Use `code-review history` to list available sessions

## Getting Help

Show help for any command:

```bash
code-review --help
code-review analyze --help
code-review status --help
```

View usage examples:

```bash
code-review examples
```

## Integration with CI/CD

The CLI can be integrated into CI/CD pipelines. See the main documentation for:
- GitHub Actions integration
- GitLab CI integration
- Jenkins integration
- Exit code handling for build failures

## Related Documentation

- [Installation Guide](INSTALLATION.md)
- [Quick Start Guide](QUICK_START.md)
- [API Documentation](api/README.md)
- [Session Management](SESSION_MANAGEMENT.md)
