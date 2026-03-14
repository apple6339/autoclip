from pathlib import Path
from unittest.mock import Mock, patch

from backend.services.config_manager import ProcessingStep
from backend.services.pipeline_adapter import PipelineAdapter
from backend.services.processing_orchestrator import ProcessingOrchestrator


def _build_project_paths(base_dir: Path):
    project_base = base_dir / "project"
    raw_dir = project_base / "raw"
    metadata_dir = project_base / "output" / "metadata"
    clips_dir = project_base / "output" / "clips"
    collections_dir = project_base / "output" / "collections"
    output_dir = project_base / "output"

    for path in (raw_dir, metadata_dir, clips_dir, collections_dir):
        path.mkdir(parents=True, exist_ok=True)

    return {
        "project_base": project_base,
        "input_dir": raw_dir,
        "output_dir": output_dir,
        "clips_dir": clips_dir,
        "collections_dir": collections_dir,
        "metadata_dir": metadata_dir,
        "logs_dir": project_base / "logs",
        "temp_dir": project_base / "temp",
    }


def test_pipeline_adapter_step2_uses_step1_outline_output(tmp_path):
    adapter = PipelineAdapter("test_project", "task-1", Mock())
    adapter.project_paths = _build_project_paths(tmp_path)
    step1_output = adapter.project_paths["metadata_dir"] / "step1_outline.json"
    step1_output.write_text("[]", encoding="utf-8")

    with patch.object(adapter, "_get_prompt_files", return_value={}):
        params = adapter.adapt_step2_timeline()

    assert params["outline_path"] == step1_output
    assert params["output_path"] == adapter.project_paths["metadata_dir"] / "step2_timeline.json"


def test_execute_step_builds_parameters_from_pipeline_adapter(tmp_path):
    db = Mock()
    orchestrator = ProcessingOrchestrator("test_project", "task-1", db)
    orchestrator.project_paths = _build_project_paths(tmp_path)
    orchestrator.adapter.project_paths = orchestrator.project_paths

    srt_file = tmp_path / "input.srt"
    srt_file.write_text("1\n00:00:01,000 --> 00:00:05,000\n测试字幕\n", encoding="utf-8")

    step_func = Mock(return_value={"status": "ok"})
    orchestrator.step_functions[ProcessingStep.STEP1_OUTLINE] = step_func

    with patch.object(orchestrator.adapter, "_get_prompt_files", return_value={}), \
         patch.object(orchestrator, "_update_task_status"), \
         patch.object(orchestrator, "_save_step_result"):
        result = orchestrator.execute_step(ProcessingStep.STEP1_OUTLINE, srt_path=srt_file)

    assert result["status"] == "completed"
    step_func.assert_called_once()
    call_kwargs = step_func.call_args.kwargs
    assert call_kwargs["srt_path"] == srt_file
    assert call_kwargs["output_path"] == orchestrator.adapter.project_paths["metadata_dir"] / "step1_outline.json"
    assert call_kwargs["metadata_dir"] == orchestrator.adapter.project_paths["metadata_dir"]


def test_execute_pipeline_validates_using_provided_srt_path(tmp_path):
    db = Mock()
    orchestrator = ProcessingOrchestrator("test_project", "task-1", db)
    srt_file = tmp_path / "input.srt"
    srt_file.write_text("1\n00:00:01,000 --> 00:00:05,000\n测试字幕\n", encoding="utf-8")

    with patch.object(orchestrator.adapter, "validate_pipeline_prerequisites", return_value=[]) as validate_mock, \
         patch.object(orchestrator, "_validate_step_dependencies"), \
         patch.object(orchestrator, "_update_task_status"), \
         patch.object(orchestrator, "_save_pipeline_results_to_database"), \
         patch.object(orchestrator, "execute_step", return_value={"status": "completed"}) as execute_step_mock:
        result = orchestrator.execute_pipeline(srt_file, [ProcessingStep.STEP1_OUTLINE])

    validate_mock.assert_called_once_with(srt_path=srt_file)
    execute_step_mock.assert_called_once_with(ProcessingStep.STEP1_OUTLINE, srt_path=srt_file)
    assert result["status"] == "completed"
