# VIRU Study Notes (Developer Terms)

## Core Web Terms

- **Frontend**: The UI users see and interact with (HTML, CSS, JavaScript).
- **Backend**: Server-side logic, APIs, auth checks, and integrations.
- **Full Stack**: Frontend + backend working together.
- **Responsive Design**: UI that adapts to mobile, tablet, desktop.
- **Accessibility (a11y)**: Building UI usable by everyone (screen readers, keyboard navigation, contrast).

## Project Architecture Terms

- **Flask**: Python web framework used for routes and APIs.
- **Route**: URL path mapped to a function (example: `/api/generate`).
- **Template**: HTML file rendered by Flask (`templates/*.html`).
- **Static Assets**: CSS, JS, images in `static/`.
- **Server-Side Rendering (SSR)**: Flask sends complete HTML response.
- **JSON API**: Backend endpoint returning JSON payloads.

## Auth & Security Terms

- **Firebase Auth**: Identity system used for login/register.
- **ID Token**: Firebase-issued token proving user identity.
- **Bearer Token**: Token sent in `Authorization: Bearer <token>`.
- **Token Verification**: Backend validates token before protected actions.
- **Protected Route/API**: Endpoint requiring valid auth.
- **Environment Variable**: Secret/config value loaded from `.env`.
- **Secret**: Sensitive values like API keys.

## LLM/Generation Terms

- **Prompt**: User instruction sent to model.
- **Prompt Engineering**: Structuring prompt for better output.
- **Provider**: LLM service source (Groq/OpenAI).
- **Model**: Specific LLM variant used for generation.
- **Strict Mode**: Reject weak model output; avoid fake fallback.
- **Fallback**: Backup output path when model fails.
- **Rewrite Seed**: AI rewrites from a layout seed for consistency.
- **Quality Preset**: Fast/Balanced/Premium generation strategy.
- **Validation**: Checks generated output quality and structure.
- **Retry**: Re-run generation when initial output fails checks.
- **Latency**: Time taken by API/model response.

## UI/UX Terms in This Project

- **Landing Page**: Public first page (`/`).
- **Auth Page**: Login/register page (`/auth`).
- **App Workspace**: Main generator page (`/app`).
- **Settings Drawer**: Right-side panel toggled by gear icon.
- **Mobile Tab Switcher**: Prompt/Output/Logs compact tabs.
- **Dashboard**: Usage metrics and recent generations.
- **Template Library**: Pre-built prompt cards with categories.
- **One-Click Remix**: Apply template prompt/style/pages instantly.
- **Prompt Assistant**: Auto-completes missing audience/tone/CTA.

## Export/Sharing Terms

- **ZIP Export**: Download `index.html`, `styles.css`, `script.js`.
- **React Starter Export**: Generated code packed for Vite + React.
- **Next Starter Export**: Generated code packed for Next.js app.
- **Share Link**: URL containing generated project and permission.
- **View Permission**: Shared user can view only.
- **Edit Permission**: Shared user can modify/regenerate.

## Clone/Deploy Terms

- **Clone from URL**: Analyze target website and infer prompt/style.
- **Heuristic Analysis**: Rule-based extraction (title/sections/style clues).
- **Deploy Connector**: Shortcut button opening deployment platform.
- **Netlify / Vercel / GitHub Pages**: Hosting/deployment platforms.
- **Build**: Process that prepares app for production.
- **Production**: Live environment used by real users.

## Form & Email Terms

- **FormSubmit**: Third-party service to send form data to email.
- **Activation Link**: First-time confirmation required by FormSubmit.
- **Preflight Request**: Browser `OPTIONS` check before cross-origin POST.
- **CORS**: Cross-Origin Resource Sharing rules between domains.

## HTTP/Debug Terms

- **200 OK**: Request succeeded.
- **400 Bad Request**: Invalid input.
- **401 Unauthorized**: Missing/invalid auth token.
- **403 Forbidden**: Authenticated but not allowed.
- **404 Not Found**: Route/resource missing.
- **500 Internal Server Error**: Backend runtime failure.
- **Network Tab**: Browser panel to inspect requests/responses.
- **Console Error**: Runtime JS/backend clues for debugging.

## Deployment Checklist Terms

- **Root Directory**: Folder Vercel builds from (`viru-frontend`).
- **`vercel.json`**: Vercel routing/build config file.
- **`requirements.txt`**: Python dependency manifest.
- **`.env.example`**: Template for required environment keys.
- **Key Rotation**: Replacing exposed API keys with new ones.

## Recommended Next Learning Order

1. HTTP basics + status codes  
2. Flask routes + template rendering  
3. Auth tokens + protected APIs  
4. Prompt engineering + validation loops  
5. Deployment on Vercel + env management  
6. Observability (logs, retries, latency analysis)
