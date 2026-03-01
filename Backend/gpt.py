import re
import os
import json
from ollama import Client, ResponseError

from dotenv import load_dotenv
from logstream import log
from typing import Tuple, List, Optional
from utils import ENV_FILE

# Load environment variables
load_dotenv(ENV_FILE)

# Set environment variables
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "180"))


def _ollama_client() -> Client:
    return Client(host=OLLAMA_BASE_URL, timeout=OLLAMA_TIMEOUT)


def _extract_model_name(model_obj) -> str:
    if hasattr(model_obj, "model") and getattr(model_obj, "model"):
        return str(getattr(model_obj, "model")).strip()
    if hasattr(model_obj, "name") and getattr(model_obj, "name"):
        return str(getattr(model_obj, "name")).strip()
    if isinstance(model_obj, dict):
        return str(model_obj.get("model") or model_obj.get("name") or "").strip()
    return ""


def list_ollama_models() -> Tuple[List[str], str]:
    """
    Returns available Ollama model names and configured default model.

    Returns:
        Tuple[List[str], str]: (available model names, default model)
    """
    try:
        response = _ollama_client().list()
    except Exception as err:
        raise RuntimeError(f"Failed to fetch Ollama models: {err}") from err

    models = []
    if hasattr(response, "models") and getattr(response, "models") is not None:
        models = list(getattr(response, "models"))
    elif isinstance(response, dict):
        models = response.get("models") or []

    model_names = [_extract_model_name(model) for model in models]
    model_names = [name for name in model_names if name]

    unique_names = list(dict.fromkeys(model_names))

    if OLLAMA_MODEL and OLLAMA_MODEL in unique_names:
        default_model = OLLAMA_MODEL
    elif unique_names:
        default_model = unique_names[0]
    else:
        default_model = OLLAMA_MODEL if OLLAMA_MODEL else ""

    return unique_names, default_model


def generate_response(prompt: str, ai_model: str) -> str:
    """
    Generate a script for a video, depending on the subject of the video.

    Args:
        video_subject (str): The subject of the video.
        ai_model (str): The AI model to use for generation.


    Returns:

        str: The response from the AI model.

    """

    model_name = (ai_model or "").strip() or OLLAMA_MODEL

    try:
        client = _ollama_client()
        try:
            response = client.chat(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                stream=False,
            )
        except ResponseError as err:
            if err.status_code == 404:
                try:
                    response = client.generate(
                        model=model_name, prompt=prompt, stream=False
                    )
                except ResponseError as fallback_err:
                    if (
                        fallback_err.status_code == 404
                        and "not found" in str(fallback_err).lower()
                    ):
                        available_models, _ = list_ollama_models()
                        available = (
                            ", ".join(available_models) if available_models else "none"
                        )
                        raise RuntimeError(
                            f"Ollama model '{model_name}' is not installed. Available models: {available}. "
                            f"Install it with: ollama pull {model_name}"
                        ) from fallback_err
                    raise
            else:
                raise
    except RuntimeError:
        raise
    except Exception as err:
        raise RuntimeError(f"Failed to connect to Ollama: {err}") from err

    content = ""
    if hasattr(response, "message") and getattr(response, "message") is not None:
        message = getattr(response, "message")
        if hasattr(message, "content") and getattr(message, "content"):
            content = str(getattr(message, "content")).strip()
        elif isinstance(message, dict):
            content = str(message.get("content") or "").strip()

    if not content:
        if hasattr(response, "response") and getattr(response, "response"):
            content = str(getattr(response, "response")).strip()
        elif isinstance(response, dict):
            content = (
                str(response.get("message", {}).get("content") or "")
                or str(response.get("response") or "")
            ).strip()

    if not content:
        raise RuntimeError("Ollama returned an empty response.")

    return content


