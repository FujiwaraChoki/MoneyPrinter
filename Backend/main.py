import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from sqlalchemy import and_, case, select

from db import SessionLocal, init_db
from gpt import list_ollama_models
from logstream import log
from repository import create_job, get_job, list_job_events, request_cancel
from utils import ENV_FILE, SONGS_DIR, check_env_vars, clean_dir


load_dotenv(ENV_FILE)
check_env_vars()
init_db()

app = Flask(__name__)
CORS(app)

HOST = "0.0.0.0"
PORT = 8080


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


@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.get_json() or {}
    if not data.get("videoSubject"):
        return jsonify({"status": "error", "message": "videoSubject is required."}), 400

    with SessionLocal() as session:
        job = create_job(session, payload=data)

    return jsonify(
        {
            "status": "success",
            "message": "Video generation queued.",
            "jobId": job.id,
        }
    )


@app.route("/api/jobs/<job_id>", methods=["GET"])
def get_job_status(job_id: str):
    with SessionLocal() as session:
        job = get_job(session, job_id)
        if not job:
            return jsonify({"status": "error", "message": "Job not found."}), 404

        return jsonify(
            {
                "status": "success",
                "job": {
                    "id": job.id,
                    "state": job.status,
                    "cancelRequested": job.cancel_requested,
                    "resultPath": job.result_path,
                    "errorMessage": job.error_message,
                    "createdAt": job.created_at.isoformat() if job.created_at else None,
                    "startedAt": job.started_at.isoformat() if job.started_at else None,
                    "completedAt": job.completed_at.isoformat()
                    if job.completed_at
                    else None,
                },
            }
        )


@app.route("/api/jobs/<job_id>/events", methods=["GET"])
def get_events(job_id: str):
    after_id = request.args.get("after", default=0, type=int)

    with SessionLocal() as session:
        job = get_job(session, job_id)
        if not job:
            return jsonify({"status": "error", "message": "Job not found."}), 404

        events = list_job_events(session, job_id, after_id=after_id)
        return jsonify(
            {
                "status": "success",
                "events": [
                    {
                        "id": event.id,
                        "type": event.event_type,
                        "level": event.level,
                        "message": event.message,
                        "payload": event.payload,
                        "timestamp": event.created_at.timestamp()
                        if event.created_at
                        else None,
                    }
                    for event in events
                ],
            }
        )


@app.route("/api/jobs/<job_id>/cancel", methods=["POST"])
def cancel_job(job_id: str):
    with SessionLocal() as session:
        cancelled = request_cancel(session, job_id)
        if not cancelled:
            return jsonify({"status": "error", "message": "Job not found."}), 404

    return jsonify({"status": "success", "message": "Cancellation requested."})


@app.route("/api/upload-songs", methods=["POST"])
def upload_songs():
    try:
        files = request.files.getlist("songs")
        if not files:
            return jsonify({"status": "error", "message": "No files uploaded."}), 400

        clean_dir(str(SONGS_DIR))
        saved = 0
        for file_item in files:
            if file_item.filename and file_item.filename.lower().endswith(".mp3"):
                safe_name = os.path.basename(file_item.filename)
                file_item.save(str(SONGS_DIR / safe_name))
                saved += 1

        if saved == 0:
            return jsonify({"status": "error", "message": "No MP3 files found."}), 400

        log(f"[+] Uploaded {saved} song(s) to {SONGS_DIR}", "success")
        return jsonify({"status": "success", "message": f"Uploaded {saved} song(s)."})
    except Exception as err:
        log(f"[-] Error uploading songs: {str(err)}", "error")
        return jsonify({"status": "error", "message": str(err)}), 500


@app.route("/api/cancel", methods=["POST"])
def cancel_latest_running_job():
    with SessionLocal() as session:
        from models import GenerationJob

        stmt = (
            select(GenerationJob)
            .where(and_(GenerationJob.status.in_(["queued", "running"])))
            .order_by(
                case((GenerationJob.status == "running", 0), else_=1),
                GenerationJob.created_at.desc(),
            )
            .limit(1)
        )
        latest_job = session.scalars(stmt).first()
        if not latest_job:
            return jsonify({"status": "error", "message": "No active job found."}), 404

        request_cancel(session, latest_job.id)

    return jsonify(
        {
            "status": "success",
            "message": "Cancellation requested.",
            "jobId": latest_job.id,
        }
    )


if __name__ == "__main__":
    app.run(debug=True, host=HOST, port=PORT, threaded=True)
