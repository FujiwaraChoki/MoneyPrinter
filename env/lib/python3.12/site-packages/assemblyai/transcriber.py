from __future__ import annotations

import concurrent.futures
import functools
import json
import os
import queue
import threading
import time
from typing import (
    Any,
    BinaryIO,
    Callable,
    Dict,
    Generator,
    Iterable,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)
from urllib.parse import urlencode, urlparse

import httpx
import websockets
import websockets.exceptions
from typing_extensions import Self
from websockets.sync.client import connect as websocket_connect

from . import api, lemur, types
from . import client as _client


class _TranscriptImpl:
    def __init__(
        self,
        *,
        client: _client.Client,
        transcript_id: Optional[str],
    ) -> None:
        self._client = client
        self.transcript_id = transcript_id

        self.transcript: Optional[types.TranscriptResponse] = None

    @property
    def config(self) -> types.TranscriptionConfig:
        "Returns the configuration from the internal Transcript object"
        if self.transcript is None:
            raise ValueError(
                "Canot access the configuration. The internal Transcript object is None."
            )

        return types.TranscriptionConfig(
            **self.transcript.dict(
                include=set(types.RawTranscriptionConfig.__fields__),
                exclude_none=True,
            )
        )

    @classmethod
    def from_response(
        cls,
        *,
        client: _client.Client,
        response: types.TranscriptResponse,
    ) -> Self:
        self = cls(
            client=client,
            transcript_id=response.id,
        )
        self.transcript = response

        return self

    def wait_for_completion(self) -> Self:
        """
        polls the given transcript until we have a status other than `processing` or `queued`
        """
        if not self.transcript_id:
            raise ValueError(
                "Cannot wait for completion. The internal transcript ID is None."
            )

        while True:
            # No try-except - if there is an HTTP error then surface it to user
            self.transcript = api.get_transcript(
                self._client.http_client,
                self.transcript_id,
            )

            if self.transcript.status in (
                types.TranscriptStatus.completed,
                types.TranscriptStatus.error,
            ):
                break

            time.sleep(self._client.settings.polling_interval)

        return self

    def export_subtitles_srt(
        self,
        *,
        chars_per_caption: Optional[int],
    ) -> str:
        if not self.transcript or not self.transcript.id:
            raise ValueError(
                "Cannot export subtitles. The internal Transcript object is None."
            )

        return api.export_subtitles_srt(
            client=self._client.http_client,
            transcript_id=self.transcript.id,
            chars_per_caption=chars_per_caption,
        )

    def export_subtitles_vtt(
        self,
        *,
        chars_per_caption: Optional[int],
    ) -> str:
        if not self.transcript or not self.transcript.id:
            raise ValueError(
                "Cannot export subtitles. The internal Transcript object is None."
            )

        return api.export_subtitles_vtt(
            client=self._client.http_client,
            transcript_id=self.transcript.id,
            chars_per_caption=chars_per_caption,
        )

    def word_search(
        self,
        *,
        words: List[str],
    ) -> List[types.WordSearchMatch]:
        if not self.transcript or not self.transcript.id:
            raise ValueError(
                "Cannot perform word search. The internal Transcript object is None."
            )

        response = api.word_search(
            client=self._client.http_client,
            transcript_id=self.transcript.id,
            words=words,
        )

        return response.matches

    def get_sentences(self) -> List[types.Sentence]:
        if not self.transcript or not self.transcript.id:
            raise ValueError(
                "Cannot get sentences. The internal Transcript object is None."
            )

        response = api.get_sentences(
            client=self._client.http_client,
            transcript_id=self.transcript.id,
        )

        return response.sentences

    def get_paragraphs(self) -> List[types.Paragraph]:
        if not self.transcript or not self.transcript.id:
            raise ValueError(
                "Cannot get paragraphs. The internal Transcript object is None."
            )

        response = api.get_paragraphs(
            client=self._client.http_client,
            transcript_id=self.transcript.id,
        )

        return response.paragraphs

    @functools.lru_cache
    def get_redacted_audio_url(self) -> str:
        """
        Retrieve the URL for the PII-redacted audio file, if `redact_pii_audio` was enabled on the `TranscriptionConfig`.
        Subsequent calls will return cached URL rather than requesting it from the API again.

        Returns: The URL of the redacted audio file.
        """
        if not self.config.redact_pii or not self.config.redact_pii_audio:
            raise ValueError(
                "Redacted audio is only available when `redact_pii` and `redact_pii_audio` are set to `True`."
            )

        if not self.transcript_id:
            raise ValueError(
                "Cannot get redacted audio url. The internal transcript ID is None."
            )

        while True:
            try:
                return api.get_redacted_audio(
                    client=self._client.http_client,
                    transcript_id=self.transcript_id,
                ).redacted_audio_url
            except types.RedactedAudioIncompleteError:
                time.sleep(self._client.settings.polling_interval)

    def save_redacted_audio(self, filepath: str):
        """
        Retrieve the PII-redacted audio file, if `redact_pii_audio` was enabled on the `TranscriptionConfig`

        Args:
            filepath: The path to save the redacted audio file to.
        """
        with httpx.stream(method="GET", url=self.get_redacted_audio_url()) as response:
            if response.status_code not in (httpx.codes.OK, httpx.codes.NOT_MODIFIED):
                raise types.RedactedAudioUnavailableError(
                    f"Fetching redacted audio failed with status code {response.status_code}",
                    response.status_code,
                )
            with open(filepath, "wb") as f:
                for chunk in response.iter_bytes():
                    f.write(chunk)

    @classmethod
    def delete_by_id(cls, transcript_id: str) -> types.Transcript:
        client = _client.Client.get_default()
        response = api.delete_transcript(
            client=client.http_client, transcript_id=transcript_id
        )

        return Transcript.from_response(client=client, response=response)


