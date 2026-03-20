# Firebase Setup

This project uses Firestore for metadata only.

Current file storage model:

- Firestore: project/share/converter metadata
- Local disk: uploaded files, converted files, previews

Firebase Storage is not required for the current setup.
`firebase/storage.rules` can be ignored for now.

## 1. Service Account

Create a Firebase service account with Firestore access and provide one of:

- `FIREBASE_SERVICE_ACCOUNT_PATH=firebase-service-account.json`
- `FIREBASE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}`

Set:

- `PERSISTENCE_PROVIDER=firestore`

If these are missing, the app falls back to local JSON persistence at `data/storage.json`.

## 2. Deploy Rules

From a Firebase-enabled project:

```bash
firebase deploy --only firestore:rules --project <your-project-id>
firebase deploy --only firestore:indexes --project <your-project-id>
```

Use these files:

- `firebase/firestore.rules`
- `firebase/firestore.indexes.json`

## 3. Admin Claims

The rules expect admin users to have:

```json
{
  "admin": true
}
```

Set custom claims from a trusted server or admin script only.

## 4. Collections Covered

- `projects`
- `shares`
- `published`
- `users`
- `conversion_jobs`
- `conversion_history`
- `converter_uploads`
- `converter_jobs`
- `admin_metrics`

## 5. Important Note

The Flask backend uses the Firebase Admin SDK when Firestore is configured. Admin SDK requests bypass Firestore security rules. The rules in this folder are for direct client access and future frontend Firebase reads/writes.

## 6. Local File Storage Note

Uploaded and converted documents currently stay on local server disk under:

- `data/converter/uploads`
- `data/converter/outputs`
- `data/converter/previews`

This keeps Firebase usage cheaper, but it also means:

- it is suitable for local development or a persistent VPS/dedicated server
- it is not ideal for ephemeral serverless disks
- browser localStorage is not used for document binaries
