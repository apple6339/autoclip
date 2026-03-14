"""
处理编排器
负责协调流水线执行和Task状态管理
"""

import logging
import time
import sys
import json
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
from sqlalchemy.orm import Session

from backend.models.task import Task, TaskStatus, TaskType
from backend.repositories.task_repository import TaskRepository
from backend.services.config_manager import ProjectConfigManager, ProcessingStep
# from backend.services.pipeline_adapter import PipelineAdapter  # 临时注释，文件不存在
from backend.core.config import get_project_root
from backend.core.shared_config import config_manager as shared_config_manager

logger = logging.getLogger(__name__)

STEP_DEPENDENCIES = {
    ProcessingStep.STEP2_TIMELINE: [ProcessingStep.STEP1_OUTLINE],
    ProcessingStep.STEP3_SCORING: [ProcessingStep.STEP2_TIMELINE],
    ProcessingStep.STEP4_TITLE: [ProcessingStep.STEP3_SCORING],
    ProcessingStep.STEP5_CLUSTERING: [ProcessingStep.STEP4_TITLE],
    ProcessingStep.STEP6_VIDEO: [ProcessingStep.STEP5_CLUSTERING]
}

STEP_OUTPUT_CANDIDATES = {
    ProcessingStep.STEP1_OUTLINE: ["step1_outline.json", "step1_outlines.json"],
    ProcessingStep.STEP2_TIMELINE: ["step2_timeline.json"],
    ProcessingStep.STEP3_SCORING: ["step3_high_score_clips.json", "step3_scoring.json", "step3_all_scored.json"],
    ProcessingStep.STEP4_TITLE: ["step4_titles.json"],
    ProcessingStep.STEP5_CLUSTERING: ["step5_collections.json"],
    ProcessingStep.STEP6_VIDEO: ["clips_metadata.json", "step6_video_output.json"]
}

STEP_OUTPUT_REQUIREMENTS = {
    ProcessingStep.STEP1_OUTLINE: {"container_type": list},
    ProcessingStep.STEP2_TIMELINE: {"container_type": list},
    ProcessingStep.STEP3_SCORING: {"container_type": list},
    ProcessingStep.STEP4_TITLE: {"container_type": list},
    ProcessingStep.STEP5_CLUSTERING: {"container_type": list},
    ProcessingStep.STEP6_VIDEO: {"container_type": (list, dict)}
}

# 导入流水线步骤

try:
    from backend.pipeline.step1_outline import run_step1_outline
    from backend.pipeline.step2_timeline import run_step2_timeline
    from backend.pipeline.step3_scoring import run_step3_scoring
    from backend.pipeline.step4_title import run_step4_title
    from backend.pipeline.step5_clustering import run_step5_clustering
    from backend.pipeline.step6_video import run_step6_video
    logger.info("流水线模块导入成功")
