from datetime import datetime
from enum import Enum, EnumMeta
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Tuple, Union
from urllib.parse import parse_qs, urlparse
from warnings import warn

if TYPE_CHECKING:
    from .transcriber import Transcript

try:
    # pydantic v2 import
    from pydantic import UUID4, BaseModel, ConfigDict, Field
    from pydantic_settings import BaseSettings, SettingsConfigDict

    pydantic_v2 = True
except ImportError:
    # pydantic v1 import
    from pydantic.v1 import UUID4, BaseModel, BaseSettings, ConfigDict, Field

    pydantic_v2 = False

from typing_extensions import Self


class AssemblyAIError(Exception):
    """
    Base exception for all AssemblyAI errors
    """

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class TranscriptError(AssemblyAIError):
    """
    Error class when a transcription fails
    """


class RedactedAudioIncompleteError(AssemblyAIError):
    """
    Error class when a PII-redacted audio URL is requested
    before the file has finished processing
    """


class RedactedAudioExpiredError(AssemblyAIError):
    """
    Error class when a PII-redacted audio URL is requested
    but the file has expired and is no longer available
    """


class RedactedAudioUnavailableError(AssemblyAIError):
    """
    Error class when a PII-redacted audio file is requested
    but it is not available at the given URL
    """


class LemurError(AssemblyAIError):
    """
    Error class when a Lemur request fails
    """


class Sourcable:
    """
    A base class for all sourcable objects

    Currently, only `Transcript` is sourcable
    """


class Settings(BaseSettings):
    """
    Settings for the AssemblyAI client
    """

    api_key: Optional[str] = None
    "The API key to authenticate with"

    http_timeout: float = 30.0
    "The default HTTP timeout for general requests"

    base_url: str = "https://api.assemblyai.com"
    "The base URL for the AssemblyAI API"

    polling_interval: float = Field(default=3.0, gt=0.0)
    "The default polling interval for long-running requests (e.g. polling the `Transcript`'s status)"

    if pydantic_v2:
        model_config = SettingsConfigDict(env_prefix="assemblyai_")
    else:

        class Config:
            env_prefix = "assemblyai_"


class TranscriptStatus(str, Enum):
    """
    Transcript status
    """

    queued = "queued"
    processing = "processing"
    completed = "completed"
    error = "error"


class DeprecatedLanguageCodeMeta(EnumMeta):
    def __getattribute__(self, item):
        # Deprecate all 20 possible values
        languages = [
            "de",
            "en",
            "en_au",
            "en_uk",
            "en_us",
            "es",
            "fi",
            "fr",
            "hi",
            "it",
            "ja",
            "ko",
            "nl",
            "pl",
            "pt",
            "ru",
            "tr",
            "uk",
            "vi",
            "zh",
        ]
        if item in languages:
            warn(
                "LanuageCode Enum is deprecated and will be removed in 1.0.0. Use a string instead.",
                DeprecationWarning,
                stacklevel=2,
            )

        return EnumMeta.__getattribute__(self, item)


class LanguageCode(str, Enum, metaclass=DeprecatedLanguageCodeMeta):
    """
    DeprecationWarning: LanuageCode is deprecated and will be removed in 1.0.0. Use a string instead.

    Supported languages for transcribing audio.
    """

    de = "de"
    "German"

    en = "en"
    "Global English"

    en_au = "en_au"
    "Australian English"

    en_uk = "en_uk"
    "British English"

    en_us = "en_us"
    "English (US)"

    es = "es"
    "Spanish"

    fi = "fi"
    "Finnish"

    fr = "fr"
    "French"

    hi = "hi"
    "Hindi"

    it = "it"
    "Italian"

    ja = "ja"
    "Japanese"

    ko = "ko"
    "Korean"

    nl = "nl"
    "Dutch"

    pl = "pl"
    "Polish"

    pt = "pt"
    "Portuguese"

    ru = "ru"
    "Russian"

    tr = "tr"
    "Turkish"

    uk = "uk"
    "Ukrainian"

    vi = "vi"
    "Vietnamese"

    zh = "zh"
    "Chinese"


class WordBoost(str, Enum):
    low = "low"
    default = "default"
    high = "high"


class PIIRedactedAudioQuality(str, Enum):
    mp3 = "mp3"
    wav = "wav"


class EntityType(str, Enum):
    """
    Used for AssemblyAI's Entity Detection feature.

    See: https://www.assemblyai.com/docs/audio-intelligence/entity-detection
    """

    account_number = "account_number"
    "Customer account or membership identification number (e.g., Policy No. 10042992; Member ID: HZ-5235-001)"

    banking_information = "banking_information"
    "Banking information, including account and routing numbers (e.g., Acct. No.: 012345-67)"

    blood_type = "blood_type"
    "Blood type (e.g., O-, AB positive)"

    credit_card_cvv = "credit_card_cvv"
    "Credit card verification code (e.g., CVV: 080)"

    credit_card_expiration = "credit_card_expiration"
    "Expiration date of a credit card (e.g., Expires: July 2023; Exp: 02/28)"

    credit_card_number = "credit_card_number"
    "Credit card number (e.g., 0123 0123 0123 0123)"

    date = "date"
    "Specific calendar date (e.g., December 18)"

    date_interval = "date_interval"
    "Broader time periods, including date ranges, months, seasons, years, and decades (e.g., 2020-2021; 5-9 May; January 1984 )"

    date_of_birth = "date_of_birth"
    "Date of Birth (e.g., Date of Birth: March 7,1961)"

    drivers_license = "drivers_license"
    "Driver's license number (e.g., DL# 356933-540)"

    drug = "drug"
    "Medications, vitamins, or supplements (e.g., Advil, Acetaminophen, Panadol)"

    duration = "duration"
    "Periods of time, specified as a number and a unit of time (e.g., 8 months; 2 years)"

    email_address = "email_address"
    "Email address (e.g., support@assemblyai.com)"

    event = "event"
    "Name of an event or holiday (e.g., Olympics, Yom Kippur)"

    filename = "filename"
    "Names of computer files, including the extension or filepath (e.g., Taxes/2012/brad-tax-returns.pdf)"

    gender_sexuality = "gender_sexuality"
    "Terms indicating gender identity or sexual orientation, including slang terms (e.g., female; bisexual; trans)"

    healthcare_number = "healthcare_number"
    "Healthcare numbers and health plan beneficiary numbers (e.g., Policy No.: 5584-486-674-YM)"

    injury = "injury"
    "Bodily injury (e.g., I broke my arm, I have a sprained wrist)"

    ip_address = "ip_address"
    "Internet IP address, including IPv4 and IPv6 formats (e.g., 192.168.0.1)"

    language = "language"
    "Name of a natural language (e.g., Spanish, French)"

    location = "location"
    "Any Location reference including mailing address, postal code, city, state, province, country, or coordinates (e.g., Lake Victoria, 145 Windsor St., 90210)"

    marital_status = "marital_status"
    "Terms indicating marital status (e.g., Single, common-law, ex-wife, married)"

    medical_condition = "medical_condition"
    "Name of a medical condition, disease, syndrome, deficit, or disorder (e.g., chronic fatigue syndrome, arrhythmia, depression)"

    medical_process = "medical_process"
    "Medical process, including treatments, procedures, and tests (e.g., heart surgery, CT scan)"

    money_amount = "money_amount"
    "Name and/or amount of currency (e.g., 15 pesos, $94.50)"

    nationality = "nationality"
    "Terms indicating nationality, ethnicity, or race (e.g., American, Asian, Caucasian)"

    number_sequence = "number_sequence"
    "Numerical PII (including alphanumeric strings) that doesn't fall under other categories"

    occupation = "occupation"
    "Job title or profession (e.g., professor, actors, engineer, CPA)"

    organization = "organization"
    "Name of an organization (e.g., CNN, McDonalds, University of Alaska, Northwest General Hospital)"

    passport_number = "passport_number"
    "Passport numbers, issued by any country (e.g., PA4568332; NU3C6L86S12)"

    password = "password"
    "Account passwords, PINs, access keys, or verification answers (e.g., 27%alfalfa, temp1234, My mother's maiden name is Smith)"

    person_age = "person_age"
    "Number associated with an age (e.g., 27, 75)"

    person_name = "person_name"
    "Name of a person (e.g., Bob, Doug Jones, Dr. Kay Martinez, MD)"

    phone_number = "phone_number"
    "Telephone or fax number (e.g., +4917643476050)"

    physical_attribute = "physical_attribute"
    "Distinctive bodily attributes, including terms indicating race (e.g., I'm 190cm tall, He has black hair)"

    political_affiliation = "political_affiliation"
    "Terms referring to a political party, movement, or ideology (e.g., Republican, Liberal)"

    religion = "religion"
    "Terms indicating religious affiliation (e.g., Hindu, Catholic)"

    statistics = "statistics"
    "Medical statistics (e.g., 18%, 18 percent)"

    time = "time"
    "Expressions indicating clock times (e.g., 19:37:28, 10pm EST)"

    url = "url"
    "Internet addresses (e.g., www.assemblyai.com)"

    us_social_security_number = "us_social_security_number"
    "Social Security Number or equivalent (e.g., 078-05-1120, ***-***-3256)"

    username = "username"
    "Usernames, login names, or handles (e.g., @AssemblyAI)"

    vehicle_id = "vehicle_id"
    "Vehicle identification numbers (VINs), vehicle serial numbers, and license plate numbers (e.g., 5FNRL38918B111818, BIF7547)"

    zodiac_sign = "zodiac_sign"
    "Names of Zodiac signs (e.g., Aries, Taurus)"


