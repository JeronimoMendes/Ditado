import os

import httpx

from .base import TranscriptResult, Utterance

API_URL = "https://api.elevenlabs.io/v1/speech-to-text"


class ElevenLabsProvider:
    def __init__(self) -> None:
        self.api_key = os.environ["ELEVENLABS_API_KEY"]

    async def transcribe(self, audio_data: bytes, filename: str) -> TranscriptResult:
        async with httpx.AsyncClient(timeout=600) as client:
            resp = await client.post(
                API_URL,
                headers={"xi-api-key": self.api_key},
                files={"file": (filename, audio_data)},
                data={
                    "model_id": "scribe_v2",
                    "language_code": "por",
                    "diarize": "true",
                    "tag_audio_events": "false",
                    "timestamps_granularity": "word",
                },
            )
            resp.raise_for_status()
            raw = resp.json()

        utterances = _group_words_into_utterances(raw.get("words", []))
        return TranscriptResult(utterances=utterances, raw=raw)


def _speaker_to_int(speaker_id: str | None) -> int:
    if not speaker_id:
        return 0
    # speaker_id is like "speaker_0", "speaker_1", etc.
    try:
        return int(speaker_id.rsplit("_", 1)[-1])
    except ValueError:
        return 0


def _group_words_into_utterances(words: list[dict]) -> list[Utterance]:
    """Group consecutive words by the same speaker into utterances."""
    if not words:
        return []

    utterances: list[Utterance] = []
    current_speaker = _speaker_to_int(words[0].get("speaker_id"))
    current_start = words[0].get("start", 0.0)
    current_texts: list[str] = []
    current_end = words[0].get("end", 0.0)

    for w in words:
        if w.get("type") != "word":
            continue
        speaker = _speaker_to_int(w.get("speaker_id"))
        if speaker != current_speaker and current_texts:
            utterances.append(Utterance(
                speaker=current_speaker,
                text=" ".join(current_texts),
                start=current_start,
                end=current_end,
            ))
            current_speaker = speaker
            current_start = w.get("start", 0.0)
            current_texts = []

        current_texts.append(w["text"])
        current_end = w.get("end", 0.0)

    if current_texts:
        utterances.append(Utterance(
            speaker=current_speaker,
            text=" ".join(current_texts),
            start=current_start,
            end=current_end,
        ))

    return utterances