class Transcript(types.Sourcable):
    """
    Transcript object to perform operations on the actual transcript.
    """

    def __init__(
        self,
        transcript_id: Optional[str],
        client: Optional[_client.Client] = None,
    ) -> None:
        self._client = client or _client.Client.get_default()

        self._impl = _TranscriptImpl(
            client=self._client,
            transcript_id=transcript_id,
        )
        self._executor = concurrent.futures.ThreadPoolExecutor()

    def wait_for_completion(self) -> Self:
        self._impl.wait_for_completion()

        return self

    def wait_for_completion_async(
        self,
    ) -> concurrent.futures.Future[Self]:
        return self._executor.submit(self.wait_for_completion)

    @classmethod
    def from_response(
        cls,
        *,
        client: _client.Client,
        response: types.TranscriptResponse,
    ) -> Self:
        _impl = _TranscriptImpl.from_response(client=client, response=response)

        self = cls(
            client=client,
            transcript_id=response.id,
        )

        self._impl = _impl

        return self

    @classmethod
    def get_by_id(cls, transcript_id: str) -> Self:
        """Fetch an existing transcript. Blocks until the transcript is completed.

        Args:
            transcript_id: the id of the transcript to fetch

        Returns:
            The transcript object identified by the given id.
        """
        return cls(transcript_id=transcript_id).wait_for_completion()

    @classmethod
    def get_by_id_async(cls, transcript_id: str) -> concurrent.futures.Future[Self]:
        """Fetch an existing transcript asynchronously.

        Args:
            transcript_id: the id of the transcript to fetch

        Returns:
            A future that will resolve to the transcript object identified by the given id.
        """
        return cls(transcript_id=transcript_id).wait_for_completion_async()

    @classmethod
    def delete_by_id(cls, transcript_id: str) -> types.Transcript:
        """Delete an existing transcript. Blocks until the transcript is completed.

        Args:
            transcript_id: the id of the transcript to delete

        Returns:
            A transcript object identified by the given id, with relevant fields/attributes cleared.
        """
        return _TranscriptImpl.delete_by_id(transcript_id)

    @classmethod
    def delete_by_id_async(
        cls, transcript_id: str
    ) -> concurrent.futures.Future[types.Transcript]:
        """Delete an existing transcript asynchronously.

        Args:
            transcript_id: the id of the transcript to delete

        Returns:
            A future that will resolve to a transcript object identified by the given id, with relevant fields/attributes cleared.
        """

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future_transcript = executor.submit(
                _TranscriptImpl.delete_by_id, transcript_id
            )
        return future_transcript

    @property
    def id(self) -> Optional[str]:
        "The unique identifier of your transcription"

        return self._impl.transcript_id

    @property
    def config(self) -> types.TranscriptionConfig:
        "Return the corresponding configurations for the given transcript."

        return self._impl.config

    @property
    def json_response(self) -> Optional[dict]:
        "The full JSON response associated with the transcript."
        if not self._impl.transcript:
            raise ValueError("The internal Transcript object is None.")

        return self._impl.transcript.dict()

    @property
    def audio_url(self) -> str:
        "The corresponding audio url"
        if not self._impl.transcript:
            raise ValueError("The internal Transcript object is None.")

        return self._impl.transcript.audio_url

    @property
    def speech_model(self) -> Optional[str]:
        "The speech model used for the transcription"
        if not self._impl.transcript:
            raise ValueError("The internal Transcript object is None.")

        return self._impl.transcript.speech_model

    @property
    def text(self) -> Optional[str]:
        "The text transcription of your media file"
        if not self._impl.transcript:
            raise ValueError("The internal Transcript object is None.")

        return self._impl.transcript.text

    @property
    def summary(self) -> Optional[str]:
        "The summarization of the transcript"
        if not self._impl.transcript:
            raise ValueError("The internal Transcript object is None.")

        return self._impl.transcript.summary

    @property
    def chapters(self) -> Optional[List[types.Chapter]]:
        "The list of auto-chapters results"
        if not self._impl.transcript:
            raise ValueError("The internal Transcript object is None.")

        return self._impl.transcript.chapters

    @property
    def content_safety(self) -> Optional[types.ContentSafetyResponse]:
        "The results from the content safety analysis"
        if not self._impl.transcript:
            raise ValueError("The internal Transcript object is None.")

        return self._impl.transcript.content_safety_labels

    @property
    def sentiment_analysis(self) -> Optional[List[types.Sentiment]]:
        "The list of sentiment analysis results"
        if not self._impl.transcript:
            raise ValueError("The internal Transcript object is None.")

        return self._impl.transcript.sentiment_analysis_results

    @property
    def entities(self) -> Optional[List[types.Entity]]:
        "The list of entity detection results"
        if not self._impl.transcript:
            raise ValueError("The internal Transcript object is None.")

        return self._impl.transcript.entities

    @property
    def iab_categories(self) -> Optional[types.IABResponse]:
        "The results from the IAB category detection"
        if not self._impl.transcript:
            raise ValueError("The internal Transcript object is None.")

        return self._impl.transcript.iab_categories_result

    @property
    def auto_highlights(self) -> Optional[types.AutohighlightResponse]:
        "The results from the auto-highlights model"
        if not self._impl.transcript:
            raise ValueError("The internal Transcript object is None.")

        return self._impl.transcript.auto_highlights_result

    @property
    def status(self) -> types.TranscriptStatus:
        "The current status of the transcript"
        if not self._impl.transcript:
            raise ValueError("The internal Transcript object is None.")

        return self._impl.transcript.status

    @property
    def error(self) -> Optional[str]:
        "The error message in case the transcription fails"
        if not self._impl.transcript:
            raise ValueError("The internal Transcript object is None.")

        return self._impl.transcript.error

    @property
    def words(self) -> Optional[List[types.Word]]:
        "The list of words in the transcript"
        if not self._impl.transcript:
            raise ValueError("The internal Transcript object is None.")

        return self._impl.transcript.words

    @property
    def utterances(self) -> Optional[List[types.Utterance]]:
        """
        When `dual_channel` or `speaker_labels` is enabled,
        a list of utterances in the transcript.
        """
        if not self._impl.transcript:
            raise ValueError("The internal Transcript object is None.")

        return self._impl.transcript.utterances

    @property
    def confidence(self) -> Optional[float]:
        "The confidence our model has in the transcribed text, between 0 and 1"
        if not self._impl.transcript:
            raise ValueError("The internal Transcript object is None.")

        return self._impl.transcript.confidence

    @property
    def audio_duration(self) -> Optional[int]:
        "The duration of the audio in seconds"
        if not self._impl.transcript:
            raise ValueError("The internal Transcript object is None.")

        return self._impl.transcript.audio_duration

    @property
    def webhook_status_code(self) -> Optional[int]:
        "The status code we received from your server when delivering your webhook"
        if not self._impl.transcript:
            raise ValueError("The internal Transcript object is None.")

        return self._impl.transcript.webhook_status_code

    @property
    def webhook_auth(self) -> Optional[bool]:
        "Whether the webhook was sent with an HTTP authentication header"
        if not self._impl.transcript:
            raise ValueError("The internal Transcript object is None.")

        return self._impl.transcript.webhook_auth

    @property
    def lemur(self) -> lemur.Lemur:
        """
        Access AssemblyAI's LeMUR features.
        """

        return lemur.Lemur(
            client=self._client,
            sources=[types.LemurSource(self)],
        )

    def export_subtitles_srt(
        self,
        chars_per_caption: Optional[int] = None,
    ) -> str:
        """
        You can export your complete transcripts in SRT format,
        to be plugged into a video player for subtitles and closed captions.

        Args:
            chars_per_caption: To control the maximum number of characters per caption

        Returns: A string containing the all subtitles in SRT format.
        """

        return self._impl.export_subtitles_srt(
            chars_per_caption=chars_per_caption,
        )

    def export_subtitles_vtt(
        self,
        chars_per_caption: Optional[int] = None,
    ) -> str:
        """
        You can export your complete transcripts in VTT format,
        to be plugged into a video player for subtitles and closed captions.

        Args:
            chars_per_caption: To control the maximum number of characters per caption

        Returns: A string containing the all subtitles in VTT format.
        """

        return self._impl.export_subtitles_vtt(
            chars_per_caption=chars_per_caption,
        )

    def word_search(
        self,
        words: List[str],
    ) -> List[types.WordSearchMatch]:
        """
        Once a transcript has been completed, you can search through the transcript for a specific set of keywords.
        You can search for individual words, numbers, or phrases containing up to five words or numbers.

        Args:
            words: A list of words, numbers, or phrases (containing up to five words or numbers)

        Returns: A list of matches
        """

        return self._impl.word_search(
            words=words,
        )

    def get_sentences(
        self,
    ) -> List[types.Sentence]:
        """
        Semantically segment your transcript into sentences to create more reader-friendly transcripts.

        Returns: A list of sentence objects.
        """

        return self._impl.get_sentences()

    def get_paragraphs(
        self,
    ) -> List[types.Paragraph]:
        """
        Semantically segment your transcript into paragraphs to create more reader-friendly transcripts.

        Returns: A list of paragraph objects.
        """

        return self._impl.get_paragraphs()

    def get_redacted_audio_url(self) -> str:
        """
        Retrieve the URL for the PII-redacted audio file, if `redact_pii_audio` was enabled on the `TranscriptionConfig`.
        Subsequent calls will return cached URL rather than requesting it from the API again.

        Returns: The URL of the redacted audio file.
        """
        return self._impl.get_redacted_audio_url()

    def save_redacted_audio(self, filepath: str):
        """
        Retrieve the PII-redacted audio file, if `redact_pii_audio` was enabled on the `TranscriptionConfig`

        Args:
            filepath: The path to save the redacted audio file to.
        """
        return self._impl.save_redacted_audio(filepath=filepath)


