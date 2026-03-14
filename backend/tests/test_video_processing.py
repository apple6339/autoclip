"""
视频切片相关测试
"""

import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from backend.pipeline.step6_video import VideoGenerator, run_step6_video
from backend.services.processing_service import ProcessingService
from backend.tasks.video import extract_video_clips
from backend.utils.video_processor import VideoProcessor


class TestVideoProcessor:
    def test_batch_extract_clips_skips_invalid_ranges(self, tmp_path):
        clips_dir = tmp_path / "clips"
        collections_dir = tmp_path / "collections"
        input_video = tmp_path / "input.mp4"
        input_video.touch()
        
        processor = VideoProcessor(
            clips_dir=str(clips_dir),
            collections_dir=str(collections_dir)
        )
        
        extracted_ranges = []
        
        def fake_extract_clip(_input, output, start_time, end_time):
            output.parent.mkdir(parents=True, exist_ok=True)
            output.touch()
            extracted_ranges.append((output.name, start_time, end_time))
            return True
        
        with patch.object(VideoProcessor, "extract_clip", side_effect=fake_extract_clip):
            result = processor.batch_extract_clips(input_video, [
                {"id": "1", "title": "精彩/片段", "start_time": "1.5", "end_time": 5},
                {"id": "2", "title": "无效片段", "start_time": "00:00:05,000", "end_time": "00:00:04,000"},
                {"id": "3", "title": "缺少时间", "start_time": "", "end_time": "3"},
            ])
        
        assert len(result) == 1
        assert result[0].name == "1_精彩_片段.mp4"
        assert extracted_ranges == [("1_精彩_片段.mp4", "00:00:01.500", "00:00:05.000")]


class TestStep6Video:
    def test_run_step6_video_enriches_clip_metadata(self, tmp_path):
        metadata_dir = tmp_path / "metadata"
        clips_dir = tmp_path / "output" / "clips"
        collections_dir = tmp_path / "output" / "collections"
        output_dir = tmp_path / "output"
        input_video = tmp_path / "input.mp4"
        input_video.touch()
        
        titles_path = metadata_dir / "step4_titles.json"
        collections_path = metadata_dir / "step5_collections.json"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        
        clips_payload = [
            {"id": "1", "generated_title": "Clip/One", "start_time": 1, "end_time": 4}
        ]
        titles_path.write_text(json.dumps(clips_payload, ensure_ascii=False), encoding="utf-8")
        collections_path.write_text("[]", encoding="utf-8")
        
        def fake_generate_clips(self, clips_with_titles, _input_video):
            output_path = self.get_clip_output_path(clips_with_titles[0])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.touch()
            return [output_path]
        
        with patch.object(VideoGenerator, "generate_clips", fake_generate_clips), \
             patch.object(VideoGenerator, "generate_collections", return_value=[]):
            result = run_step6_video(
                clips_with_titles_path=titles_path,
                collections_path=collections_path,
                input_video=input_video,
                output_dir=output_dir,
                clips_dir=str(clips_dir),
                collections_dir=str(collections_dir),
                metadata_dir=str(metadata_dir)
            )
        
        saved_metadata = json.loads((metadata_dir / "clips_metadata.json").read_text(encoding="utf-8"))
        assert saved_metadata[0]["video_path"] == str(clips_dir / "1_Clip_One.mp4")
        assert saved_metadata[0]["status"] == "completed"
        assert saved_metadata[0]["duration_seconds"] == 3.0
        assert result["clips_generated"] == 1
        assert result["clips_count"] == 1
        assert result["collections_generated"] == 0
        assert result["collections_count"] == 0


class TestProcessingService:
    def test_extract_clips_runs_step6_pipeline(self, tmp_path):
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
        
        (project_paths["input_dir"] / "input.mp4").touch()
        (project_paths["metadata_dir"] / "step4_titles.json").write_text("[]", encoding="utf-8")
        (project_paths["metadata_dir"] / "step5_collections.json").write_text("[]", encoding="utf-8")
        
        service = ProcessingService(Mock())
        
        with patch("backend.services.processing_service.config_manager.get_project_paths", return_value=project_paths), \
             patch("backend.services.processing_service.run_step6_video", return_value={"clips_generated": 2}) as mock_run_step6, \
             patch("backend.services.data_sync_service.DataSyncService") as mock_sync_service:
            mock_sync_service.return_value.sync_project_from_filesystem.return_value = {"success": True}
            result = service.extract_clips("project-1", {})
        
        assert result["success"] is True
        assert result["result"]["clips_generated"] == 2
        mock_run_step6.assert_called_once_with(
            clips_with_titles_path=project_paths["metadata_dir"] / "step4_titles.json",
            collections_path=project_paths["metadata_dir"] / "step5_collections.json",
            input_video=project_paths["input_dir"] / "input.mp4",
            output_dir=project_paths["output_dir"],
            clips_dir=str(project_paths["clips_dir"]),
            collections_dir=str(project_paths["collections_dir"]),
            metadata_dir=str(project_paths["metadata_dir"])
        )


class TestVideoTasks:
    def test_extract_video_clips_task_updates_metadata(self, tmp_path):
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
        
        input_video = project_paths["input_dir"] / "input.mp4"
        input_video.touch()
        clip_output = project_paths["clips_dir"] / "clip-1_测试片段.mp4"
        
        clip_payload = [{"id": "clip-1", "title": "测试片段", "start_time": 2, "end_time": 6}]
        
        def fake_batch_extract(_input_video, _clip_data):
            clip_output.parent.mkdir(parents=True, exist_ok=True)
            clip_output.touch()
            return [clip_output]
        
        with patch("backend.tasks.video.config_manager.get_project_paths", return_value=project_paths), \
             patch.object(VideoProcessor, "batch_extract_clips", side_effect=fake_batch_extract):
            result = extract_video_clips.run("project-1", clip_payload)
        
        saved_metadata = json.loads((project_paths["metadata_dir"] / "clips_metadata.json").read_text(encoding="utf-8"))
        assert result["success"] is True
        assert result["clips_generated"] == 1
        assert result["clip_paths"] == [str(clip_output)]
        assert saved_metadata[0]["video_path"] == str(clip_output)
        assert saved_metadata[0]["status"] == "completed"
        assert saved_metadata[0]["duration_seconds"] == 4.0