# EntityType and PIIRedactionPolicy share the same values
PIIRedactionPolicy = EntityType
"""
Used for AssemblyAI's PII Redaction feature.

See: https://www.assemblyai.com/docs/audio-intelligence/pii-redaction
"""


class PIISubstitutionPolicy(str, Enum):
    """
    Used for AssemblyAI's PII Redaction feature.

    See: https://www.assemblyai.com/docs/audio-intelligence/pii-redaction
    """

    hash = "hash"
    "PII that is detected is replaced with a hash - #. For example, I'm calling for John is replaced with ####. (Applied by default)"

    entity_name = "entity_name"
    "PII that is detected is replaced with the associated policy name. For example, John is replaced with [PERSON_NAME]. This is recommended for readability."


class SummarizationModel(str, Enum):
    """
    Used for AssemblyAI's Summarization feature.

    See: https://www.assemblyai.com/docs/audio-intelligence/summarization
    """

    informative = "informative"
    """
    Best for files with a single speaker such as presentations or lectures.

    Supported Summarization Types:
        - `bullets`
        - `bullets_verbose`
        - `headline`
        - `paragraph`

    Required Parameters:
        - `punctuate`: `True`
        - `format_text`: `True`
    """

    conversational = "conversational"
    """
    Best for any 2 person conversation such as customer/agent or interview/interviewee calls.

    Supported Summarization Types:
        - `bullets`
        - `bullets_verbose`
        - `headline`
        - `paragraph`

    Required Parameters:
        - `punctuate`: `True`
        - `format_text`: `True`
        - `speaker_labels` or `dual_channel` set to `True`
    """

    catchy = "catchy"
    """
    Best for creating video, podcast, or media titles.

    Supported Summarization Types:
        - `headline`
        - `gist`

    Required Parameters:
        - `punctuate`: `True`
        - `format_text`: `True`
    """


class SummarizationType(str, Enum):
    """
    Used for AssemblyAI's Summarization feature.

    See: https://www.assemblyai.com/docs/audio-intelligence/summarization
    """

    bullets = "bullets"
    "A bulleted summary with the most important points."

    bullets_verbose = "bullets_verbose"
    "A longer bullet point list summarizing the entire transcription text."

    gist = "gist"
    "A few words summarizing the entire transcription text."

    headline = "headline"
    "A single sentence summarizing the entire transcription text."

    paragraph = "paragraph"
    "A single paragraph summarizing the entire transcription text."


class SpeechModel(str, Enum):
    """
    Used for AssemblyAI's Speech Model feature.
    """

    best = "best"
    "The best model optimized for accuracy."

    nano = "nano"
    "A lightweight, lower cost model for a wide range of languages."


class RawTranscriptionConfig(BaseModel):
    language_code: Optional[Union[str, LanguageCode]] = None
    """
    The language of your audio file. Possible values are found in Supported Languages.

    The default value is "en_us".
    """

    punctuate: Optional[bool] = None
    "Enable Automatic Punctuation"

    format_text: Optional[bool] = None
    "Enable Text Formatting"

    dual_channel: Optional[bool] = None
    "Enable Dual Channel transcription"

    multichannel: Optional[bool] = None
    "Enable Multichannel transcription"

    webhook_url: Optional[str] = None
    "The URL we should send webhooks to when your transcript is complete."
    webhook_auth_header_name: Optional[str] = None
    "The name of the header that is sent when the `webhook_url` is being called."
    webhook_auth_header_value: Optional[str] = None
    "The value of the `webhook_auth_header_name` that is sent when the `webhook_url` is being called."

    audio_start_from: Optional[int] = None
    "The point in time, in milliseconds, to begin transcription from in your media file."
    audio_end_at: Optional[int] = None
    "The point in time, in milliseconds, to stop transcribing in your media file."

    word_boost: Optional[List[str]] = None
    "A list of custom vocabulary to boost accuracy for."
    boost_param: Optional[WordBoost] = None
    "The weight to apply to words/phrases in the word_boost array."

    filter_profanity: Optional[bool] = None
    "Filter profanity from the transcribed text."

    redact_pii: Optional[bool] = None
    "Redact PII from the transcribed text."
    redact_pii_audio: Optional[bool] = None
    "Generate a copy of the original media file with spoken PII 'beeped' out."
    redact_pii_audio_quality: Optional[PIIRedactedAudioQuality] = None
    "The quality of the redacted audio file in case `redact_pii_audio` is enabled."
    redact_pii_policies: Optional[List[PIIRedactionPolicy]] = None
    "The list of PII Redaction policies to enable."
    redact_pii_sub: Optional[PIISubstitutionPolicy] = None
    "The replacement logic for detected PII."

    speaker_labels: Optional[bool] = None
    "Enable Speaker Diarization."

    speakers_expected: Optional[int] = None
    "The number of speakers you expect to be in your audio file."

    content_safety: Optional[bool] = None
    "Enable Content Safety Detection."

    content_safety_confidence: Optional[int] = None
    "The minimum confidence level for a content safety label to be produced."

    iab_categories: Optional[bool] = None
    "Enable Topic Detection."

    custom_spelling: Optional[List[Dict[str, Union[str, List[str]]]]] = None
    "Customize how words are spelled and formatted using to and from values."

    disfluencies: Optional[bool] = None
    "Transcribe Filler Words, like 'umm', in your media file."

    sentiment_analysis: Optional[bool] = None
    "Enable Sentiment Analysis."

    auto_chapters: Optional[bool] = None
    "Enable Auto Chapters."

    entity_detection: Optional[bool] = None
    "Enable Entity Detection."

    summarization: Optional[bool] = None
    "Enable Summarization"
    summary_model: Optional[SummarizationModel] = None
    "The summarization model to use in case `summarization` is enabled"
    summary_type: Optional[SummarizationType] = None
    "The summarization type to use in case `summarization` is enabled"

    auto_highlights: Optional[bool] = None
    "Detect important phrases and words in your transcription text."

    language_detection: Optional[bool] = None
    """
    Identify the dominant language that's spoken in an audio file, and route the file to the appropriate model for the detected language.

    See the docs for supported languages: https://www.assemblyai.com/docs/getting-started/supported-languages
    """

    language_confidence_threshold: Optional[float] = None
    """
    The confidence threshold that must be reached if `language_detection` is enabled. An error will be returned
    if the language confidence is below this threshold. Valid values are in the range [0,1] inclusive.
    """

    speech_threshold: Optional[float] = None
    "Reject audio files that contain less than this fraction of speech. Valid values are in the range [0,1] inclusive."

    speech_model: Optional[SpeechModel] = None
    """
    The speech model to use for the transcription.
    """
    model_config = ConfigDict(extra="allow")


class TranscriptionConfig:
    def __init__(
        self,
        language_code: Optional[Union[str, LanguageCode]] = None,
        punctuate: Optional[bool] = None,
        format_text: Optional[bool] = None,
        dual_channel: Optional[bool] = None,
        multichannel: Optional[bool] = None,
        webhook_url: Optional[str] = None,
        webhook_auth_header_name: Optional[str] = None,
        webhook_auth_header_value: Optional[str] = None,
        audio_start_from: Optional[int] = None,
        audio_end_at: Optional[int] = None,
        word_boost: List[str] = [],
        boost_param: Optional[WordBoost] = None,
        filter_profanity: Optional[bool] = None,
        redact_pii: Optional[bool] = None,
        redact_pii_audio: Optional[bool] = None,
        redact_pii_audio_quality: Optional[PIIRedactedAudioQuality] = None,
        redact_pii_policies: Optional[List[PIIRedactionPolicy]] = None,
        redact_pii_sub: Optional[PIISubstitutionPolicy] = None,
        speaker_labels: Optional[bool] = None,
        speakers_expected: Optional[int] = None,
        content_safety: Optional[bool] = None,
        content_safety_confidence: Optional[int] = None,
        iab_categories: Optional[bool] = None,
        custom_spelling: Optional[Dict[str, Union[str, Sequence[str]]]] = None,
        disfluencies: Optional[bool] = None,
        sentiment_analysis: Optional[bool] = None,
        auto_chapters: Optional[bool] = None,
        entity_detection: Optional[bool] = None,
        summarization: Optional[bool] = None,
        summary_model: Optional[SummarizationModel] = None,
        summary_type: Optional[SummarizationType] = None,
        auto_highlights: Optional[bool] = None,
        language_detection: Optional[bool] = None,
        language_confidence_threshold: Optional[float] = None,
        speech_threshold: Optional[float] = None,
        raw_transcription_config: Optional[RawTranscriptionConfig] = None,
        speech_model: Optional[SpeechModel] = None,
    ) -> None:
        """
        Args:
            language_code: The language of your audio file. Possible values are found in Supported Languages.
            punctuate: Enable Automatic Punctuation
            format_text: Enable Text Formatting
            dual_channel: Enable Dual Channel transcription
            multichannel: Enable Multichannel transcription
            webhoook_url: The URL we should send webhooks to when your transcript is complete.
            webhook_auth_header_name: The name of the header that is sent when the `webhook_url` is being called.
            webhook_auth_header_value: The value of the `webhook_auth_header_name` that is sent when the `webhoook_url` is being called.
            audio_start_from: The point in time, in milliseconds, to begin transcription from in your media file.
            audio_end_at: The point in time, in milliseconds, to stop transcribing in your media file.
            word_boost: A list of custom vocabulary to boost accuracy for.
            boost_param: The weight to apply to words/phrases in the word_boost array.
            filter_profanity: Filter profanity from the transcribed text.
            redact_pii: Redact PII from the transcribed text.
            redact_pii_audio: Generate a copy of the original media file with spoken PII 'beeped' out (new audio only available for 24 hours).
            redact_pii_audio_quality: The quality of the redacted audio file in case `redact_pii_audio` is enabled.
            redact_pii_policies: The list of PII Redaction policies to enable.
            redact_pii_sub: The replacement logic for detected PII.
            speaker_labels: Enable Speaker Diarization.
            speakers_expected: The number of speakers you expect to hear in your audio file. Up to 10 speakers are supported.
            content_safety: Enable Content Safety Detection.
            iab_categories: Enable Topic Detection.
            custom_spelling: Customize how words are spelled and formatted using to and from values.
            disfluencies: Transcribe Filler Words, like 'umm', in your media file.
            sentiment_analysis: Enable Sentiment Analysis.
            auto_chapters: Enable Auto Chapters.
            entity_detection: Enable Entity Detection.
            summarization: Enable Summarization
            summary_model: The summarization model to use in case `summarization` is enabled
            summary_type: The summarization type to use in case `summarization` is enabled
            auto_highlights: Detect important phrases and words in your transcription text.
            language_detection: Identify the dominant language that's spoken in an audio file, and route the file to the appropriate model for the detected language.
            language_confidence_threshold: The confidence threshold that must be reached if `language_detection` is enabled.
                An error will be returned if the language confidence is below this threshold. Valid values are in the range [0,1] inclusive.
            speech_threshold: Reject audio files that contain less than this fraction of speech. Valid values are in the range [0,1] inclusive.
            raw_transcription_config: Create the config from a `RawTranscriptionConfig`
        """
        self._raw_transcription_config = (
            raw_transcription_config
            if raw_transcription_config is not None
            else RawTranscriptionConfig()
        )

        # explicit configurations have higher priority if `raw_transcription_config` has been passed as well
        self.language_code = language_code
        self.punctuate = punctuate
        self.format_text = format_text
        self.dual_channel = dual_channel
        self.multichannel = multichannel
        self.set_webhook(
            webhook_url,
            webhook_auth_header_name,
            webhook_auth_header_value,
        )
        self.set_audio_slice(
            audio_start_from,
            audio_end_at,
        )
        self.set_word_boost(word_boost, boost_param)
        self.filter_profanity = filter_profanity
        self.set_redact_pii(
            redact_pii,
            redact_pii_audio,
            redact_pii_audio_quality,
            redact_pii_policies,
            redact_pii_sub,
        )
        self.set_speaker_diarization(speaker_labels, speakers_expected)
        self.set_content_safety(content_safety, content_safety_confidence)
        self.iab_categories = iab_categories
        self.set_custom_spelling(custom_spelling, override=True)
        self.disfluencies = disfluencies
        self.sentiment_analysis = sentiment_analysis
        self.auto_chapters = auto_chapters
        self.entity_detection = entity_detection
        self.set_summarize(
            summarization,
            summary_model,
            summary_type,
        )
        self.auto_highlights = auto_highlights
        self.language_detection = language_detection
        self.language_confidence_threshold = language_confidence_threshold
        self.speech_threshold = speech_threshold
        self.speech_model = speech_model

    @property
    def raw(self) -> RawTranscriptionConfig:
        return self._raw_transcription_config

    # region: Getters/Setters

    @property
    def language_code(self) -> Optional[Union[str, LanguageCode]]:
        "The language code of the audio file."
        return self._raw_transcription_config.language_code

    @language_code.setter
    def language_code(self, language_code: Optional[Union[str, LanguageCode]]) -> None:
        "Sets the language code of the audio file."

        self._raw_transcription_config.language_code = language_code

    @property
    def speech_model(self) -> Optional[SpeechModel]:
        "The speech model to use for the transcription."
        return self._raw_transcription_config.speech_model

    @speech_model.setter
    def speech_model(self, speech_model: Optional[SpeechModel]) -> None:
        "Sets the speech model to use for the transcription."
        self._raw_transcription_config.speech_model = speech_model

    @property
    def punctuate(self) -> Optional[bool]:
        "Returns the status of the Automatic Punctuation feature."

        return self._raw_transcription_config.punctuate

    @punctuate.setter
    def punctuate(self, enable: Optional[bool]) -> None:
        "Enable Automatic Punctuation feature."

        self._raw_transcription_config.punctuate = enable

    @property
    def format_text(self) -> Optional[bool]:
        "Returns the status of the Text Formatting feature."

        return self._raw_transcription_config.format_text

    @format_text.setter
    def format_text(self, enable: Optional[bool]) -> None:
        "Enables Formatting Text feature."

        self._raw_transcription_config.format_text = enable

    @property
    def dual_channel(self) -> Optional[bool]:
        "Returns the status of the Dual Channel transcription feature"

        return self._raw_transcription_config.dual_channel

    @dual_channel.setter
    def dual_channel(self, enable: Optional[bool]) -> None:
        "Enable Dual Channel transcription"

        self._raw_transcription_config.dual_channel = enable

    @property
    def multichannel(self) -> Optional[bool]:
        "Returns the status of the Multichannel transcription feature"

        return self._raw_transcription_config.multichannel

    @multichannel.setter
    def multichannel(self, enable: Optional[bool]) -> None:
        "Enable Multichannel transcription"

        self._raw_transcription_config.multichannel = enable

    @property
    def webhook_url(self) -> Optional[str]:
        "The URL we should send webhooks to when your transcript is complete."

        return self._raw_transcription_config.webhook_url

    @property
    def webhook_auth_header_name(self) -> Optional[str]:
        "The name of the header that is sent when the `webhook_url` is being called."

        return self._raw_transcription_config.webhook_auth_header_name

    @property
    def webhook_auth_header_value(self) -> Optional[str]:
        "The value of the `webhook_auth_header_name` that is sent when the `webhook_url` is being called."

        return self._raw_transcription_config.webhook_auth_header_value

    @property
    def audio_start_from(self) -> Optional[int]:
        "Returns the point in time, in milliseconds, to begin transcription from in your media file."

        return self._raw_transcription_config.audio_start_from

    @property
    def audio_end_at(self) -> Optional[int]:
        "Returns the point in time, in milliseconds, to stop transcribing in your media file."

        return self._raw_transcription_config.audio_end_at

    @property
    def word_boost(self) -> Optional[List[str]]:
        "Returns the list of custom vocabulary to boost accuracy for."

        return self._raw_transcription_config.word_boost

    @property
    def boost_param(self) -> Optional[WordBoost]:
        "Returns how much weight is being applied when boosting custom vocabularies."

        return self._raw_transcription_config.boost_param

    @property
    def filter_profanity(self) -> Optional[bool]:
        "Returns the status of whether filtering profanity is enabled or not."

        return self._raw_transcription_config.filter_profanity

    @filter_profanity.setter
    def filter_profanity(self, enable: Optional[bool]) -> None:
        "Filter profanity from the transcribed text."

        self._raw_transcription_config.filter_profanity = enable

    @property
    def redact_pii(self) -> Optional[bool]:
        "Returns the status of the PII Redaction feature."

        return self._raw_transcription_config.redact_pii

    @property
    def redact_pii_audio(self) -> Optional[bool]:
        "Whether or not to generate a copy of the original media file with spoken PII 'beeped' out."

        return self._raw_transcription_config.redact_pii_audio

    @property
    def redact_pii_audio_quality(self) -> Optional[PIIRedactedAudioQuality]:
        "The quality of the redacted audio file in case `redact_pii_audio` is enabled."

        return self._raw_transcription_config.redact_pii_audio_quality

    @property
    def redact_pii_policies(self) -> Optional[List[PIIRedactionPolicy]]:
        "Returns a list of set of defined PII redaction policies."

        return self._raw_transcription_config.redact_pii_policies

    @property
    def redact_pii_sub(self) -> Optional[PIISubstitutionPolicy]:
        "Returns the replacement logic for detected PII."

        return self._raw_transcription_config.redact_pii_sub

    @property
    def speaker_labels(self) -> Optional[bool]:
        "Returns the status of the Speaker Diarization feature."

        return self._raw_transcription_config.speaker_labels

    @property
    def speakers_expected(self) -> Optional[int]:
        "Returns the number of speakers expected to be in the audio file. Used in combination with the `speaker_labels` parameter."

        return self._raw_transcription_config.speakers_expected

    @property
    def content_safety(self) -> Optional[bool]:
        "Returns the status of the Content Safety feature."

        return self._raw_transcription_config.content_safety

    @property
    def content_safety_confidence(self) -> Optional[int]:
        "The minimum confidence level for a content safety label to be produced. Used in combination with the `content_safety` parameter."

        return self._raw_transcription_config.content_safety_confidence

    def set_content_safety(
        self,
        enable: Optional[bool] = True,
        content_safety_confidence: Optional[int] = None,
    ) -> Self:
        """Enable Content Safety feature.

        Args:
            `enable`: Whether or not to enable the Content Safety feature.
            `content_safety_confidence`: The minimum confidence level for a content safety label to be produced.

        Raises:
            `ValueError`: Raised if `content_safety_confidence` is not between 25 and 100 (inclusive).
        """

        if not enable:
            self._raw_transcription_config.content_safety = None
            self._raw_transcription_config.content_safety_confidence = None
            return self

        if content_safety_confidence is not None and (
            content_safety_confidence < 25 or content_safety_confidence > 100
        ):
            raise ValueError(
                "content_safety_confidence must be between 25 and 100 (inclusive)."
            )

        self._raw_transcription_config.content_safety = enable
        self._raw_transcription_config.content_safety_confidence = (
            content_safety_confidence
        )

        return self

    @property
    def iab_categories(self) -> Optional[bool]:
        "Returns the status of the Topic Detection feature."

        return self._raw_transcription_config.iab_categories

    @iab_categories.setter
    def iab_categories(self, enable: Optional[bool]) -> None:
        "Enable Topic Detection feature."

        self._raw_transcription_config.iab_categories = enable

    @property
    def custom_spelling(self) -> Optional[Dict[str, Union[str, List[str]]]]:
        """
        Returns the current set of custom spellings. For each key-value pair in the dictionary,
        the key is the 'to' field, and the value is the 'from' field.
        """

        if self._raw_transcription_config.custom_spelling is None:
            return None

        custom_spellings = {}
        for custom_spelling in self._raw_transcription_config.custom_spelling:
            _to = custom_spelling["to"]
            if not isinstance(_to, str):
                raise ValueError("`to` argument must be a string!")

            custom_spellings[_to] = custom_spelling["from"]

        return custom_spellings if custom_spelling else None

    @property
    def disfluencies(self) -> Optional[bool]:
        "Returns whether to transcribing filler words is enabled or not."

        return self._raw_transcription_config.disfluencies

    @disfluencies.setter
    def disfluencies(self, enable: Optional[bool]) -> None:
        "Transcribe filler words, like 'umm', in your media file."

        self._raw_transcription_config.disfluencies = enable

    @property
    def sentiment_analysis(self) -> Optional[bool]:
        "Returns the status of the Sentiment Analysis feature."

        return self._raw_transcription_config.sentiment_analysis

    @sentiment_analysis.setter
    def sentiment_analysis(self, enable: Optional[bool]) -> None:
        "Enable Sentiment Analysis."

        self._raw_transcription_config.sentiment_analysis = enable

    @property
    def auto_chapters(self) -> Optional[bool]:
        "Returns the status of the Auto Chapters feature."

        return self._raw_transcription_config.auto_chapters

    @auto_chapters.setter
    def auto_chapters(self, enable: Optional[bool]) -> None:
        "Enable Auto Chapters."

        # Validate required params are also set
        if enable and self.punctuate is False:
            raise ValueError(
                "If `auto_chapters` is enabled, then `punctuate` must not be disabled"
            )

        self._raw_transcription_config.auto_chapters = enable

    @property
    def entity_detection(self) -> Optional[bool]:
        "Returns whether Entity Detection feature is enabled or not."

        return self._raw_transcription_config.entity_detection

    @entity_detection.setter
    def entity_detection(self, enable: Optional[bool]) -> None:
        "Enable Entity Detection."

        self._raw_transcription_config.entity_detection = enable

    @property
    def summarization(self) -> Optional[bool]:
        "Returns whether the Summarization feature is enabled or not."

        return self._raw_transcription_config.summarization

    @property
    def summary_model(self) -> Optional[SummarizationModel]:
        "Returns the model of the Summarization feature."

        return self._raw_transcription_config.summary_model

    @property
    def summary_type(self) -> Optional[SummarizationType]:
        "Returns the type of the Summarization feature."

        return self._raw_transcription_config.summary_type

    @property
    def auto_highlights(self) -> Optional[bool]:
        "Returns whether the Auto Highlights feature is enabled or not."

        return self._raw_transcription_config.auto_highlights

    @auto_highlights.setter
    def auto_highlights(self, enable: Optional[bool]) -> None:
        "Detect important phrases and words in your transcription text."

        self._raw_transcription_config.auto_highlights = enable

    @property
    def language_detection(self) -> Optional[bool]:
        "Returns whether Automatic Language Detection is enabled or not."

        return self._raw_transcription_config.language_detection

    @language_detection.setter
    def language_detection(self, enable: Optional[bool]) -> None:
        """
        Identify the dominant language that's spoken in an audio file, and route the file to the appropriate model for the detected language.

        See the docs for supported languages: https://www.assemblyai.com/docs/getting-started/supported-languages
        """

        self._raw_transcription_config.language_detection = enable

    @property
    def language_confidence_threshold(self) -> Optional[float]:
        "Returns the confidence threshold that must be reached for automatic language detection."

        return self._raw_transcription_config.language_confidence_threshold

    @language_confidence_threshold.setter
    def language_confidence_threshold(self, threshold: Optional[float]) -> None:
        """
        Set the confidence threshold that must be reached if `language_detection` is enabled. An error will be returned
        if the language confidence is below this threshold. Valid values are in the range [0,1] inclusive.
        """

        self._raw_transcription_config.language_confidence_threshold = threshold

    @property
    def speech_threshold(self) -> Optional[float]:
        "Returns the current speech threshold."

        return self._raw_transcription_config.speech_threshold

    @speech_threshold.setter
    def speech_threshold(self, threshold: Optional[float]) -> None:
        "Reject audio files that contain less than this fraction of speech. Valid values are in the range [0,1] inclusive."

        self._raw_transcription_config.speech_threshold = threshold

    # endregion

    # region: Convenience (helper) methods

    def set_casing_and_formatting(
        self,
        enable: bool = True,
    ) -> Self:
        """
        Whether to enable Automatic Punctuation and Text Formatting on the transcript.

        Args:
            enable: Enable Automatic Punctuation and Text Formatting
        """
        self._raw_transcription_config.punctuate = enable
        self._raw_transcription_config.format_text = enable

        return self

    def set_speaker_diarization(
        self,
        enable: Optional[bool] = True,
        speakers_expected: Optional[int] = None,
    ) -> Self:
        """
        Whether to enable Speaker Diarization on the transcript.

        Args:
            `enable`: Enable Speaker Diarization
            `speakers_expected`: The number of speakers in the audio file.
        """

        if not enable:
            self._raw_transcription_config.speaker_labels = None
            self._raw_transcription_config.speakers_expected = None
        else:
            self._raw_transcription_config.speaker_labels = True
            self._raw_transcription_config.speakers_expected = speakers_expected

        return self

    def set_webhook(
        self,
        url: Optional[str],
        auth_header_name: Optional[str] = None,
        auth_header_value: Optional[str] = None,
    ) -> Self:
        """
        A webhook that is called on transcript completion.

        Args:
            url: The URL we should send webhooks to when your transcript is complete.
            auth_header_name: The name of the header that is sent when the `url` is being called.
            auth_header_value: The value of the `auth_header_name` that is sent when the `url` is being called.

        """

        if url is None:
            self._raw_transcription_config.webhook_url = None
            self._raw_transcription_config.webhook_auth_header_name = None
            self._raw_transcription_config.webhook_auth_header_value = None

            return self

        self._raw_transcription_config.webhook_url = url
        if auth_header_name and auth_header_value:
            self._raw_transcription_config.webhook_auth_header_name = auth_header_name
            self._raw_transcription_config.webhook_auth_header_value = auth_header_value

        return self

    def set_audio_slice(
        self,
        start: Optional[int] = None,
        end: Optional[int] = None,
    ) -> Self:
        """
        Slice the audio to specify the start or end for transcription.

        Args:
            start: The point in time, in milliseconds, to begin transcription from in your media file.
            end: The point in time, in milliseconds, to stop transcribing in your media file.
        """

        self._raw_transcription_config.audio_start_from = start
        self._raw_transcription_config.audio_end_at = end

        return self

    def set_word_boost(
        self,
        words: List[str],
        boost: Optional[WordBoost] = WordBoost.default,
    ) -> Self:
        """
        Improve transcription accuracy when you know certain words or phrases will appear frequently in your audio file.

        Args:
            words: A list of words to improve accuracy on.
            boost: control how much weight should be applied to your keywords/phrases.

        Note: It's important to follow formatting guidelines for custom vocabulary to ensure the best results:
          - Remove all punctuation, except apostrophes, and make sure each word is in its spoken form.
          - Acronyms should have no spaces between letters.
          - Additionally, the model will still accept words with unique characters such as é,
            but will convert them to their ASCII equivalent.

        There are some limitations to the parameter. You can pass a maximum of 1,000 unique keywords/phrases in your list,
        and each of them must contain 6 words or less.
        """

        if not words:
            self._raw_transcription_config.word_boost = None
            self._raw_transcription_config.boost_param = None

            return self

        if not boost:
            self._raw_transcription_config.boost_param = WordBoost.default

        self._raw_transcription_config.word_boost = words
        self._raw_transcription_config.boost_param = boost

        return self

    def set_redact_pii(
        self,
        enable: Optional[bool] = True,
        redact_audio: Optional[bool] = None,
        redact_audio_quality: Optional[PIIRedactedAudioQuality] = None,
        policies: Optional[List[PIIRedactionPolicy]] = None,
        substitution: Optional[PIISubstitutionPolicy] = None,
    ) -> Self:
        """
        Enables Personal Identifiable Information (PII) Redaction feature.

        Args:
            enable: whether to enable or disable the PII Redaction feature.
            redact_audio: Generate a copy of the original media file with spoken PII 'beeped' out. NOTE: The copy is available for 24h
            redact_audio_quality: The quality of the redacted audio file in case `redact_audio` is enabled.
            policies: A list of PII redaction policies to enable.
            substitution: The replacement logic for detected PII (`PIISubstutionPolicy.hash` by default).
        """

        if not enable:
            self._raw_transcription_config.redact_pii = None
            self._raw_transcription_config.redact_pii_audio = None
            self._raw_transcription_config.redact_pii_audio_quality = None
            self._raw_transcription_config.redact_pii_policies = None
            self._raw_transcription_config.redact_pii_sub = None

            return self

        if not policies:
            raise ValueError("You must provide at least one PII redaction policy.")

        self._raw_transcription_config.redact_pii = True
        self._raw_transcription_config.redact_pii_audio = redact_audio
        self._raw_transcription_config.redact_pii_audio_quality = redact_audio_quality
        self._raw_transcription_config.redact_pii_policies = policies
        self._raw_transcription_config.redact_pii_sub = substitution

        return self

    def set_custom_spelling(
        self,
        replacement: Optional[Dict[str, Union[str, Sequence[str]]]],
        override: bool = True,
    ) -> Self:
        """
        Customize how given words are being spelled or formatted in the transcription's text.

        Args:
            replacement: A dictionary that contains the replacement object (see below example).
                For each key-value pair, the key is the 'to' field, and the value is the 'from' field.
            override: If `True` `replacement` gets overriden with the given `replacement` argument, otherwise merged.

        Example:
            ```
            config.custom_spelling({
                "AssemblyAI": "assemblyAI",
                "Kubernetes": ["k8s", "kubernetes"]
            })
            ```
        """
        if replacement is None:
            self._raw_transcription_config.custom_spelling = None
            return self

        if self._raw_transcription_config.custom_spelling is None or override:
            self._raw_transcription_config.custom_spelling = []

        for to, from_ in replacement.items():
            if isinstance(from_, str):
                from_ = [from_]

            self._raw_transcription_config.custom_spelling.append(
                {
                    "from": list(from_),
                    "to": to,
                }
            )

        return self

    def set_summarize(
        self,
        enable: Optional[bool] = True,
        model: Optional[SummarizationModel] = None,
        type: Optional[SummarizationType] = None,
    ) -> Self:
        """
        Enable Summarization.

        Args:
            enable: whether to enable to disable the Summarization feature.
            model: The summarization model to use
            type: The type of summarization to return
        """

        if not enable:
            self._raw_transcription_config.summarization = None
            self._raw_transcription_config.summary_model = None
            self._raw_transcription_config.summary_type = None

            return self

        # Validate that required parameters are also set
        if self._raw_transcription_config.punctuate is False:
            raise ValueError(
                "If `summarization` is enabled, then `punctuate` must not be disabled"
            )
        if self._raw_transcription_config.format_text is False:
            raise ValueError(
                "If `summarization` is enabled, then `format_text` must not be disabled"
            )

        self._raw_transcription_config.summarization = True
        self._raw_transcription_config.summary_model = model
        self._raw_transcription_config.summary_type = type

        return self

        # endregion


