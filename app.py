from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session as flask_session,
    flash,
    g,
)
# Compatibility shim: recent Flask versions removed `flask.Markup` which some
# extensions (older Flask-WTF) still import. If `Markup` is available from
# `markupsafe`, expose it on the `flask` module so imports succeed.
try:
    import flask as _flask_mod
    from markupsafe import Markup as _Markup
    if not hasattr(_flask_mod, "Markup"):
        _flask_mod.Markup = _Markup
except Exception:
    # best-effort only; if markupsafe isn't available we'll surface the
    # original import error when attempting to import `flask_wtf`.
    pass
try:
    from flask_wtf import CSRFProtect
    from flask_wtf.csrf import CSRFError
    _HAS_FLASK_WTF = True
except Exception:
    # Allow the app to run even if `flask-wtf` is not installed.
    CSRFProtect = None
    CSRFError = None
    _HAS_FLASK_WTF = False
import sqlite3
import time
from typing import Dict, List


# --- Flask setup ---
app = Flask(__name__)
app.secret_key = "change_this_secret_key"  # change this for production
# Enable CSRF protection for forms (requires `flask-wtf` in requirements)
if _HAS_FLASK_WTF and CSRFProtect is not None:
    csrf = CSRFProtect()
    csrf.init_app(app)

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        # Render a user-friendly page for CSRF validation failures
        return render_template('csrf_error.html'), 400
else:
    # Provide a no-op `csrf_token()` helper for templates so existing forms
    # that include `{{ csrf_token() }}` will still render when `flask-wtf`
    # is not installed. In production you should install `flask-wtf`.
    @app.context_processor
    def _inject_noop_csrf_token():
        def _csrf_token():
            return ""
        return {"csrf_token": _csrf_token}

# Security: set cookie flags. In development on plain HTTP you may need to set
# `SESSION_COOKIE_SECURE=False` so cookies work without HTTPS. In production,
# ensure `SESSION_COOKIE_SECURE=True` and serve over HTTPS.
app.config.update(
    # In development we need cookies to work over plain HTTP. Set to True
    # in production (HTTPS). For local smoke tests use False so session
    # cookies are returned by the client.
    SESSION_COOKIE_SECURE=False,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_HTTPONLY=True,
)


# --- Database helper ---
DATABASE = "cbt.db"


def get_db() -> sqlite3.Connection:
    """Return a SQLite connection stored on Flask's `g` object.

    The connection uses `sqlite3.Row` so rows behave like dicts.
    """
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()



