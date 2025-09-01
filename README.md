# Secured Option Chain Dashboard (Render Deployment with .env Secret File)

## Setup on Render with Secret File
1. Push this project to GitHub.
2. On Render.com → Create new Web Service → Connect GitHub repo.
3. Build command:
   pip install -r requirements.txt
4. Start command (auto from Procfile):
   streamlit run app.py --server.port $PORT --server.address 0.0.0.0
5. In Render dashboard:
   - Go to Settings → Secret Files
   - Add new file called `.env`
   - Paste your secrets in this format:
       MASTER_PASSWORD=your_master_password
       API_KEY=your_api_key
       CLIENT_ID=your_client_id
       PASSWORD=your_password
       TOTP=your_totp
6. Deploy → first build may take 5–10 minutes.

## Notes
- Python version is pinned to 3.11.9 (via runtime.txt)
- Secrets are read from `/etc/secrets/.env` using python-dotenv
- Much simpler than typing many environment variables