class ContentSafetyLabel(str, Enum):
    accidents = "accidents"
    "Any man-made incident that happens unexpectedly and results in damage, injury, or death."

    alcohol = "alcohol"
    "Content that discusses any alcoholic beverage or its consumption."

    financials = "financials"
    "Content that discusses any sensitive company financial information."

    crime_violence = "crime_violence"
    "Content that discusses any type of criminal activity or extreme violence that is criminal in nature."

    drugs = "drugs"
    "Content that discusses illegal drugs or their usage."

    gambling = "gambling"
    "Includes gambling on casino-based games such as poker, slots, etc. as well as sports betting."

    hate_speech = "hate_speech"
    """
    Content that is a direct attack against people or groups based on their
    sexual orientation, gender identity, race, religion, ethnicity, national origin, disability, etc.
    """

    health_issues = "health_issues"
    "Content that discusses any medical or health-related problems."

    manga = "manga"
    """
    Mangas are comics or graphic novels originating from Japan with some of the more popular series being
    "Pokemon", "Naruto", "Dragon Ball Z", "One Punch Man", and "Sailor Moon".
    """

    marijuana = "marijuana"
    "This category includes content that discusses marijuana or its usage."

    disasters = "disasters"
    """
    Phenomena that happens infrequently and results in damage, injury, or death.
    Such as hurricanes, tornadoes, earthquakes, volcano eruptions, and firestorms.
    """

    negative_news = "negative_news"
    """
    News content with a negative sentiment which typically will occur in the third person as an unbiased recapping of events.
    """

    nsfw = "nsfw"
    """
    Content considered "Not Safe for Work" and consists of content that a viewer would not want to be heard/seen in a public environment.
    """

    pornography = "pornography"
    "Content that discusses any sexual content or material."

    profanity = "profanity"
    "Any profanity or cursing."

    sensitive_social_issues = "sensitive_social_issues"
    """
    This category includes content that may be considered insensitive, irresponsible, or harmful
    to certain groups based on their beliefs, political affiliation, sexual orientation, or gender identity.
    """

    terrorism = "terrorism"
    """
    Includes terrorist acts as well as terrorist groups.
    Examples include bombings, mass shootings, and ISIS. Note that many texts corresponding to this topic may also be classified into the crime violence topic.
    """

    tobacco = "tobacco"
    "Text that discusses tobacco and tobacco usage, including e-cigarettes, nicotine, vaping, and general discussions about smoking."

    weapons = "weapons"
    "Text that discusses any type of weapon including guns, ammunition, shooting, knives, missiles, torpedoes, etc."


class Word(BaseModel):
    text: str
    start: int
    end: int
    confidence: float
    speaker: Optional[str] = None
    channel: Optional[str] = None


class UtteranceWord(Word):
    channel: Optional[str] = None
    speaker: Optional[str] = None


class Utterance(UtteranceWord):
    words: List[UtteranceWord]


class Chapter(BaseModel):
    summary: str
    headline: str
    gist: str
    start: int
    end: int


class StatusResult(str, Enum):
    success = "success"
    unavailable = "unavailable"


class SentimentType(str, Enum):
    positive = "POSITIVE"
    neutral = "NEUTRAL"
    negative = "NEGATIVE"


class Timestamp(BaseModel):
    start: int
    end: int


class AutohighlightResult(BaseModel):
    count: int
    rank: float
    text: str
    timestamps: List[Timestamp]


class AutohighlightResponse(BaseModel):
    status: StatusResult
    results: Optional[List[AutohighlightResult]] = None


class ContentSafetyLabelResult(BaseModel):
    label: ContentSafetyLabel
    confidence: float
    severity: Optional[float] = None


class ContentSafetySeverityScore(BaseModel):
    low: float
    medium: float
    high: float


class ContentSafetyResult(BaseModel):
    text: str
    labels: List[ContentSafetyLabelResult]
    timestamp: Timestamp


