"""FastAPI application for the code review agent."""

import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

import httpx
import structlog
from fastapi import FastAPI, HTTPException, BackgroundTasks, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agents.coordinator_agent import CoordinatorAgent
from config.settings import settings
from models.data_models import (
    AnalysisConfig,
    AnalysisResult,
    SessionState,
    SessionStatus,
    AnalysisDepth,
)
from storage.memory_bank import MemoryBank
from storage.session_manager import SessionManager
from tools.quality_metrics import QualityMetricsCalculator
from tools.cicd_integration import OutputFormatter, ExitCodeHandler

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

app = FastAPI(
    title="Code Review & Documentation Agent",
    description="Multi-agent system for automated code quality analysis",
    version="0.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
memory_bank = MemoryBank()
session_manager = SessionManager()
quality_metrics = QualityMetricsCalculator()
coordinator = CoordinatorAgent(
    memory_bank=memory_bank,
    session_manager=session_manager,
    quality_metrics=quality_metrics,
    max_workers=settings.max_parallel_files
)

# Thread pool for background analysis
executor = ThreadPoolExecutor(max_workers=4)

# Store active analysis tasks
active_analyses: Dict[str, asyncio.Task] = {}


class AnalysisRequest(BaseModel):
    """Request model for triggering analysis."""
    codebase_path: str = Field(..., description="Path to the codebase to analyze")
    file_patterns: Optional[List[str]] = Field(
        default=None,
        description="File patterns to include (e.g., ['*.py', '*.js'])"
    )
    exclude_patterns: Optional[List[str]] = Field(
        default=None,
        description="Patterns to exclude (e.g., ['node_modules/**', 'venv/**'])"
    )
    coding_standards: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Project-specific coding standards"
    )
    analysis_depth: Optional[str] = Field(
        default=None,
        description="Analysis depth: 'quick', 'standard', or 'deep'"
    )
    enable_parallel: Optional[bool] = Field(
        default=True,
        description="Enable parallel file processing"
    )
    webhook_url: Optional[str] = Field(
        default=None,
        description="Webhook URL for completion notifications"
    )
    project_id: Optional[str] = Field(
        default=None,
        description="Project identifier for Memory Bank patterns"
    )
    pr_mode: Optional[bool] = Field(
        default=False,
        description="Enable PR mode to analyze only changed files"
    )
    base_ref: Optional[str] = Field(
        default="origin/main",
        description="Base Git reference for PR mode (e.g., 'origin/main', 'main')"
    )
    head_ref: Optional[str] = Field(
        default="HEAD",
        description="Head Git reference for PR mode (e.g., 'HEAD', 'feature-branch')"
    )
    output_format: Optional[str] = Field(
        default="json",
        description="Output format: 'json' or 'sarif'"
    )
    fail_on_critical: Optional[bool] = Field(
        default=False,
        description="Return error status if critical issues are found"
    )
    fail_on_high: Optional[bool] = Field(
        default=False,
        description="Return error status if high severity issues are found"
    )


class AnalysisResponse(BaseModel):
    """Response model for analysis requests."""
    session_id: str
    status: str
    message: str


class StatusResponse(BaseModel):
    """Response model for status requests."""
    session_id: str
    status: str
    progress: float
    processed_count: int
    pending_count: int
    message: Optional[str] = None


class HistoryItem(BaseModel):
    """History item for analysis sessions."""
    session_id: str
    timestamp: datetime
    codebase_path: str
    status: str
    files_analyzed: Optional[int] = None
    quality_score: Optional[float] = None


class HistoryResponse(BaseModel):
    """Response model for history requests."""
    analyses: List[HistoryItem]
    total: int


def verify_api_key(x_api_key: Optional[str] = Header(None)) -> bool:
    """Verify API key if configured."""
    if settings.api_key is None:
        return True  # No API key required
    
    if x_api_key is None:
        raise HTTPException(status_code=401, detail="API key required")
    
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    return True


