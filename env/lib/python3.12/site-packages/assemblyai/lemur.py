from __future__ import annotations

import concurrent.futures
from typing import Any, Dict, List, Optional, Union

from . import api, types
from . import client as _client


class _LemurImpl:
    def __init__(
        self,
        *,
        client: _client.Client,
        sources: Optional[List[types.LemurSource]],
    ) -> None:
        self._client = client

        self._sources = (
            [types.LemurSourceRequest.from_lemur_source(s) for s in sources]
            if sources is not None
            else []
        )

    def question(
        self,
        questions: List[types.LemurQuestion],
        context: Optional[Union[str, Dict[str, Any]]],
        timeout: Optional[float],
        final_model: Optional[types.LemurModel],
        max_output_size: Optional[int],
        temperature: Optional[float],
        input_text: Optional[str],
    ) -> types.LemurQuestionResponse:
        response = api.lemur_question(
            client=self._client.http_client,
            request=types.LemurQuestionRequest(
                sources=self._sources,
                questions=questions,
                context=context,
                final_model=final_model,
                max_output_size=max_output_size,
                temperature=temperature,
                input_text=input_text,
            ),
            http_timeout=timeout,
        )

        return response

    def summarize(
        self,
        context: Optional[Union[str, Dict[str, Any]]],
        answer_format: Optional[str],
        final_model: Optional[types.LemurModel],
        max_output_size: Optional[int],
        timeout: Optional[float],
        temperature: Optional[float],
        input_text: Optional[str],
    ) -> types.LemurSummaryResponse:
        response = api.lemur_summarize(
            client=self._client.http_client,
            request=types.LemurSummaryRequest(
                sources=self._sources,
                context=context,
                answer_format=answer_format,
                final_model=final_model,
                max_output_size=max_output_size,
                temperature=temperature,
                input_text=input_text,
            ),
            http_timeout=timeout,
        )

        return response

    def action_items(
        self,
        context: Optional[Union[str, Dict[str, Any]]],
        answer_format: Optional[str],
        final_model: Optional[types.LemurModel],
        max_output_size: Optional[int],
        timeout: Optional[float],
        temperature: Optional[float],
        input_text: Optional[str],
    ) -> types.LemurActionItemsResponse:
        response = api.lemur_action_items(
            client=self._client.http_client,
            request=types.LemurActionItemsRequest(
                sources=self._sources,
                context=context,
                answer_format=answer_format,
                final_model=final_model,
                max_output_size=max_output_size,
                temperature=temperature,
                input_text=input_text,
            ),
            http_timeout=timeout,
        )

        return response

    def task(
        self,
        prompt: str,
        context: Optional[Union[str, Dict[str, Any]]],
        final_model: Optional[types.LemurModel],
        max_output_size: Optional[int],
        timeout: Optional[float],
        temperature: Optional[float],
        input_text: Optional[str],
    ):
        response = api.lemur_task(
            client=self._client.http_client,
            request=types.LemurTaskRequest(
                sources=self._sources,
                prompt=prompt,
                context=context,
                final_model=final_model,
                max_output_size=max_output_size,
                temperature=temperature,
                input_text=input_text,
            ),
            http_timeout=timeout,
        )

        return response

    @classmethod
    def purge_request_data(
        cls,
        request_id: str,
        timeout: Optional[float] = None,
    ) -> types.LemurPurgeResponse:
        response = api.lemur_purge_request_data(
            client=_client.Client.get_default().http_client,
            request=types.LemurPurgeRequest(
                request_id=request_id,
            ),
            http_timeout=timeout,
        )

        return response

    def get_response_data(
        self,
        request_id: str,
        timeout: Optional[float] = None,
    ) -> Union[
        types.LemurStringResponse,
        types.LemurQuestionResponse,
    ]:
        response = api.lemur_get_response_data(
            client=_client.Client.get_default().http_client,
            request_id=request_id,
            http_timeout=timeout,
        )

        return response


