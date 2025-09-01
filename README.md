# Secured Option Chain Dashboard (Streamlit Cloud Safe Version)

## Setup on Streamlit Cloud
1. Push this project to GitHub.
2. On Streamlit Cloud → Create new app → Connect GitHub repo.
3. Make sure files are at repo root: app.py, requirements.txt, runtime.txt, Procfile, README.md.
4. In Streamlit Cloud → App Settings → Secrets, add:

MASTER_PASSWORD="your_master_password"
API_KEY="your_api_key"
CLIENT_ID="your_client_id"
PASSWORD="your_password"
TOTP="your_totp"

5. Deploy. First build may take 5–10 minutes.

## Notes
- Uses `st.secrets` (no .env needed)
- Python pinned to 3.11.9 (if Streamlit supports it)
- Dependencies pinned for stability
