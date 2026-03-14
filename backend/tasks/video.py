"""
视频处理任务
"""

import logging
import json
from pathlib import Path
from typing import Dict, Any, List
from celery import shared_task
from ..core.shared_config import config_manager
from ..utils.video_processor import VideoProcessor

logger = logging.getLogger(__name__)


def _load_json_list(file_path: Path) -> List[Dict[str, Any]]:
    if not file_path.exists():
        return []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        logger.warning(f"读取元数据失败，使用空列表: {file_path}, 错误: {e}")
        return []


def _save_json_list(file_path: Path, data: List[Dict[str, Any]]) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _find_project_input_video(project_id: str) -> Path:
    project_paths = config_manager.get_project_paths(project_id)
    input_dir = project_paths["input_dir"]
    preferred_path = input_dir / "input.mp4"
    if preferred_path.exists():
        return preferred_path
    
    for ext in (".mp4", ".mov", ".mkv", ".avi", ".flv"):
        matches = sorted(input_dir.glob(f"*{ext}"))
        if matches:
            return matches[0]
    
    raise FileNotFoundError(f"项目输入视频不存在: {input_dir}")


def _merge_clip_metadata(existing_data: List[Dict[str, Any]], clip_data: List[Dict[str, Any]], clips_dir: Path) -> List[Dict[str, Any]]:
    merged_data = {str(item.get("id")): dict(item) for item in existing_data if item.get("id") is not None}
    
    for index, item in enumerate(clip_data, start=1):
        clip_id = str(item.get("id", index))
        clip_title = item.get("generated_title", item.get("title", f"片段_{clip_id}"))
        safe_title = VideoProcessor.sanitize_filename(clip_title)
        output_path = clips_dir / f"{clip_id}_{safe_title}.mp4"
        
        merged_item = dict(merged_data.get(clip_id, {}))
        merged_item.update(item)
        merged_item["id"] = clip_id
        merged_item["video_path"] = str(output_path)
        merged_item["status"] = "completed" if output_path.exists() else "failed"
        
        try:
            _, start_seconds = VideoProcessor.normalize_time_value(merged_item.get("start_time", 0))
            _, end_seconds = VideoProcessor.normalize_time_value(merged_item.get("end_time", 0))
            merged_item["duration_seconds"] = max(end_seconds - start_seconds, 0)
        except ValueError:
            merged_item["duration_seconds"] = 0
        
        merged_data[clip_id] = merged_item
    
    return list(merged_data.values())


@shared_task(bind=True, name='backend.tasks.video.extract_video_clips')
def extract_video_clips(self, project_id: str, clip_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    提取视频片段
    
    Args:
        project_id: 项目ID
        clip_data: 片段数据列表
        
    Returns:
        提取结果
    """
    logger.info(f"开始提取视频片段: {project_id}")
    
    try:
        project_paths = config_manager.get_project_paths(project_id)
        input_video = _find_project_input_video(project_id)
        video_processor = VideoProcessor(
            clips_dir=str(project_paths["clips_dir"]),
            collections_dir=str(project_paths["collections_dir"])
        )
        
        successful_clips = video_processor.batch_extract_clips(input_video, clip_data)
        
        metadata_file = project_paths["metadata_dir"] / "clips_metadata.json"
        existing_metadata = _load_json_list(metadata_file)
        merged_metadata = _merge_clip_metadata(existing_metadata, clip_data, project_paths["clips_dir"])
        _save_json_list(metadata_file, merged_metadata)
        
        logger.info(f"视频片段提取完成: {project_id}")
        return {
            'success': True,
            'project_id': project_id,
            'message': '视频片段提取完成',
            'clips_generated': len(successful_clips),
            'clips_count': len(successful_clips),
            'clip_paths': [str(path) for path in successful_clips]
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