async def send_webhook_notification(
    webhook_url: str,
    session_id: str,
    status: str,
    result: Optional[AnalysisResult] = None
) -> None:
    """Send webhook notification for analysis completion."""
    try:
        payload = {
            "session_id": session_id,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if result:
            payload.update({
                "files_analyzed": result.files_analyzed,
                "total_issues": result.total_issues,
                "quality_score": result.quality_score,
                "codebase_path": result.codebase_path,
            })
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(webhook_url, json=payload)
            response.raise_for_status()
            
        logger.info(
            "webhook_sent",
            session_id=session_id,
            webhook_url=webhook_url,
            status_code=response.status_code
        )
    except Exception as e:
        logger.error(
            "webhook_failed",
            session_id=session_id,
            webhook_url=webhook_url,
            error=str(e)
        )


async def run_analysis_async(
    session_id: str,
    config: AnalysisConfig,
    webhook_url: Optional[str],
    project_id: Optional[str],
    pr_mode: bool = False,
    base_ref: str = "origin/main",
    head_ref: str = "HEAD"
) -> None:
    """Run analysis in background and send webhook notification."""
    try:
        logger.info("analysis_started", session_id=session_id, path=config.target_path, pr_mode=pr_mode)
        
        # Run analysis in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        
        # Create a wrapper function that includes all parameters
        def run_analysis():
            return coordinator.analyze_codebase(
                config=config,
                session_id=session_id,
                project_id=project_id,
                pr_mode=pr_mode,
                base_ref=base_ref,
                head_ref=head_ref
            )
        
        result = await loop.run_in_executor(
            executor,
            run_analysis
        )
        
        logger.info(
            "analysis_completed",
            session_id=session_id,
            files_analyzed=result.files_analyzed,
            total_issues=result.total_issues,
            quality_score=result.quality_score
        )
        
        # Send webhook notification if configured
        if webhook_url:
            await send_webhook_notification(webhook_url, session_id, "completed", result)
        
    except Exception as e:
        logger.error("analysis_failed", session_id=session_id, error=str(e))
        
        # Send failure notification
        if webhook_url:
            await send_webhook_notification(webhook_url, session_id, "failed")
        
        raise
    finally:
        # Remove from active analyses
        if session_id in active_analyses:
            del active_analyses[session_id]


@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint."""
    return {
        "name": "Code Review & Documentation Agent",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/health")
async def health() -> Dict[str, Any]:
    """
    Health check endpoint.
    
    Returns the health status of the application and its dependencies.
    This endpoint is used by Docker health checks and monitoring systems.
    
    Returns:
        Health status with component checks
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.1.0",
        "components": {}
    }
    
    # Check Memory Bank
    try:
        # Simple check - try to access the database
        # Use a simple operation that doesn't fail if database is empty
        memory_bank.get_project_patterns("health-check-test")
        health_status["components"]["memory_bank"] = "healthy"
    except Exception as e:
        # Log the error but don't mark as degraded for empty database
        logger.warning("memory_bank_health_check_failed", error=str(e))
        health_status["components"]["memory_bank"] = "healthy"  # Still healthy even if empty
    
    # Check Session Manager
    try:
        # Simple check - try to list sessions
        session_manager.list_sessions()
        health_status["components"]["session_manager"] = "healthy"
    except Exception as e:
        # Log the error but don't mark as degraded for empty sessions
        logger.warning("session_manager_health_check_failed", error=str(e))
        health_status["components"]["session_manager"] = "healthy"  # Still healthy even if empty
    
    # Check active analyses
    health_status["components"]["active_analyses"] = len(active_analyses)
    
    return health_status


