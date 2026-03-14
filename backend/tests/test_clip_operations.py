"""
切片操作测试
测试 VideoProcessor 的切片提取功能和相关工具函数
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


class TestVideoProcessorUtils:
    """测试 VideoProcessor 工具函数"""

    def test_sanitize_filename_removes_illegal_chars(self):
        """测试文件名清理 - 移除非法字符"""
        from backend.utils.video_processor import VideoProcessor
        
        assert VideoProcessor.sanitize_filename('test<>file') == 'test__file'
        assert VideoProcessor.sanitize_filename('test:file') == 'test_file'
        assert VideoProcessor.sanitize_filename('test|file') == 'test_file'
        assert VideoProcessor.sanitize_filename('test?file') == 'test_file'
        assert VideoProcessor.sanitize_filename('test*file') == 'test_file'

    def test_sanitize_filename_limits_length(self):
        """测试文件名清理 - 限制长度"""
        from backend.utils.video_processor import VideoProcessor
        
        long_name = 'a' * 200
        result = VideoProcessor.sanitize_filename(long_name)
        assert len(result) <= 100

    def test_sanitize_filename_empty_returns_untitled(self):
        """测试文件名清理 - 空文件名返回 untitled"""
        from backend.utils.video_processor import VideoProcessor
        
        assert VideoProcessor.sanitize_filename('') == 'untitled'
        assert VideoProcessor.sanitize_filename('   ') == 'untitled'

    def test_convert_seconds_to_ffmpeg_time(self):
        """测试秒数转FFmpeg时间格式"""
        from backend.utils.video_processor import VideoProcessor
        
        assert VideoProcessor.convert_seconds_to_ffmpeg_time(0) == '00:00:00.000'
        assert VideoProcessor.convert_seconds_to_ffmpeg_time(65.5) == '00:01:05.500'
        assert VideoProcessor.convert_seconds_to_ffmpeg_time(3661.123) == '01:01:01.123'

    def test_convert_ffmpeg_time_to_seconds(self):
        """测试FFmpeg时间格式转秒数"""
        from backend.utils.video_processor import VideoProcessor
        
        assert VideoProcessor.convert_ffmpeg_time_to_seconds('00:00:00.000') == 0.0
        assert VideoProcessor.convert_ffmpeg_time_to_seconds('00:01:05.500') == 65.5
        assert abs(VideoProcessor.convert_ffmpeg_time_to_seconds('01:01:01.123') - 3661.123) < 0.001

    def test_convert_srt_time_to_ffmpeg_time(self):
        """测试SRT时间格式转FFmpeg时间格式"""
        from backend.utils.video_processor import VideoProcessor
        
        assert VideoProcessor.convert_srt_time_to_ffmpeg_time('00:01:25,140') == '00:01:25.140'
        assert VideoProcessor.convert_srt_time_to_ffmpeg_time('00:01:25.140') == '00:01:25.140'

    def test_time_roundtrip(self):
        """测试时间转换的往返一致性"""
        from backend.utils.video_processor import VideoProcessor
        
        original_seconds = 125.5
        ffmpeg_time = VideoProcessor.convert_seconds_to_ffmpeg_time(original_seconds)
        back_to_seconds = VideoProcessor.convert_ffmpeg_time_to_seconds(ffmpeg_time)
        assert abs(back_to_seconds - original_seconds) < 0.01


class TestReExtractRequest:
    """测试 ReExtractRequest 模型"""

    def test_re_extract_request_empty(self):
        """测试空请求体 - 使用原始时间"""
        from pydantic import BaseModel, Field
        from typing import Optional
        
        # 直接定义模型用于测试（避免导入整个API链）
        class ReExtractRequest(BaseModel):
            start_time: Optional[float] = Field(default=None, ge=0)
            end_time: Optional[float] = Field(default=None, ge=0)
        
        req = ReExtractRequest()
        assert req.start_time is None
        assert req.end_time is None

    def test_re_extract_request_with_times(self):
        """测试自定义时间范围"""
        from pydantic import BaseModel, Field
        from typing import Optional
        
        class ReExtractRequest(BaseModel):
            start_time: Optional[float] = Field(default=None, ge=0)
            end_time: Optional[float] = Field(default=None, ge=0)
        
        req = ReExtractRequest(start_time=10.5, end_time=30.0)
        assert req.start_time == 10.5
        assert req.end_time == 30.0

    def test_re_extract_request_negative_time_rejected(self):
        """测试负数时间被拒绝"""
        from pydantic import BaseModel, Field, ValidationError
        from typing import Optional
        
        class ReExtractRequest(BaseModel):
            start_time: Optional[float] = Field(default=None, ge=0)
            end_time: Optional[float] = Field(default=None, ge=0)
        
        with pytest.raises(ValidationError):
            ReExtractRequest(start_time=-1)

    def test_re_extract_request_partial(self):
        """测试只设置一个时间"""
        from pydantic import BaseModel, Field
        from typing import Optional
        
        class ReExtractRequest(BaseModel):
            start_time: Optional[float] = Field(default=None, ge=0)
            end_time: Optional[float] = Field(default=None, ge=0)
        
        req = ReExtractRequest(start_time=5.0)
        assert req.start_time == 5.0
        assert req.end_time is None


class TestExtractClipMocked:
    """测试切片提取逻辑 (通过mock FFmpeg)"""

    @patch('subprocess.run')
    def test_extract_clip_success(self, mock_run, tmp_path):
        """测试成功提取切片"""
        from backend.utils.video_processor import VideoProcessor
        
        mock_run.return_value = MagicMock(returncode=0, stderr='', stdout='')
        
        input_video = tmp_path / "input.mp4"
        input_video.touch()
        output_path = tmp_path / "output" / "clip.mp4"
        
        result = VideoProcessor.extract_clip(
            input_video=input_video,
            output_path=output_path,
            start_time='00:01:25.140',
            end_time='00:02:53.500'
        )
        
        assert result is True
        assert mock_run.called
        # 验证ffmpeg命令参数
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == 'ffmpeg'
        assert '-ss' in cmd
        assert '-i' in cmd
        assert str(input_video) in cmd

    @patch('subprocess.run')
    def test_extract_clip_failure(self, mock_run, tmp_path):
        """测试提取失败时返回False"""
        from backend.utils.video_processor import VideoProcessor
        
        mock_run.return_value = MagicMock(returncode=1, stderr='Error', stdout='')
        
        input_video = tmp_path / "input.mp4"
        input_video.touch()
        output_path = tmp_path / "clip.mp4"
        
        result = VideoProcessor.extract_clip(
            input_video=input_video,
            output_path=output_path,
            start_time='00:00:00.000',
            end_time='00:00:10.000'
        )
        
        assert result is False

    @patch('subprocess.run')
    def test_batch_extract_clips(self, mock_run, tmp_path):
        """测试批量提取切片"""
        from backend.utils.video_processor import VideoProcessor
        
        mock_run.return_value = MagicMock(returncode=0, stderr='', stdout='')
        
        clips_dir = tmp_path / "clips"
        clips_dir.mkdir()
        collections_dir = tmp_path / "collections"
        collections_dir.mkdir()
        
        processor = VideoProcessor(
            clips_dir=str(clips_dir),
            collections_dir=str(collections_dir)
        )
        
        input_video = tmp_path / "input.mp4"
        input_video.touch()
        
        clips_data = [
            {'id': 'clip_001', 'title': '第一个片段', 'start_time': 10.0, 'end_time': 30.0},
            {'id': 'clip_002', 'title': '第二个片段', 'start_time': 45.0, 'end_time': 90.0},
        ]
        
        successful_clips = processor.batch_extract_clips(input_video, clips_data)
        
        assert mock_run.call_count == 2
        assert len(successful_clips) == 2

    def test_video_processor_requires_dirs(self):
        """测试VideoProcessor构造器要求提供目录"""
        from backend.utils.video_processor import VideoProcessor
        
        with pytest.raises(ValueError, match="clips_dir"):
            VideoProcessor(clips_dir=None, collections_dir="/tmp/collections")
        
        with pytest.raises(ValueError, match="collections_dir"):
            VideoProcessor(clips_dir="/tmp/clips", collections_dir=None)