except ImportError as e:
    logger.warning(f"无法导入流水线模块: {e}")
    # 定义占位符函数
    def run_step1_outline(**kwargs): 
        logger.warning("流水线模块未正确导入，使用占位符函数")
        # 生成模拟输出
        srt_path = kwargs.get('srt_path')
        output_path = kwargs.get('output_path')
        if output_path:
            import json
            from pathlib import Path
            # 确保output_path是Path对象
            if isinstance(output_path, str):
                output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            mock_output = {
                "outlines": [
                    {"topic": "测试话题1", "start_time": "00:00:00", "end_time": "00:00:05", "content": "测试内容1"},
                    {"topic": "测试话题2", "start_time": "00:00:05", "end_time": "00:00:10", "content": "测试内容2"}
                ],
                "status": "completed",
                "message": "占位符函数生成的模拟输出"
            }
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(mock_output, f, ensure_ascii=False, indent=2)
        return {"status": "skipped", "message": "流水线模块未正确导入"}
    
    def run_step2_timeline(**kwargs): 
        logger.warning("流水线模块未正确导入，使用占位符函数")
        # 生成模拟输出
        output_path = kwargs.get('output_path')
        if output_path:
            import json
            from pathlib import Path
            # 确保output_path是Path对象
            if isinstance(output_path, str):
                output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            mock_output = {
                "timeline": [
                    {"time": "00:00:00", "event": "开始"},
                    {"time": "00:00:05", "event": "话题1"},
                    {"time": "00:00:10", "event": "话题2"}
                ],
                "status": "completed",
                "message": "占位符函数生成的模拟输出"
            }
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(mock_output, f, ensure_ascii=False, indent=2)
        return {"status": "skipped", "message": "流水线模块未正确导入"}
    
    def run_step3_scoring(**kwargs): 
        logger.warning("流水线模块未正确导入，使用占位符函数")
        # 生成模拟输出
        output_path = kwargs.get('output_path')
        if output_path:
            import json
            from pathlib import Path
            # 确保output_path是Path对象
            if isinstance(output_path, str):
                output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            mock_output = {
                "scored_clips": [
                    {"clip_id": "1", "score": 0.8, "content": "高分内容1"},
                    {"clip_id": "2", "score": 0.7, "content": "高分内容2"}
                ],
                "status": "completed",
                "message": "占位符函数生成的模拟输出"
            }
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(mock_output, f, ensure_ascii=False, indent=2)
        return {"status": "skipped", "message": "流水线模块未正确导入"}
    
    def run_step4_title(**kwargs): 
        logger.warning("流水线模块未正确导入，使用占位符函数")
        # 生成模拟输出
        output_path = kwargs.get('output_path')
        if output_path:
            import json
            from pathlib import Path
            # 确保output_path是Path对象
            if isinstance(output_path, str):
                output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            mock_output = {
                "titles": [
                    {"clip_id": "1", "title": "测试标题1"},
                    {"clip_id": "2", "title": "测试标题2"}
                ],
                "status": "completed",
                "message": "占位符函数生成的模拟输出"
            }
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(mock_output, f, ensure_ascii=False, indent=2)
        return {"status": "skipped", "message": "流水线模块未正确导入"}
    
    def run_step5_clustering(**kwargs): 
        logger.warning("流水线模块未正确导入，使用占位符函数")
        # 生成模拟输出
        output_path = kwargs.get('output_path')
        if output_path:
            import json
            from pathlib import Path
            # 确保output_path是Path对象
            if isinstance(output_path, str):
                output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            mock_output = {
                "collections": [
                    {"collection_id": "1", "title": "测试合集1", "clips": ["1", "2"]},
                    {"collection_id": "2", "title": "测试合集2", "clips": ["3", "4"]}
                ],
                "status": "completed",
                "message": "占位符函数生成的模拟输出"
            }
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(mock_output, f, ensure_ascii=False, indent=2)
        return {"status": "skipped", "message": "流水线模块未正确导入"}
    
    def run_step6_video(**kwargs): 
        logger.warning("流水线模块未正确导入，使用占位符函数")
        # 生成模拟输出
        output_path = kwargs.get('output_path')
        if output_path:
            import json
            from pathlib import Path
            # 确保output_path是Path对象
            if isinstance(output_path, str):
                output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            mock_output = {
                "videos": [
                    {"clip_id": "1", "video_path": "output/clip_1.mp4"},
                    {"clip_id": "2", "video_path": "output/clip_2.mp4"}
                ],
                "status": "completed",
                "message": "占位符函数生成的模拟输出"
            }
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(mock_output, f, ensure_ascii=False, indent=2)
        return {"status": "skipped", "message": "流水线模块未正确导入"}