class ContentSafetyResponse(BaseModel):
    status: StatusResult
    results: Optional[List[ContentSafetyResult]] = None
    summary: Optional[Dict[ContentSafetyLabel, float]] = None
    severity_score_summary: Optional[
        Dict[ContentSafetyLabel, ContentSafetySeverityScore]
    ] = None


class IABLabelResult(BaseModel):
    relevance: float
    label: str


class IABResult(BaseModel):
    text: str
    labels: List[IABLabelResult]
    timestamp: Timestamp


class IABResponse(BaseModel):
    status: StatusResult
    results: Optional[List[IABResult]] = None
    summary: Optional[Dict[str, float]] = None


class Sentiment(Word):
    sentiment: SentimentType
    speaker: Optional[str] = None
    channel: Optional[str] = None


class Entity(BaseModel):
    entity_type: EntityType
    text: str
    start: int
    end: int


class WordSearchMatch(BaseModel):
    text: str
    "The word itself"

    count: int
    "The total amount of times the word is in the transcript"

    timestamps: List[Tuple[int, int]]
    "An array of timestamps structured as [start_time, end_time]"

    indexes: List[int]
    "An array of all index locations for that word within the words array of the completed transcript"


class WordSearchMatchResponse(BaseModel):
    total_count: int
    "Equals the total of all matched instances."

    matches: List[WordSearchMatch]
    "Contains a list/array of all matched words and associated data"


class RedactedAudioResponse(BaseModel):
    redacted_audio_url: str
    "The URL of the redacted audio file."

    status: str
    "Information about the status of the redaction process (will be `redacted_audio_ready` if successful)"


class Sentence(Word):
    words: List[Word]
    start: int
    end: int
    confidence: float
    speaker: Optional[str] = None
    channel: Optional[str] = None


class SentencesResponse(BaseModel):
    sentences: List[Sentence]
    confidence: float
    audio_duration: float


class Paragraph(Word):
    words: List[Word]
    start: int
    end: int
    confidence: float
    text: str


class ParagraphsResponse(BaseModel):
    paragraphs: List[Paragraph]
    confidence: float
    audio_duration: float


class BaseTranscript(BaseModel):
    """
    Available transcription features
    """

    language_code: Optional[Union[str, LanguageCode]] = None
    """
    The language of your audio file. Possible values are found in Supported Languages.

    The default value is "en_us".
    """

    audio_url: str
    "The URL of your media file to transcribe."

    punctuate: Optional[bool] = None
    "Enable Automatic Punctuation"

    format_text: Optional[bool] = None
    "Enable Text Formatting"

    dual_channel: Optional[bool] = None
    "Enable Dual Channel transcription"

    multichannel: Optional[bool] = None
    "Enable Multichannel transcription"
    audio_channels: Optional[int] = None
    "The number of audio channels in the media file"

    webhook_url: Optional[str] = None
    "The URL we should send webhooks to when your transcript is complete."
    webhook_auth_header_name: Optional[str] = None
    "The name of the header that is sent when the `webhook_url` is being called."
    webhook_auth_header_value: Optional[str] = None
    "The value of the `webhook_auth_header_name` that is sent when the `webhook_url` is being called."

    audio_start_from: Optional[int] = None
    "The point in time, in milliseconds, to begin transcription from in your media file."
    audio_end_at: Optional[int] = None
    "The point in time, in milliseconds, to stop transcribing in your media file."

    word_boost: Optional[List[str]] = None
    "A list of custom vocabulary to boost accuracy for."
    boost_param: Optional[WordBoost] = None
    "The weight to apply to words/phrases in the word_boost array."

    filter_profanity: Optional[bool] = None
    "Filter profanity from the transcribed text."

    redact_pii: Optional[bool] = None
    "Redact PII from the transcribed text."
    redact_pii_audio: Optional[bool] = None
    "Generate a copy of the original media file with spoken PII 'beeped' out."
    redact_pii_audio_quality: Optional[PIIRedactedAudioQuality] = None
    "The quality of the redacted audio file in case `redact_pii_audio` is enabled."
    redact_pii_policies: Optional[List[PIIRedactionPolicy]] = None
    "The list of PII Redaction policies to enable."
    redact_pii_sub: Optional[PIISubstitutionPolicy] = None
    "The replacement logic for detected PII."

    speaker_labels: Optional[bool] = None
    "Enable Speaker Diarization."

    speakers_expected: Optional[int] = None
    "The number of speakers you expect to be in your audio file."

    content_safety: Optional[bool] = None
    "Enable Content Safety Detection."

    content_safety_confidence: Optional[int] = None
    "The minimum confidence level for a content safety label to be produced."

    iab_categories: Optional[bool] = None
    "Enable Topic Detection."

    custom_spelling: Optional[List[Dict[str, Union[str, List[str]]]]] = None
    "Customize how words are spelled and formatted using to and from values."

    disfluencies: Optional[bool] = None
    "Transcribe Filler Words, like 'umm', in your media file."

    sentiment_analysis: Optional[bool] = None
    "Enable Sentiment Analysis."

    auto_chapters: Optional[bool] = None
    "Enable Auto Chapters."

    entity_detection: Optional[bool] = None
    "Enable Entity Detection."

    summarization: Optional[bool] = None
    "Enable Summarization"
    summary_model: Optional[SummarizationModel] = None
    "The summarization model to use in case `summarization` is enabled"
    summary_type: Optional[SummarizationType] = None
    "The summarization type to use in case `summarization` is enabled"

    auto_highlights: Optional[bool] = None
    "Detect important phrases and words in your transcription text."

    language_detection: Optional[bool] = None
    """
    Identify the dominant language that's spoken in an audio file, and route the file to the appropriate model for the detected language.

    See the docs for supported languages: https://www.assemblyai.com/docs/getting-started/supported-languages
    """

    language_confidence_threshold: Optional[float] = None
    "The confidence threshold that must be reached if `language_detection` is enabled."

    language_confidence: Optional[float] = None
    "The confidence score for the detected language, between 0.0 (low confidence) and 1.0 (high confidence)."

    speech_threshold: Optional[float] = None
    "Reject audio files that contain less than this fraction of speech. Valid values are in the range [0,1] inclusive"

    speech_model: Optional[SpeechModel] = None
    "The speech model to use for the transcription."