class _TranscriptGroupImpl:
    def __init__(
        self,
        *,
        transcript_ids: List[str],
        client: _client.Client,
    ) -> None:
        self._client = client
        self.transcripts: List[Transcript] = []

        for transcript_id in transcript_ids:
            self.add_transcript(transcript_id)

    @property
    def transcript_ids(self) -> List[str]:
        if any(t.id is None for t in self.transcripts):
            raise ValueError("All transcripts must have a transcript ID.")
        return [
            t.id for t in self.transcripts if t.id
        ]  # include the if check for mypy type checker

    def add_transcript(self, transcript: Union[Transcript, str]) -> None:
        if isinstance(transcript, Transcript):
            self.transcripts.append(transcript)
        elif isinstance(transcript, str):
            self.transcripts.append(
                Transcript(
                    client=self._client,
                    transcript_id=transcript,
                )
            )
        else:
            raise TypeError("Unsupported type for `transcript`")

    def wait_for_completion(
        self, return_failures
    ) -> Union[None, List[types.AssemblyAIError]]:
        transcripts: List[Transcript] = []
        failures: List[types.AssemblyAIError] = []

        future_transcripts: Set[concurrent.futures.Future[Transcript]] = set()

        for transcript in self.transcripts:
            future = transcript.wait_for_completion_async()
            future_transcripts.add(future)

        finished_futures, _ = concurrent.futures.wait(future_transcripts)

        for future in finished_futures:
            try:
                transcripts.append(future.result())
            except types.TranscriptError as e:
                failures.append(e)

        self.transcripts = transcripts

        if return_failures is True:
            return failures
        return None


