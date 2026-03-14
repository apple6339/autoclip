"""
模块检查相关测试
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from fastapi import HTTPException

from backend.api.v1.pipeline_control import (
    get_pipeline_modules_status,
    get_pipeline_status,
    validate_pipeline_modules,
)
from backend.services.processing_orchestrator import ProcessingOrchestrator


class TestProcessingOrchestratorModuleChecks:
    def test_get_all_step_health_statuses_marks_blocked_steps(self, tmp_path):
        project_paths = {
            "project_base": tmp_path / "project",
            "input_dir": tmp_path / "project" / "raw",
            "output_dir": tmp_path / "project" / "output",
            "clips_dir": tmp_path / "project" / "output" / "clips",
            "collections_dir": tmp_path / "project" / "output" / "collections",
            "metadata_dir": tmp_path / "project" / "output" / "metadata",
        }
        for path in project_paths.values():
            path.mkdir(parents=True, exist_ok=True)

        # 仅创建第一步输出，验证后续模块检查状态
        (project_paths["metadata_dir"] / "step1_outline.json").write_text("{}", encoding="utf-8")

        orchestrator = ProcessingOrchestrator("project-1", "task-1", Mock())
        with patch("backend.services.processing_orchestrator.shared_config_manager.get_project_paths", return_value=project_paths):
            summary = orchestrator.get_all_step_health_statuses()

        step_status_map = {item["step"]: item for item in summary["steps"]}
        assert step_status_map["step1_outline"]["status"] == "completed"
        assert step_status_map["step2_timeline"]["status"] == "pending"
        assert step_status_map["step3_scoring"]["status"] == "blocked"
        assert "step2_timeline" in step_status_map["step3_scoring"]["missing_dependencies"]

    def test_validate_all_step_outputs_reports_failed_and_blocked_steps(self, tmp_path):
        project_paths = {
            "project_base": tmp_path / "project",
            "input_dir": tmp_path / "project" / "raw",
            "output_dir": tmp_path / "project" / "output",
            "clips_dir": tmp_path / "project" / "output" / "clips",
            "collections_dir": tmp_path / "project" / "output" / "collections",
            "metadata_dir": tmp_path / "project" / "output" / "metadata",
        }
        for path in project_paths.values():
            path.mkdir(parents=True, exist_ok=True)

        (project_paths["metadata_dir"] / "step1_outline.json").write_text("{}", encoding="utf-8")
        (project_paths["metadata_dir"] / "step2_timeline.json").write_text("{}", encoding="utf-8")

        orchestrator = ProcessingOrchestrator("project-1", "task-1", Mock())
        orchestrator.step_status["step4_title"] = {"status": "failed", "error": "标题模块失败"}

        with patch("backend.services.processing_orchestrator.shared_config_manager.get_project_paths", return_value=project_paths):
            validation = orchestrator.validate_all_step_outputs()

        assert validation["valid"] is False
        issue_map = {item["step"]: item for item in validation["issues"]}
        assert issue_map["step4_title"]["status"] == "failed"
        assert issue_map["step5_clustering"]["status"] == "blocked"


class TestPipelineControlModuleApis:
    @staticmethod
    def _mock_db_with_project(project_id: str = "project-1"):
        db = Mock()
        project = Mock()
        project.id = project_id
        project.status = "pending"

        query = Mock()
        query.filter.return_value.first.return_value = project
        db.query.return_value = query
        return db, project

    def test_get_pipeline_modules_status_returns_orchestrator_summary(self):
        db, _ = self._mock_db_with_project()
        orchestrator = Mock()
        orchestrator.get_all_step_health_statuses.return_value = {"project_id": "project-1", "steps": []}

        with patch("backend.api.v1.pipeline_control._create_project_orchestrator", return_value=orchestrator):
            result = asyncio.run(get_pipeline_modules_status("project-1", db))

        assert result["project_id"] == "project-1"
        orchestrator.get_all_step_health_statuses.assert_called_once()

    def test_validate_pipeline_modules_returns_validation_result(self):
        db, _ = self._mock_db_with_project()
        orchestrator = Mock()
        orchestrator.validate_all_step_outputs.return_value = {"valid": True, "steps": [], "issues": []}

        with patch("backend.api.v1.pipeline_control._create_project_orchestrator", return_value=orchestrator):
            result = asyncio.run(validate_pipeline_modules("project-1", db))

        assert result["valid"] is True
        orchestrator.validate_all_step_outputs.assert_called_once()

    def test_get_pipeline_status_includes_module_summary(self):
        db = Mock()
        project = Mock()
        project.id = "project-1"
        project.status = "processing"

        task = Mock()
        task.id = "task-1"
        task.name = "处理任务"
        task.status = "running"
        task.progress = 50
        task.current_step = "step2_timeline"
        task.created_at = None
        task.started_at = None
        task.completed_at = None
        task.updated_at = None

        project_query = Mock()
        project_query.filter.return_value.first.return_value = project
        task_query = Mock()
        task_query.filter.return_value.all.return_value = [task]
        db.query.side_effect = [project_query, task_query]

        orchestrator = Mock()
        orchestrator.get_all_step_health_statuses.return_value = {"project_id": "project-1", "steps": []}

        with patch("backend.api.v1.pipeline_control._create_project_orchestrator", return_value=orchestrator), \
             patch("backend.api.v1.pipeline_control.progress_update_service.get_task_progress", return_value=None):
            result = asyncio.run(get_pipeline_status("project-1", db))

        assert result["module_summary"]["project_id"] == "project-1"
        assert result["total_tasks"] == 1

    def test_get_pipeline_modules_status_raises_404_for_missing_project(self):
        db = Mock()
        query = Mock()
        query.filter.return_value.first.return_value = None
        db.query.return_value = query

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(get_pipeline_modules_status("missing-project", db))

        assert exc_info.value.status_code == 404
