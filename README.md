# CBT App — Local HTTPS and Security Notes

This project is a small Flask-based CBT application. A few security recommendations and quick steps for local development are below.

Local development
- Install dependencies:
```powershell
pip install -r .\requirements.txt
```
- Run the app (development server):
  - Quick (HTTP):
    ```powershell
    python .\app.py
    ```
    Note: `SESSION_COOKIE_SECURE=True` is enabled in `app.py`. If you need to run over plain HTTP for local testing, set
    `app.config['SESSION_COOKIE_SECURE'] = False` in `app.py` (or set it via environment-specific config).

  - Recommended (HTTPS, adhoc certificate):
    ```powershell
    $env:FLASK_APP = 'app.py'
    flask run --cert=adhoc
    ```
    This uses a temporary self-signed certificate so the browser can use HTTPS locally. Browsers may show a warning for the self-signed certificate.

Security recommendations
- Use HTTPS in production and set `SESSION_COOKIE_SECURE=True` (already set in `app.py`).
- Keep `SESSION_COOKIE_SAMESITE='Lax'` to mitigate some CSRF vectors.
- All state-changing endpoints are POST-only and protected with CSRF tokens (via `flask-wtf`).
- For production, run behind a reverse proxy (nginx, IIS, etc.) that terminates TLS and provides HSTS.

If you want help generating a self-signed cert and wiring a local dev proxy, tell me which approach you prefer (built-in `flask run --cert=adhoc`, a local nginx proxy, or a Windows dev setup) and I can add commands and examples.
