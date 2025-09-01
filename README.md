# Secured Option Chain Dashboard (Railway Deployment)

## Setup on Railway
1. Push this project to GitHub.
2. On Railway.app → Create new project → Deploy from GitHub repo.
3. Build command:
   pip install -r requirements.txt
4. Start command (auto from Procfile):
   streamlit run app.py --server.port $PORT --server.address 0.0.0.0
5. In Railway dashboard:
   - Go to Variables tab
   - Add the following secrets:
       MASTER_PASSWORD=your_master_password
       API_KEY=your_api_key
       CLIENT_ID=your_client_id
       PASSWORD=your_password
       TOTP=your_totp
6. Deploy → first build may take 5–10 minutes.

## Notes
- Python version is pinned to 3.11.9 (via runtime.txt)
- Secrets are read directly from Railway Variables (os.getenv)
- Simpler than Render because no .env file handling is needed