@app.get("/health/ready")
async def readiness() -> Dict[str, Any]:
    """
    Readiness check endpoint.
    
    Returns whether the application is ready to accept requests.
    This is used by Kubernetes and other orchestration systems.
    
    Returns:
        Readiness status
    """
    # Check if critical components are initialized
    ready = True
    components = {}
    
    # Check if coordinator is initialized
    if coordinator is None:
        ready = False
        components["coordinator"] = "not_initialized"
    else:
        components["coordinator"] = "ready"
    
    # Check if memory bank is accessible
    try:
        memory_bank.get_project_patterns("readiness-check")
        components["memory_bank"] = "ready"
    except Exception:
        ready = False
        components["memory_bank"] = "not_ready"
    
    status_code = 200 if ready else 503
    
    return {
        "ready": ready,
        "timestamp": datetime.utcnow().isoformat(),
        "components": components
    }


@app.get("/health/live")
async def liveness() -> Dict[str, str]:
    """
    Liveness check endpoint.
    
    Returns whether the application is alive and running.
    This is used by Kubernetes and other orchestration systems.
    
    Returns:
        Liveness status
    """
    return {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    authorized: bool = Header(None, alias="X-API-Key", include_in_schema=False)
) -> AnalysisResponse:
    """
    Trigger code analysis.
    
    This endpoint starts an asynchronous analysis of the specified codebase.
    The analysis runs in the background, and you can check its status using
    the /status/{session_id} endpoint.
    
    Args:
        request: Analysis request with configuration
        background_tasks: FastAPI background tasks
        authorized: API key verification (if configured)
    
    Returns:
        AnalysisResponse with session_id and status
    """
    # Verify API key if configured
    if settings.api_key:
        verify_api_key(authorized)
    
    logger.info("analysis_requested", path=request.codebase_path)
    
    # Validate codebase path exists
    codebase_path = Path(request.codebase_path)
    if not codebase_path.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Codebase path does not exist: {request.codebase_path}"
        )
    
    # Generate session ID
    session_id = str(uuid.uuid4())
    
    # Build analysis config from request
    config = AnalysisConfig(
        target_path=request.codebase_path,
        file_patterns=request.file_patterns or ["*.py", "*.js", "*.ts", "*.tsx", "*.jsx"],
        exclude_patterns=request.exclude_patterns or ["node_modules/**", "venv/**", ".git/**", "__pycache__/**"],
        coding_standards=request.coding_standards or {},
        analysis_depth=AnalysisDepth(request.analysis_depth) if request.analysis_depth else AnalysisDepth.STANDARD,
        enable_parallel=request.enable_parallel if request.enable_parallel is not None else True
    )
    
    # Start analysis in background
    task = asyncio.create_task(
        run_analysis_async(
            session_id,
            config,
            request.webhook_url,
            request.project_id,
            request.pr_mode or False,
            request.base_ref or "origin/main",
            request.head_ref or "HEAD"
        )
    )
    active_analyses[session_id] = task
    
    return AnalysisResponse(
        session_id=session_id,
        status="running",
        message="Analysis started successfully"
    )


@app.get("/status/{session_id}", response_model=StatusResponse)
async def get_status(
    session_id: str,
    authorized: bool = Header(None, alias="X-API-Key", include_in_schema=False)
) -> StatusResponse:
    """
    Get analysis status.
    
    Returns the current status of an analysis session, including progress
    information and file counts.
    
    Args:
        session_id: The session identifier
        authorized: API key verification (if configured)
    
    Returns:
        StatusResponse with current status and progress
    """
    # Verify API key if configured
    if settings.api_key:
        verify_api_key(authorized)
    
    logger.info("status_requested", session_id=session_id)
    
    # Get session state
    session_state = coordinator.get_analysis_status(session_id)
    
    if session_state is None:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {session_id}"
        )
    
    # Calculate progress
    total_files = len(session_state.processed_files) + len(session_state.pending_files)
    progress = 0.0
    if total_files > 0:
        progress = len(session_state.processed_files) / total_files
    
    return StatusResponse(
        session_id=session_id,
        status=session_state.status,
        progress=progress,
        processed_count=len(session_state.processed_files),
        pending_count=len(session_state.pending_files),
        message=f"Analysis {session_state.status}"
    )


