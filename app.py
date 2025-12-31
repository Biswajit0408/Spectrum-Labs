from flask import Flask, render_template, request, session, redirect, url_for
import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
from flask import jsonify


load_dotenv()

from palette_logic import (
    extract_palette,
    assign_color_roles,
    wcag_result,
    rgb_to_hex
)

app = Flask(__name__)

# =====================
# SESSION CONFIG
# =====================
app.secret_key = "super-secret-key-123"
app.config["SESSION_PERMANENT"] = True

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# =====================
# TOKENS FILE
# =====================
STATIC_FOLDER = "static"
os.makedirs(STATIC_FOLDER, exist_ok=True)

TOKENS_FILE = os.path.join(STATIC_FOLDER, "tokens.css")


# =====================
# HELPER: WRITE TOKENS
# =====================
def write_tokens_css(roles: dict):
    with open(TOKENS_FILE, "w") as f:
        f.write(f"""
:root {{
  --bg: {roles["background"]};
  --text: {roles["text"]};
  --primary: {roles["primary"]};
  --accent: {roles["accent"]};
}}
""".strip())


# =====================
# MAIN PAGE
# =====================
@app.route("/", methods=["GET", "POST"])
def index():

    if request.method == "POST":
        action = request.form.get("action")

        # =====================
        # GENERATE PALETTE
        # =====================
        if action == "generate":
            file = request.files.get("image")

            if file:
                image_path = os.path.join(UPLOAD_FOLDER, file.filename)
                file.save(image_path)

                rgb_colors, hex_colors = extract_palette(image_path, n_colors=6)
                roles_rgb = assign_color_roles(rgb_colors)

                roles = {role: rgb_to_hex(rgb) for role, rgb in roles_rgb.items()}

                ratio, level = wcag_result(
                    roles_rgb["text"],
                    roles_rgb["background"]
                )

                write_tokens_css(roles)

                session["data"] = {
                    "palette": hex_colors,
                    "roles": roles,
                    "contrast_ratio": ratio,
                    "contrast_level": level
                }

        # =====================
        # APPLY ROLE CHANGES + SAVE USER CODE
        # =====================
        elif action == "apply":

            # ---------- PALETTE ----------
            hex_colors = request.form.getlist("palette[]")

            rgb_colors = [
                tuple(int(c[i:i+2], 16) for i in (1, 3, 5))
                for c in hex_colors
            ]

            roles_rgb = assign_color_roles(rgb_colors)

            for role in ["text", "background", "primary", "accent"]:
                hex_val = request.form.get(role)
                if hex_val:
                    roles_rgb[role] = tuple(
                        int(hex_val[i:i+2], 16) for i in (1, 3, 5)
                    )

            roles = {role: rgb_to_hex(rgb) for role, rgb in roles_rgb.items()}

            ratio, level = wcag_result(
                roles_rgb["text"],
                roles_rgb["background"]
            )

            write_tokens_css(roles)

            session["data"] = {
                "palette": hex_colors,
                "roles": roles,
                "contrast_ratio": ratio,
                "contrast_level": level
            }

            # ---------- USER HTML + CSS ----------
            user_html = request.form.get("user_html", "")
            user_css = request.form.get("user_css", "")

            session["user_code"] = {
                "html": user_html,
                "css": user_css
            }

        return redirect(url_for("index"))

    # =====================
    # HANDLE GET
    # =====================
    data = session.get("data")
    user_code = session.get("user_code", {"html": "", "css": ""})

    return render_template(
        "index.html",
        data=data,
        user_code=user_code
    )


# =====================
# UI PREVIEW PAGE
# =====================
@app.route("/ui-preview")
def ui_preview():

    data = session.get("data")
    user_code = session.get("user_code")

    if not data or not user_code:
        return redirect(url_for("index"))

    return render_template(
        "ui-preview.html",
        data=data,
        user_code=user_code
    )

# =====================
# SEND EMAIL
# =====================
def send_contact_email(name, email, message):
    user = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")
    to_email = os.getenv("TO_EMAIL")

    subject = "New message from SPECTRUM Contact Form"

    body = f"""New message received:

Name: {name}
Email: {email}

Message:
{message}
"""

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to_email

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(user, password)
            server.sendmail(user, to_email, msg.as_string())

        print("Email sent successfully")
        return True

    except Exception as e:
        print("Email error:", e)
        return False




# =====================
# CONTACT API
# =====================
@app.route("/contact", methods=["POST"])
def contact():

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    message = request.form.get("message", "").strip()

    if not name or not email or not message:
        return jsonify({"ok": False, "error": "Missing fields"}), 400

    if send_contact_email(name, email, message):
        return jsonify({"ok": True})

    return jsonify({"ok": False, "error": "Email failed"}), 500


# =====================
# RUN
# =====================
import os

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )