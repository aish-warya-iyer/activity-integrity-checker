import os

from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request

load_dotenv()

import analysis  # noqa: E402  (must import after load_dotenv so env vars are populated)
import guardrail  # noqa: E402
import lyzr_client  # noqa: E402
import strava  # noqa: E402

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev")

APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:5001")
REDIRECT_URI = f"{APP_BASE_URL}/exchange_token"
SCOPE = "activity:write,activity:read_all"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login")
def login():
    authorize_url = (
        "https://www.strava.com/oauth/authorize"
        f"?client_id={strava.CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        "&response_type=code"
        "&approval_prompt=auto"
        f"&scope={SCOPE}"
    )
    return redirect(authorize_url)


@app.route("/exchange_token")
def exchange_token():
    error = request.args.get("error")
    if error:
        return f"Authorization denied: {error}", 400

    code = request.args.get("code")
    if not code:
        return "Missing code parameter", 400

    strava.exchange_code_for_token(code)
    return redirect("/profile")


@app.route("/profile")
def profile():
    athlete = strava.api_get("/athlete")
    return jsonify(athlete)


@app.route("/activities")
def activities():
    raw = strava.api_get("/athlete/activities", params={"per_page": 10, "page": 1})
    summary = [
        {
            "id": a["id"],
            "name": a["name"],
            "type": a["type"],
            "start_date_local": a["start_date_local"],
            "distance_m": a["distance"],
            "has_gps": a.get("start_latlng") not in (None, []),
        }
        for a in raw
    ]
    return jsonify(summary)


@app.route("/activity/<int:activity_id>/detail")
def activity_detail(activity_id):
    detail = strava.api_get(f"/activities/{activity_id}", params={"include_all_efforts": "true"})
    return jsonify(detail)


@app.route("/activity/<int:activity_id>/streams")
def activity_streams(activity_id):
    streams = strava.api_get(
        f"/activities/{activity_id}/streams",
        params={"keys": "latlng,distance,time", "key_by_type": "true"},
    )
    return jsonify(streams)


@app.route("/activity/<int:activity_id>/analyze")
def activity_analyze(activity_id):
    return jsonify(analysis.analyze_activity(activity_id))


@app.route("/activity/<int:activity_id>/explain")
def activity_explain(activity_id):
    deviation_results = analysis.analyze_activity(activity_id)
    if not deviation_results:
        return jsonify({"deviation_results": [], "explanation": None, "note": "No matched segment efforts on this activity."})
    raw_explanation = lyzr_client.generate_explanation(deviation_results)
    guarded = guardrail.guard_explanation(raw_explanation, deviation_results)
    return jsonify(
        {
            "deviation_results": deviation_results,
            "raw_explanation": raw_explanation,
            "final_text": guarded["text"],
            "guardrail_blocked": guarded["blocked"],
            "adherence_score": guarded["adherence_score"],
        }
    )


@app.route("/activity/<int:activity_id>/writeback", methods=["POST"])
def activity_writeback(activity_id):
    deviation_results = analysis.analyze_activity(activity_id)
    if not deviation_results:
        return jsonify({"deviation_results": [], "written": False, "note": "No matched segment efforts on this activity."})

    raw_explanation = lyzr_client.generate_explanation(deviation_results)
    guarded = guardrail.guard_explanation(raw_explanation, deviation_results)
    updated_activity = strava.append_activity_description(activity_id, guarded["text"])

    return jsonify(
        {
            "deviation_results": deviation_results,
            "raw_explanation": raw_explanation,
            "written_text": guarded["text"],
            "guardrail_blocked": guarded["blocked"],
            "adherence_score": guarded["adherence_score"],
            "description": updated_activity.get("description"),
        }
    )


if __name__ == "__main__":
    app.run(port=int(os.environ.get("PORT", 5001)), debug=True)