class TranscriptGroup:
    """
    A group of transcripts.

    Used when transcribing multiple transcripts at once.
    """

    def __init__(
        self,
        transcript_ids: List[str] = [],
        client: Optional[_client.Client] = None,
    ) -> None:
        self._client = client or _client.Client.get_default()

        self._impl = _TranscriptGroupImpl(
            transcript_ids=transcript_ids,
            client=self._client,
        )
        self._executor = concurrent.futures.ThreadPoolExecutor()

    @property
    def transcripts(self) -> List[Transcript]:
        """
        Returns the list of the transcripts within the `TranscriptGroup`
        """

        return self._impl.transcripts

    def __iter__(self) -> Iterator[Transcript]:
        """
        Iterate over the transcripts within the `TranscriptGroup`
        """

        return iter(self.transcripts)

    @classmethod
    def get_by_ids(
        cls, transcript_ids: List[str]
    ) -> Union[Self, Tuple[Self, List[types.AssemblyAIError]]]:
        return cls(transcript_ids=transcript_ids).wait_for_completion()

    @classmethod
    def get_by_ids_async(
        cls, transcript_ids: List[str]
    ) -> concurrent.futures.Future[
        Union[Self, Tuple[Self, List[types.AssemblyAIError]]]
    ]:
        return cls(transcript_ids=transcript_ids).wait_for_completion_async()

    @property
    def status(self) -> types.TranscriptStatus:
        """
        Return the status of the `TranscriptGroup`.

        e.g. if any of the transcripts is in `error` status, the whole `TranscriptGroup` will be in `error` status.
        """

        all_status = {t.status for t in self.transcripts}

        if any(s == types.TranscriptStatus.error for s in all_status):
            return types.TranscriptStatus.error
        elif any(s == types.TranscriptStatus.queued for s in all_status):
            return types.TranscriptStatus.queued
        elif any(s == types.TranscriptStatus.processing for s in all_status):
            return types.TranscriptStatus.processing
        elif all(s == types.TranscriptStatus.completed for s in all_status):
            return types.TranscriptStatus.completed
        else:
            raise ValueError(f"Unexpected status type: {all_status}")

    @property
    def lemur(self) -> lemur.Lemur:
        """
        Access AssemblyAI's LeMUR functionality.
        """

        return lemur.Lemur(
            client=self._impl._client,
            sources=[types.LemurSource(t) for t in self.transcripts],
        )

    def add_transcript(
        self,
        transcript: Union[Transcript, str],
    ) -> Self:
        """
        Adds a transcript to the given `TranscriptGroup`

        Args:
            transcript: A `Transcript` object or the ID as a `str`
        """
        self._impl.add_transcript(transcript)

        return self

    def wait_for_completion(
        self,
        return_failures: Optional[bool] = False,
    ) -> Union[Self, Tuple[Self, List[types.AssemblyAIError]]]:
        """
        Polls each transcript within the `TranscriptGroup`.

        Note - if an HTTP error is encountered when waiting for a Transcript in the TranscriptGroup, it will be popped from the group and added to the list of failures.
        You can return this list of failures with `return_failures=True`.

        Args:
            return_failures: Whether to return a list of errors for transcripts that failed due to HTTP errors.
        """
        if return_failures is True:
            failures = self._impl.wait_for_completion(return_failures=return_failures)
            if failures is None:
                raise ValueError("return_failures was set but failures object is None")
            return self, failures

        self._impl.wait_for_completion(return_failures=return_failures)

        return self

    def wait_for_completion_async(
        self,
        return_failures: Optional[bool] = False,
    ) -> concurrent.futures.Future[
        Union[Self, Tuple[Self, List[types.AssemblyAIError]]],
    ]:
        return self._executor.submit(
            self.wait_for_completion, return_failures=return_failures
        )