class ProcessingOrchestrator:
    """处理编排器，负责协调流水线执行和Task状态管理"""
    
    def __init__(self, project_id: str, task_id: str, db: Session):
        self.project_id = project_id
        self.task_id = task_id
        self.db = db
        
        # 初始化组件
        self.config_manager = ProjectConfigManager(project_id)
        # self.adapter = PipelineAdapter(db, task_id, project_id)  # 临时注释，文件不存在
        self.task_repo = TaskRepository(db)
        
        # 步骤映射
        self.step_functions = {
            ProcessingStep.STEP1_OUTLINE: run_step1_outline,
            ProcessingStep.STEP2_TIMELINE: run_step2_timeline,
            ProcessingStep.STEP3_SCORING: run_step3_scoring,
            ProcessingStep.STEP4_TITLE: run_step4_title,
            ProcessingStep.STEP5_CLUSTERING: run_step5_clustering,
            ProcessingStep.STEP6_VIDEO: run_step6_video
        }
        
        # 步骤适配器映射 - 暂时禁用
        self.step_adapters = {
            # ProcessingStep.STEP1_OUTLINE: self.adapter.adapt_step1_outline,
            # ProcessingStep.STEP2_TIMELINE: self.adapter.adapt_step2_timeline,
            # ProcessingStep.STEP3_SCORING: self.adapter.adapt_step3_scoring,
            # ProcessingStep.STEP4_TITLE: self.adapter.adapt_step4_title,
            # ProcessingStep.STEP5_CLUSTERING: self.adapter.adapt_step5_clustering,
            # ProcessingStep.STEP6_VIDEO: self.adapter.adapt_step6_video
        }
        
        # 步骤状态管理
        self.step_status = {}
        self.step_timings = {}
        self.step_results = {}
    
    def execute_step(self, step: ProcessingStep, **kwargs) -> Dict[str, Any]:
        """
        执行单个步骤
        
        Args:
            step: 处理步骤
            **kwargs: 步骤特定参数
            
        Returns:
            步骤执行结果
        """
        step_name = step.value
        logger.info(f"开始执行步骤: {step_name}")
        
        # 更新步骤状态为运行中
        self._update_step_status(step, "running")
        
        try:
            # 获取步骤编号
            step_number = self._get_step_number(step)
            
            # 更新任务状态为运行中
            self._update_task_status(TaskStatus.RUNNING, progress=self._get_step_progress(step), current_step=step_number)
            
            # 获取步骤函数和适配器
            step_func = self.step_functions[step]
            step_adapter = self.step_adapters[step]
            
            # 准备步骤环境
            self.adapter.prepare_step_environment(step_name)
            
            # 执行步骤（使用高精度计时器）
            start_time = time.perf_counter()
            
            if step == ProcessingStep.STEP1_OUTLINE:
                # Step1需要SRT文件路径
                srt_path = kwargs.get('srt_path')
                if not srt_path:
                    raise ValueError("Step1需要提供SRT文件路径")
                
                adapted_params = step_adapter(srt_path)
            else:
                # 其他步骤使用前一步的输出
                adapted_params = step_adapter()
            
            # 执行步骤函数
            result = step_func(**adapted_params)
            
            execution_time = time.perf_counter() - start_time
            logger.info(f"步骤 {step_name} 执行完成，耗时: {execution_time:.4f}秒")
            
            # 记录步骤执行信息
            self.step_timings[step_name] = {
                "start_time": start_time,
                "end_time": time.perf_counter(),
                "execution_time": execution_time
            }
            
            # 保存结果到数据库
            self._save_step_result(step, result)
            
            # 更新步骤状态为完成
            self._update_step_status(step, "completed", execution_time=execution_time)
            
            # 更新任务进度
            self._update_task_status(TaskStatus.RUNNING, progress=self._get_step_progress(step), current_step=step_number)
            
            return {
                "step": step_name,
                "status": "completed",
                "execution_time": execution_time,
                "result": result
            }
            
        except Exception as e:
            execution_time = time.perf_counter() - start_time if 'start_time' in locals() else 0
            logger.error(f"步骤 {step_name} 执行失败: {e}")
            
            # 更新步骤状态为失败
            self._update_step_status(step, "failed", execution_time=execution_time, error=str(e))
            
            self._update_task_status(TaskStatus.FAILED, error_message=str(e))
            raise
    
    def execute_pipeline(self, srt_path: Path, steps_to_execute: Optional[List[ProcessingStep]] = None) -> Dict[str, Any]:
        """
        执行流水线（支持按需执行子集步骤）
        
        Args:
            srt_path: SRT文件路径
            steps_to_execute: 要执行的步骤列表，None表示执行完整流水线
            
        Returns:
            流水线执行结果
        """
        if steps_to_execute is None:
            # 执行完整流水线
            steps_to_execute = [
                ProcessingStep.STEP1_OUTLINE,
                ProcessingStep.STEP2_TIMELINE,
                ProcessingStep.STEP3_SCORING,
                ProcessingStep.STEP4_TITLE,
                ProcessingStep.STEP5_CLUSTERING,
                ProcessingStep.STEP6_VIDEO
            ]
            logger.info(f"开始执行项目 {self.project_id} 的完整流水线")
        else:
            logger.info(f"开始执行项目 {self.project_id} 的子集流水线: {[step.value for step in steps_to_execute]}")
        
        # 验证前置条件
        errors = self.adapter.validate_pipeline_prerequisites()
        if errors:
            error_msg = "; ".join(errors)
            self._update_task_status(TaskStatus.FAILED, error_message=error_msg)
            raise ValueError(f"流水线前置条件验证失败: {error_msg}")
        
        # 验证步骤依赖关系
        self._validate_step_dependencies(steps_to_execute)
        
        # 更新任务状态为运行中
        self._update_task_status(TaskStatus.RUNNING, progress=0)
        
        results = {}
        total_steps = len(steps_to_execute)
        
        try:
            for i, step in enumerate(steps_to_execute):
                step_number = self._get_step_number(step)
                logger.info(f"执行步骤 {i+1}/{total_steps}: {step.value}")
                
                if step == ProcessingStep.STEP1_OUTLINE:
                    step_result = self.execute_step(step, srt_path=srt_path)
                else:
                    step_result = self.execute_step(step)
                
                results[step.value] = step_result
                
                # 更新总体进度
                progress = ((i + 1) / total_steps) * 100
                self._update_task_status(TaskStatus.RUNNING, progress=progress, current_step=step_number)
            
            # 流水线执行完成，保存数据到数据库
            self._save_pipeline_results_to_database(results)
            
            # 更新任务状态为完成
            self._update_task_status(TaskStatus.COMPLETED, progress=100)
            
            logger.info(f"项目 {self.project_id} 流水线执行完成")
            return {
                "status": "completed",
                "project_id": self.project_id,
                "task_id": self.task_id,
                "results": results,
                "executed_steps": [step.value for step in steps_to_execute]
            }
            
        except Exception as e:
            logger.error(f"流水线执行失败: {e}")
            self._update_task_status(TaskStatus.FAILED, error_message=str(e))
            raise
    
    def _update_step_status(self, step: ProcessingStep, status: str, execution_time: Optional[float] = None, 
                           error: Optional[str] = None):
        """更新步骤状态"""
        step_name = step.value
        self.step_status[step_name] = {
            "status": status,
            "timestamp": time.time(),
            "execution_time": execution_time,
            "error": error
        }
        logger.debug(f"步骤 {step_name} 状态更新: {status}")
    
    def _update_task_status(self, status: TaskStatus, progress: Optional[float] = None, 
                           error_message: Optional[str] = None, result: Optional[Dict] = None,
                           current_step: Optional[int] = None):
        """更新任务状态"""
        # 使用TaskRepository的专用方法
        if progress is not None:
            self.task_repo.update_task_progress(self.task_id, progress)
        
        if error_message is not None:
            self.task_repo.update_task_error(self.task_id, error_message)
        
        if result is not None:
            self.task_repo.update_task_result(self.task_id, result)
        
        # 更新状态
        self.task_repo.update_task_status(self.task_id, status)
        
        # 更新项目状态
        if current_step is not None:
            self._update_project_status(current_step, progress)
        
        logger.info(f"任务 {self.task_id} 状态更新为: {status.value}, 进度: {progress}%, 步骤: {current_step}")
        
        # 发送WebSocket实时进度更新
        self._send_realtime_progress_update(status, progress, error_message, current_step)
    
    def _update_project_status(self, current_step: int, progress: Optional[float] = None):
        """更新项目状态"""
        try:
            from ..services.project_service import ProjectService
            from ..core.database import SessionLocal
            
            db = SessionLocal()
            try:
                project_service = ProjectService(db)
                project = project_service.get(self.project_id)
                if project:
                    # 更新项目状态
                    update_data = {
                        "current_step": current_step,
                        "total_steps": 6,
                        "status": "processing" if current_step < 6 else "completed"
                    }
                    if progress is not None:
                        update_data["progress"] = progress
                    
                    project_service.update(self.project_id, **update_data)
                    db.commit()
                    logger.info(f"项目 {self.project_id} 状态已更新: 步骤 {current_step}/6, 进度 {progress}%")
                else:
                    logger.warning(f"项目 {self.project_id} 不存在")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"更新项目状态失败: {e}")
    
    def _send_realtime_progress_update(self, status: TaskStatus, progress: Optional[float] = None, 
                                     error_message: Optional[str] = None, current_step: Optional[int] = None):
        """发送实时进度更新到前端 - 集成快照发布"""
        try:
            import asyncio
            import json
            from ..services.websocket_notification_service import WebSocketNotificationService
            from ..services.progress_snapshot_service import snapshot_service
            
            # 获取当前步骤信息
            if current_step is None:
                current_step = 0
                step_name = "初始化中..."
                
                # 根据进度推断当前步骤
                if progress is not None:
                    if progress <= 10:
                        current_step = 1
                        step_name = "大纲提取"
                    elif progress <= 30:
                        current_step = 2
                        step_name = "时间定位"
                    elif progress <= 50:
                        current_step = 3
                        step_name = "内容评分"
                    elif progress <= 70:
                        current_step = 4
                        step_name = "标题生成"
                    elif progress <= 85:
                        current_step = 5
                        step_name = "主题聚类"
                    elif progress <= 95:
                        current_step = 6
                        step_name = "视频切割"
                    else:
                        current_step = 6
                        step_name = "处理完成"
            else:
                # 根据步骤编号获取步骤名称
                step_name_map = {
                    1: "大纲提取",
                    2: "时间定位", 
                    3: "内容评分",
                    4: "标题生成",
                    5: "主题聚类",
                    6: "视频切割"
                }
                step_name = step_name_map.get(current_step, "处理中...")
            
            # 构建进度消息
            progress_message = f"正在执行{step_name}..."
            if error_message:
                progress_message = f"处理失败: {error_message}"
            elif status == TaskStatus.COMPLETED:
                progress_message = "处理完成"
            
            # 构建富消息载荷
            payload = {
                "type": "task_progress_update",
                "task_id": self.task_id,
                "project_id": self.project_id,
                "status": status.value,
                "progress": progress or 0,
                "current_step": current_step,
                "total_steps": 6,
                "step_name": step_name,
                "phase": step_name,
                "message": progress_message,
                "timestamp": time.time()
            }
            
            # 使用同步方式发送WebSocket通知和快照
            def send_notification():
                try:
                    # 尝试获取现有的事件循环
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # 如果事件循环正在运行，使用线程池
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(
                                asyncio.run,
                                self._async_send_progress_update(payload)
                            )
                            future.result(timeout=5)  # 5秒超时
                    else:
                        # 如果事件循环没有运行，直接运行
                        loop.run_until_complete(
                            self._async_send_progress_update(payload)
                        )
                except Exception as e:
                    logger.error(f"发送WebSocket通知失败: {e}")
            
            # 在后台线程中发送通知
            import threading
            thread = threading.Thread(target=send_notification)
            thread.daemon = True
            thread.start()
            
            logger.debug(f"已发送实时进度更新: {self.project_id} - {progress}% - {step_name}")
            
        except Exception as e:
            logger.error(f"发送实时进度更新失败: {e}")
    
    async def _async_send_progress_update(self, payload: dict):
        """异步发送进度更新和快照"""
        try:
            import redis.asyncio as redis
            import json
            from ..core.config import get_redis_url
            from .progress_snapshot_service import snapshot_service
            
            # 连接Redis
            redis_client = redis.from_url(get_redis_url(), decode_responses=True)
            
            # 频道名 - 使用规范化函数
            from .websocket_gateway_service import WebSocketGatewayService
            channel = WebSocketGatewayService.normalize_channel(self.project_id)
            
            # 1) 保存快照
            await snapshot_service.save_snapshot(channel, payload)
            
            # 2) 发布消息到Redis
            await redis_client.publish(channel, json.dumps(payload, ensure_ascii=False))
            
            # 3) 关闭Redis连接
            await redis_client.aclose()
            
            logger.debug(f"进度更新已发布: {channel} - {payload}")
            
        except Exception as e:
            logger.error(f"异步发送进度更新失败: {e}")
    
    def _get_step_number(self, step: ProcessingStep) -> int:
        """获取步骤编号"""
        step_number_map = {
            ProcessingStep.STEP1_OUTLINE: 1,
            ProcessingStep.STEP2_TIMELINE: 2,
            ProcessingStep.STEP3_SCORING: 3,
            ProcessingStep.STEP4_TITLE: 4,
            ProcessingStep.STEP5_CLUSTERING: 5,
            ProcessingStep.STEP6_VIDEO: 6
        }
        return step_number_map.get(step, 0)
    
    def _get_step_progress(self, step: ProcessingStep) -> float:
        """获取步骤对应的进度百分比"""
        step_progress_map = {
            ProcessingStep.STEP1_OUTLINE: 10,
            ProcessingStep.STEP2_TIMELINE: 30,
            ProcessingStep.STEP3_SCORING: 50,
            ProcessingStep.STEP4_TITLE: 70,
            ProcessingStep.STEP5_CLUSTERING: 85,
            ProcessingStep.STEP6_VIDEO: 95
        }
        return step_progress_map.get(step, 0)
    
    def _save_step_result(self, step: ProcessingStep, result: Any):
        """保存步骤结果到数据库"""
        # 这里可以根据需要将结果保存到相应的数据库表
        # 比如切片结果保存到Clip表，合集结果保存到Collection表
        logger.info(f"步骤 {step.value} 结果已保存")
    
    def _save_pipeline_results_to_database(self, results: Dict[str, Any]):
        """将流水线执行结果保存到数据库"""
        try:
            logger.info(f"开始保存项目 {self.project_id} 流水线结果到数据库")
            
            # 获取项目目录
            project_dir = self.adapter.data_dir / "projects" / self.project_id
            
            # 使用DataSyncService同步数据到数据库
            from ..services.data_sync_service import DataSyncService
            sync_service = DataSyncService(self.db)
            
            # 同步项目数据
            sync_result = sync_service.sync_project_from_filesystem(self.project_id, project_dir)
            
            if sync_result.get("success"):
                logger.info(f"项目 {self.project_id} 数据同步成功: {sync_result}")
            else:
                logger.error(f"项目 {self.project_id} 数据同步失败: {sync_result}")
            
            logger.info(f"项目 {self.project_id} 流水线结果已全部保存到数据库")
            
        except Exception as e:
            logger.error(f"保存流水线结果到数据库失败: {e}")
            # 不抛出异常，避免影响整个流水线的完成状态
    
    def _validate_step_dependencies(self, steps_to_execute: List[ProcessingStep]):
        """验证步骤依赖关系"""
        # 对执行列表中的每个步骤都做依赖检查，避免中间步骤缺失时延迟失败
        if steps_to_execute:
            missing_dependencies = {}
            
            for step in steps_to_execute:
                required_steps = STEP_DEPENDENCIES.get(step, [])
                missing_steps = [req_step.value for req_step in required_steps if not self._step_has_output(req_step)]
                if missing_steps:
                    missing_dependencies[step.value] = missing_steps
            
            if missing_dependencies:
                raise ValueError(f"步骤依赖检查失败: {missing_dependencies}")
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """获取流水线状态"""
        task = self.task_repo.get_by_id(self.task_id)
        if not task:
            return {"error": "任务不存在"}
        
        return {
            "task_id": self.task_id,
            "project_id": self.project_id,
            "task_status": task.status.value,
            "task_progress": task.progress,
            "error_message": task.error_message,
            "step_status": self.step_status,
            "step_timings": self.step_timings,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None
        }
    
    def retry_step(self, step: ProcessingStep, **kwargs) -> Dict[str, Any]:
        """重试特定步骤"""
        logger.info(f"重试步骤: {step.value}")
        
        # 清理步骤的中间文件
        self.adapter.cleanup_intermediate_files(step.value)
        
        # 重新执行步骤
        return self.execute_step(step, **kwargs)
    
    def get_step_result(self, step: ProcessingStep) -> Any:
        """获取步骤结果"""
        return self.adapter.get_step_result(step.value)
    
    def get_step_performance_summary(self) -> Dict[str, Any]:
        """获取步骤性能摘要"""
        if not self.step_timings:
            return {"message": "暂无性能数据"}
        
        total_time = sum(timing["execution_time"] for timing in self.step_timings.values())
        step_performance = {}
        
        for step_name, timing in self.step_timings.items():
            percentage = (timing["execution_time"] / total_time * 100) if total_time > 0 else 0
            step_performance[step_name] = {
                "execution_time": timing["execution_time"],
                "percentage": percentage,
                "start_time": timing["start_time"],
                "end_time": timing["end_time"]
            }
        
        return {
            "total_execution_time": total_time,
            "step_performance": step_performance,
            "slowest_step": max(self.step_timings.items(), key=lambda x: x[1]["execution_time"])[0] if self.step_timings else None,
            "fastest_step": min(self.step_timings.items(), key=lambda x: x[1]["execution_time"])[0] if self.step_timings else None
        }
    
    def resume_from_step(self, start_step: ProcessingStep, srt_path: Optional[Path] = None) -> Dict[str, Any]:
        """从指定步骤恢复执行"""
        logger.info(f"从步骤 {start_step.value} 恢复执行")
        
        # 获取从指定步骤开始的所有步骤
        all_steps = [
            ProcessingStep.STEP1_OUTLINE,
            ProcessingStep.STEP2_TIMELINE,
            ProcessingStep.STEP3_SCORING,
            ProcessingStep.STEP4_TITLE,
            ProcessingStep.STEP5_CLUSTERING,
            ProcessingStep.STEP6_VIDEO
        ]
        
        try:
            start_index = all_steps.index(start_step)
            
            # 只执行未完成的步骤
            steps_to_execute = []
            for step in all_steps[start_index:]:
                step_output = self.adapter.get_step_output_path(step.value)
                if not step_output.exists():
                    steps_to_execute.append(step)
                else:
                    logger.info(f"步骤 {step.value} 已完成，跳过")
            
            if not steps_to_execute:
                logger.info("所有步骤都已完成，无需执行")
                return {"message": "所有步骤都已完成"}
            
            logger.info(f"将执行步骤: {[step.value for step in steps_to_execute]}")
            
            if start_step == ProcessingStep.STEP1_OUTLINE:
                if not srt_path:
                    raise ValueError("从Step1恢复需要提供SRT文件路径")
                return self.execute_pipeline(srt_path, steps_to_execute)
            else:
                # 验证前置步骤是否已完成
                for step in all_steps[:start_index]:
                    step_output = self.adapter.get_step_output_path(step.value)
                    if not step_output.exists():
                        raise ValueError(f"前置步骤 {step.value} 未完成，无法从 {start_step.value} 恢复")
                
                return self.execute_pipeline(Path("dummy.srt"), steps_to_execute)
                
        except ValueError as e:
            logger.error(f"恢复执行失败: {e}")
            raise
    
    def get_step_status_summary(self) -> Dict[str, Any]:
        """获取步骤状态摘要"""
        if not self.step_status:
            return {"message": "暂无步骤状态数据"}
        
        completed_steps = [step for step, status in self.step_status.items() if status["status"] == "completed"]
        failed_steps = [step for step, status in self.step_status.items() if status["status"] == "failed"]
        running_steps = [step for step, status in self.step_status.items() if status["status"] == "running"]
        
        return {
            "total_steps": len(self.step_status),
            "completed_steps": completed_steps,
            "failed_steps": failed_steps,
            "running_steps": running_steps,
            "completion_rate": len(completed_steps) / len(self.step_status) * 100 if self.step_status else 0,
            "step_details": self.step_status
        }

    def _get_project_paths(self) -> Dict[str, Path]:
        """获取项目相关路径。"""
        return shared_config_manager.get_project_paths(self.project_id)

    def _get_step_candidate_outputs(self, step: ProcessingStep) -> List[Path]:
        """获取步骤可能产生的输出文件路径。"""
        project_paths = self._get_project_paths()
        search_dirs = [
            project_paths["metadata_dir"],
            project_paths["output_dir"]
        ]
        candidates = []
        
        for filename in STEP_OUTPUT_CANDIDATES.get(step, []):
            for directory in search_dirs:
                candidates.append(directory / filename)
        
        return candidates

    def _get_existing_step_output(self, step: ProcessingStep) -> Optional[Path]:
        """获取步骤实际存在的输出文件。"""
        for candidate in self._get_step_candidate_outputs(step):
            if candidate.exists():
                return candidate
        return None

    def _step_has_output(self, step: ProcessingStep) -> bool:
        """检查步骤是否已有可用输出。"""
        return self._get_existing_step_output(step) is not None

    def _inspect_step_output(self, step: ProcessingStep, output_path: Optional[Path]) -> Dict[str, Any]:
        """检查步骤输出文件是否可用，以及是否满足基础结构要求。"""
        if not output_path:
            return {
                "valid": False,
                "reason": "missing_output",
                "issues": ["missing_output"],
                "item_count": 0,
                "required_fields_present": None
            }

        if output_path.suffix.lower() != ".json":
            return {
                "valid": True,
                "reason": "non_json_output",
                "issues": [],
                "item_count": None,
                "required_fields_present": None
            }

        try:
            with open(output_path, "r", encoding="utf-8") as file:
                payload = json.load(file)
        except (OSError, json.JSONDecodeError) as exc:
            return {
                "valid": False,
                "reason": "invalid_json",
                "issues": [f"invalid_json:{exc}"],
                "item_count": 0,
                "required_fields_present": False
            }

        expected_type = STEP_OUTPUT_REQUIREMENTS.get(step, {}).get("container_type")
        if expected_type and not isinstance(payload, expected_type):
            expected_name = (
                [item.__name__ for item in expected_type]
                if isinstance(expected_type, tuple) else expected_type.__name__
            )
            return {
                "valid": False,
                "reason": "unexpected_container_type",
                "issues": [f"unexpected_container_type:{expected_name}"],
                "item_count": 0,
                "required_fields_present": False
            }

        issues = []
        required_fields_present = None

        if isinstance(payload, list):
            item_count = len(payload)
            if payload and not all(isinstance(item, dict) for item in payload):
                issues.append("non_object_items")
            if output_path.name == "clips_metadata.json" and payload:
                required_fields = {"video_path", "status", "duration_seconds"}
                required_fields_present = all(required_fields.issubset(item.keys()) for item in payload if isinstance(item, dict))
                if not required_fields_present:
                    issues.append("missing_required_clip_metadata_fields")
            elif payload:
                required_fields_present = True
        elif isinstance(payload, dict):
            item_count = len(payload)
            if output_path.name == "step6_video_output.json":
                required_fields = {"clips_generated", "collections_generated"}
                required_fields_present = required_fields.issubset(payload.keys())
                if not required_fields_present:
                    issues.append("missing_required_step6_summary_fields")
            else:
                required_fields_present = True
        else:
            item_count = 1

        if item_count == 0:
            issues.append("empty_output")

        return {
            "valid": len(issues) == 0 or issues == ["empty_output"],
            "reason": "ok" if len(issues) == 0 else ("warning" if issues == ["empty_output"] else "invalid_content"),
            "issues": issues,
            "item_count": item_count,
            "required_fields_present": required_fields_present
        }

    def _get_step_recommendation(
        self,
        status: str,
        missing_dependencies: List[str],
        output_validation: Dict[str, Any]
    ) -> str:
        """为步骤给出下一步建议。"""
        if status == "failed":
            return "retry_step"
        if status == "running":
            return "wait_for_completion"
        if status == "blocked":
            return f"complete_dependencies:{','.join(missing_dependencies)}"
        if status == "invalid_output":
            return "regenerate_output"
        if output_validation.get("issues") == ["empty_output"]:
            return "review_empty_output"
        if status == "pending":
            return "ready_to_run"
        return "no_action_needed"

    def get_step_health_status(self, step: ProcessingStep) -> Dict[str, Any]:
        """获取单个步骤/模块的健康状态。"""
        existing_output = self._get_existing_step_output(step)
        required_steps = STEP_DEPENDENCIES.get(step, [])
        missing_dependencies = [req_step.value for req_step in required_steps if not self._step_has_output(req_step)]
        runtime_status = self.step_status.get(step.value, {}).get("status")
        output_validation = self._inspect_step_output(step, existing_output)
        
        if runtime_status == "failed":
            status = "failed"
        elif runtime_status == "running":
            status = "running"
        elif existing_output and not output_validation["valid"]:
            status = "invalid_output"
        elif existing_output and not missing_dependencies:
            status = "completed"
        elif missing_dependencies:
            status = "blocked"
        else:
            status = "pending"
        
        return {
            "step": step.value,
            "display_name": step.value.replace("_", " "),
            "status": status,
            "can_execute": status == "pending" and not missing_dependencies,
            "can_retry": status in {"failed", "invalid_output"},
            "has_output": existing_output is not None,
            "output_path": str(existing_output) if existing_output else None,
            "output_validation": output_validation,
            "missing_dependencies": missing_dependencies,
            "recommendation": self._get_step_recommendation(status, missing_dependencies, output_validation),
            "runtime_details": self.step_status.get(step.value, {})
        }

    def get_all_step_health_statuses(self) -> Dict[str, Any]:
        """获取所有步骤/模块的健康状态。"""
        steps = [
            ProcessingStep.STEP1_OUTLINE,
            ProcessingStep.STEP2_TIMELINE,
            ProcessingStep.STEP3_SCORING,
            ProcessingStep.STEP4_TITLE,
            ProcessingStep.STEP5_CLUSTERING,
            ProcessingStep.STEP6_VIDEO
        ]
        step_checks = [self.get_step_health_status(step) for step in steps]
        
        return {
            "project_id": self.project_id,
            "total_steps": len(step_checks),
            "completed_steps": len([item for item in step_checks if item["status"] == "completed"]),
            "blocked_steps": len([item for item in step_checks if item["status"] == "blocked"]),
            "pending_steps": len([item for item in step_checks if item["status"] == "pending"]),
            "failed_steps": len([item for item in step_checks if item["status"] == "failed"]),
            "invalid_steps": len([item for item in step_checks if item["status"] == "invalid_output"]),
            "running_steps": len([item for item in step_checks if item["status"] == "running"]),
            "ready_steps": [item["step"] for item in step_checks if item["can_execute"]],
            "steps": step_checks
        }

    def validate_all_step_outputs(self) -> Dict[str, Any]:
        """校验所有步骤模块的输出和依赖情况。"""
        summary = self.get_all_step_health_statuses()
        issues = []
        
        for step_status in summary["steps"]:
            if step_status["status"] in {"blocked", "failed", "invalid_output"}:
                issues.append({
                    "step": step_status["step"],
                    "status": step_status["status"],
                    "missing_dependencies": step_status["missing_dependencies"],
                    "output_path": step_status["output_path"],
                    "output_issues": step_status["output_validation"]["issues"],
                    "recommendation": step_status["recommendation"]
                })
        
        summary["valid"] = len(issues) == 0
        summary["issues"] = issues
        return summary
