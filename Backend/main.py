import os
import shutil
import subprocess
import threading
from utils import *
from dotenv import load_dotenv

# Load environment variables
load_dotenv(ENV_FILE)
# Check if all required environment variables are set
# This must happen before importing video which uses API keys without checking
check_env_vars()

from gpt import *
from video import *
from search import *
from uuid import uuid4
from tiktokvoice import *
from flask_cors import CORS
from youtube import upload_video
from apiclient.errors import HttpError
from flask import Flask, request, jsonify, Response
from moviepy import AudioFileClip, CompositeAudioClip, VideoFileClip, afx, concatenate_audioclips
from moviepy.config import change_settings
from logstream import log, log_stream


# Set environment variables
SESSION_ID = os.getenv("TIKTOK_SESSION_ID")
change_settings({"IMAGEMAGICK_BINARY": os.environ["IMAGEMAGICK_BINARY"]})

# Initialize Flask
app = Flask(__name__)
CORS(app)

# Constants
HOST = "0.0.0.0"
PORT = 8080
AMOUNT_OF_STOCK_VIDEOS = 5
GENERATING = False


@app.route("/api/models", methods=["GET"])
def models():
    try:
        available_models, default_model = list_ollama_models()
        return jsonify(
            {
                "status": "success",
                "models": available_models,
                "default": default_model,
            }
        )
    except Exception as err:
        log(f"[-] Error fetching Ollama models: {str(err)}", "error")
        return jsonify(
            {
                "status": "error",
                "message": "Could not fetch Ollama models. Is Ollama running?",
                "models": [os.getenv("OLLAMA_MODEL", "llama3.1:8b")],
                "default": os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
            }
        )