class _TranscriberImpl:
    """
    Implementation of the Transcriber class.
    """

    def __init__(
        self,
        *,
        client: _client.Client,
        config: types.TranscriptionConfig,
    ) -> None:
        self._client = client
        self.config = config

    def upload_file(self, data: Union[str, BinaryIO]) -> str:
        if isinstance(data, str):
            with open(data, "rb") as audio_file:
                return api.upload_file(
                    client=self._client.http_client,
                    audio_file=audio_file,
                )
        else:
            return api.upload_file(
                client=self._client.http_client,
                audio_file=data,
            )

    def transcribe_url(
        self,
        *,
        url: str,
        config: types.TranscriptionConfig,
        poll: bool,
    ) -> Transcript:
        transcript_request = types.TranscriptRequest(
            audio_url=url,
            **config.raw.dict(exclude_none=True),
        )
        # No try-except - if there is an HTTP error raise it to the user
        transcript = Transcript.from_response(
            client=self._client,
            response=api.create_transcript(
                client=self._client.http_client,
                request=transcript_request,
            ),
        )

        if poll:
            return transcript.wait_for_completion()

        return transcript

    def transcribe_file(
        self,
        *,
        data: Union[str, BinaryIO],
        config: types.TranscriptionConfig,
        poll: bool,
    ) -> Transcript:
        # Note: If uploading fails, it should raise an Exception to the user, hence no try-except here.
        audio_url = self.upload_file(data)

        return self.transcribe_url(
            url=audio_url,
            config=config,
            poll=poll,
        )

    def transcribe(
        self,
        data: Union[str, BinaryIO],
        config: Optional[types.TranscriptionConfig],
        poll: bool,
    ) -> Transcript:
        if config is None:
            config = self.config

        if isinstance(data, str) and urlparse(data).scheme in {"http", "https"}:
            return self.transcribe_url(
                url=data,
                config=config,
                poll=poll,
            )

        return self.transcribe_file(
            data=data,
            config=config,
            poll=poll,
        )

    def transcribe_group(
        self,
        *,
        data: List[Union[str, BinaryIO]],
        config: Optional[types.TranscriptionConfig],
        poll: bool,
        return_failures: Optional[bool] = False,
    ) -> Union[TranscriptGroup, Tuple[TranscriptGroup, List[types.AssemblyAIError]]]:
        if config is None:
            config = self.config

        future_transcripts: Set[concurrent.futures.Future[Transcript]] = set()

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            for d in data:
                transcript_future = executor.submit(
                    self.transcribe,
                    data=d,
                    config=config,
                    poll=False,
                )

                future_transcripts.add(transcript_future)

        finished_futures, _ = concurrent.futures.wait(future_transcripts)

        transcript_group = TranscriptGroup(
            client=self._client,
        )
        failures: List[types.AssemblyAIError] = []

        for future in finished_futures:
            try:
                transcript_group.add_transcript(future.result())
            except types.TranscriptError as e:
                failures.append(e)

        if poll is True and return_failures is True:
            res = transcript_group.wait_for_completion(return_failures=return_failures)
            if not isinstance(res, tuple):
                raise ValueError(
                    "return_failures was set but did not receive failures object"
                )
            transcript_group, completion_failures = res
            failures.extend(completion_failures)
        elif poll:
            res = transcript_group.wait_for_completion(return_failures=return_failures)
            if not isinstance(res, TranscriptGroup):
                raise ValueError(
                    "return_failures was not set but did receive failures object"
                )
            transcript_group = res

        if return_failures is True:
            return transcript_group, failures
        else:
            return transcript_group

    def list_transcripts(
        self,
        params: Optional[types.ListTranscriptParameters],
    ) -> types.ListTranscriptResponse:
        return api.list_transcripts(client=self._client.http_client, params=params)


