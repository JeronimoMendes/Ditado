import os

from deepgram import DeepgramClient, PrerecordedOptions

from .base import TranscriptResult, Utterance


class DeepgramProvider:
    def __init__(self) -> None:
        api_key = os.environ["DEEPGRAM_API_KEY"]
        self.client = DeepgramClient(api_key)

    async def transcribe(self, audio_data: bytes, filename: str) -> TranscriptResult:
        source = {"buffer": audio_data}
        options = PrerecordedOptions(
            model="nova-3",
            language="pt",
            diarize=True,
            punctuate=True,
            smart_format=True,
            utterances=True,
        )
        response = await self.client.listen.asyncrest.v("1").transcribe_file(source, options)
        raw = response.to_dict()

        utterances = [
            Utterance(
                speaker=u["speaker"],
                text=u["transcript"],
                start=u["start"],
                end=u["end"],
            )
            for u in raw.get("results", {}).get("utterances", [])
        ]

        return TranscriptResult(utterances=utterances, raw=raw)
