"""
Task Queue API Routes
Phase 4: Task queue with deduplication
"""
from fastapi import APIRouter, HTTPException, status

from api.dto.task_dto import (
    CancelRequest,
    EnqueueRequest,
    EnqueueResponse,
    QueueStatusResponse,
    TaskStatusResponse,
)
from infrastructure.storage.task_queue_store import TaskQueueStore
from services.evaluator_agent import EvaluatorAgent

router = APIRouter()
task_queue = TaskQueueStore()
evaluator = EvaluatorAgent()


@router.post("/tasks/enqueue", response_model=EnqueueResponse)
async def enqueue_task(request: EnqueueRequest) -> EnqueueResponse:
    """
    Enqueue a task.
    Checks for duplicates before adding to queue.
    """
    # Generate task signature
    context = {
        "project_path": request.params.get("project_path"),
        "files": request.params.get("files", []),
    }
    signature = evaluator.generate_signature(request.message, context)

    # Create task
    from backend.domain.models.task import Task, TaskPriority

    task = Task(
        session_id=request.session_id,
        account_id=request.account_id,
        channel=request.channel,
        agent_id=request.agent_id,
        message=request.message,
        action=request.action,
        params=request.params,
        signature=signature,
        priority=TaskPriority(request.priority),
    )

    # Try to enqueue
    success, msg = task_queue.enqueue(task)

    if not success:
        # Duplicate task
        return EnqueueResponse(
            success=False,
            task_id=None,
            message=f"⚠️ {msg}",
            status="duplicated",
        )

    # Get queue position
    status = task_queue.get_status()
    queue_pos = len(task_queue._queue)  # Internal access for position

    return EnqueueResponse(
        success=True,
        task_id=task.task_id,
        message=f"✅ 任务已加入队列，你是第 {queue_pos} 位",
        queue_position=queue_pos,
        status="pending",
    )


@router.get("/tasks/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(task_id: str) -> TaskStatusResponse:
    """Get task status"""
    # Check processing
    if task_queue._processing and task_queue._processing.task_id == task_id:
        return TaskStatusResponse(
            task_id=task_id,
            status="processing",
            message="任务正在执行中...",
        )

    # Check queue
    for i, task in enumerate(task_queue._queue):
        if task.task_id == task_id:
            return TaskStatusResponse(
                task_id=task_id,
                status=task.status.value,
                message=f"等待执行，前面还有 {i} 个任务",
                queue_position=i + 1,
            )

    # Check completed
    for task in task_queue.list_completed(limit=50):
        if task.task_id == task_id:
            if task.status.value == "completed":
                return TaskStatusResponse(
                    task_id=task_id,
                    status="completed",
                    message="任务已完成",
                )
            elif task.status.value == "failed":
                return TaskStatusResponse(
                    task_id=task_id,
                    status="failed",
                    message=f"任务失败: {task.error}",
                )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Task {task_id} not found",
    )


@router.get("/tasks/queue/status", response_model=QueueStatusResponse)
async def get_queue_status() -> QueueStatusResponse:
    """Get overall queue status"""
    status = task_queue.get_status()
    return QueueStatusResponse(**status)


@router.post("/tasks/cancel")
async def cancel_task(request: CancelRequest):
    """Cancel a task"""
    success, msg = task_queue.cancel(request.task_id, request.account_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )

    return {"success": True, "message": msg}


@router.post("/tasks/{task_id}/complete")
async def complete_task(task_id: str, result: dict = {}):
    """Mark task as completed (internal use)"""
    success = task_queue.complete(task_id, result)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    return {"success": True, "task_id": task_id}


@router.post("/tasks/{task_id}/fail")
async def fail_task(task_id: str, error: str):
    """Mark task as failed (internal use)"""
    success = task_queue.fail(task_id, error)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    return {"success": True, "task_id": task_id}