class Transcriber:
    """
    A transcriber used for transcribing URLs or local audio files.
    """

    def __init__(
        self,
        *,
        client: Optional[_client.Client] = None,
        config: Optional[types.TranscriptionConfig] = None,
        max_workers: Optional[int] = None,
    ) -> None:
        """
        Initializes the `Transcriber` with the given parameters.

        Args:
            `client`: The `Client` to use for the `Transcriber`. If `None` is given, the
                default settings for the `Client` will be used.
            `config`: The default configuration for the `Transcriber`. If `None` is given,
                the default configuration of a `TranscriptionConfig` will be used.
            `max_workers`: The maximum number of parallel jobs when using the `_async`
                methods on the `Transcriber`. By default it uses `os.cpu_count() - 1`

        Example:
            To use the `Transcriber` with the default settings, you can simply do:
            ```
            transcriber = aai.Transcriber()
            ```

            To use the `Transcriber` with a custom configuration, you can do:
            ```
            config = aai.TranscriptionConfig(punctuate=False, format_text=False)

            transcriber = aai.Transcriber(config=config)
            ```
        """
        self._client = client or _client.Client.get_default()

        self._impl = _TranscriberImpl(
            client=self._client,
            config=config or types.TranscriptionConfig(),
        )

        if not max_workers:
            cpu_count = os.cpu_count()
            if not cpu_count:
                max_workers = 1
            else:
                max_workers = max(1, cpu_count - 1)

        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers,
        )

    @property
    def config(self) -> types.TranscriptionConfig:
        """
        Returns the default configuration of the `Transcriber`.
        """
        return self._impl.config

    @config.setter
    def config(self, config: types.TranscriptionConfig) -> None:
        """
        Sets the default configuration of the `Transcriber`.

        Args:
            `config`: The new default configuration.
        """
        self._impl.config = config

    def upload_file(self, data: Union[str, BinaryIO]) -> str:
        """
        Uploads an audio file which can be specified as local path or binary object.

        Args:
            `data`: A local file (as path), or a binary object.

        Returns: The URL of the uploaded audio file.
        """
        return self._impl.upload_file(data=data)

    def upload_file_async(
        self, data: Union[str, BinaryIO]
    ) -> concurrent.futures.Future[str]:
        """
        Uploads an audio file which can be specified as local path or binary object.

        Args:
            `data`: A local file (as path), or a binary object.

        Returns: The URL of the uploaded audio file.
        """
        return self._executor.submit(
            self._impl.upload_file,
            data=data,
        )

    def submit(
        self,
        data: Union[str, BinaryIO],
        config: Optional[types.TranscriptionConfig] = None,
    ) -> Transcript:
        """
        Submits a transcription job without waiting for its completion.

        Args:
            data: An URL, a local file (as path), or a binary object.
            config: Transcription options and features. If `None` is given, the Transcriber's
                default configuration will be used.
        """
        return self._impl.transcribe(
            data=data,
            config=config,
            poll=False,
        )

    def submit_group(
        self,
        data: List[Union[str, BinaryIO]],
        config: Optional[types.TranscriptionConfig] = None,
        return_failures: Optional[bool] = False,
    ) -> Union[TranscriptGroup, Tuple[TranscriptGroup, List[types.AssemblyAIError]]]:
        """
        Submits multiple transcription jobs without waiting for their completion.

        Args:
            data: A list of local paths, URLs, or binary objects (can be mixed).
            config: Transcription options and features. If `None` is given, the Transcriber's
                default configuration will be used.
            return_failures: Whether to include a list of errors for transcriptions that failed due to HTTP errors
        """
        return self._impl.transcribe_group(
            data=data,
            config=config,
            poll=False,
            return_failures=return_failures,
        )

    def transcribe(
        self,
        data: Union[str, BinaryIO],
        config: Optional[types.TranscriptionConfig] = None,
    ) -> Transcript:
        """
        Transcribes an audio file which can be specified as local path, URL, or binary object.

        Args:
            data: An URL, a local file (as path), or a binary object.
            config: Transcription options and features. If `None` is given, the Transcriber's
                default configuration will be used.
        """

        return self._impl.transcribe(
            data=data,
            config=config,
            poll=True,
        )

    def transcribe_async(
        self,
        data: Union[str, BinaryIO],
        config: Optional[types.TranscriptionConfig] = None,
    ) -> concurrent.futures.Future[Transcript]:
        """
        Transcribes an audio file which can be specified as local path, URL, or binary object.

        Args:
            data: An URL, a local file (as path), or a binary object.
            config: Transcription options and features. If `None` is given, the Transcriber's
                default configuration will be used.
        """

        return self._executor.submit(
            self._impl.transcribe,
            data=data,
            config=config,
            poll=True,
        )

    def transcribe_group(
        self,
        data: List[Union[str, BinaryIO]],
        config: Optional[types.TranscriptionConfig] = None,
        return_failures: Optional[bool] = False,
    ) -> Union[TranscriptGroup, Tuple[TranscriptGroup, List[types.AssemblyAIError]]]:
        """
        Transcribes a list of files (as local paths, URLs, or binary objects).

        Args:
            data: A list of local paths, URLs, or binary objects (can be mixed).
            config: Transcription options and features. If `None` is given, the Transcriber's
                default configuration will be used.
            return_failures: Whether to include a list of errors for transcriptions that failed due to HTTP errors
        """

        return self._impl.transcribe_group(
            data=data,
            config=config,
            poll=True,
            return_failures=return_failures,
        )

    def transcribe_group_async(
        self,
        data: List[Union[str, BinaryIO]],
        config: Optional[types.TranscriptionConfig] = None,
        return_failures: Optional[bool] = False,
    ) -> concurrent.futures.Future[
        Union[TranscriptGroup, Tuple[TranscriptGroup, List[types.AssemblyAIError]]]
    ]:
        """
        Transcribes a list of files (as local paths, URLs, or binary objects) asynchronously.

        Args:
            data: A list of local paths, URLs, or binary objects (can be mixed).
            config: Transcription options and features. If `None` is given, the Transcriber's
                default configuration will be used.
            return_failures: Whether to include a list of errors for transcriptions that failed due to HTTP errors
        """

        return self._executor.submit(
            self._impl.transcribe_group,
            data=data,
            config=config,
            poll=True,
            return_failures=return_failures,
        )

    def list_transcripts(
        self,
        params: Optional[types.ListTranscriptParameters] = None,
    ) -> types.ListTranscriptResponse:
        """
        Retrieve a list of transcripts that were created. Transcripts are sorted from newest to oldest.

        Args:
            params: The parameters to filter the transcript list by.

        Returns: A page with a list of transcripts along with page details.

        To paginate over all pages, you can set the `ListTranscriptParameters.before_id`
        to the `before_id` of the `prev_url`. Example:
        ```
        transcriber = aai.Transcriber()
        params = aai.ListTranscriptParameters()
        page = transcriber.list_transcripts(params)
        while page.page_details.before_id_of_prev_url is not None:
            params.before_id = page.page_details.before_id_of_prev_url
            page = transcriber.list_transcripts(params)
        ```
        """
        return self._impl.list_transcripts(params=params)

    def list_transcripts_async(
        self,
        params: Optional[types.ListTranscriptParameters] = None,
    ) -> concurrent.futures.Future[types.ListTranscriptResponse]:
        """
        Retrieve a list of transcripts that were created. Transcripts are sorted from newest to oldest.

        Args:
            params: The parameters to filter the transcript list by.

        Returns: A page with a list of transcripts along with page details.
        """
        return self._executor.submit(self._impl.list_transcripts, params=params)


