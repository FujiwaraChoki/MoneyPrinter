import re
import os
import g4f
import json
import openai
import google.generativeai as genai

from g4f.client import Client
from termcolor import colored
from dotenv import load_dotenv
from typing import Tuple, List
import requests  # Tambahkan di bagian import paling atas


# Load environment variables
load_dotenv("../.env")

# Set environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)


def generate_response_mistral(prompt: str) -> str:
    """
    Generate response menggunakan API Mistral AI dari Ryzendesu

    Args:
        prompt (str): Teks prompt

    Returns:
        str: Respon dari API
    """
    try:
        # URL API
        url = "https://api.ryzendesu.vip/api/ai/mistral"

        # Parameter query
        params = {"text": prompt}

        # Headers
        headers = {"accept": "application/json"}

        # Kirim request
        response = requests.get(url, params=params, headers=headers)

        # Periksa respon
        if response.status_code == 200:
            data = response.json()

            # Periksa struktur respon spesifik untuk Mistral AI
            if data.get("action") == "success":
                return data.get("response", "").strip()
            else:
                print(f"API Mistral AI Error: {data}")
                return ""
        else:
            print(f"HTTP Error: {response.status_code}")
            return ""

    except Exception as e:
        print(f"Error generate response Mistral AI: {e}")
        return ""


def generate_response_ryzendesu(prompt: str) -> str:
    """
    Generate response menggunakan API ryzendesu

    Args:
        prompt (str): Teks prompt

    Returns:
        str: Respon dari API
    """
    try:
        # URL API
        url = "https://api.ryzendesu.vip/api/ai/chatgpt"

        # Parameter query
        params = {"text": prompt}

        # Headers
        headers = {"accept": "application/json"}

        # Kirim request
        response = requests.get(url, params=params, headers=headers)

        # Periksa respon
        if response.status_code == 200:
            data = response.json()

            # Periksa struktur respon
            if data.get("success", False):
                return data.get("response", "")
            else:
                print(f"API Ryzendesu Error: {data}")
                return ""
        else:
            print(f"HTTP Error: {response.status_code}")
            return ""

    except Exception as e:
        print(f"Error generate response Ryzendesu: {e}")
        return ""


def generate_response_meta_llama(prompt: str) -> str:
    try:
        # URL API
        url = "https://api.ryzendesu.vip/api/ai/meta-llama"

        # Parameter query
        params = {"text": prompt}

        # Headers
        headers = {"accept": "application/json"}

        # Kirim request
        response = requests.get(url, params=params, headers=headers)

        # Periksa respon
        if response.status_code == 200:
            data = response.json()

            # Periksa struktur respon spesifik untuk meta-llama
            if data.get("action") == "success":
                return data.get("response", "")
            else:
                print(f"API Meta-Llama Error: {data}")
                return ""
        else:
            print(f"HTTP Error: {response.status_code}")
            return ""

    except Exception as e:
        print(f"Error generate response Meta-Llama: {e}")
        return ""


def generate_response_claude(prompt: str) -> str:
    """
    Generate response menggunakan API Claude AI dari Ryzendesu

    Args:
        prompt (str): Teks prompt

    Returns:
        str: Respon dari API
    """
    try:
        # URL API
        url = "https://api.ryzendesu.vip/api/ai/claude"

        # Parameter query
        params = {"text": prompt}

        # Headers
        headers = {"accept": "application/json"}

        # Kirim request
        response = requests.get(url, params=params, headers=headers)

        # Periksa respon
        if response.status_code == 200:
            data = response.json()

            # Periksa struktur respon spesifik untuk Claude AI
            if data.get("action") == "success":
                return data.get("response", "").strip()
            else:
                print(f"API Claude AI Error: {data}")
                return ""
        else:
            print(f"HTTP Error: {response.status_code}")
            return ""

    except Exception as e:
        print(f"Error generate response Claude AI: {e}")
        return ""