def _run_generation(data: dict) -> None:
    """Pipeline body — runs in a background thread."""
    global GENERATING
    try:
        paragraph_number = int(data.get("paragraphNumber", 1))
        ai_model = data.get("aiModel")
        n_threads = data.get("threads")
        subtitles_position = data.get("subtitlesPosition")
        text_color = data.get("color")
        use_music = data.get("useMusic", False)
        automate_youtube_upload = data.get("automateYoutubeUpload", False)

        log("[Video to be generated]", "info")
        log("   Subject: " + data["videoSubject"], "info")
        log("   AI Model: " + ai_model, "info")
        log("   Custom Prompt: " + data["customPrompt"], "info")

        if not GENERATING:
            log_stream.push_event("cancelled", {"message": "Video generation was cancelled."})
            return

        voice = data["voice"]
        voice_prefix = voice[:2]

        if not voice:
            log('[!] No voice was selected. Defaulting to "en_us_001"', "warning")
            voice = "en_us_001"
            voice_prefix = voice[:2]

        # Generate a script
        script = generate_script(
            data["videoSubject"],
            paragraph_number,
            ai_model,
            voice,
            data["customPrompt"],
        )

        if not script:
            log_stream.push_event("error", {"message": "Could not generate a script. Try a different model or prompt."})
            return

        # Generate search terms
        search_terms = get_search_terms(
            data["videoSubject"], AMOUNT_OF_STOCK_VIDEOS, script, ai_model
        )

        # Search for a video of the given search term
        video_urls = []
        it = 15
        min_dur = 10

        for search_term in search_terms:
            if not GENERATING:
                log_stream.push_event("cancelled", {"message": "Video generation was cancelled."})
                return
            found_urls = search_for_stock_videos(
                search_term, os.getenv("PEXELS_API_KEY"), it, min_dur
            )
            for url in found_urls:
                if url not in video_urls:
                    video_urls.append(url)
                    break

        if not video_urls:
            log("[-] No videos found to download.", "error")
            log_stream.push_event("error", {"message": "No videos found to download."})
            return

        video_paths = []
        log(f"[+] Downloading {len(video_urls)} videos...", "info")

        for video_url in video_urls:
            if not GENERATING:
                log_stream.push_event("cancelled", {"message": "Video generation was cancelled."})
                return
            try:
                saved_video_path = save_video(video_url)
                video_paths.append(saved_video_path)
            except Exception:
                log(f"[-] Could not download video: {video_url}", "error")

        log("[+] Videos downloaded!", "success")
        log("[+] Script generated!\n", "success")

        if not GENERATING:
            log_stream.push_event("cancelled", {"message": "Video generation was cancelled."})
            return

        # Split script into sentences
        sentences = script.split(". ")
        sentences = list(filter(lambda x: x != "", sentences))
        paths = []

        for sentence in sentences:
            if not GENERATING:
                log_stream.push_event("cancelled", {"message": "Video generation was cancelled."})
                return
            current_tts_path = str(TEMP_DIR / f"{uuid4()}.mp3")
            tts(sentence, voice, filename=current_tts_path)
            audio_clip = AudioFileClip(current_tts_path)
            paths.append(audio_clip)

        # Combine all TTS files using moviepy
        final_audio = concatenate_audioclips(paths)
        tts_path = str(TEMP_DIR / f"{uuid4()}.mp3")
        try:
            final_audio.write_audiofile(tts_path)
        finally:
            final_audio.close()
            for audio_clip in paths:
                audio_clip.close()

        try:
            subtitles_path = generate_subtitles(
                audio_path=tts_path,
                sentences=sentences,
                audio_clips=paths,
                voice=voice_prefix,
            )
        except Exception as e:
            log(f"[-] Error generating subtitles: {e}", "error")
            subtitles_path = None

        if not subtitles_path:
            log_stream.push_event("error", {"message": "Could not generate subtitles. Check AssemblyAI key or local subtitle settings."})
            return

        # Concatenate videos
        temp_audio = AudioFileClip(tts_path)
        try:
            combined_video_path = combine_videos(
                video_paths, temp_audio.duration, 5, n_threads or 2
            )
        finally:
            temp_audio.close()

        # Put everything together
        try:
            final_video_path = generate_video(
                combined_video_path,
                tts_path,
                subtitles_path,
                n_threads or 2,
                subtitles_position,
                text_color or "#FFFF00",
            )
        except Exception as e:
            log(f"[-] Error generating final video: {e}", "error")
            final_video_path = None

        if not final_video_path:
            log_stream.push_event("error", {"message": "Could not render final video. Check subtitle/font/ImageMagick setup."})
            return

        # Generate metadata
        title, description, keywords = generate_metadata(
            data["videoSubject"], script, ai_model
        )

        log("[-] Metadata for YouTube upload:", "info")
        log("   Title: ", "info")
        log(f"   {title}", "info")
        log("   Description: ", "info")
        log(f"   {description}", "info")
        log("   Keywords: ", "info")
        log(f"  {', '.join(keywords)}", "info")

        if automate_youtube_upload:
            client_secrets_file = str((BASE_DIR / "client_secret.json").resolve())
            SKIP_YT_UPLOAD = False
            if not os.path.exists(client_secrets_file):
                SKIP_YT_UPLOAD = True
                log("[-] Client secrets file missing. YouTube upload will be skipped.", "warning")
                log("[-] Please download the client_secret.json from Google Cloud Platform and store this inside the /Backend directory.", "error")

            if not SKIP_YT_UPLOAD:
                video_category_id = "28"
                privacyStatus = "private"
                video_metadata = {
                    "video_path": str((TEMP_DIR / final_video_path).resolve()),
                    "title": title,
                    "description": description,
                    "category": video_category_id,
                    "keywords": ",".join(keywords),
                    "privacyStatus": privacyStatus,
                }

                try:
                    video_response = upload_video(
                        video_path=video_metadata["video_path"],
                        title=video_metadata["title"],
                        description=video_metadata["description"],
                        category=video_metadata["category"],
                        keywords=video_metadata["keywords"],
                        privacy_status=video_metadata["privacyStatus"],
                    )
                    log(f"Uploaded video ID: {video_response.get('id')}", "success")
                except HttpError as e:
                    log(f"An HTTP error {e.resp.status} occurred:\n{e.content}", "error")

        final_output_path = str(PROJECT_ROOT / final_video_path)
        rendered_video_path = str(TEMP_DIR / final_video_path)
        render_threads = n_threads or (os.cpu_count() or 2)

        if use_music:
            song_path = choose_random_song()

            if not song_path:
                log(
                    "[-] Could not find songs in Songs/. Continuing without background music.",
                    "warning",
                )
                use_music = False

            if use_music:
                video_clip = VideoFileClip(rendered_video_path)
                song_clip = None
                mixed_audio = None
                mixed_audio_path = str(TEMP_DIR / f"{uuid4()}_mixed_audio.m4a")
                try:
                    original_duration = video_clip.duration
                    original_audio = video_clip.audio
                    song_clip = AudioFileClip(song_path).with_fps(44100)
                    song_clip = song_clip.with_effects(
                        [afx.AudioLoop(duration=original_duration)]
                    )
                    song_clip = song_clip.with_volume_scaled(0.1).with_fps(44100)

                    mixed_audio = CompositeAudioClip(
                        [original_audio, song_clip]
                    ).with_duration(original_duration)
                    mixed_audio.write_audiofile(
                        mixed_audio_path,
                        fps=44100,
                        codec="aac",
                        bitrate="192k",
                    )
                finally:
                    video_clip.close()
                    if mixed_audio is not None:
                        mixed_audio.close()
                    if song_clip is not None:
                        song_clip.close()

                try:
                    # Keep video quality identical by copying the video stream and only replacing audio.
                    subprocess.run(
                        [
                            "ffmpeg",
                            "-y",
                            "-i",
                            rendered_video_path,
                            "-i",
                            mixed_audio_path,
                            "-map",
                            "0:v:0",
                            "-map",
                            "1:a:0",
                            "-c:v",
                            "copy",
                            "-c:a",
                            "aac",
                            "-b:a",
                            "192k",
                            "-shortest",
                            final_output_path,
                        ],
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                except Exception:
                    # Fallback: if ffmpeg CLI isn't available, render through MoviePy.
                    log(
                        "[!] ffmpeg remux failed. Falling back to MoviePy render for music mix.",
                        "warning",
                    )
                    video_clip = VideoFileClip(rendered_video_path)
                    song_clip = None
                    try:
                        original_duration = video_clip.duration
                        original_audio = video_clip.audio
                        song_clip = AudioFileClip(song_path).with_fps(44100)
                        song_clip = song_clip.with_effects(
                            [afx.AudioLoop(duration=original_duration)]
                        )
                        song_clip = song_clip.with_volume_scaled(0.1).with_fps(44100)
                        comp_audio = CompositeAudioClip(
                            [original_audio, song_clip]
                        ).with_duration(original_duration)
                        video_clip = video_clip.with_audio(comp_audio).with_fps(30).with_duration(
                            original_duration
                        )
                        video_clip.write_videofile(
                            final_output_path,
                            threads=render_threads,
                            fps=30,
                            codec="libx264",
                            audio_codec="aac",
                            preset="medium",
                        )
                    finally:
                        video_clip.close()
                        if song_clip is not None:
                            song_clip.close()
                finally:
                    if os.path.exists(mixed_audio_path):
                        os.remove(mixed_audio_path)

        if not use_music:
            # Reuse the already rendered file to avoid a second lossy re-encode.
            shutil.copy2(rendered_video_path, final_output_path)

        log(f"[+] Video generated: {final_video_path}!", "success")

        # Stop FFMPEG processes
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/f", "/im", "ffmpeg.exe"],
                check=False,
                capture_output=True,
                text=True,
            )
        elif shutil.which("pkill"):
            subprocess.run(
                ["pkill", "-f", "ffmpeg"],
                check=False,
                capture_output=True,
                text=True,
            )

        log_stream.push_event("complete", {
            "message": "Video generated! See MoneyPrinter/output.mp4 for result.",
            "data": final_video_path,
        })

    except Exception as err:
        log(f"[-] Error: {str(err)}", "error")
        log_stream.push_event("error", {"message": f"Could not retrieve stock videos: {str(err)}"})
    finally:
        GENERATING = False


