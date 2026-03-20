# VIRU Frontend Generator

Prompt-to-website generator built with Flask + Firebase Auth + Groq/OpenAI compatible API.

Detailed product spec for the next module:

- `DOCUMENT_CONVERTER_SPEC.md`

Persistence now supports:

- Firestore via Firebase Admin SDK
- Local JSON fallback at `data/storage.json`
- Local document files under `data/converter/*`

## Local Setup

1. Create `.env` from `.env.example`.
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Run:
```bash
python app.py
```
4. Open `http://127.0.0.1:5000`.

## Pages

- `/` landing
- `/auth` login/register
- `/app` generator
- `/projects` My Work hub (saved generations)
- `/converter` document converter

## Vercel Deployment

Set project root to `viru-frontend` in Vercel.

### Required Environment Variables

- `GENERATOR_PROVIDER`
- `GENERATOR_ALLOW_FALLBACK`
- `GROQ_API_KEY`
- `GROQ_MODEL`
- `GROQ_BASE_URL`
- `OPENAI_API_KEY` (optional)
- `OPENAI_MODEL` (optional)
- `OPENAI_BASE_URL` (optional)
- `OCR_PROVIDER` (optional)
- `OCR_API_KEY` (optional)
- `OCR_MODEL` (optional)
- `OCR_BASE_URL` (optional)
- `VITE_FIREBASE_API_KEY`
- `VITE_FIREBASE_AUTH_DOMAIN`
- `VITE_FIREBASE_PROJECT_ID`
- `VITE_FIREBASE_STORAGE_BUCKET`
- `VITE_FIREBASE_MESSAGING_SENDER_ID`
- `VITE_FIREBASE_APP_ID`
- `SECRET_KEY`
- `PERSISTENCE_PROVIDER`
- `FIREBASE_SERVICE_ACCOUNT_PATH` or `FIREBASE_SERVICE_ACCOUNT_JSON`
- `ADMIN_EMAILS`
- `NETLIFY_ACCESS_TOKEN` (for one-click deploy button)
- `NETLIFY_SITE_ID` (for one-click deploy button)

## Notes

- Suggestion form uses FormSubmit (`formsubmit.co`).
- First FormSubmit email requires activation from receiver inbox.
- Share links, saved projects, and local published pages now use the persistence layer.
- If Firestore credentials are configured, data is stored in Firebase.
- If Firestore credentials are missing, data is stored locally in `data/storage.json`.
- Publish button first deploys on VIRU server domain (`/published/<id>`), then falls back to Netlify if local publish is unavailable.
- Document converter now supports real backend conversion for TXT, DOCX, PDF, and image-based flows.
- OCR works through local Tesseract when installed, or can fall back to a vision-capable model through the same OpenAI-compatible API shape.
- Converter APIs are now auth-protected and scoped per Firebase user.
- Admin metrics and global cleanup are enabled for emails listed in `ADMIN_EMAILS`.
- Firebase Storage is not required in the current setup.
- Converter binaries are stored on local server disk to reduce Firebase cost.

## Document Converter Backend

Implemented APIs:

- `POST /api/converter/upload`
- `POST /api/converter/convert`
- `GET /api/converter/jobs`
- `GET /api/converter/jobs/<job_id>`
- `GET /api/converter/preview/<job_id>`
- `GET /api/converter/download/<job_id>`

Current supported real conversions:

- `PDF -> DOCX`
- `PDF -> TXT`
- `PDF -> PNG` (single image or ZIP for multi-page PDFs)
- `DOCX -> TXT`
- `DOCX -> PDF`
- `TXT -> DOCX`
- `TXT -> PDF`
- `PNG/JPG/JPEG -> PDF`
- `PNG/JPG/JPEG -> TXT` via OCR

For best OCR on scanned documents:

1. Install local Tesseract OCR on the machine, or
2. Set `OCR_MODEL` to a vision-capable model using the same API account pattern

## Firebase Persistence Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```
2. Add one of these env vars:
```bash
FIREBASE_SERVICE_ACCOUNT_PATH=firebase-service-account.json
```
or
```bash
FIREBASE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}
```
3. Set:
```bash
PERSISTENCE_PROVIDER=firestore
```
4. Deploy Firebase rules and indexes using the files inside `firebase/`.

See:

- `firebase/firestore.rules`
- `firebase/firestore.indexes.json`
- `firebase/README.md`

## One-Click Deploy Button Setup

Local publish works without Netlify env vars.

1. Create a Netlify Personal Access Token.
2. Get Netlify Site ID (Site settings -> General -> Site details).
3. Set these env vars in local `.env` and Vercel project env:
   - `NETLIFY_ACCESS_TOKEN`
   - `NETLIFY_SITE_ID` (site id, site name, `https://<site>.netlify.app`, or `app.netlify.com/sites/<site>`)
4. In `/app`, generate a page then click `Publish Live URL`.
5. VIRU returns live URL and copies it to clipboard.

Note: local published pages are in-memory and reset on server restart/redeploy.
