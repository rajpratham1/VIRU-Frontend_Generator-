import os
import json
import urllib.error
import urllib.request
import smtplib
import re
import uuid
import io
import zipfile
from urllib.parse import urlparse
from datetime import datetime, timezone
from pathlib import Path
from email.message import EmailMessage
from threading import Lock

from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request, url_for

from services.generator import WebsiteGenerator

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / '.env'
ENV_EXAMPLE_PATH = BASE_DIR / '.env.example'
load_dotenv(dotenv_path=ENV_EXAMPLE_PATH)
load_dotenv(dotenv_path=ENV_PATH, override=True)

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False
SHARE_STORE = {}
SHARE_LOCK = Lock()
PROJECT_STORE = {}
PROJECT_LOCK = Lock()
PUBLISHED_STORE = {}
PUBLISHED_LOCK = Lock()


def _fresh_generator() -> WebsiteGenerator:
    # Reload env from app directory for hot updates during local dev.
    load_dotenv(dotenv_path=ENV_EXAMPLE_PATH)
    load_dotenv(dotenv_path=ENV_PATH, override=True)
    return WebsiteGenerator()


def _verify_firebase_token(id_token: str):
    api_key = os.getenv('VITE_FIREBASE_API_KEY', '').strip()
    if not api_key:
        return None, 'Firebase API key is not configured on server.'

    url = f'https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={api_key}'
    payload = json.dumps({'idToken': id_token}).encode('utf-8')
    req = urllib.request.Request(url, data=payload, method='POST')
    req.add_header('Content-Type', 'application/json')

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        return None, f'Auth verification failed ({exc.code}).'
    except Exception:
        return None, 'Auth verification failed.'

    users = data.get('users') or []
    if not users:
        return None, 'Invalid login token.'
    return users[0], ''


def _require_auth():
    auth_header = (request.headers.get('Authorization') or '').strip()
    if not auth_header.startswith('Bearer '):
        return None, 'Missing auth token. Please login first.'

    token = auth_header.replace('Bearer ', '', 1).strip()
    if not token:
        return None, 'Invalid auth token.'

    return _verify_firebase_token(token)


