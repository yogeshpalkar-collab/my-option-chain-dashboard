
# Secured Option Chain Dashboard

This is your **password-protected** Streamlit dashboard for NIFTY / BANKNIFTY / FINNIFTY option chains with Angel One SmartAPI integration.

## 🔒 Password Protection
- The app requires a **Master Password** stored in `secrets.toml`.
- Once entered correctly, the app stays unlocked until the browser tab is closed.

## ⚙️ Setup Instructions

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.streamlit/secrets.toml` file with:
   ```toml
   MASTER_PASSWORD = "your_secret_password"
   API_KEY = "your_api_key"
   CLIENT_ID = "your_client_id"
   PASSWORD = "your_password"
   TOTP = "your_totp"
   ```

3. Run the app locally:
   ```bash
   streamlit run app.py
   ```

4. For deployment on **Streamlit Cloud**:
   - Upload this repo.
   - Add all secrets (including MASTER_PASSWORD) in Streamlit Cloud → Settings → Secrets.

## ✅ Behavior
- App asks for password once per browser session.
- Remains unlocked until browser tab is closed.
- On reopening, password prompt appears again.
