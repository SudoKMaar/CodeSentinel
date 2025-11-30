# API Documentation

The Code Review & Documentation Agent provides a RESTful API for programmatic access to code analysis functionality. This API is designed for integration with CI/CD pipelines, development tools, and custom workflows.

## Table of Contents

- [Getting Started](#getting-started)
- [Authentication](#authentication)
- [Endpoints](#endpoints)
- [Request/Response Models](#requestresponse-models)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Examples](#examples)
- [OpenAPI Specification](#openapi-specification)

## Getting Started

### Starting the API Server

Start the API server using uvicorn:

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

For production deployment with multiple workers:

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Base URL

When running locally:
```
http://localhost:8000
```

### Interactive Documentation

Once the server is running, access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Authentication

The API supports optional API key authentication. If configured, include the API key in the request header:

```
X-API-Key: your-api-key-here
```

### Configuring API Key

Set the API key in your environment:

```bash
export API_KEY=your-secret-key
```

Or in `.env` file:

```
API_KEY=your-secret-key
```

## Endpoints

### Health Check

#### GET /

Root endpoint providing basic service information.

**Response:**
```json
{
  "name": "Code Review & Documentation Agent",
  "version": "0.1.0",
  "status": "running"
}
```

#### GET /health

Health check endpoint for monitoring.

**Response:**
```json
{
  "status": "healthy"
}
```

---

### Analysis Operations

#### POST /analyze

Trigger a new code analysis.

**Request Body:**
```json
{
  "codebase_path": "./src",
  "file_patterns": ["*.py", "*.js", "*.ts"],
  "exclude_patterns": ["node_modules/**", "venv/**"],
  "coding_standards": {
    "max_complexity": 10,
    "max_line_length": 100
  },
  "analysis_depth": "standard",
  "enable_parallel": true,
  "webhook_url": "https://example.com/webhook",
  "project_id": "my-project",
  "pr_mode": false,
  "base_ref": "origin/main",
  "head_ref": "HEAD",
  "output_format": "json",
  "fail_on_critical": false,
  "fail_on_high": false
}
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `codebase_path` | string | Yes | Path to the codebase to analyze |
| `file_patterns` | array[string] | No | File patterns to include (default: common source files) |
| `exclude_patterns` | array[string] | No | Patterns to exclude (default: common build/dependency dirs) |
| `coding_standards` | object | No | Project-specific coding standards |
| `analysis_depth` | string | No | Analysis depth: 'quick', 'standard', or 'deep' (default: 'standard') |
| `enable_parallel` | boolean | No | Enable parallel processing (default: true) |
| `webhook_url` | string | No | Webhook URL for completion notifications |
| `project_id` | string | No | Project identifier for Memory Bank patterns |
| `pr_mode` | boolean | No | Enable PR mode to analyze only changed files (default: false) |
| `base_ref` | string | No | Base Git reference for PR mode (default: 'origin/main') |
| `head_ref` | string | No | Head Git reference for PR mode (default: 'HEAD') |
| `output_format` | string | No | Output format: 'json' or 'sarif' (default: 'json') |
| `fail_on_critical` | boolean | No | Return error if critical issues found (default: false) |
| `fail_on_high` | boolean | No | Return error if high severity issues found (default: false) |

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "message": "Analysis started successfully"
}
```

**Status Codes:**
- `200 OK`: Analysis started successfully
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Missing API key
- `403 Forbidden`: Invalid API key

---

#### GET /status/{session_id}

Get the status of an analysis session.

**Path Parameters:**
- `session_id` (string, required): The session identifier

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "progress": 0.65,
  "processed_count": 65,
  "pending_count": 35,
  "message": "Analysis running"
}
```

**Status Values:**
- `running`: Analysis is in progress
- `paused`: Analysis has been paused
- `completed`: Analysis finished successfully
- `failed`: Analysis encountered an error

**Status Codes:**
- `200 OK`: Status retrieved successfully
- `404 Not Found`: Session not found

---

#### POST /pause/{session_id}

Pause a running analysis session.

**Path Parameters:**
- `session_id` (string, required): The session identifier

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "paused",
  "message": "Analysis paused successfully"
}
```

**Status Codes:**
- `200 OK`: Analysis paused successfully
- `400 Bad Request`: Session is not running
- `404 Not Found`: Session not found

---

#### POST /resume/{session_id}

Resume a paused analysis session.

**Path Parameters:**
- `session_id` (string, required): The session identifier

**Query Parameters:**
- `webhook_url` (string, optional): Webhook URL for completion notification

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "message": "Analysis resumed successfully"
}
```

**Status Codes:**
- `200 OK`: Analysis resumed successfully
- `400 Bad Request`: Session is not paused
- `404 Not Found`: Session not found

---

#### GET /results/{session_id}

Get the results of a completed analysis.

**Path Parameters:**
- `session_id` (string, required): The session identifier

**Query Parameters:**
- `format` (string, optional): Output format ('json' or 'sarif', default: 'json')

**Response (JSON format):**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "timestamp": "2024-01-15T10:30:00Z",
  "codebase_path": "./src",
  "files_analyzed": 100,
  "results": {
    "file_analyses": [...],
    "quality_score": 85.5,
    "total_issues": 15,
    "issues_by_severity": {
      "critical": 0,
      "high": 2,
      "medium": 8,
      "low": 5
    }
  }
}
```

**Status Codes:**
- `200 OK`: Results retrieved successfully
- `400 Bad Request`: Analysis not completed
- `404 Not Found`: Session not found

---

#### GET /history

Get analysis history.

**Query Parameters:**
- `status_filter` (string, optional): Filter by status ('running', 'paused', 'completed', 'failed')
- `limit` (integer, optional): Maximum number of results (default: 50, max: 100)

**Response:**
```json
{
  "analyses": [
    {
      "session_id": "550e8400-e29b-41d4-a716-446655440000",
      "timestamp": "2024-01-15T10:30:00Z",
      "codebase_path": "./src",
      "status": "completed",
      "files_analyzed": 100,
      "quality_score": 85.5
    }
  ],
  "total": 1
}
```

**Status Codes:**
- `200 OK`: History retrieved successfully
- `400 Bad Request`: Invalid status filter

---

## Request/Response Models

### AnalysisRequest

```typescript
{
  codebase_path: string;              // Required
  file_patterns?: string[];           // Optional
  exclude_patterns?: string[];        // Optional
  coding_standards?: {                // Optional
    max_complexity?: number;
    max_line_length?: number;
    [key: string]: any;
  };
  analysis_depth?: "quick" | "standard" | "deep";  // Optional
  enable_parallel?: boolean;          // Optional
  webhook_url?: string;               // Optional
  project_id?: string;                // Optional
  pr_mode?: boolean;                  // Optional
  base_ref?: string;                  // Optional
  head_ref?: string;                  // Optional
  output_format?: "json" | "sarif";   // Optional
  fail_on_critical?: boolean;         // Optional
  fail_on_high?: boolean;             // Optional
}
```

### AnalysisResponse

```typescript
{
  session_id: string;
  status: "running" | "paused" | "completed" | "failed";
  message: string;
}
```

### StatusResponse

```typescript
{
  session_id: string;
  status: "running" | "paused" | "completed" | "failed";
  progress: number;        // 0.0 to 1.0
  processed_count: number;
  pending_count: number;
  message?: string;
}
```

### HistoryItem

```typescript
{
  session_id: string;
  timestamp: string;       // ISO 8601 format
  codebase_path: string;
  status: "running" | "paused" | "completed" | "failed";
  files_analyzed?: number;
  quality_score?: number;
}
```

---

## Error Handling

### Error Response Format

All errors follow a consistent format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common Error Codes

| Status Code | Description |
|-------------|-------------|
| 400 Bad Request | Invalid request parameters or malformed JSON |
| 401 Unauthorized | Missing API key when authentication is required |
| 403 Forbidden | Invalid API key |
| 404 Not Found | Resource (session) not found |
| 500 Internal Server Error | Server-side error during processing |

### Error Examples

**Invalid codebase path:**
```json
{
  "detail": "Codebase path does not exist: /invalid/path"
}
```

**Session not found:**
```json
{
  "detail": "Session not found: invalid-session-id"
}
```

**Invalid status filter:**
```json
{
  "detail": "Invalid status filter: invalid_status"
}
```

---

## Rate Limiting

Currently, the API does not enforce rate limiting. For production deployments, consider implementing rate limiting at the reverse proxy level (e.g., Nginx, API Gateway).

**Recommended limits:**
- 100 requests per minute per IP
- 10 concurrent analysis sessions per API key

---

## Examples

### Example 1: Basic Analysis

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "codebase_path": "./src",
    "analysis_depth": "standard"
  }'
```

### Example 2: Analysis with Custom Configuration

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "codebase_path": "./src",
    "file_patterns": ["*.py", "*.js"],
    "exclude_patterns": ["tests/**", "node_modules/**"],
    "coding_standards": {
      "max_complexity": 10,
      "max_line_length": 100
    },
    "analysis_depth": "deep",
    "project_id": "my-project"
  }'
```

### Example 3: PR Mode Analysis

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "codebase_path": ".",
    "pr_mode": true,
    "base_ref": "origin/main",
    "head_ref": "HEAD",
    "fail_on_critical": true
  }'
```

### Example 4: Check Status

```bash
curl http://localhost:8000/status/550e8400-e29b-41d4-a716-446655440000
```

### Example 5: Get Results

```bash
curl http://localhost:8000/results/550e8400-e29b-41d4-a716-446655440000?format=json
```

### Example 6: Get Results in SARIF Format

```bash
curl http://localhost:8000/results/550e8400-e29b-41d4-a716-446655440000?format=sarif \
  -o report.sarif.json
```

### Example 7: Pause Analysis

```bash
curl -X POST http://localhost:8000/pause/550e8400-e29b-41d4-a716-446655440000
```

### Example 8: Resume Analysis

```bash
curl -X POST http://localhost:8000/resume/550e8400-e29b-41d4-a716-446655440000
```

### Example 9: Get History

```bash
curl "http://localhost:8000/history?status_filter=completed&limit=10"
```

### Example 10: Analysis with Webhook

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "codebase_path": "./src",
    "webhook_url": "https://example.com/webhook",
    "analysis_depth": "standard"
  }'
```

---

## Webhook Notifications

When a `webhook_url` is provided, the API will send POST requests to that URL when the analysis completes or fails.

### Webhook Payload

**On Success:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "timestamp": "2024-01-15T10:30:00Z",
  "files_analyzed": 100,
  "total_issues": 15,
  "quality_score": 85.5,
  "codebase_path": "./src"
}
```

**On Failure:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "failed",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Webhook Security

For production use, implement webhook signature verification:

1. Generate a secret key
2. Include HMAC signature in webhook requests
3. Verify signature on receiving end

---

## OpenAPI Specification

The complete OpenAPI 3.0 specification is available at:

```
http://localhost:8000/openapi.json
```

You can use this specification to:
- Generate client libraries in various languages
- Import into API testing tools (Postman, Insomnia)
- Generate documentation
- Validate requests/responses

### Generating Client Libraries

Using OpenAPI Generator:

```bash
# Python client
openapi-generator-cli generate \
  -i http://localhost:8000/openapi.json \
  -g python \
  -o ./client-python