def _extract_title(html: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return re.sub(r"\s+", " ", match.group(1)).strip()


def _extract_netlify_site_slug(raw_value: str) -> str:
    value = (raw_value or "").strip()
    if not value:
        return ""
    # Team dashboard URL does not encode a specific site; caller must resolve via sites API.
    if "app.netlify.com/teams/" in value and "/projects" in value:
        return "__team_projects_url__"
    if re.fullmatch(r"[a-zA-Z0-9_-]{6,}", value):
        return value
    if "netlify.app" in value:
        parsed = urlparse(value if "://" in value else f"https://{value}")
        host = parsed.netloc or parsed.path
        return host.split(".")[0]
    if "app.netlify.com/sites/" in value:
        match = re.search(r"app\.netlify\.com/sites/([^/?#]+)", value)
        return match.group(1) if match else ""
    return ""


def _resolve_netlify_site_id(token: str, raw_value: str):
    site_slug = _extract_netlify_site_slug(raw_value)
    if not site_slug:
        return "", "NETLIFY_SITE_ID must be a site id/name or a netlify.app/site URL."

    sites_req = urllib.request.Request("https://api.netlify.com/api/v1/sites", method="GET")
    sites_req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(sites_req, timeout=25) as resp:
            sites = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return "", "Unable to read Netlify sites list. Check NETLIFY_ACCESS_TOKEN permissions."

    if site_slug == "__team_projects_url__":
        if len(sites) == 1:
            return str(sites[0].get("id") or ""), ""
        if len(sites) > 1:
            names = [str(s.get("name") or s.get("id") or "") for s in sites[:5]]
            return "", (
                "Team projects URL detected. Multiple sites found. "
                f"Set NETLIFY_SITE_ID to one site name/id, for example: {', '.join(names)}"
            )
        return "", "No Netlify sites found for this token."

    for site in sites:
        candidates = {
            str(site.get("id") or ""),
            str(site.get("name") or ""),
            str(site.get("url") or "").replace("https://", "").replace("http://", "").split(".")[0],
            str(site.get("ssl_url") or "").replace("https://", "").replace("http://", "").split(".")[0],
        }
        if site_slug in candidates:
            return str(site.get("id") or ""), ""

    return "", f"Netlify site not found for '{raw_value}'. Use actual site URL or site name."


@app.get('/')
def landing_page():
    return render_template('landing.html')


@app.get('/auth')
def auth_page():
    return render_template('auth.html')


@app.get('/app')
def app_page():
    return render_template('app.html')


@app.get('/projects')
def projects_page():
    return render_template('projects.html')


@app.get('/index')
def index_alias():
    return redirect(url_for('landing_page'), code=302)


@app.get('/api/public-config')
def public_config():
    return jsonify(
        {
            'firebase': {
                'apiKey': os.getenv('VITE_FIREBASE_API_KEY', ''),
                'authDomain': os.getenv('VITE_FIREBASE_AUTH_DOMAIN', ''),
                'projectId': os.getenv('VITE_FIREBASE_PROJECT_ID', ''),
                'storageBucket': os.getenv('VITE_FIREBASE_STORAGE_BUCKET', ''),
                'messagingSenderId': os.getenv('VITE_FIREBASE_MESSAGING_SENDER_ID', ''),
                'appId': os.getenv('VITE_FIREBASE_APP_ID', ''),
            },
            'features': {
                'abstractApiConfigured': bool(os.getenv('VITE_ABSTRACT_API_KEY', '').strip()),
            },
        }
    )


@app.get('/favicon.ico')
def favicon():
    return redirect(url_for('static', filename='images/logo.png'), code=302)


@app.get('/api/health')
def health():
    user, auth_error = _require_auth()
    if not user:
        return jsonify({'ok': False, 'message': auth_error}), 401

    try:
        generator = _fresh_generator()
        response = generator.health_check()
        response['auth'] = {'email': user.get('email', ''), 'uid': user.get('localId', '')}
        return jsonify(response)
    except Exception:
        return jsonify({'ok': False, 'message': 'Health check failed unexpectedly.'}), 500


@app.post('/api/generate')
def generate():
    user, auth_error = _require_auth()
    if not user:
        return jsonify({'ok': False, 'error': auth_error}), 401

    payload = request.get_json(silent=True) or {}

    prompt = (payload.get('prompt') or '').strip()
    style = (payload.get('style') or 'modern saas').strip()
    pages = int(payload.get('pages') or 1)
    strict_mode = bool(payload.get('strict_mode', True))
    quality_preset = (payload.get('quality_preset') or 'balanced').strip().lower()
    rewrite_mode = bool(payload.get('rewrite_mode', True))

    if not prompt:
        return jsonify({'ok': False, 'error': 'Prompt is required.'}), 400

    pages = max(1, min(pages, 5))

    try:
        generator = _fresh_generator()
        result = generator.generate(
            prompt=prompt,
            style=style,
            pages=pages,
            strict_mode=strict_mode,
            quality_preset=quality_preset,
            rewrite_mode=rewrite_mode,
        )
        result['ok'] = True
        result['auth'] = {'email': user.get('email', ''), 'uid': user.get('localId', '')}
        return jsonify(result)
    except ValueError as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 400
    except Exception:
        return jsonify({'ok': False, 'error': 'Generation failed. Check API settings and try again.'}), 500


@app.post('/api/analyze-url')
def analyze_url():
    user, auth_error = _require_auth()
    if not user:
        return jsonify({'ok': False, 'error': auth_error}), 401

    payload = request.get_json(silent=True) or {}
    target_url = (payload.get('url') or '').strip()
    if not target_url:
        return jsonify({'ok': False, 'error': 'URL is required.'}), 400
    if not target_url.startswith(('http://', 'https://')):
        return jsonify({'ok': False, 'error': 'URL must start with http:// or https://'}), 400

    req = urllib.request.Request(target_url, headers={'User-Agent': 'VIRU-Frontend/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
    except Exception:
        return jsonify({'ok': False, 'error': 'Unable to fetch target URL for analysis.'}), 400

    html_lower = html.lower()
    title = _extract_title(html)
    has_pricing = 'pricing' in html_lower
    has_testimonial = 'testimonial' in html_lower or 'review' in html_lower
    has_faq = 'faq' in html_lower
    has_contact = 'contact' in html_lower or '<form' in html_lower
    has_blog = 'blog' in html_lower or 'article' in html_lower
    sections = ['hero', 'features']
    if has_pricing:
        sections.append('pricing')
    if has_testimonial:
        sections.append('testimonials')
    if has_faq:
        sections.append('faq')
    if has_contact:
        sections.append('contact')
    if has_blog:
        sections.append('blog')

    style = 'modern saas'
    if any(k in html_lower for k in ['bank', 'fintech', 'payment', 'finance']):
        style = 'clean fintech'
    elif any(k in html_lower for k in ['creative', 'studio', 'portfolio']):
        style = 'editorial bold'
    elif any(k in html_lower for k in ['shop', 'cart', 'product']):
        style = 'playful startup'

    prompt = (
        f"Create a responsive website inspired by {target_url}. "
        f"Reference tone from title '{title or 'Website'}'. "
        f"Include sections: {', '.join(sections)}. "
        f"Target audience: modern web users. Tone: premium and clear. "
        f"CTA: start now."
    )

    return jsonify(
        {
            'ok': True,
            'analysis': {
                'url': target_url,
                'title': title,
                'style': style,
                'sections': sections,
                'prompt': prompt,
                'recommended_pages': 2 if has_blog else 1,
            },
        }
    )


@app.post('/api/share')
def create_share():
    user, auth_error = _require_auth()
    if not user:
        return jsonify({'ok': False, 'error': auth_error}), 401

    payload = request.get_json(silent=True) or {}
    result = payload.get('result') or {}
    permission = (payload.get('permission') or 'view').strip().lower()
    if permission not in {'view', 'edit'}:
        permission = 'view'
    if not result or not isinstance(result, dict) or not result.get('pages'):
        return jsonify({'ok': False, 'error': 'Generated result payload is required.'}), 400

    share_id = uuid.uuid4().hex[:12]
    with SHARE_LOCK:
        SHARE_STORE[share_id] = {
            'owner_uid': user.get('localId', ''),
            'owner_email': user.get('email', ''),
            'permission': permission,
            'result': result,
        }

    link = f"{request.host_url.rstrip('/')}/app?share={share_id}&perm={permission}"
    return jsonify({'ok': True, 'share_id': share_id, 'permission': permission, 'share_link': link})


@app.get('/api/share/<share_id>')
def get_share(share_id: str):
    user, auth_error = _require_auth()
    if not user:
        return jsonify({'ok': False, 'error': auth_error}), 401

    mode = (request.args.get('perm') or 'view').strip().lower()
    if mode not in {'view', 'edit'}:
        mode = 'view'

    with SHARE_LOCK:
        item = SHARE_STORE.get(share_id)

    if not item:
        return jsonify({'ok': False, 'error': 'Share link not found.'}), 404

    if item['permission'] == 'view' and mode == 'edit':
        return jsonify({'ok': False, 'error': 'This share link is view-only.'}), 403

    return jsonify(
        {
            'ok': True,
            'mode': mode,
            'share': {
                'id': share_id,
                'owner_email': item.get('owner_email', ''),
                'permission': item.get('permission', 'view'),
            },
            'result': item.get('result') or {},
        }
    )


@app.post('/api/projects')
def create_project():
    user, auth_error = _require_auth()
    if not user:
        return jsonify({'ok': False, 'error': auth_error}), 401

    payload = request.get_json(silent=True) or {}
    result = payload.get('result') or {}
    if not isinstance(result, dict) or not result.get('pages'):
        return jsonify({'ok': False, 'error': 'Generated result is required.'}), 400

    project = {
        'id': uuid.uuid4().hex[:12],
        'owner_uid': user.get('localId', ''),
        'owner_email': user.get('email', ''),
        'title': (payload.get('title') or 'Generated Output').strip(),
        'prompt': (payload.get('prompt') or '').strip(),
        'style': (payload.get('style') or 'modern saas').strip(),
        'pages': int(payload.get('pages') or 1),
        'source': (payload.get('source') or '').strip(),
        'qualityScore': (payload.get('qualityScore') or '').strip(),
        'latencyMs': int(payload.get('latencyMs') or 0),
        'result': result,
        'createdAt': datetime.now(timezone.utc).isoformat(),
    }

    owner_uid = project['owner_uid']
    with PROJECT_LOCK:
        projects = PROJECT_STORE.get(owner_uid, [])
        projects.insert(0, project)
        PROJECT_STORE[owner_uid] = projects[:100]

    return jsonify({'ok': True, 'project': project})


@app.get('/api/projects')
def list_projects():
    user, auth_error = _require_auth()
    if not user:
        return jsonify({'ok': False, 'error': auth_error}), 401

    owner_uid = user.get('localId', '')
    with PROJECT_LOCK:
        projects = list(PROJECT_STORE.get(owner_uid, []))
    return jsonify({'ok': True, 'projects': projects})


@app.delete('/api/projects/<project_id>')
def delete_project(project_id: str):
    user, auth_error = _require_auth()
    if not user:
        return jsonify({'ok': False, 'error': auth_error}), 401

    owner_uid = user.get('localId', '')
    with PROJECT_LOCK:
        projects = PROJECT_STORE.get(owner_uid, [])
        filtered = [p for p in projects if p.get('id') != project_id]
        PROJECT_STORE[owner_uid] = filtered
        deleted = len(filtered) != len(projects)

    if not deleted:
        return jsonify({'ok': False, 'error': 'Project not found.'}), 404
    return jsonify({'ok': True})


@app.post('/api/suggestions')
def submit_suggestion():
    user, auth_error = _require_auth()
    if not user:
        return jsonify({'ok': False, 'error': auth_error}), 401

    payload = request.get_json(silent=True) or {}
    name = (payload.get('name') or '').strip()
    email = (payload.get('email') or '').strip()
    message = (payload.get('message') or '').strip()

    if not name or not email or not message:
        return jsonify({'ok': False, 'error': 'Name, email, and message are required.'}), 400

    smtp_host = os.getenv('MAIL_SMTP_HOST', 'smtp.gmail.com').strip() or 'smtp.gmail.com'
    smtp_port = int(os.getenv('MAIL_SMTP_PORT', '587') or '587')
    smtp_user = os.getenv('MAIL_USERNAME', '').strip()
    smtp_password = os.getenv('MAIL_APP_PASSWORD', '').strip()
    recipient = os.getenv('MAIL_TO', 'shrivastavapratham@gmail.com').strip() or 'shrivastavapratham@gmail.com'

    if not smtp_user or not smtp_password:
        return jsonify({'ok': False, 'error': 'Mail server is not configured. Set MAIL_USERNAME and MAIL_APP_PASSWORD.'}), 500

    subject = f'VIRU Suggestion from {name}'
    body = (
        f'New suggestion submitted from VIRU website.\n\n'
        f'Submitter Name: {name}\n'
        f'Submitter Email: {email}\n'
        f'Authenticated User: {user.get("email", "")}\n'
        f'Authenticated UID: {user.get("localId", "")}\n\n'
        f'Message:\n{message}\n'
    )

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = smtp_user
    msg['To'] = recipient
    msg.set_content(body)

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        return jsonify({'ok': True, 'message': 'Suggestion sent successfully.'})
    except Exception:
        return jsonify({'ok': False, 'error': 'Failed to send suggestion email. Check mail env settings.'}), 500


@app.post('/api/deploy/local')
def deploy_local_project():
    user, auth_error = _require_auth()
    if not user:
        return jsonify({'ok': False, 'error': auth_error}), 401

    payload = request.get_json(silent=True) or {}
    result = payload.get('result') or {}
    page_index = int(payload.get('page_index') or 0)
    pages = result.get('pages') or []

    if not pages:
        return jsonify({'ok': False, 'error': 'No generated pages available to publish.'}), 400
    if page_index < 0 or page_index >= len(pages):
        page_index = 0

    page = pages[page_index] or {}
    html = page.get('html') or ''
    css = page.get('css') or ''
    js = page.get('js') or ''
    if not html.strip():
        return jsonify({'ok': False, 'error': 'Selected page HTML is empty.'}), 400

    published_id = uuid.uuid4().hex[:14]
    document = (
        '<!doctype html><html lang="en"><head><meta charset="UTF-8" />'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0" />'
        f'<style>{css}</style></head><body>{html}<script>{js}</script></body></html>'
    )

    with PUBLISHED_LOCK:
        PUBLISHED_STORE[published_id] = {
            'owner_uid': user.get('localId', ''),
            'owner_email': user.get('email', ''),
            'createdAt': datetime.now(timezone.utc).isoformat(),
            'document': document,
        }

    live_url = f"{request.host_url.rstrip('/')}/published/{published_id}"
    return jsonify({'ok': True, 'deploy_url': live_url, 'deploy_id': published_id, 'provider': 'viru-local'})


@app.get('/published/<published_id>')
def render_published_page(published_id: str):
    with PUBLISHED_LOCK:
        item = PUBLISHED_STORE.get(published_id)
    if not item:
        return 'Published page not found.', 404
    return item.get('document') or 'Published page is empty.', 200, {'Content-Type': 'text/html; charset=utf-8'}


@app.post('/api/deploy')
def deploy_current_project():
    user, auth_error = _require_auth()
    if not user:
        return jsonify({'ok': False, 'error': auth_error}), 401

    payload = request.get_json(silent=True) or {}
    result = payload.get('result') or {}
    page_index = int(payload.get('page_index') or 0)

    pages = result.get('pages') or []
    if not pages:
        return jsonify({'ok': False, 'error': 'No generated pages available to deploy.'}), 400
    if page_index < 0 or page_index >= len(pages):
        page_index = 0

    page = pages[page_index] or {}
    html = page.get('html') or ''
    css = page.get('css') or ''
    js = page.get('js') or ''

    if not html.strip():
        return jsonify({'ok': False, 'error': 'Selected page HTML is empty.'}), 400

    netlify_token = os.getenv('NETLIFY_ACCESS_TOKEN', '').strip()
    netlify_site_raw = os.getenv('NETLIFY_SITE_ID', '').strip()
    if not netlify_token or not netlify_site_raw:
        return jsonify(
            {
                'ok': False,
                'error': 'Deploy is not configured. Set NETLIFY_ACCESS_TOKEN and NETLIFY_SITE_ID in server env.',
            }
        ), 500

    netlify_site_id, site_error = _resolve_netlify_site_id(netlify_token, netlify_site_raw)
    if not netlify_site_id:
        return jsonify({'ok': False, 'error': site_error}), 400

    index_document = (
        '<!doctype html><html lang="en"><head><meta charset="UTF-8" />'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0" />'
        '<link rel="stylesheet" href="./styles.css" /></head><body>'
        f'{html}<script src="./script.js"></script></body></html>'
    )

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('index.html', index_document)
        zf.writestr('styles.css', css)
        zf.writestr('script.js', js)
    zip_bytes = zip_buffer.getvalue()

    deploy_url = f'https://api.netlify.com/api/v1/sites/{netlify_site_id}/deploys'
    deploy_req = urllib.request.Request(deploy_url, data=zip_bytes, method='POST')
    deploy_req.add_header('Authorization', f'Bearer {netlify_token}')
    deploy_req.add_header('Content-Type', 'application/zip')

    try:
        with urllib.request.urlopen(deploy_req, timeout=45) as resp:
            deploy_data = json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode('utf-8')
        except Exception:
            detail = ''
        return jsonify({'ok': False, 'error': f'Netlify deploy failed ({exc.code}). {detail[:180]}'}), 500
    except Exception:
        return jsonify({'ok': False, 'error': 'Netlify deploy request failed.'}), 500

    live_url = deploy_data.get('ssl_url') or deploy_data.get('url') or ''
    admin_url = deploy_data.get('admin_url') or ''
    deploy_id = deploy_data.get('id') or ''

    return jsonify({'ok': True, 'deploy_url': live_url, 'admin_url': admin_url, 'deploy_id': deploy_id})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
