from flask import Flask, render_template, request, session, redirect, url_for
import os

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
    """
    Writes CSS variables to static/tokens.css
    """
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

                roles = {
                    role: rgb_to_hex(rgb)
                    for role, rgb in roles_rgb.items()
                }

                ratio, level = wcag_result(
                    roles_rgb["text"],
                    roles_rgb["background"]
                )

                # ✅ WRITE DESIGN TOKENS
                write_tokens_css(roles)

                session["data"] = {
                    "palette": hex_colors,
                    "roles": roles,
                    "contrast_ratio": ratio,
                    "contrast_level": level
                }

        # =====================
        # APPLY ROLE CHANGES
        # =====================
        elif action == "apply":
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

            roles = {
                role: rgb_to_hex(rgb)
                for role, rgb in roles_rgb.items()
            }

            ratio, level = wcag_result(
                roles_rgb["text"],
                roles_rgb["background"]
            )

            # ✅ UPDATE DESIGN TOKENS
            write_tokens_css(roles)

            session["data"] = {
                "palette": hex_colors,
                "roles": roles,
                "contrast_ratio": ratio,
                "contrast_level": level
            }

        # 🔴 POST → REDIRECT → GET (CRITICAL)
        return redirect(url_for("index"))

    # =====================
    # HANDLE GET
    # =====================
    data = session.get("data")
    return render_template("index.html", data=data)


# =====================
# UI PREVIEW PAGE
# =====================
@app.route("/ui-preview")
def ui_preview():
    """
    Dedicated UI preview page.
    Uses tokens.css automatically.
    """
    data = session.get("data")
    if not data:
        return redirect(url_for("index"))

    return render_template("ui-preview.html", data=data)


# =====================
# RUN APP
# =====================
if __name__ == "__main__":
    # 🔴 Disable reloader (prevents session wipe)
    app.run(debug=True, use_reloader=False)
