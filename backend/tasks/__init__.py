"""
任务模块
包含所有异步任务定义
"""

from .processing import process_video_pipeline, process_single_step, retry_processing_step
from .video import extract_video_clips, generate_video_collections, optimize_video_quality
from .notification import send_processing_notification, send_error_notification, send_completion_notification
from .maintenance import cleanup_expired_tasks, health_check, backup_project_data
from .upload import upload_clip_task, upload_project_task
from .data_cleanup import cleanup_expired_data, check_data_consistency, cleanup_orphaned_data

__all__ = [
    # 处理任务
    'process_video_pipeline',
    'process_single_step',
    'retry_processing_step',
    
    # 视频任务
    'extract_video_clips',
    'generate_video_collections',
    'optimize_video_quality',
    
    # 通知任务
    'send_processing_notification',
    'send_error_notification',
    'send_completion_notification',
    
    # 维护任务
    'cleanup_expired_tasks',
    'health_check',
    'backup_project_data',
    
    # 数据清理任务
    'cleanup_expired_data',
    'check_data_consistency',
    'cleanup_orphaned_data',
    
    # 投稿任务
    'upload_clip_task',
    'upload_project_task',
] 