class TranscriptRequest(BaseTranscript):
    """
    Transcript request schema
    """


class TranscriptResponse(BaseTranscript):
    """
    Transcript response schema
    """

    id: Optional[str] = None
    "The unique identifier of your transcription"

    status: TranscriptStatus
    "The status of your transcription. queued, processing, completed, or error"

    error: Optional[str] = None
    "The error message in case the transcription fails"

    text: Optional[str] = None
    "The text transcription of your media file"

    words: Optional[List[Word]] = None
    "A list of all the individual words transcribed"

    utterances: Optional[List[Utterance]] = None
    "When `dual_channel`, `multichannel`,  or `speaker_labels` is enabled, a list of turn-by-turn utterances"

    confidence: Optional[float] = None
    "The confidence our model has in the transcribed text, between 0.0 and 1.0"

    audio_duration: Optional[int] = None
    "The duration of your media file, in seconds"

    webhook_status_code: Optional[int] = None
    "The status code we received from your server when delivering your webhook"
    webhook_auth: Optional[bool] = None
    "Whether the webhook was sent with an HTTP authentication header"

    summary: Optional[str] = None
    "The summarization of the transcript"

    auto_highlights_result: Optional[AutohighlightResponse] = None
    "The list of results when enabling Automatic Transcript Highlights"

    content_safety_labels: Optional[ContentSafetyResponse] = None
    "The list of results when Content Safety is enabled"

    iab_categories_result: Optional[IABResponse] = None
    "The list of results when Topic Detection is enabled"

    chapters: Optional[List[Chapter]] = None
    "When Auto Chapters is enabled, the list of Auto Chapters results"

    sentiment_analysis_results: Optional[List[Sentiment]] = None
    "When Sentiment Analysis is enabled, the list of Sentiment Analysis results"

    entities: Optional[List[Entity]] = None
    "When Entity Detection is enabled, the list of detected Entities"

    speech_model: Optional[SpeechModel] = None
    "The speech model used for the transcription"

    def __init__(self, **data: Any):
        # cleanup the response before creating the object
        if not data.get("iab_categories_result") or (
            not data.get("iab_categories")
            and data.get("iab_categories_result", {}).get("status") == "unavailable"
        ):
            data["iab_categories_result"] = None

        if not data.get("content_safety_labels") or (
            not data.get("content_safety")
            and data.get("content_safety_labels", {}).get("status") == "unavailable"
        ):
            data["content_safety_labels"] = None

        super().__init__(**data)


class ListTranscriptParameters(BaseModel):
    """
    The query parameters when listing transcripts.
    """

    after_id: Optional[str] = None
    "Get transcripts that were created after this transcript ID"

    before_id: Optional[str] = None
    "Get transcripts that were created before this transcript ID"

    created_on: Optional[str] = None
    "Get only transcripts created on this date"

    limit: Optional[int] = None
    "Maximum amount of transcripts to retrieve. Default is 10"

    status: Optional[TranscriptStatus] = None
    "Filter by transcript status"

    throttled_only: Optional[bool] = None
    "Get only throttled transcripts, overrides the status filter"
    model_config = ConfigDict(use_enum_values=True)


class PageDetails(BaseModel):
    """
    Details of the transcript page.
    """

    current_url: str
    "The URL used to retrieve the current page of transcripts"

    limit: int
    "The number of results this page is limited to"

    next_url: Optional[str] = None
    "The URL to the next page of transcripts. The next URL always points to a page with newer transcripts."

    prev_url: Optional[str] = None
    "The URL to the next page of transcripts. The previous URL always points to a page with older transcripts."

    result_count: int
    "The actual number of results in the page"

    @property
    def before_id_of_prev_url(self) -> Optional[str]:
        """
        The `before_id` contained in the `prev_url` query params. Can be used as the
        `ListTranscriptParameters.before_id` for the subsequent `list_transcripts()` call to paginate over results.
        """
        if not self.prev_url:
            return None
        parsed_query_params = parse_qs(urlparse(self.prev_url).query)
        before_id_list = parsed_query_params.get("before_id")
        return before_id_list[0] if before_id_list else None


class TranscriptItem(BaseModel):
    audio_url: str
    completed: Optional[str] = None
    created: str
    error: Optional[str] = None
    id: str
    resource_url: str
    status: TranscriptStatus


class ListTranscriptResponse(BaseModel):
    """
    A list of returned transcripts along with page details.
    Transcripts are sorted from newest to oldest. The previous URL always points to a page with older transcripts.
    """

    page_details: PageDetails
    "Details of the returned transcript page"

    transcripts: List[TranscriptItem]
    "A list of transcripts sorted from newest to oldest"


class LemurSourceType(str, Enum):
    """
    The source type of the LeMUR request
    """

    transcript = "transcript"
    "The source is a transcript"


class LemurSource:
    """
    A LeMUR source is a source that can be used to process it with an LLM.
    """

    def __init__(
        self,
        source: Sourcable,
    ) -> None:
        """
        Creates a new LeMUR source to process audio files with an LLM.

        Args:

            source: The source to process (e.g. a `Transcript`)
        """
        self._source = source
        self._type = None

        from . import Transcript

        if isinstance(source, Transcript):
            self._type = LemurSourceType.transcript
        else:
            raise ValueError(f"Invalid source: {source}")

    @property
    def source(self) -> Sourcable:
        """
        The source to process (e.g. a `Transcript`)
        """
        return self._source

    @property
    def type(self) -> LemurSourceType:
        """
        The type of the source.
        """
        return self._type  # type: ignore


class LemurTranscriptSource(LemurSource):
    """
    A LeMUR source that can be used to process a transcript with an LLM.
    """

    def __init__(
        self,
        transcript: Union["Transcript", str],
    ) -> None:
        """
        Creates a new LeMUR transcript source to process audio files with an LLM.

        Args:

            transcript: The transcript to process
            context: An optional context on the source (can be a string or an arbitrary dictionary)
        """
        from . import Transcript

        if isinstance(transcript, str):
            transcript = Transcript(transcript_id=transcript)

        super().__init__(transcript)


class LemurSourceRequest(BaseModel):
    id: Optional[str] = None
    "The unique identifier of your source - only relevant for transcript sources"

    type: LemurSourceType
    "The type of source"

    @classmethod
    def from_lemur_source(cls, source: LemurSource) -> Self:
        """
        Creates a LemurSourceRequest from a LemurSource
        """
        if source.type == LemurSourceType.transcript:
            return cls(
                id=source.source.id,  # type:ignore
                type=source.type,
            )

        raise ValueError("Unsupported source type")