# --- User login ---
@app.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login and initialize an exam session for the user.

    On successful POST: clears previous answers for the user and stores
    a list of question ids and start time in the session.
    """
    if request.method == "POST":
        user_id = request.form.get("user_id", "").strip()
        pin = request.form.get("pin", "").strip()

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE user_id=? AND pin=? AND active=1",
            (user_id, pin),
        ).fetchone()

        if user:
            # Clear any existing session state to avoid leftover flags
            flask_session.clear()

            # store user id in session
            flask_session["user_id"] = user_id

            # clear any previous answers for this user
            db.execute("DELETE FROM answers WHERE user_id=?", (user_id,))
            db.commit()

            # load question ids and initialize progress
            rows = db.execute("SELECT id FROM questions ORDER BY RANDOM () LIMIT 50").fetchall() # To limit questions, replace with "SELECT id FROM questions ORDER BY RANDOM () LIMIT 50"
            flask_session["questions"] = [r["id"] for r in rows]
            flask_session["current_q"] = 0
            flask_session["instructions_shown"] = False
            # exam_start will be set when user clicks "Start Exam"

            return redirect(url_for("exam"))

        return render_template("user_login.html", error="Invalid ID or PIN")

    return render_template("user_login.html")


# --- Exam route ---
@app.route("/exam", methods=["GET", "POST"])
def exam():
    """Display and handle navigation/answer submission for the exam."""
    db = get_db()
    # (no debug prints) determine exam state normally

    # Timer: 30 minutes (in seconds)
    exam_duration = 30 * 60

    # Handle POST actions first so we can set `exam_start` when the user clicks Start Exam
    if request.method == "POST":
        action = request.form.get("action")
        selected_option = request.form.get("option")
        jump_to = request.form.get("jump_to")

        # Mark instructions as shown and set exam start when user clicks Start Exam
        if action == "start_exam":
            flask_session["instructions_shown"] = True
            flask_session["exam_start"] = int(time.time())
            return redirect(url_for("exam"))

        current_index = int(flask_session.get("current_q", 0))
        question_id = flask_session["questions"][current_index]

        # Save answer if provided
        if selected_option:
            db.execute(
                "INSERT OR REPLACE INTO answers (user_id, question_id, selected_option) VALUES (?, ?, ?)",
                (flask_session["user_id"], question_id, selected_option),
            )
            db.commit()

        # Jump navigation (takes precedence)
        if jump_to is not None:
            try:
                target = int(jump_to)
            except (ValueError, TypeError):
                target = None
            if target is not None and 0 <= target < len(flask_session["questions"]):
                flask_session["current_q"] = target

        # Next / previous controls
        elif action == "next":
            if flask_session["current_q"] < len(flask_session["questions"]) - 1:
                flask_session["current_q"] += 1
            else:
                return redirect(url_for("results"))

        elif action == "previous":
            if flask_session["current_q"] > 0:
                flask_session["current_q"] -= 1
        elif action == "next":
            if flask_session["current_q"] < len(flask_session["questions"]) - 1:
                flask_session["current_q"] += 1
            else:
                return redirect(url_for("results"))

        elif action == "previous":
            if flask_session["current_q"] > 0:
                flask_session["current_q"] -= 1

    # Determine remaining time depending on whether the exam has actually started
    instructions_shown = flask_session.get("instructions_shown", False)
    if not instructions_shown:
        # If instructions are still showing, do not require exam_start yet — user has full duration
        remaining = exam_duration
    else:
        exam_start = flask_session.get("exam_start")
        if not exam_start:
            # start time missing even though instructions were marked shown; force user back to login
            return redirect(url_for("login"))

        elapsed = int(time.time()) - int(exam_start)
        remaining = max(exam_duration - elapsed, 0)

        # If time is up, go to results
        if remaining <= 0:
            return redirect(url_for("results"))

    # Fetch current question and saved answer
    current_q_index = int(flask_session.get("current_q", 0))
    question_id = flask_session["questions"][current_q_index]
    question = db.execute("SELECT * FROM questions WHERE id=?", (question_id,)).fetchone()

    saved_answer = db.execute(
        "SELECT * FROM answers WHERE user_id=? AND question_id=?",
        (flask_session["user_id"], question_id),
    ).fetchone()

    # Prepare navigation states used by the template
    rows = db.execute("SELECT question_id FROM answers WHERE user_id=?", (flask_session["user_id"],)).fetchall()
    answered_map = {r["question_id"]: True for r in rows}

    nav_states = [
        {"index": idx, "answered": qid in answered_map, "active": idx == current_q_index}
        for idx, qid in enumerate(flask_session["questions"]) ]

    return render_template(
        "exam.html",
        question=question,
        current_q=current_q_index,
        total_q=len(flask_session["questions"]),
        saved_answer=saved_answer,
        nav_states=nav_states,
        remaining=remaining,
        show_instructions=not flask_session.get("instructions_shown", False),
    )


# --- Results route ---
@app.route("/results")
def results():
    """Compute and display exam results for the current user."""
    if "user_id" not in flask_session:
        return redirect(url_for("login"))

    db = get_db()
    questions = db.execute("SELECT * FROM questions").fetchall()

    answers = {
        a["question_id"]: a["selected_option"]
        for a in db.execute("SELECT * FROM answers WHERE user_id=?", (flask_session["user_id"],)).fetchall()
    }

    score = 0
    answered_count = 0
    skipped_count = 0
    detailed_results: List[Dict] = []

    option_map = {"option_a": "A", "option_b": "B", "option_c": "C", "option_d": "D"}

    for q in questions:
        user_answer = answers.get(q["id"])
        correct_option = q["correct_option"]

        if user_answer:
            answered_count += 1
        else:
            skipped_count += 1

        is_correct = (user_answer == correct_option) if user_answer else False
        if is_correct:
            score += 1

        detailed_results.append({
            "question": q["question"],
            "options": {
                "option_a": q["option_a"],
                "option_b": q["option_b"],
                "option_c": q["option_c"],
                "option_d": q["option_d"],
            },
            "user_answer": option_map.get(user_answer, "Unanswered"),
            "correct_answer": option_map.get(correct_option, correct_option),
            "is_correct": is_correct,
        })

    return render_template(
        "results.html",
        score=score,
        total=len(questions),
        answered=answered_count,
        skipped=skipped_count,
        results=detailed_results,
    )


# --- Homepage ---
@app.route("/")
def homepage():
    return render_template("homepage.html")


# --- Admin login / dashboard ---
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        pin = request.form.get("pin", "").strip()

        # reuse get_db to keep connections consistent
        db = get_db()
        row = db.execute("SELECT id FROM admins WHERE username=? AND pin=? AND active=1", (username, pin)).fetchone()

        if row:
            flask_session["is_admin"] = True
            flask_session["admin_id"] = row["id"]
            return redirect(url_for("admin_dashboard"))

        error = "Invalid credentials or inactive admin."

    return render_template("admin_login.html", error=error)


@app.route("/admin")
def admin_dashboard():
    if not flask_session.get("is_admin"):
        return redirect(url_for("admin_login"))
    return render_template("admin_dashboard.html")


@app.route("/admin/users", methods=["GET", "POST"])
def admin_users():
    db = get_db()

    if request.method == "POST":
        user_id = request.form.get("user_id", "").strip()
        pin = request.form.get("pin", "").strip()
        message = None
        try:
            db.execute("INSERT INTO users (user_id, pin, active) VALUES (?, ?, ?)", (user_id, pin, 1))
            db.commit()
            message = f"✅ User {user_id} added successfully!"
        except sqlite3.IntegrityError:
            message = f"⚠ User ID {user_id} already exists."

        users = db.execute("SELECT * FROM users WHERE active=1 ORDER BY id").fetchall()
        return render_template("admin_users.html", users=users, message=message)

    users = db.execute("SELECT * FROM users WHERE active=1 ORDER BY id").fetchall()
    return render_template("admin_users.html", users=users)


@app.route('/admin/inactive_users')
def admin_inactive_users():
    """Show inactive users for audit/restore."""
    db = get_db()
    users = db.execute("SELECT * FROM users WHERE active=0 ORDER BY id").fetchall()
    return render_template('admin_inactive_users.html', users=users)


@app.route("/delete_user/<int:user_id>", methods=["POST"])
def delete_user(user_id: int):
    db = get_db()
    # Find the user's string `user_id` (login id) so we can remove related rows
    row = db.execute("SELECT user_id FROM users WHERE id=?", (user_id,)).fetchone()
    if row:
        uid = row["user_id"]
        # Remove answers and saved sessions for this user to avoid orphaned data
        db.execute("DELETE FROM answers WHERE user_id=?", (uid,))
        # If a sessions table is used, remove attempts tied to this user
        try:
            db.execute("DELETE FROM sessions WHERE user_id=?", (uid,))
        except sqlite3.OperationalError:
            # sessions table may not exist in some schemas; ignore if missing
            pass
        # Finally remove the user record
        db.execute("DELETE FROM users WHERE id=?", (user_id,))
        db.commit()

        flash(f"User '{uid}' deleted.")

    return redirect(url_for("admin_users"))


@app.route("/toggle_user/<int:user_id>", methods=["POST"])
def toggle_user(user_id: int):
    db = get_db()
    user = db.execute("SELECT active FROM users WHERE id=?", (user_id,)).fetchone()
    if user:
        new_status = 0 if user["active"] == 1 else 1
        db.execute("UPDATE users SET active=? WHERE id=?", (new_status, user_id))
        db.commit()
    return redirect(url_for("admin_users"))


@app.route('/deactivate_user/<int:user_id>', methods=["POST"])
def deactivate_user(user_id: int):
    """Set the user's `active` flag to 0 (deactivate) and return to manage users."""
    db = get_db()
    user = db.execute("SELECT id FROM users WHERE id=?", (user_id,)).fetchone()
    if user:
        db.execute("UPDATE users SET active=0 WHERE id=?", (user_id,))
        db.commit()
        # Try to show which user was deactivated by fetching their user_id
        row = db.execute("SELECT user_id FROM users WHERE id=?", (user_id,)).fetchone()
        if row:
            flash(f"User '{row['user_id']}' deactivated.")
    return redirect(url_for("admin_users"))