def generate_script(
    video_subject: str,
    paragraph_number: int,
    ai_model: str,
    voice: str,
    customPrompt: str,
) -> Optional[str]:
    """
    Generate a script for a video, depending on the subject of the video, the number of paragraphs, and the AI model.



    Args:

        video_subject (str): The subject of the video.

        paragraph_number (int): The number of paragraphs to generate.

        ai_model (str): The AI model to use for generation.



    Returns:

        str: The script for the video.

    """

    # Build prompt

    if customPrompt:
        prompt = customPrompt
    else:
        prompt = """
            Generate a script for a video, depending on the subject of the video.

            The script is to be returned as a string with the specified number of paragraphs.

            Here is an example of a string:
            "This is an example string."

            Do not under any circumstance reference this prompt in your response.

            Get straight to the point, don't start with unnecessary things like, "welcome to this video".

            Obviously, the script should be related to the subject of the video.

            YOU MUST NOT INCLUDE ANY TYPE OF MARKDOWN OR FORMATTING IN THE SCRIPT, NEVER USE A TITLE.
            YOU MUST WRITE THE SCRIPT IN THE LANGUAGE SPECIFIED IN [LANGUAGE].
            ONLY RETURN THE RAW CONTENT OF THE SCRIPT. DO NOT INCLUDE "VOICEOVER", "NARRATOR" OR SIMILAR INDICATORS OF WHAT SHOULD BE SPOKEN AT THE BEGINNING OF EACH PARAGRAPH OR LINE. YOU MUST NOT MENTION THE PROMPT, OR ANYTHING ABOUT THE SCRIPT ITSELF. ALSO, NEVER TALK ABOUT THE AMOUNT OF PARAGRAPHS OR LINES. JUST WRITE THE SCRIPT.

        """

    prompt += f"""
    
    Subject: {video_subject}
    Number of paragraphs: {paragraph_number}
    Language: {voice}

    """

    # Generate script
    response = generate_response(prompt, ai_model)

    log(response, "info")

    # Return the generated script
    if response:
        # Clean the script
        # Remove asterisks, hashes
        response = response.replace("*", "")
        response = response.replace("#", "")

        # Remove markdown syntax
        response = re.sub(r"\[.*\]", "", response)
        response = re.sub(r"\(.*\)", "", response)

        # Split the script into paragraphs
        paragraphs = response.split("\n\n")

        # Select the specified number of paragraphs
        selected_paragraphs = paragraphs[:paragraph_number]

        # Join the selected paragraphs into a single string
        final_script = "\n\n".join(selected_paragraphs)

        # Print to console the number of paragraphs used
        log(f"Number of paragraphs used: {len(selected_paragraphs)}", "success")

        return final_script
    else:
        log("[-] GPT returned an empty response.", "error")
        return None


def get_search_terms(
    video_subject: str, amount: int, script: str, ai_model: str
) -> List[str]:
    """
    Generate a JSON-Array of search terms for stock videos,
    depending on the subject of a video.

    Args:
        video_subject (str): The subject of the video.
        amount (int): The amount of search terms to generate.
        script (str): The script of the video.
        ai_model (str): The AI model to use for generation.

    Returns:
        List[str]: The search terms for the video subject.
    """

    # Build prompt
    prompt = f"""
    Generate {amount} search terms for stock videos,
    depending on the subject of a video.
    Subject: {video_subject}

    The search terms are to be returned as
    a JSON-Array of strings.

    Each search term should consist of 1-3 words,
    always add the main subject of the video.
    
    YOU MUST ONLY RETURN THE JSON-ARRAY OF STRINGS.
    YOU MUST NOT RETURN ANYTHING ELSE. 
    YOU MUST NOT RETURN THE SCRIPT.
    
    The search terms must be related to the subject of the video.
    Here is an example of a JSON-Array of strings:
    ["search term 1", "search term 2", "search term 3"]

    For context, here is the full text:
    {script}
    """

    # Generate search terms
    response = generate_response(prompt, ai_model)
    log(response, "info")

    # Parse response into a list of search terms
    search_terms = []

    try:
        search_terms = json.loads(response)
        if not isinstance(search_terms, list) or not all(
            isinstance(term, str) for term in search_terms
        ):
            raise ValueError("Response is not a list of strings.")

    except (json.JSONDecodeError, ValueError):
        log("[*] GPT returned an unformatted response. Attempting to clean...", "warning")

        # Attempt to extract JSON array first
        match = re.search(r"\[[\s\S]*\]", response)
        if match:
            try:
                search_terms = json.loads(match.group())
            except json.JSONDecodeError:
                search_terms = []

        # Last-resort fallback: collect quoted strings
        if not search_terms:
            search_terms = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', response)
            search_terms = [term.strip() for term in search_terms if term.strip()]

    # Let user know
    log(f"\nGenerated {len(search_terms)} search terms: {', '.join(search_terms)}", "info")

    # Return search terms
    return search_terms


def generate_metadata(
    video_subject: str, script: str, ai_model: str
) -> Tuple[str, str, List[str]]:
    """
    Generate metadata for a YouTube video, including the title, description, and keywords.

    Args:
        video_subject (str): The subject of the video.
        script (str): The script of the video.
        ai_model (str): The AI model to use for generation.

    Returns:
        Tuple[str, str, List[str]]: The title, description, and keywords for the video.
    """

    # Build prompt for title
    title_prompt = f"""  
    Generate a catchy and SEO-friendly title for a YouTube shorts video about {video_subject}.  
    """

    # Generate title
    title = generate_response(title_prompt, ai_model).strip()

    # Build prompt for description
    description_prompt = f"""  
    Write a brief and engaging description for a YouTube shorts video about {video_subject}.  
    The video is based on the following script:  
    {script}  
    """

    # Generate description
    description = generate_response(description_prompt, ai_model).strip()

    # Generate keywords
    keywords = get_search_terms(video_subject, 6, script, ai_model)

    return title, description, keywords
