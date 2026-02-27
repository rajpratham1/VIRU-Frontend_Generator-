# VIRU Frontend Generator

Prompt-to-website generator built with Flask + Firebase Auth + Groq/OpenAI compatible API.

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
- `VITE_FIREBASE_API_KEY`
- `VITE_FIREBASE_AUTH_DOMAIN`
- `VITE_FIREBASE_PROJECT_ID`
- `VITE_FIREBASE_STORAGE_BUCKET`
- `VITE_FIREBASE_MESSAGING_SENDER_ID`
- `VITE_FIREBASE_APP_ID`
- `SECRET_KEY`
- `NETLIFY_ACCESS_TOKEN` (for one-click deploy button)
- `NETLIFY_SITE_ID` (for one-click deploy button)

## Notes

- Suggestion form uses FormSubmit (`formsubmit.co`).
- First FormSubmit email requires activation from receiver inbox.
- Share links are currently in-memory on the Flask instance (not persistent).
- Saved projects use Firebase Firestore collection `projects`.
- One-click deploy button publishes current generated page to configured Netlify site.

## One-Click Deploy Button Setup

1. Create a Netlify Personal Access Token.
2. Get Netlify Site ID (Site settings -> General -> Site details).
3. Set these env vars in local `.env` and Vercel project env:
   - `NETLIFY_ACCESS_TOKEN`
   - `NETLIFY_SITE_ID`
4. In `/app`, generate a page then click `Deploy Current Page`.
5. VIRU returns live URL and copies it to clipboard.

## Firestore Rules (Minimum)

Use rules so each user can only access own projects:

```text
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /projects/{projectId} {
      allow read, write: if request.auth != null && request.auth.uid == resource.data.ownerUid;
      allow create: if request.auth != null && request.auth.uid == request.resource.data.ownerUid;
    }
  }
}
```