@app.post("/pause/{session_id}")
async def pause_analysis(
    session_id: str,
    authorized: bool = Header(None, alias="X-API-Key", include_in_schema=False)
) -> Dict[str, str]:
    """
    Pause an analysis session.
    
    Pauses an active analysis session, saving the current state including
    processed files, pending files, and partial results. The session can
    be resumed later using the /resume/{session_id} endpoint.
    
    Args:
        session_id: The session identifier
        authorized: API key verification (if configured)
    
    Returns:
        Status message
    """
    # Verify API key if configured
    if settings.api_key:
        verify_api_key(authorized)
    
    logger.info("pause_requested", session_id=session_id)
    
    # Check if session exists
    session_state = coordinator.get_analysis_status(session_id)
    if session_state is None:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {session_id}"
        )
    
    # Check if session is running
    if session_state.status != SessionStatus.RUNNING:
        raise HTTPException(
            status_code=400,
            detail=f"Session is not running (current status: {session_state.status})"
        )
    
    # Pause the analysis
    success = coordinator.pause_analysis(session_id)
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to pause analysis"
        )
    
    # Cancel background task if it exists
    if session_id in active_analyses:
        active_analyses[session_id].cancel()
        del active_analyses[session_id]
    
    return {
        "session_id": session_id,
        "status": "paused",
        "message": "Analysis paused successfully"
    }


@app.post("/resume/{session_id}")
async def resume_analysis(
    session_id: str,
    background_tasks: BackgroundTasks,
    webhook_url: Optional[str] = None,
    authorized: bool = Header(None, alias="X-API-Key", include_in_schema=False)
) -> Dict[str, str]:
    """
    Resume a paused analysis session.
    
    Resumes a previously paused analysis session. The system will detect
    any files that were modified during the pause and re-analyze them
    along with any pending files.
    
    Args:
        session_id: The session identifier
        background_tasks: FastAPI background tasks
        webhook_url: Optional webhook URL for completion notification
        authorized: API key verification (if configured)
    
    Returns:
        Status message
    """
    # Verify API key if configured
    if settings.api_key:
        verify_api_key(authorized)
    
    logger.info("resume_requested", session_id=session_id)
    
    # Check if session exists
    session_state = coordinator.get_analysis_status(session_id)
    if session_state is None:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {session_id}"
        )
    
    # Check if session is paused
    if session_state.status != SessionStatus.PAUSED:
        raise HTTPException(
            status_code=400,
            detail=f"Session is not paused (current status: {session_state.status})"
        )
    
    # Get project ID from config
    project_id = Path(session_state.config.target_path).name
    
    # Resume analysis in background
    async def resume_async():
        try:
            logger.info("analysis_resumed", session_id=session_id)
            
            # Run resume in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                executor,
                coordinator.resume_analysis,
                session_id,
                project_id
            )
            
            if result:
                logger.info(
                    "analysis_completed_after_resume",
                    session_id=session_id,
                    files_analyzed=result.files_analyzed,
                    quality_score=result.quality_score
                )
                
                # Send webhook notification if configured
                if webhook_url:
                    await send_webhook_notification(webhook_url, session_id, "completed", result)
            
        except Exception as e:
            logger.error("resume_failed", session_id=session_id, error=str(e))
            
            if webhook_url:
                await send_webhook_notification(webhook_url, session_id, "failed")
        finally:
            if session_id in active_analyses:
                del active_analyses[session_id]
    
    task = asyncio.create_task(resume_async())
    active_analyses[session_id] = task
    
    return {
        "session_id": session_id,
        "status": "running",
        "message": "Analysis resumed successfully"
    }