class _RealtimeTranscriberImpl:
    def __init__(
        self,
        *,
        on_data: Callable[[types.RealtimeTranscript], None],
        on_error: Callable[[types.RealtimeError], None],
        on_open: Optional[Callable[[types.RealtimeSessionOpened], None]],
        on_close: Optional[Callable[[], None]],
        sample_rate: int,
        word_boost: List[str],
        encoding: Optional[types.AudioEncoding] = None,
        token: Optional[str] = None,
        client: _client.Client,
        end_utterance_silence_threshold: Optional[int],
        disable_partial_transcripts: Optional[bool],
        on_extra_session_information: Optional[
            Callable[[types.RealtimeSessionInformation], None]
        ] = None,
    ) -> None:
        self._client = client
        self._websocket: Optional[websockets.sync.client.ClientConnection] = None

        self._on_open = on_open
        self._on_data = on_data
        self._on_error = on_error
        self._on_close = on_close
        self._sample_rate = sample_rate
        self._word_boost = word_boost
        self._encoding = encoding
        self._token = token
        self._end_utterance_silence_threshold = end_utterance_silence_threshold
        self._disable_partial_transcripts = disable_partial_transcripts
        self._on_extra_session_information = on_extra_session_information

        self._write_queue: queue.Queue[Union[bytes, Dict]] = queue.Queue()
        self._write_thread = threading.Thread(target=self._write)
        self._read_thread = threading.Thread(target=self._read)
        self._stop_event = threading.Event()

    def connect(
        self,
        timeout: Optional[float],
    ) -> None:
        """
        Connects to the real-time service.

        Args:
            `timeout`: The maximum time to wait for the connection to be established.
        """

        params: Dict[str, Any] = {
            "sample_rate": self._sample_rate,
        }
        if self._word_boost:
            params["word_boost"] = json.dumps(self._word_boost)
        if self._encoding:
            params["encoding"] = self._encoding.value
        if self._token:
            params["token"] = self._token
        if self._disable_partial_transcripts:
            params["disable_partial_transcripts"] = self._disable_partial_transcripts
        if self._on_extra_session_information:
            params["enable_extra_session_information"] = True

        websocket_base_url = self._client.settings.base_url.replace("https", "wss")

        additional_headers = None
        if self._token is None:
            additional_headers = {"Authorization": f"{self._client.settings.api_key}"}

        try:
            self._websocket = websocket_connect(
                f"{websocket_base_url}{api.ENDPOINT_REALTIME_WEBSOCKET}?{urlencode(params)}",
                additional_headers=additional_headers,
                open_timeout=timeout,
            )
        except Exception as exc:
            return self._on_error(
                types.RealtimeError(
                    f"Could not connect to the real-time service: {exc}"
                )
            )

        self._read_thread.start()
        self._write_thread.start()

        if self._end_utterance_silence_threshold is not None:
            self.configure_end_utterance_silence_threshold(
                self._end_utterance_silence_threshold
            )

    def stream(self, data: bytes) -> None:
        """
        Streams audio data to the real-time service by putting it into a queue.
        """

        self._write_queue.put(data)

    def configure_end_utterance_silence_threshold(
        self, threshold_milliseconds: int
    ) -> None:
        """
        Configures the end of utterance silence threshold.
        Can be called multiple times during a session at any point after the session starts.

        Args:
            `threshold_milliseconds`: The threshold in milliseconds.
        """

        self._write_queue.put(
            _RealtimeEndUtteranceSilenceThreshold(threshold_milliseconds).as_dict()
        )

    def force_end_utterance(self) -> None:
        """
        Forces the end of the current utterance.
        """

        self._write_queue.put(_RealtimeForceEndUtterance().as_dict())

    def close(self, terminate: bool = False) -> None:
        """
        Closes the connection to the real-time service gracefully.
        """
        if terminate and not self._stop_event.is_set():
            self._write_queue.put({"terminate_session": True})

        try:
            self._read_thread.join()
            self._write_thread.join()
            if self._websocket:
                self._websocket.close()
        except Exception:
            pass

        if self._on_close:
            self._on_close()

    def _read(self) -> None:
        """
        Reads messages from the real-time service.

        Must run in a separate thread to avoid blocking the main thread.
        """

        while not self._stop_event.is_set():
            if not self._websocket:
                raise ValueError("Websocket is None")

            try:
                recv_message = self._websocket.recv(timeout=1)
            except TimeoutError:
                continue
            except websockets.exceptions.ConnectionClosed as exc:
                return self._handle_error(exc)

            try:
                message = json.loads(recv_message)
            except json.JSONDecodeError as exc:
                self._on_error(
                    types.RealtimeError(
                        f"Could not decode message: {exc}",
                    )
                )
                continue

            self._handle_message(message)

    def _write(self) -> None:
        """
        Writes messages to the real-time service.

        Must run in a separate thread to avoid blocking the main thread.
        """

        while not self._stop_event.is_set():
            try:
                data = self._write_queue.get(timeout=1)
            except queue.Empty:
                continue

            try:
                if not self._websocket:
                    raise ValueError("websocket is None")
                elif isinstance(data, dict):
                    self._websocket.send(json.dumps(data))
                elif isinstance(data, bytes):
                    self._websocket.send(data)
                else:
                    raise ValueError("unsupported message type")
            except websockets.exceptions.ConnectionClosed as exc:
                return self._handle_error(exc)

    def _handle_message(
        self,
        message: Dict[str, Any],
    ) -> None:
        """
        Handles a message received from the real-time service by calling the appropriate
        callback.

        Args:
            `message`: The message to handle.
        """
        if "message_type" in message:
            if message["message_type"] == types.RealtimeMessageTypes.partial_transcript:
                self._on_data(types.RealtimePartialTranscript(**message))
            elif message["message_type"] == types.RealtimeMessageTypes.final_transcript:
                self._on_data(types.RealtimeFinalTranscript(**message))
            elif (
                message["message_type"] == types.RealtimeMessageTypes.session_begins
                and self._on_open
            ):
                self._on_open(types.RealtimeSessionOpened(**message))
            elif (
                message["message_type"] == types.RealtimeMessageTypes.session_terminated
            ):
                self._stop_event.set()
            elif (
                message["message_type"]
                == types.RealtimeMessageTypes.session_information
            ):
                if self._on_extra_session_information is not None:
                    self._on_extra_session_information(
                        types.RealtimeSessionInformation(**message)
                    )
        elif "error" in message:
            self._on_error(types.RealtimeError(message["error"]))

    def _handle_error(self, error: websockets.exceptions.ConnectionClosed) -> None:
        """
        Handles a WebSocket error by calling the appropriate callback.

        See a list of errors here:

        - https://www.iana.org/assignments/websocket/websocket.xhtml#close-code-number
        - https://www.assemblyai.com/docs/Guides/real-time_streaming_transcription#closing-and-status-codes
        """
        if (
            error.code >= 4000
            and error.code <= 4999
            and error.code in types.RealtimeErrorMapping
        ):
            error_message = types.RealtimeErrorMapping[error.code]
        else:
            error_message = error.reason

        if error.code != 1000:
            self._on_error(types.RealtimeError(error_message, error.code))

        self.close()

    @classmethod
    def create_temporary_token(
        cls,
        expires_in: int,
        timeout: Optional[float] = None,
    ) -> str:
        """
        Request a temporary authentication token.

        Args:
            expires_in: The amount of time until the token expires in seconds.
            timeout: The timeout in seconds to wait for a response.
                A `timeout` of `None` means no timeout.

        Returns: The temporary authentication token.
        """

        return api.create_temporary_token(
            client=_client.Client.get_default().http_client,
            request=types.RealtimeCreateTemporaryTokenRequest(
                expires_in=expires_in,
            ),
            http_timeout=timeout,
        )


