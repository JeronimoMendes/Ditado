from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class Utterance:
    speaker: int
    text: str
    start: float
    end: float


@dataclass
class TranscriptResult:
    utterances: list[Utterance]
    raw: dict[str, Any]


class TranscriptionProvider(Protocol):
    async def transcribe(self, audio_data: bytes, filename: str) -> TranscriptResult: ...