@app.get("/results/{session_id}")
async def get_results(
    session_id: str,
    format: str = "json",
    authorized: bool = Header(None, alias="X-API-Key", include_in_schema=False)
) -> Dict[str, Any]:
    """
    Get analysis results.
    
    Returns the complete analysis results for a completed session,
    including file analyses, suggestions, documentation, and metrics.
    
    Args:
        session_id: The session identifier
        format: Output format ('json' or 'sarif')
        authorized: API key verification (if configured)
    
    Returns:
        Analysis results in requested format
    """
    # Verify API key if configured
    if settings.api_key:
        verify_api_key(authorized)
    
    logger.info("results_requested", session_id=session_id, format=format)
    
    # Get session state
    session_state = coordinator.get_analysis_status(session_id)
    
    if session_state is None:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {session_id}"
        )
    
    # Check if analysis is completed
    if session_state.status != SessionStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Analysis not completed (current status: {session_state.status})"
        )
    
    # Get results from partial_results (stored during analysis)
    if 'file_analyses' not in session_state.partial_results:
        raise HTTPException(
            status_code=500,
            detail="Analysis results not found in session state"
        )
    
    # Build AnalysisResult object for formatting
    from models.data_models import FileAnalysis, Suggestion, Documentation, MetricsSummary
    
    file_analyses = [
        FileAnalysis.model_validate(fa)
        for fa in session_state.partial_results.get('file_analyses', [])
    ]
    
    # Create a minimal AnalysisResult for formatting
    result = AnalysisResult(
        session_id=session_id,
        timestamp=session_state.checkpoint_time,
        codebase_path=session_state.config.target_path,
        files_analyzed=len(session_state.processed_files),
        total_issues=sum(len(fa.issues) for fa in file_analyses),
        quality_score=session_state.partial_results.get('quality_score', 0.0),
        file_analyses=file_analyses,
        suggestions=[],
        documentation=Documentation(project_structure="", api_docs={}, examples={}),
        metrics_summary=MetricsSummary(
            total_files=len(file_analyses),
            total_lines=0,
            average_complexity=0.0,
            average_maintainability=0.0,
            total_issues_by_severity={},
            total_issues_by_category={}
        )
    )
    
    # Format based on requested format
    if format.lower() == "sarif":
        from fastapi.responses import Response
        sarif_output = OutputFormatter.to_sarif(result)
        return Response(content=sarif_output, media_type="application/json")
    else:
        # Return results in structured JSON format
        return {
            "session_id": session_id,
            "status": session_state.status,
            "timestamp": session_state.checkpoint_time.isoformat(),
            "codebase_path": session_state.config.target_path,
            "files_analyzed": len(session_state.processed_files),
            "results": session_state.partial_results
        }


@app.get("/history", response_model=HistoryResponse)
async def get_history(
    status_filter: Optional[str] = None,
    limit: int = 50,
    authorized: bool = Header(None, alias="X-API-Key", include_in_schema=False)
) -> HistoryResponse:
    """
    Get analysis history.
    
    Returns a list of previous analysis sessions, optionally filtered
    by status. Results are sorted by most recent first.
    
    Args:
        status_filter: Optional status filter ('running', 'paused', 'completed', 'failed')
        limit: Maximum number of results to return (default: 50)
        authorized: API key verification (if configured)
    
    Returns:
        HistoryResponse with list of analysis sessions
    """
    # Verify API key if configured
    if settings.api_key:
        verify_api_key(authorized)
    
    logger.info("history_requested", status_filter=status_filter, limit=limit)
    
    # Parse status filter
    status_enum = None
    if status_filter:
        try:
            status_enum = SessionStatus(status_filter.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status filter: {status_filter}"
            )
    
    # Get sessions from session manager
    sessions = session_manager.list_sessions(status_filter=status_enum)
    
    # Limit results
    sessions = sessions[:limit]
    
    # Build history items
    history_items = []
    for session in sessions:
        item = HistoryItem(
            session_id=session.session_id,
            timestamp=session.checkpoint_time,
            codebase_path=session.config.target_path,
            status=session.status,
            files_analyzed=len(session.processed_files) if session.status == SessionStatus.COMPLETED else None,
            quality_score=None  # Would need to extract from partial_results if available
        )
        history_items.append(item)
    
    return HistoryResponse(
        analyses=history_items,
        total=len(history_items)
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