class _RealtimeForceEndUtterance:
    def as_dict(self) -> Dict[str, bool]:
        return {
            "force_end_utterance": True,
        }


class _RealtimeEndUtteranceSilenceThreshold:
    def __init__(self, threshold_milliseconds: int) -> None:
        self._value = threshold_milliseconds

    @property
    def value(self) -> int:
        return self._value

    def as_dict(self) -> Dict[str, int]:
        return {"end_utterance_silence_threshold": self._value}


class RealtimeTranscriber:
    def __init__(
        self,
        *,
        on_data: Callable[[types.RealtimeTranscript], None],
        on_error: Callable[[types.RealtimeError], None],
        on_open: Optional[Callable[[types.RealtimeSessionOpened], None]] = None,
        on_close: Optional[Callable[[], None]] = None,
        sample_rate: int,
        word_boost: List[str] = [],
        encoding: Optional[types.AudioEncoding] = None,
        token: Optional[str] = None,
        client: Optional[_client.Client] = None,
        end_utterance_silence_threshold: Optional[int] = None,
        disable_partial_transcripts: Optional[bool] = None,
        on_extra_session_information: Optional[
            Callable[[types.RealtimeSessionInformation], None]
        ] = None,
    ) -> None:
        """
        Creates a new real-time transcriber.

        Args:
            `on_data`: The callback to call when a new transcript is received.
            `on_error`: The callback to call when an error occurs.
            `on_open`: (Optional) The callback to call when the connection to the real-time service opens.
            `on_close`: (Optional) The callback to call when the connection to the real-time service closes.
            `sample_rate`: The sample rate of the audio data.
            `word_boost`: (Optional) A list of words to boost transcription probability for.
            `encoding`: (Optional) The encoding of the audio data.
            `token`: (Optional) A temporary authentication token.
            `client`: (Optional) The client to use for the real-time service.
            `end_utterance_silence_threshold`: (Optional) The end utterance silence threshold in milliseconds.
            `disable_partial_transcripts`: (Optional) If set to `True`, only final transcripts will be received.
            `on_extra_session_information`: (Optional) The callback to call when a `SessionInformation` message is received.
                If this callback is set, the parameter `enable_extra_session_information` is sent to the API, and the client
                receives a `SessionInformation` message right before receiving the session termination message.
        """

        self._client = client or _client.Client.get_default(
            api_key_required=token is None
        )

        self._impl = _RealtimeTranscriberImpl(
            on_open=on_open,
            on_data=on_data,
            on_error=on_error,
            on_close=on_close,
            sample_rate=sample_rate,
            word_boost=word_boost,
            encoding=encoding,
            token=token,
            client=self._client,
            end_utterance_silence_threshold=end_utterance_silence_threshold,
            disable_partial_transcripts=disable_partial_transcripts,
            on_extra_session_information=on_extra_session_information,
        )

    def connect(
        self,
        timeout: Optional[float] = 10.0,
    ) -> None:
        """
        Connects to the real-time service.

        Args:
            `timeout`: The timeout in seconds to wait for the connection to be established.
                A `timeout` of `None` means no timeout.
        """

        self._impl.connect(timeout=timeout)

    def stream(
        self, data: Union[bytes, Generator[bytes, None, None], Iterable[bytes]]
    ) -> None:
        """
        Streams raw audio data to the real-time service.

        Args:
            `data`: Raw audio data in `bytes` or a generator/iterable of `bytes`.

        Note: Make sure that `data` matches the `sample_rate` that was given in the constructor.
        """
        if isinstance(data, bytes):
            self._impl.stream(data)
            return

        for chunk in data:
            self._impl.stream(chunk)

    def configure_end_utterance_silence_threshold(
        self, threshold_milliseconds: int
    ) -> None:
        """
        Configures the silence duration threshold used to detect the end of an utterance.
        In practice, it's used to tune how the transcriptions are split into final transcripts.
        Can be called multiple times during a session at any point after the session starts.

        Args:
            `threshold_milliseconds`: The threshold in milliseconds.
        """
        self._impl.configure_end_utterance_silence_threshold(threshold_milliseconds)

    def force_end_utterance(self) -> None:
        """
        Forces the end of the current utterance.
        After calling this method, the server will end the current utterance and return a final transcript.
        """
        self._impl.force_end_utterance()

    def close(self) -> None:
        """
        Closes the connection to the real-time service.
        """

        self._impl.close(terminate=True)

    @classmethod
    def create_temporary_token(
        cls,
        expires_in: int,
        timeout: Optional[float] = None,
    ) -> str:
        """
        Request a temporary authentication token.

        Example:
            To create a token, you can simply do:
            ```
            token = aai.RealtimeTranscriber.create_temporary_token(expires_in=360000)
            ```

        Args:
            expires_in: The amount of time until the token expires in seconds.
            timeout: The timeout in seconds to wait for a response.
                A `timeout` of `None` means no timeout.

        Returns: The temporary authentication token.
        """
        return _RealtimeTranscriberImpl.create_temporary_token(
            expires_in=expires_in, timeout=timeout
        )
