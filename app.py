import io
import logging
import pandas as pd
from flask import Flask, request, render_template, send_file, jsonify
from label_generator import generate_labels_pdf

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32 MB upload limit

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    if "master" not in request.files or "field_list" not in request.files:
        return jsonify(error="Both files are required."), 400

    master_file = request.files["master"]
    field_file = request.files["field_list"]

    if not master_file.filename or not field_file.filename:
        return jsonify(error="Both files are required."), 400

    try:
        master_df = pd.read_excel(io.BytesIO(master_file.read()))
        master_df = master_df.astype(str).replace(r"\.0$", "", regex=True)
        query_df = pd.read_excel(io.BytesIO(field_file.read()))

        cruise_year = request.form.get("cruise_year", "").strip()
        box_number = request.form.get("box_number", "").strip()

        pdf_bytes, missing = generate_labels_pdf(master_df, query_df, cruise_year, box_number)

        response = send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name="labels.pdf",
        )
        if missing:
            response.headers["X-Warnings"] = "\t".join(missing)
        return response

    except ValueError as e:
        return jsonify(error=str(e)), 400
    except Exception as e:
        log.exception("Error generating labels")
        return jsonify(error=f"Server error: {e}"), 500


if __name__ == "__main__":
    app.run(debug=True)
