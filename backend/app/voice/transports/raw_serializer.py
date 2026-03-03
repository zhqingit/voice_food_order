"""Raw binary serializer for the pipecat WebSocket transport.

Incoming binary messages → InputAudioRawFrame (PCM16 16kHz mono).
Outgoing OutputAudioRawFrame → raw bytes (WAV wrapping handled by transport).
Text messages are ignored (the Flutter client only sends binary audio).
"""

from __future__ import annotations

try:
    from pipecat.frames.frames import Frame, InputAudioRawFrame, OutputAudioRawFrame
    from pipecat.serializers.base_serializer import FrameSerializer
except ImportError:  # pragma: no cover
    FrameSerializer = object
    Frame = None
    InputAudioRawFrame = None
    OutputAudioRawFrame = None


class RawAudioSerializer(FrameSerializer):
    """Minimal serializer: binary ↔ audio frames, no protobuf wrapping."""

    def __init__(self, *, sample_rate: int = 16000, num_channels: int = 1):
        super().__init__()
        self._sample_rate = sample_rate
        self._num_channels = num_channels

    async def serialize(self, frame: Frame) -> str | bytes | None:
        if isinstance(frame, OutputAudioRawFrame):
            return bytes(frame.audio)
        return None

    async def deserialize(self, data: str | bytes) -> Frame | None:
        if isinstance(data, (bytes, bytearray)):
            return InputAudioRawFrame(
                audio=bytes(data),
                sample_rate=self._sample_rate,
                num_channels=self._num_channels,
            )
        return None