@app.route('/reactivate_user/<int:user_id>', methods=["POST"])
def reactivate_user(user_id: int):
    """Reactivate a previously deactivated user and return to inactive users list."""
    db = get_db()
    user = db.execute("SELECT user_id FROM users WHERE id=?", (user_id,)).fetchone()
    if user:
        db.execute("UPDATE users SET active=1 WHERE id=?", (user_id,))
        db.commit()
        flash(f"User '{user['user_id']}' reactivated.")
    return redirect(url_for('admin_inactive_users'))


@app.route("/logout", methods=["POST"])
def logout():
    """Clear the session and return to the login page.

    This endpoint is POST-only to avoid CSRF-vulnerable GET logout links.
    """
    flask_session.clear()
    return redirect(url_for("homepage"))


@app.route("/admin/questions", methods=["GET", "POST"])
def admin_questions():
    if not flask_session.get("is_admin"):
        return redirect(url_for("admin_login"))

    db = get_db()

    if request.method == "POST":
        action = request.form.get("action")

        if action == "add":
            db.execute(
                """
                INSERT INTO questions (question, option_a, option_b, option_c, option_d, correct_option)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    request.form.get("question", "").strip(),
                    request.form.get("option_a", "").strip(),
                    request.form.get("option_b", "").strip(),
                    request.form.get("option_c", "").strip(),
                    request.form.get("option_d", "").strip(),
                    request.form.get("correct_option", ""),
                ),
            )
            db.commit()

        elif action == "delete":
            qid = request.form.get("delete_id")
            db.execute("DELETE FROM questions WHERE id=?", (qid,))
            db.commit()

        elif action == "edit":
            qid = request.form.get("edit_id")
            db.execute(
                """
                UPDATE questions
                SET question=?, option_a=?, option_b=?, option_c=?, option_d=?, correct_option=?
                WHERE id=?
                """,
                (
                    request.form.get("question", "").strip(),
                    request.form.get("option_a", "").strip(),
                    request.form.get("option_b", "").strip(),
                    request.form.get("option_c", "").strip(),
                    request.form.get("option_d", "").strip(),
                    request.form.get("correct_option", ""),
                    qid,
                ),
            )
            db.commit()

    questions = db.execute("SELECT * FROM questions ORDER BY id DESC").fetchall()
    return render_template("admin_questions.html", questions=questions)


# --- Must be last. DO NOT TOUCH! ---
if __name__ == "__main__":
    app.run(debug=True)