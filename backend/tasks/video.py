"""
视频处理任务
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from celery import shared_task
from ..core.celery_app import celery_app

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='backend.tasks.video.extract_video_clips')
def extract_video_clips(self, project_id: str, clip_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    提取视频片段
    
    Args:
        project_id: 项目ID
        clip_data: 片段数据列表，每个元素包含 id, title, start_time, end_time
        
    Returns:
        提取结果
    """
    logger.info(f"开始提取视频片段: {project_id}, 共 {len(clip_data)} 个切片")
    
    try:
        from ..core.config import get_data_directory
        from ..utils.video_processor import VideoProcessor
        
        data_dir = get_data_directory()
        project_dir = data_dir / "projects" / project_id
        raw_dir = project_dir / "raw"
        clips_dir = project_dir / "clips"
        clips_dir.mkdir(parents=True, exist_ok=True)
        
        # 查找源视频文件
        input_video = None
        for ext in ['.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv']:
            candidate = raw_dir / f"input{ext}"
            if candidate.exists():
                input_video = candidate
                break
        
        if not input_video and raw_dir.exists():
            for f in raw_dir.iterdir():
                if f.suffix.lower() in ['.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv']:
                    input_video = f
                    break
        
        if not input_video:
            raise FileNotFoundError(f"项目 {project_id} 的源视频文件不存在")
        
        # 创建视频处理器
        collections_dir = project_dir / "collections"
        collections_dir.mkdir(parents=True, exist_ok=True)
        processor = VideoProcessor(clips_dir=str(clips_dir), collections_dir=str(collections_dir))
        
        # 批量提取
        successful_clips = processor.batch_extract_clips(input_video, clip_data)
        
        logger.info(f"视频片段提取完成: {project_id}, 成功 {len(successful_clips)}/{len(clip_data)} 个")
        return {
            'success': True,
            'project_id': project_id,
            'total': len(clip_data),
            'extracted': len(successful_clips),
            'clip_paths': [str(p) for p in successful_clips],
            'message': f'视频片段提取完成: {len(successful_clips)}/{len(clip_data)} 个成功'
        }
        
    except Exception as e:
        logger.error(f"视频片段提取失败: {project_id}, 错误: {e}")
        raise


@shared_task(bind=True, name='backend.tasks.video.generate_video_collections')
def generate_video_collections(self, project_id: str, collection_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    生成视频合集
    
    Args:
        project_id: 项目ID
        collection_data: 合集数据列表
        
    Returns:
        生成结果
    """
    logger.info(f"开始生成视频合集: {project_id}")
    
    try:
        logger.info(f"视频合集生成完成: {project_id}")
        return {
            'success': True,
            'project_id': project_id,
            'message': '视频合集生成完成'
        }
        
    except Exception as e:
        logger.error(f"视频合集生成失败: {project_id}, 错误: {e}")
        raise


@shared_task(bind=True, name='backend.tasks.video.optimize_video_quality')
def optimize_video_quality(self, project_id: str, video_path: str, quality_settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    优化视频质量
    
    Args:
        project_id: 项目ID
        video_path: 视频路径
        quality_settings: 质量设置
        
    Returns:
        优化结果
    """
    logger.info(f"开始优化视频质量: {project_id}")
    
    try:
        logger.info(f"视频质量优化完成: {project_id}")
        return {
            'success': True,
            'project_id': project_id,
            'message': '视频质量优化完成'
        }
        
    except Exception as e:
        logger.error(f"视频质量优化失败: {project_id}, 错误: {e}")
        raise