# TypeScript client
openapi-generator-cli generate \
  -i http://localhost:8000/openapi.json \
  -g typescript-axios \
  -o ./client-typescript

# Java client
openapi-generator-cli generate \
  -i http://localhost:8000/openapi.json \
  -g java \
  -o ./client-java
```

---

## Best Practices

### 1. Use Project IDs

Always provide a `project_id` for consistent pattern tracking:

```json
{
  "codebase_path": "./src",
  "project_id": "my-project"
}
```

### 2. Enable PR Mode for Pull Requests

Use PR mode in CI/CD to analyze only changed files:

```json
{
  "codebase_path": ".",
  "pr_mode": true,
  "base_ref": "origin/main",
  "head_ref": "HEAD"
}
```

### 3. Configure Webhooks

Use webhooks for asynchronous notifications:

```json
{
  "codebase_path": "./src",
  "webhook_url": "https://your-service.com/webhook"
}
```

### 4. Handle Long-Running Analyses

For large codebases:
1. Start analysis with POST /analyze
2. Poll GET /status/{session_id} for progress
3. Use pause/resume if needed
4. Retrieve results when status is "completed"

### 5. Use Appropriate Analysis Depth

- **Quick**: Fast feedback during development
- **Standard**: Balanced analysis for most use cases
- **Deep**: Comprehensive analysis for releases

### 6. Implement Retry Logic

Implement exponential backoff for transient failures:

```python
import time
import requests