class LemurModel(str, Enum):
    """
    LeMUR features different model modes that allow you to configure your request to suit your needs.
    """

    claude3_5_sonnet = "anthropic/claude-3-5-sonnet"
    """
    Claude 3.5 Sonnet is the most intelligent model to date, outperforming Claude 3 Opus on a wide range of evaluations, with the speed and cost of Claude 3 Sonnet.
    """

    claude3_opus = "anthropic/claude-3-opus"
    """
    Claude 3 Opus is good at handling complex analysis, longer tasks with many steps, and higher-order math and coding tasks.
    """

    claude3_haiku = "anthropic/claude-3-haiku"
    """
    Claude 3 Haiku is the fastest model that can execute lightweight actions.
    """

    claude3_sonnet = "anthropic/claude-3-sonnet"
    """
    Claude 3 Sonnet is a legacy model with a balanced combination of performance and speed for efficient, high-throughput tasks.
    """

    claude2_1 = "anthropic/claude-2-1"
    """
    Claude 2.1 is a legacy model similar to Claude 2.0. The key difference is that it minimizes model hallucination and system prompts, has a larger context window, and performs better in citations.
    """

    claude2_0 = "anthropic/claude-2"
    """
    Claude 2.0 is a legacy model that has good complex reasoning. It offers more nuanced responses and improved contextual comprehension.
    """

    default = "default"
    """
    Legacy model. The same as `claude2_0`.
    """

    mistral7b = "assemblyai/mistral-7b"
    """
    Mistral 7B is an open source model that works well for summarization and answering questions.
    """


class LemurQuestionAnswer(BaseModel):
    """
    The result of your Question and Answer LeMUR request.
    """

    question: str
    "The question that was asked"

    answer: str
    "The answer to the question"


class LemurQuestion(BaseModel):
    """
    The question you wish to ask LeMUR
    """

    question: str
    "The question you wish to ask"

    context: Optional[Union[str, Dict[str, Any]]] = None
    "Context to provide the model - this can be a string or an arbitrary dictionary"

    answer_format: Optional[str] = None
    """
    How you want the answer to be returned. This can be any text.
    Cannot be used with answer_options.

    Examples:

        - "short sentence"
        - "bullet points"
    """

    answer_options: Optional[List[str]] = None
    """
    What discrete options to return. Useful for precise responses.

    Cannot be used with answer_format.

    Examples:

        - ["Yes", "No"]
        - ["High", "Medium", "Low"]
    """


class BaseLemurRequest(BaseModel):
    sources: List[LemurSourceRequest]
    final_model: Optional[LemurModel] = None
    max_output_size: Optional[int] = None
    temperature: Optional[float] = None
    input_text: Optional[str] = None


class LemurUsage(BaseModel):
    """
    The usage numbers for the LeMUR request
    """

    input_tokens: int
    "The number of input tokens used by the model"

    output_tokens: int
    "The number of output tokens generated by the model"


class BaseLemurResponse(BaseModel):
    request_id: str
    "The unique identifier of your LeMUR request"

    usage: LemurUsage
    "The usage numbers for the LeMUR request"


class LemurStringResponse(BaseLemurResponse):
    """
    The result of your LeMUR request with a string response.
    """

    response: str
    "The LLM response to your request"


class LemurTaskRequest(BaseLemurRequest):
    context: Optional[Union[str, Dict[str, Any]]] = None
    prompt: str


class LemurTaskResponse(LemurStringResponse):
    """
    The result of your LeMUR Task request.
    """


class LemurQuestionRequest(BaseLemurRequest):
    context: Optional[Union[str, Dict[str, Any]]] = None
    questions: List[LemurQuestion]


class LemurQuestionResponse(BaseLemurResponse):
    """
    The result of your Question and Answer LeMUR request.
    """

    response: List[LemurQuestionAnswer]
    "The list of answers to your questions"


class LemurSummaryRequest(BaseLemurRequest):
    context: Optional[Union[str, Dict[str, Any]]] = None
    answer_format: Optional[str] = None


class LemurSummaryResponse(LemurStringResponse):
    """
    The result of your Summary LeMUR request.
    """


class LemurActionItemsRequest(BaseLemurRequest):
    context: Optional[Union[str, Dict[str, Any]]] = None
    answer_format: Optional[str] = None


class LemurActionItemsResponse(LemurStringResponse):
    """
    The result of your Action Items LeMUR request.
    """


class LemurPurgeRequest(BaseModel):
    request_id: str


class LemurPurgeResponse(BaseModel):
    """
    The result of your LeMUR purge request.
    """

    request_id: str
    "The unique identifier of the LeMUR purge request"

    request_id_to_purge: str
    "The unique identifier of the LeMUR request nneds to be purged"

    deleted: bool
    "The result of the LeMUR purge request"


class RealtimeMessageTypes(str, Enum):
    """
    The type of message received from the real-time API
    """

    partial_transcript = "PartialTranscript"
    final_transcript = "FinalTranscript"
    session_begins = "SessionBegins"
    session_terminated = "SessionTerminated"
    session_information = "SessionInformation"


class AudioEncoding(str, Enum):
    """
    The encoding of the audio data
    """

    pcm_s16le = "pcm_s16le"
    pcm_mulaw = "pcm_mulaw"


class RealtimeCreateTemporaryTokenRequest(BaseModel):
    expires_in: int
    "The amount of time until the token expires in seconds"


class RealtimeCreateTemporaryTokenResponse(BaseModel):
    token: str
    "The temporary authentication token for real-time transcription"


class RealtimeSessionOpened(BaseModel):
    """
    Once a real-time session is opened, the client will receive this message
    """

    message_type: RealtimeMessageTypes = RealtimeMessageTypes.session_begins

    session_id: UUID4
    "Unique identifier for the established session."

    expires_at: datetime
    "Timestamp when this session will expire."


class RealtimeWord(BaseModel):
    """
    A word in a real-time transcript
    """

    start: int
    "Start time of word relative to session start, in milliseconds"

    end: int
    "End time of word relative to session start, in milliseconds"

    confidence: float
    "The confidence score of the word, between 0 and 1"

    text: str
    "The word itself"


class RealtimeTranscript(BaseModel):
    """
    Base class for real-time transcript messages.
    """

    message_type: RealtimeMessageTypes
    "Describes the type of message"

    audio_start: int
    "Start time of audio sample relative to session start, in milliseconds"

    audio_end: int
    "End time of audio sample relative to session start, in milliseconds"

    confidence: float
    "The confidence score of the entire transcription, between 0 and 1"

    text: str
    "The transcript for your audio"

    words: List[RealtimeWord]
    """
    An array of objects, with the information for each word in the transcription text.
    Will include the `start`/`end` time (in milliseconds) of the word, the `confidence` score of the word,
    and the `text` (i.e. the word itself)
    """

    created: datetime
    "Timestamp when this message was created"


class RealtimePartialTranscript(RealtimeTranscript):
    """
    As you send audio data to the service, the service will immediately start responding with partial transcripts.
    """

    message_type: RealtimeMessageTypes = RealtimeMessageTypes.partial_transcript


class RealtimeFinalTranscript(RealtimeTranscript):
    """
    After you've received your partial results, our model will continue to analyze incoming audio and,
    when it detects the end of an "utterance" (usually a pause in speech), it will finalize the results
    sent to you so far with higher accuracy, as well as add punctuation and casing to the transcription text.
    """

    message_type: RealtimeMessageTypes = RealtimeMessageTypes.final_transcript

    punctuated: bool
    "Whether the transcript has been punctuated and cased"

    text_formatted: bool
    "Whether the transcript has been formatted (e.g. Dollar -> $)"


class RealtimeSessionInformation(BaseModel):
    """
    If `on_extra_session_information` is set, the client receives this message
    right before receiving the session termination message.
    """

    message_type: RealtimeMessageTypes = RealtimeMessageTypes.session_information

    audio_duration_seconds: float
    "The duration of the audio in seconds"


class RealtimeError(AssemblyAIError):
    """
    Real-time error message
    """


RealtimeErrorMapping = {
    4000: "Sample rate must be a positive integer",
    4001: "Not Authorized",
    4002: "Insufficient Funds",
    4003: """This feature is paid-only and requires you to add a credit card.
    Please visit https://app.assemblyai.com/ to add a credit card to your account""",
    4004: "Session Not Found",
    4008: "Session Expired",
    4010: "Session Previously Closed",
    4029: "Client sent audio too fast",
    4030: "Session is handled by another websocket",
    4031: "Session idle for too long",
    4032: "Audio duration is too short",
    4033: "Audio duration is too long",
    4034: "Audio too small to transcode",
    4100: "Endpoint received invalid JSON",
    4101: "Endpoint received a message with an invalid schema",
    4102: "This account has exceeded the number of allowed streams",
    4103: "The session has been reconnected. This websocket is no longer valid.",
    4104: "Could not parse word boost parameter",
    1013: "Temporary server condition forced blocking client's request",
}