class Lemur:
    """
    AssemblyAI's LeMUR (Leveraging Large Language Models to Understand Recognized Speech) framework
    to process audio files with an LLM.

    See https://www.assemblyai.com/docs/Models/lemur for more information.
    """

    def __init__(
        self,
        sources: Optional[List[types.LemurSource]] = None,
        client: Optional[_client.Client] = None,
    ) -> None:
        """
        Creates a new LeMUR instance to process audio files with an LLM.

        Args:

            sources: One or a list of sources to process (e.g. a `Transcript` or a `TranscriptGroup`)
            client: The client to use for the LeMUR instance. If not provided, the default client will be used
        """
        self._client = client or _client.Client.get_default()

        self._impl = _LemurImpl(
            client=self._client,
            sources=sources,
        )
        self._executor = concurrent.futures.ThreadPoolExecutor()

    def question(
        self,
        questions: Union[types.LemurQuestion, List[types.LemurQuestion]],
        context: Optional[Union[str, Dict[str, Any]]] = None,
        final_model: Optional[types.LemurModel] = None,
        max_output_size: Optional[int] = None,
        timeout: Optional[float] = None,
        temperature: Optional[float] = None,
        input_text: Optional[str] = None,
    ) -> types.LemurQuestionResponse:
        """
        Question & Answer allows you to ask free form questions about one or many transcripts.

        This can be any question you find useful, such as judging the outcome or determining facts
        about the audio. For instance, you can ask for action items from a meeting, did the customer
        respond positively, or count how many times a word or phrase was said.

        See also Best Practices on LeMUR: https://www.assemblyai.com/docs/Guides/lemur_best_practices

        Args:
            questions: One or a list of questions to ask.
            context: The context which is shared among all questions. This can be a string or a dictionary.
            final_model: The model that is used for the final prompt after compression is performed.
            max_output_size: Max output size in tokens
            timeout: The timeout in seconds to wait for the answer(s).
            temperature: Change how deterministic the response is, with 0 being the most deterministic and 1 being the least deterministic.
            input_text: Custom formatted transcript data. Use instead of transcript_ids.

        Returns: One or a list of answer objects.
        """

        if not isinstance(questions, list):
            questions = [questions]

        return self._impl.question(
            questions=questions,
            context=context,
            final_model=final_model,
            max_output_size=max_output_size,
            timeout=timeout,
            temperature=temperature,
            input_text=input_text,
        )

    def question_async(
        self,
        questions: Union[types.LemurQuestion, List[types.LemurQuestion]],
        context: Optional[Union[str, Dict[str, Any]]] = None,
        final_model: Optional[types.LemurModel] = None,
        max_output_size: Optional[int] = None,
        timeout: Optional[float] = None,
        temperature: Optional[float] = None,
        input_text: Optional[str] = None,
    ) -> concurrent.futures.Future[types.LemurQuestionResponse]:
        """
        Question & Answer allows you to ask free form questions about one or many transcripts.

        This can be any question you find useful, such as judging the outcome or determining facts
        about the audio. For instance, you can ask for action items from a meeting, did the customer
        respond positively, or count how many times a word or phrase was said.

        See also Best Practices on LeMUR: https://www.assemblyai.com/docs/Guides/lemur_best_practices

        Args:
            questions: One or a list of questions to ask.
            context: The context which is shared among all questions. This can be a string or a dictionary.
            final_model: The model that is used for the final prompt after compression is performed.
            max_output_size: Max output size in tokens
            timeout: The timeout in seconds to wait for the answer(s).
            temperature: Change how deterministic the response is, with 0 being the most deterministic and 1 being the least deterministic.
            input_text: Custom formatted transcript data. Use instead of transcript_ids.

        Returns: One or a list of answer objects.
        """

        if not isinstance(questions, list):
            questions = [questions]

        return self._executor.submit(
            self._impl.question,
            questions=questions,
            context=context,
            final_model=final_model,
            max_output_size=max_output_size,
            timeout=timeout,
            temperature=temperature,
            input_text=input_text,
        )

    def summarize(
        self,
        context: Optional[Union[str, Dict[str, Any]]] = None,
        answer_format: Optional[str] = None,
        final_model: Optional[types.LemurModel] = None,
        max_output_size: Optional[int] = None,
        timeout: Optional[float] = None,
        temperature: Optional[float] = None,
        input_text: Optional[str] = None,
    ) -> types.LemurSummaryResponse:
        """
        Summary allows you to distill a piece of audio into a few impactful sentences.
        You can give the model context to get more pinpoint results while outputting the
        results in a variety of formats described in human language.

        See also Best Practices on LeMUR: https://www.assemblyai.com/docs/Guides/lemur_best_practices

        Args:
            context: An optional context on the transcript.
            answer_format: The format on how the summary shall be summarized.
            final_model: The model that is used for the final prompt after compression is performed.
            max_output_size: Max output size in tokens
            timeout: The timeout in seconds to wait for the summary.
            temperature: Change how deterministic the response is, with 0 being the most deterministic and 1 being the least deterministic.
            input_text: Custom formatted transcript data. Use instead of transcript_ids.

        Returns: The summary as a string.
        """

        return self._impl.summarize(
            context=context,
            answer_format=answer_format,
            final_model=final_model,
            max_output_size=max_output_size,
            timeout=timeout,
            temperature=temperature,
            input_text=input_text,
        )

    def summarize_async(
        self,
        context: Optional[Union[str, Dict[str, Any]]] = None,
        answer_format: Optional[str] = None,
        final_model: Optional[types.LemurModel] = None,
        max_output_size: Optional[int] = None,
        timeout: Optional[float] = None,
        temperature: Optional[float] = None,
        input_text: Optional[str] = None,
    ) -> concurrent.futures.Future[types.LemurSummaryResponse]:
        """
        Summary allows you to distill a piece of audio into a few impactful sentences.
        You can give the model context to get more pinpoint results while outputting the
        results in a variety of formats described in human language.

        See also Best Practices on LeMUR: https://www.assemblyai.com/docs/Guides/lemur_best_practices

        Args:
            context: An optional context on the transcript.
            answer_format: The format on how the summary shall be summarized.
            final_model: The model that is used for the final prompt after compression is performed.
            max_output_size: Max output size in tokens
            timeout: The timeout in seconds to wait for the summary.
            temperature: Change how deterministic the response is, with 0 being the most deterministic and 1 being the least deterministic.
            input_text: Custom formatted transcript data. Use instead of transcript_ids.

        Returns: The summary as a string.
        """

        return self._executor.submit(
            self._impl.summarize,
            context=context,
            answer_format=answer_format,
            final_model=final_model,
            max_output_size=max_output_size,
            timeout=timeout,
            temperature=temperature,
            input_text=input_text,
        )

    def action_items(
        self,
        context: Optional[Union[str, Dict[str, Any]]] = None,
        answer_format: Optional[str] = None,
        final_model: Optional[types.LemurModel] = None,
        max_output_size: Optional[int] = None,
        timeout: Optional[float] = None,
        temperature: Optional[float] = None,
        input_text: Optional[str] = None,
    ) -> types.LemurActionItemsResponse:
        """
        Action Items allows you to generate action items from one or many transcripts.

        You can provide the model with a context to get more pinpoint results while outputting the
        results in a variety of formats described in human language.

        See also Best Practices on LeMUR: https://www.assemblyai.com/docs/Guides/lemur_best_practices

        Args:
            context: An optional context on the transcript.
            answer_format: The preferred format for the result action items.
            final_model: The model that is used for the final prompt after compression is performed.
            max_output_size: Max output size in tokens
            timeout: The timeout in seconds to wait for the action items response.
            temperature: Change how deterministic the response is, with 0 being the most deterministic and 1 being the least deterministic.
            input_text: Custom formatted transcript data. Use instead of transcript_ids.

        Returns: The action items as a string.
        """

        return self._impl.action_items(
            context=context,
            answer_format=answer_format,
            final_model=final_model,
            max_output_size=max_output_size,
            timeout=timeout,
            temperature=temperature,
            input_text=input_text,
        )

    def action_items_async(
        self,
        context: Optional[Union[str, Dict[str, Any]]] = None,
        answer_format: Optional[str] = None,
        final_model: Optional[types.LemurModel] = None,
        max_output_size: Optional[int] = None,
        timeout: Optional[float] = None,
        temperature: Optional[float] = None,
        input_text: Optional[str] = None,
    ) -> concurrent.futures.Future[types.LemurActionItemsResponse]:
        """
        Action Items allows you to generate action items from one or many transcripts.

        You can provide the model with a context to get more pinpoint results while outputting the
        results in a variety of formats described in human language.

        See also Best Practices on LeMUR: https://www.assemblyai.com/docs/Guides/lemur_best_practices

        Args:
            context: An optional context on the transcript.
            answer_format: The preferred format for the result action items.
            final_model: The model that is used for the final prompt after compression is performed.
            max_output_size: Max output size in tokens
            timeout: The timeout in seconds to wait for the action items response.
            temperature: Change how deterministic the response is, with 0 being the most deterministic and 1 being the least deterministic.
            input_text: Custom formatted transcript data. Use instead of transcript_ids.

        Returns: The action items as a string.
        """

        return self._executor.submit(
            self._impl.action_items,
            context=context,
            answer_format=answer_format,
            final_model=final_model,
            max_output_size=max_output_size,
            timeout=timeout,
            temperature=temperature,
            input_text=input_text,
        )

    def task(
        self,
        prompt: str,
        context: Optional[Union[str, Dict[str, Any]]] = None,
        final_model: Optional[types.LemurModel] = None,
        max_output_size: Optional[int] = None,
        timeout: Optional[float] = None,
        temperature: Optional[float] = None,
        input_text: Optional[str] = None,
    ) -> types.LemurTaskResponse:
        """
        Task feature allows you to submit a custom prompt to the model.

        See also Best Practices on LeMUR: https://www.assemblyai.com/docs/Guides/lemur_best_practices

        Args:
            prompt: The prompt to use for this task.
            context: An optional context on the transcript.
            final_model: The model that is used for the final prompt after compression is performed.
            max_output_size: Max output size in tokens
            timeout: The timeout in seconds to wait for the task.
            temperature: Change how deterministic the response is, with 0 being the most deterministic and 1 being the least deterministic.
            input_text: Custom formatted transcript data. Use instead of transcript_ids.

        Returns: A response to a question or task submitted via custom prompt (with source transcripts or other sources taken into the context)
        """

        return self._impl.task(
            prompt=prompt,
            context=context,
            final_model=final_model,
            max_output_size=max_output_size,
            timeout=timeout,
            temperature=temperature,
            input_text=input_text,
        )

    def task_async(
        self,
        prompt: str,
        context: Optional[Union[str, Dict[str, Any]]] = None,
        final_model: Optional[types.LemurModel] = None,
        max_output_size: Optional[int] = None,
        timeout: Optional[float] = None,
        temperature: Optional[float] = None,
        input_text: Optional[str] = None,
    ) -> concurrent.futures.Future[types.LemurTaskResponse]:
        """
        Task feature allows you to submit a custom prompt to the model.

        See also Best Practices on LeMUR: https://www.assemblyai.com/docs/Guides/lemur_best_practices

        Args:
            prompt: The prompt to use for this task.
            context: An optional context on the transcript.
            final_model: The model that is used for the final prompt after compression is performed.
            max_output_size: Max output size in tokens
            timeout: The timeout in seconds to wait for the task.
            temperature: Change how deterministic the response is, with 0 being the most deterministic and 1 being the least deterministic.
            input_text: Custom formatted transcript data. Use instead of transcript_ids.

        Returns: A response to a question or task submitted via custom prompt (with source transcripts or other sources taken into the context)
        """

        return self._executor.submit(
            self._impl.task,
            prompt=prompt,
            context=context,
            final_model=final_model,
            max_output_size=max_output_size,
            timeout=timeout,
            temperature=temperature,
            input_text=input_text,
        )

    @classmethod
    def purge_request_data(
        cls,
        request_id: str,
        timeout: Optional[float] = None,
    ) -> types.LemurPurgeResponse:
        """
        Purge sent LeMUR request data that was previously sent.

        Args:
            request_id: The request ID that was returned to you from the original LeMUR request that should be purged.

        Returns: A response saying whether the LeMUR request data was successfully purged.
        """
        return _LemurImpl.purge_request_data(
            request_id=request_id,
            timeout=timeout,
        )

    @classmethod
    def purge_request_data_async(
        cls,
        request_id: str,
        timeout: Optional[float] = None,
    ) -> concurrent.futures.Future[types.LemurPurgeResponse]:
        """
        Purge sent LeMUR request data that was previously sent.

        Args:
            request_id: The request ID that was returned to you from the original LeMUR request that should be purged.

        Returns: A response saying whether the LeMUR request data was successfully purged.
        """
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            response_future = executor.submit(
                _LemurImpl.purge_request_data,
                request_id=request_id,
                timeout=timeout,
            )
        return response_future

    def get_response_data(
        self,
        request_id: str,
        timeout: Optional[float] = None,
    ) -> Union[
        types.LemurStringResponse,
        types.LemurQuestionResponse,
    ]:
        """
        Retrieve a LeMUR response that was previously generated.

        Args:
            request_id: The ID of a previous LeMUR request.
            timeout: The timeout in seconds to wait for the task.

        Returns: A LeMUR response that was previously generated.
        """
        return self._impl.get_response_data(request_id=request_id, timeout=timeout)

    def get_response_data_async(
        self,
        request_id: str,
        timeout: Optional[float] = None,
    ) -> concurrent.futures.Future[
        Union[
            types.LemurStringResponse,
            types.LemurQuestionResponse,
        ]
    ]:
        """
        Retrieve a LeMUR response that was previously generated.

        Args:
            request_id: The ID of a previous LeMUR request.
            timeout: The timeout in seconds to wait for the task.

        Returns: A LeMUR response that was previously generated.
        """
        return self._executor.submit(
            self._impl.get_response_data,
            request_id=request_id,
            timeout=timeout,
        )