def generate_response_blackbox(prompt: str, options: str = "blackboxai") -> str:
    """
    Generate response menggunakan API BlackBox AI dari Ryzendesu

    Args:
        prompt (str): Teks prompt
        options (str, optional): Model yang digunakan. Defaults to 'blackboxai'.

    Returns:
        str: Respon dari API
    """
    try:
        # URL API
        url = "https://api.ryzendesu.vip/api/ai/blackbox"

        # Parameter query
        params = {"chat": prompt, "options": options}

        # Headers
        headers = {"accept": "application/json"}

        # Kirim request
        response = requests.get(url, params=params, headers=headers)

        # Periksa respon
        if response.status_code == 200:
            data = response.json()

            # Periksa struktur respon spesifik untuk BlackBox AI
            if "response" in data:
                # Ambil hanya teks respon, abaikan additional info
                return data["response"].strip()
            else:
                print(f"API BlackBox AI Error: Tidak ada respon")
                return ""
        else:
            print(f"HTTP Error: {response.status_code}")
            return ""

    except Exception as e:
        print(f"Error generate response BlackBox AI: {e}")
        return ""


def generate_response(prompt: str, ai_model: str) -> str:
    """
    Generate a script for a video, depending on the subject of the video.

    Args:
        video_subject (str): The subject of the video.
        ai_model (str): The AI model to use for generation.


    Returns:

        str: The response from the AI model.

    """

    if ai_model == "g4f":
        # Newest G4F Architecture
        client = Client()
        response = (
            client.chat.completions.create(
                model="gpt-3.5-turbo",
                provider=g4f.Provider.You,
                messages=[{"role": "user", "content": prompt}],
            )
            .choices[0]
            .message.content
        )
    elif ai_model == "ryzendesu":
        # Gunakan API Ryzendesu
        response = generate_response_ryzendesu(prompt)
    elif ai_model == "meta":
        # Gunakan API Ryzendesu
        response = generate_response_meta_llama(prompt)
    elif ai_model == "mistral":
        # Gunakan API Ryzendesu Mistral AI
        response = generate_response_mistral(prompt)
    elif ai_model == "blackbox":
        # Gunakan API Ryzendesu BlackBox AI
        response = generate_response_blackbox(prompt)
    elif ai_model == "claude":
        # Gunakan API Ryzendesu BlackBox AI
        response = generate_response_claude(prompt)
    elif ai_model == "gpt40":
        # Gunakan API Ryzendesu BlackBox AI
        response = generate_response_blackbox(prompt, "gpt-4o")
    elif ai_model == "geminipro":
        # Gunakan API Ryzendesu BlackBox AI
        response = generate_response_blackbox(prompt, "gemini-pro")
    elif ai_model == "bclaude":
        # Gunakan API Ryzendesu BlackBox AI
        response = generate_response_blackbox(prompt, "claude-3.5-sonnet")

    elif ai_model in ["gpt3.5-turbo", "gpt4"]:
        model_name = (
            "gpt-3.5-turbo" if ai_model == "gpt3.5-turbo" else "gpt-4-1106-preview"
        )

        response = (
            openai.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
            )
            .choices[0]
            .message.content
        )
    elif ai_model == "gemmini":
        model = genai.GenerativeModel("gemini-pro")
        response_model = model.generate_content(prompt)
        response = response_model.text

    else:
        raise ValueError("Invalid AI model selected.")

    return response


def generate_script(
    video_subject: str,
    paragraph_number: int,
    ai_model: str,
    voice: str,
    customPrompt: str,
) -> str:
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

    print(colored(response, "cyan"))

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
        print(
            colored(f"Number of paragraphs used: {len(selected_paragraphs)}", "green")
        )

        return final_script
    else:
        print(colored("[-] GPT returned an empty response.", "red"))
        return None