# Generation Endpoint
@app.route("/api/generate", methods=["POST"])
def generate():
    global GENERATING

    if GENERATING:
        return jsonify(
            {
                "status": "error",
                "message": "A video is already being generated. Please wait or cancel first.",
            }
        ), 409

    GENERATING = True

    # Clean
    clean_dir(str(TEMP_DIR))
    clean_dir(str(SUBTITLES_DIR))

    # Clear the log queue before starting
    log_stream.clear()

    data = request.get_json()

    thread = threading.Thread(target=_run_generation, args=(data,), daemon=True)
    thread.start()

    return jsonify(
        {
            "status": "success",
            "message": "Video generation started.",
        }
    )


@app.route("/api/logs", methods=["GET"])
def stream_logs():
    return Response(
        log_stream.stream(timeout=30.0),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.route("/api/upload-songs", methods=["POST"])
def upload_songs():
    try:
        files = request.files.getlist("songs")
        if not files:
            return jsonify({"status": "error", "message": "No files uploaded."}), 400

        # Clear existing songs and save new ones
        clean_dir(str(SONGS_DIR))
        saved = 0
        for f in files:
            if f.filename and f.filename.lower().endswith(".mp3"):
                safe_name = os.path.basename(f.filename)
                f.save(str(SONGS_DIR / safe_name))
                saved += 1

        if saved == 0:
            return jsonify({"status": "error", "message": "No MP3 files found."}), 400

        log(f"[+] Uploaded {saved} song(s) to {SONGS_DIR}", "success")
        return jsonify({"status": "success", "message": f"Uploaded {saved} song(s)."})
    except Exception as err:
        log(f"[-] Error uploading songs: {str(err)}", "error")
        return jsonify({"status": "error", "message": str(err)}), 500


@app.route("/api/cancel", methods=["POST"])
def cancel():
    log("[!] Received cancellation request...", "warning")

    global GENERATING
    GENERATING = False

    return jsonify({"status": "success", "message": "Cancelled video generation."})


if __name__ == "__main__":
    # Run Flask App
    app.run(debug=True, host=HOST, port=PORT, threaded=True)
