"""Tests for pipeline module checks."""

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add the project root to the Python path.
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from fastapi import HTTPException

from backend.api.v1.pipeline_control import (
    get_pipeline_modules_status,
    get_pipeline_status,
    validate_pipeline_modules,
)
from backend.services.config_manager import ProcessingStep
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

        # Only create the first-step output so downstream states can be inferred.
        (project_paths["metadata_dir"] / "step1_outline.json").write_text("[]", encoding="utf-8")

        orchestrator = ProcessingOrchestrator("project-1", "task-1", Mock())
        with patch("backend.services.processing_orchestrator.shared_config_manager.get_project_paths", return_value=project_paths):
            step_health_summary = orchestrator.get_all_step_health_statuses()

        step_status_map = {item["step"]: item for item in step_health_summary["steps"]}
        assert step_status_map["step1_outline"]["status"] == "completed"
        assert step_status_map["step2_timeline"]["status"] == "pending"
        assert step_status_map["step3_scoring"]["status"] == "blocked"
        assert "step2_timeline" in step_status_map["step3_scoring"]["missing_dependencies"]
        assert step_status_map["step2_timeline"]["can_execute"] is True
        assert step_health_summary["ready_steps"] == ["step2_timeline"]

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

        (project_paths["metadata_dir"] / "step1_outline.json").write_text("[]", encoding="utf-8")
        (project_paths["metadata_dir"] / "step2_timeline.json").write_text("[]", encoding="utf-8")

        orchestrator = ProcessingOrchestrator("project-1", "task-1", Mock())
        orchestrator.step_status["step4_title"] = {"status": "failed", "error": "title step failed"}

        with patch("backend.services.processing_orchestrator.shared_config_manager.get_project_paths", return_value=project_paths):
            validation = orchestrator.validate_all_step_outputs()

        assert validation["valid"] is False
        issue_map = {item["step"]: item for item in validation["issues"]}
        assert issue_map["step4_title"]["status"] == "failed"
        assert issue_map["step5_clustering"]["status"] == "blocked"
        assert issue_map["step5_clustering"]["recommendation"] == "complete_dependencies:step4_title"

    def test_get_step_health_status_marks_invalid_json_output(self, tmp_path):
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

        invalid_output = project_paths["metadata_dir"] / "step2_timeline.json"
        invalid_output.write_text("{invalid json", encoding="utf-8")

        orchestrator = ProcessingOrchestrator("project-1", "task-1", Mock())
        with patch("backend.services.processing_orchestrator.shared_config_manager.get_project_paths", return_value=project_paths):
            step_health = orchestrator.get_step_health_status(step=ProcessingStep.STEP2_TIMELINE)

        assert step_health["status"] == "invalid_output"
        assert step_health["can_retry"] is True
        assert step_health["recommendation"] == "regenerate_output"
        assert step_health["output_validation"]["reason"] == "invalid_json"

    def test_validate_all_step_outputs_reports_invalid_output_issue_details(self, tmp_path):
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

        metadata = [
            {"id": "clip-1", "status": "completed", "duration_seconds": 3.0}
        ]
        (project_paths["metadata_dir"] / "clips_metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False),
            encoding="utf-8"
        )

        orchestrator = ProcessingOrchestrator("project-1", "task-1", Mock())
        with patch("backend.services.processing_orchestrator.shared_config_manager.get_project_paths", return_value=project_paths):
            validation = orchestrator.validate_all_step_outputs()

        issue_map = {item["step"]: item for item in validation["issues"]}
        assert issue_map["step6_video"]["status"] == "invalid_output"
        assert "missing_required_clip_metadata_fields" in issue_map["step6_video"]["output_issues"]
        assert issue_map["step6_video"]["recommendation"] == "regenerate_output"


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
        task.name = "processing task"
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