# def get_search_terms(video_subject: str, amount: int, script: str, ai_model: str) -> List[str]:
#     """
#     Generate a JSON-Array of search terms for stock videos,
#     depending on the subject of a video.
#
#     Args:
#         video_subject (str): The subject of the video.
#         amount (int): The amount of search terms to generate.
#         script (str): The script of the video.
#         ai_model (str): The AI model to use for generation.
#
#     Returns:
#         List[str]: The search terms for the video subject.
#     """
#
#     # Build prompt
#     prompt = f"""
#     Generate {amount} search terms for stock videos,
#     depending on the subject of a video.
#     Subject: {video_subject}
#
#     The search terms are to be returned as
#     a JSON-Array of strings.
#
#     Each search term should consist of 1-3 words,
#     always add the main subject of the video.
#
#     YOU MUST ONLY RETURN THE JSON-ARRAY OF STRINGS.
#     YOU MUST NOT RETURN ANYTHING ELSE.
#     YOU MUST NOT RETURN THE SCRIPT.
#
#     The search terms must be related to the subject of the video.
#     Here is an example of a JSON-Array of strings:
#     ["search term 1", "search term 2", "search term 3"]
#
#     For context, here is the full text:
#     {script}
#     """
#
#     # Generate search terms
#     response = generate_response(prompt, ai_model)
#     print(response)
#
#     # Parse response into a list of search terms
#     search_terms = []
#
#     try:
#         search_terms = json.loads(response)
#         if not isinstance(search_terms, list) or not all(isinstance(term, str) for term in search_terms):
#             raise ValueError("Response is not a list of strings.")
#
#     except (json.JSONDecodeError, ValueError):
#         # Get everything between the first and last square brackets
#         response = response[response.find("[") + 1:response.rfind("]")]
#
#         print(colored("[*] GPT returned an unformatted response. Attempting to clean...", "yellow"))
#
#         # Attempt to extract list-like string and convert to list
#         match = re.search(r'\["(?:[^"\\]|\\.)*"(?:,\s*"[^"\\]*")*\]', response)
#         print(match.group())
#         if match:
#             try:
#                 search_terms = json.loads(match.group())
#             except json.JSONDecodeError:
#                 print(colored("[-] Could not parse response.", "red"))
#                 return []
#
#
#     # Let user know
#     print(colored(f"\nGenerated {len(search_terms)} search terms: {', '.join(search_terms)}", "cyan"))
#
#     # Return search terms
#     return search_terms


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

    # Fallback search terms
    fallback_terms = [
        video_subject,
        f"{video_subject} tutorial",
        f"{video_subject} guide",
        "learning",
        "educational video",
    ]

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

    try:
        # Generate search terms
        response = generate_response(prompt, ai_model)
        print(f"Raw Search Terms Response: {response}")

        # Parsing dan validasi search terms
        search_terms = []

        # Metode parsing bertingkat
        try:
            # Coba parsing JSON langsung
            search_terms = json.loads(response)
        except (json.JSONDecodeError, ValueError):
            # Jika parsing JSON gagal, coba ekstraksi manual
            import re

            # Cari pola array JSON
            match = re.search(
                r'\["(?:[^"\\]|\\.)*"(?:,\s*"[^"\\]*")*\]', response, re.DOTALL
            )
            if match:
                try:
                    search_terms = json.loads(match.group())
                except:
                    # Ekstraksi terms dari string
                    terms = re.findall(r'"([^"]*)"', response)
                    if terms:
                        search_terms = terms

            # Jika masih kosong, gunakan fallback
            if not search_terms:
                search_terms = fallback_terms

        # Bersihkan dan filter terms
        search_terms = [
            term.strip()
            for term in search_terms
            if term.strip() and len(term.strip()) > 0
        ]

        # Batasi jumlah terms
        search_terms = search_terms[:amount]

        # Jika masih kosong, gunakan fallback
        if not search_terms:
            search_terms = fallback_terms[:amount]

        print(
            colored(
                f"\nGenerated {len(search_terms)} search terms: {', '.join(search_terms)}",
                "cyan",
            )
        )
        return search_terms

    except Exception as e:
        print(colored(f"Error generating search terms: {e}", "red"))
        # Kembalikan fallback terms jika gagal total
        return fallback_terms[:amount]


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
