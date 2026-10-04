from types import SimpleNamespace
from unittest import mock

import pytest

from src import pipeline


@pytest.mark.parametrize("partial", [False, True])
def test_lazy_cuda_failure_restarts_on_cpu_and_discards_partial_output(partial):
    gpu_segment = SimpleNamespace(text="partial GPU result")
    cpu_segment = SimpleNamespace(text="complete CPU result")

    def broken_segments():
        if partial:
            yield gpu_segment
        raise RuntimeError("Library cublas64_12.dll is not found or cannot be loaded")

    gpu = mock.Mock()
    gpu.transcribe.return_value = (broken_segments(), "gpu-info")
    cpu = mock.Mock()
    cpu.transcribe.return_value = (iter([cpu_segment]), "cpu-info")
    with mock.patch.object(pipeline, "_get_whisper_model", return_value=(gpu, "cuda", "float16")), mock.patch.object(
        pipeline, "_load_whisper_model", return_value=cpu
    ) as load, mock.patch.object(pipeline, "_WHISPER_CUDA_FAILED", False):
        segments, info = pipeline._transcribe_whisper("fixture.wav", word_timestamps=True, beam_size=1)
        assert pipeline._WHISPER_CUDA_FAILED is True
        load.assert_called_once_with(pipeline.get_whisper_model_source(), "cpu", "int8")
        cpu.transcribe.assert_called_once_with("fixture.wav", word_timestamps=True, beam_size=1)
    assert segments == [cpu_segment] and info == "cpu-info"


@pytest.mark.parametrize("device,error", [("cuda", "Invalid audio data"), ("cpu", "CPU inference failed")])
def test_unrelated_or_cpu_failure_does_not_retry(device, error):
    model = mock.Mock()
    model.transcribe.side_effect = RuntimeError(error)
    with mock.patch.object(pipeline, "_get_whisper_model", return_value=(model, device, "int8")), mock.patch.object(
        pipeline, "_load_whisper_model"
    ) as load:
        with pytest.raises(RuntimeError, match=error):
            pipeline._transcribe_whisper("fixture.wav", beam_size=1)
        load.assert_not_called()