def analyze_with_retry(payload, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.post(
                "http://localhost:8000/analyze",
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)
```

---

## Troubleshooting

### Connection Refused

**Problem**: Cannot connect to API server

**Solution**:
1. Verify server is running: `ps aux | grep uvicorn`
2. Check port is not in use: `lsof -i :8000`
3. Ensure correct host/port in request

### 401 Unauthorized

**Problem**: API key authentication failing

**Solution**:
1. Verify API key is set in environment
2. Include `X-API-Key` header in request
3. Check API key matches server configuration

### 404 Session Not Found

**Problem**: Session ID not found

**Solution**:
1. Verify session ID is correct
2. Check if session was cleaned up (old sessions auto-expire)
3. Use GET /history to list available sessions

### Analysis Stuck in "Running"

**Problem**: Analysis status remains "running" indefinitely

**Solution**:
1. Check server logs for errors
2. Verify codebase path is accessible
3. Check for resource constraints (memory, disk)
4. Consider pausing and resuming the session

---

## Related Documentation

- [CLI Usage Guide](../CLI_USAGE.md)
- [Installation Guide](../INSTALLATION.md)
- [Quick Start Guide](../QUICK_START.md)
- [Session Management](../SESSION_MANAGEMENT.md)

---

## Support

For issues, questions, or feature requests:
- GitHub Issues: [repository-url]/issues
- Documentation: [repository-url]/docs
- Email: support@example.com
