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
from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request, send_file, send_from_directory, url_for

from services.document_converter import DocumentConverterService
from services.generator import WebsiteGenerator
from services.store import build_store
from services.utils import get_writable_path

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / '.env'
ENV_LOCAL_PATH = BASE_DIR / '.env.local'
ENV_EXAMPLE_PATH = BASE_DIR / '.env.example'
AUTO_PORTFOLIO_BUILD_DIR = BASE_DIR / 'AutoPortfolio' / '.firebase' / 'crime-e6654' / 'hosting'
AUTO_PORTFOLIO_PUBLIC_DIR = BASE_DIR / 'AutoPortfolio' / 'auto-portfolio' / 'public'
AUTO_PORTFOLIO_PUBLIC_FILES = {
    'Resume.pdf',
    'classic.png',
    'modern.png',
    'creative.png',
    'corporate.png',
    'minimalist.png',
    'tech.png',
}
PORTFOLIO_PHOTO_DIR = get_writable_path(BASE_DIR, 'data/portfolio/photos')
PORTFOLIO_PREVIEW_TEMPLATES = {'classic', 'modern', 'creative', 'corporate', 'minimalist', 'tech'}


def _load_env():
    load_dotenv(dotenv_path=ENV_EXAMPLE_PATH)
    load_dotenv(dotenv_path=ENV_PATH, override=True)
    load_dotenv(dotenv_path=ENV_LOCAL_PATH, override=True)


_load_env()

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False
DATA_STORE = build_store(BASE_DIR)
CONVERTER_SERVICE = DocumentConverterService(BASE_DIR, DATA_STORE)
CONVERTER_RATE_LIMIT = {}


def _fresh_generator() -> WebsiteGenerator:
    # Reload env from app directory for hot updates during local dev.
    _load_env()
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
    token = ''
    if auth_header.startswith('Bearer '):
        token = auth_header.replace('Bearer ', '', 1).strip()
    else:
        token = (request.args.get('token') or '').strip()
    if not token:
        return None, 'Missing auth token. Please login first.'

    if not token:
        return None, 'Invalid auth token.'

    return _verify_firebase_token(token)


def _is_admin(user: dict) -> bool:
    emails = [item.strip().lower() for item in os.getenv('ADMIN_EMAILS', '').split(',') if item.strip()]
    return (user.get('email') or '').strip().lower() in emails


def _check_rate_limit(user: dict, action: str, limit: int, window_seconds: int):
    uid = (user.get('localId') or '').strip()
    if not uid:
        return ''
    now = datetime.now(timezone.utc).timestamp()
    bucket = CONVERTER_RATE_LIMIT.setdefault(uid, {}).setdefault(action, [])
    bucket[:] = [ts for ts in bucket if now - ts < window_seconds]
    if len(bucket) >= limit:
        return f'Rate limit exceeded for {action}. Try again later.'
    bucket.append(now)
    return ''


def _extract_title(html: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return re.sub(r"\s+", " ", match.group(1)).strip()


def _compose_page_document(page: dict) -> str:
    html = (page or {}).get('html') or ''
    css = (page or {}).get('css') or ''
    js = (page or {}).get('js') or ''
    return (
        '<!doctype html><html lang="en"><head><meta charset="UTF-8" />'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0" />'
        f'<style>{css}</style></head><body>{html}<script>{js}</script></body></html>'
    )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _portfolio_template_meta(template_id: str) -> dict:
    template = (template_id or 'classic').strip().lower()
    palette = {
        'classic': {'label': 'Classic Professional', 'accent': '#2563eb'},
        'modern': {'label': 'Modern Minimalist', 'accent': '#0f766e'},
        'creative': {'label': 'Creative Bold', 'accent': '#db2777'},
        'corporate': {'label': 'Corporate', 'accent': '#334155'},
        'minimalist': {'label': 'Minimalist', 'accent': '#111827'},
        'tech': {'label': 'Tech', 'accent': '#7c3aed'},
    }
    return {'id': template, **palette.get(template, palette['classic'])}


def _sample_portfolio(template_id: str) -> dict:
    meta = _portfolio_template_meta(template_id)
    return {
        'id': 'sample',
        'name': 'Pratham Kumar',
        'headline': 'AI Builder • Full-Stack Developer • Product Engineer',
        'bio': 'I build practical student-first tools, portfolio systems, and AI-assisted web products with a focus on speed, clarity, and deployable outcomes.',
        'skills': ['React', 'Flask', 'Firebase', 'Tailwind', 'Python', 'UI Systems'],
        'projects': [
            {'title': 'VIRU Workspace', 'description': 'Unified website generator and document tooling with authenticated project workflows.', 'link': '#'},
            {'title': 'Auto Portfolio', 'description': 'Fast portfolio builder with reusable templates and edit flows.', 'link': '#'},
        ],
        'experience': [
            {'company': 'Independent Builder', 'title': 'Founder / Developer', 'duration': '2024 - Present', 'description': 'Shipping product ideas from concept to working deployment.'},
        ],
        'contact': {'email': 'pratham@example.com', 'linkedin': 'https://linkedin.com', 'github': 'https://github.com', 'twitter': ''},
        'template': meta['id'],
        'templateLabel': meta['label'],
        'photoURL': '',
    }


def _rewrite_auto_portfolio_html(document: str) -> str:
    replacements = [
        ('href="/_next/', 'href="/auto-portfolio/_next/'),
        ('src="/_next/', 'src="/auto-portfolio/_next/'),
        ('"/_next/', '"/auto-portfolio/_next/'),
        ("'/_next/", "'/auto-portfolio/_next/"),
        ('href="/u/', 'href="/auto-portfolio/u/'),
        ('src="/u/', 'src="/auto-portfolio/u/'),
        ('"/u/', '"/auto-portfolio/u/'),
        ("'/u/", "'/auto-portfolio/u/"),
        ('href="/generate"', 'href="/auto-portfolio/generate"'),
        ("href='/'", "href='/auto-portfolio'"),
        ('href="/"', 'href="/auto-portfolio"'),
        ('initialCanonicalUrl":"/"', 'initialCanonicalUrl":"/auto-portfolio"'),
        ('initialCanonicalUrl":"/generate"', 'initialCanonicalUrl":"/auto-portfolio/generate"'),
    ]
    content = document
    for old, new in replacements:
        content = content.replace(old, new)
    return content


def _serve_auto_portfolio_html(filename: str, request_path: str):
    target = AUTO_PORTFOLIO_BUILD_DIR / filename
    if not target.exists():
        return 'AutoPortfolio page not found.', 404

    document = _rewrite_auto_portfolio_html(target.read_text(encoding='utf-8'))
    canonical_path = request_path if request_path.startswith('/') else f'/{request_path}'
    document = re.sub(
        r'initialCanonicalUrl":"[^"]*"',
        f'initialCanonicalUrl":"{canonical_path}"',
        document,
        count=1,
    )
    return document, 200, {'Content-Type': 'text/html; charset=utf-8'}


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


@app.get('/converter')
def converter_page():
    return render_template('converter.html')


@app.get('/conversions')
def conversions_page():
    return render_template('conversions.html')


@app.get('/admin/converter')
def admin_converter_page():
    return render_template('admin_converter.html')


@app.get('/share/<share_id>')
def public_share_page(share_id: str):
    page_index = request.args.get('page', default=0, type=int)
    item = DATA_STORE.get_share(share_id)
    if not item:
        return 'Shared page not found.', 404

    pages = (item.get('result') or {}).get('pages') or []
    if not pages:
        return 'Shared page is empty.', 404
    if page_index < 0 or page_index >= len(pages):
        page_index = 0

    return _compose_page_document(pages[page_index]), 200, {'Content-Type': 'text/html; charset=utf-8'}


@app.get('/generate')
def auto_portfolio_generate_alias():
    return render_template('portfolio_generate.html', mode='create', portfolio_id='')


@app.get('/dashboard')
def auto_portfolio_dashboard_alias():
    return render_template('portfolio_dashboard.html')


@app.get('/privacy-policy')
def auto_portfolio_privacy_alias():
    return redirect('/auto-portfolio/privacy-policy', code=302)


@app.get('/terms-of-service')
def auto_portfolio_terms_alias():
    return redirect('/auto-portfolio/terms-of-service', code=302)


@app.get('/preview/<path:item_id>')
def auto_portfolio_preview_alias(item_id: str):
    if item_id not in PORTFOLIO_PREVIEW_TEMPLATES:
        return 'Template preview not found.', 404
    sample = _sample_portfolio(item_id)
    return render_template('portfolio_public.html', portfolio=sample, preview_mode=True, resume_mode=False, template_meta=_portfolio_template_meta(item_id))


@app.get('/edit/<path:item_id>')
def auto_portfolio_edit_alias(item_id: str):
    return render_template('portfolio_generate.html', mode='edit', portfolio_id=item_id)


@app.get('/resume/<path:item_id>')
def auto_portfolio_resume_alias(item_id: str):
    portfolio = DATA_STORE.get_portfolio(item_id)
    if not portfolio:
        return 'Portfolio not found.', 404
    return render_template(
        'portfolio_public.html',
        portfolio=portfolio,
        preview_mode=False,
        resume_mode=True,
        template_meta=_portfolio_template_meta(portfolio.get('template', 'classic')),
    )


@app.get('/u/<path:item_id>')
def auto_portfolio_public_alias(item_id: str):
    portfolio = DATA_STORE.get_portfolio(item_id)
    if not portfolio:
        return 'Portfolio not found.', 404
    return render_template(
        'portfolio_public.html',
        portfolio=portfolio,
        preview_mode=False,
        resume_mode=False,
        template_meta=_portfolio_template_meta(portfolio.get('template', 'classic')),
    )


@app.get('/projects')
def projects_page():
    return render_template('projects.html')


@app.get('/portfolio-assets/templates/<path:asset_name>')
def portfolio_template_asset(asset_name: str):
    if asset_name not in AUTO_PORTFOLIO_PUBLIC_FILES:
        return 'Template asset not found.', 404
    return send_from_directory(AUTO_PORTFOLIO_PUBLIC_DIR, asset_name)


@app.get('/portfolio-assets/photos/<path:asset_name>')
def portfolio_photo_asset(asset_name: str):
    photo_root = PORTFOLIO_PHOTO_DIR.resolve()
    target = (PORTFOLIO_PHOTO_DIR / asset_name).resolve()
    try:
        target.relative_to(photo_root)
    except ValueError:
        return 'Invalid photo path.', 404
    if not target.exists() or not target.is_file():
        return 'Photo not found.', 404
    return send_from_directory(PORTFOLIO_PHOTO_DIR, asset_name)


@app.get('/<path:asset_name>')
def auto_portfolio_public_asset(asset_name: str):
    if asset_name not in AUTO_PORTFOLIO_PUBLIC_FILES:
        return 'Not Found', 404
    if not AUTO_PORTFOLIO_PUBLIC_DIR.exists():
        return 'AutoPortfolio public assets not found.', 404
    return send_from_directory(AUTO_PORTFOLIO_PUBLIC_DIR, asset_name)


@app.get('/auto-portfolio')
@app.get('/auto-portfolio/')
@app.get('/auto-portfolio/<path:asset_path>')
def auto_portfolio_page(asset_path: str = 'index.html'):
    if not AUTO_PORTFOLIO_BUILD_DIR.exists():
        return 'AutoPortfolio build not found.', 404

    normalized = (asset_path or 'index.html').strip('/')
    if not normalized:
        normalized = 'index.html'
    if normalized == 'generate':
        normalized = 'generate.html'
    if normalized == 'index':
        normalized = 'index.html'

    target = (AUTO_PORTFOLIO_BUILD_DIR / normalized).resolve()
    try:
        target.relative_to(AUTO_PORTFOLIO_BUILD_DIR.resolve())
    except ValueError:
        return 'Invalid asset path.', 404

    if not target.exists() or not target.is_file():
        if '.' not in normalized.split('/')[-1]:
            return _serve_auto_portfolio_html('index.html', f'/auto-portfolio/{normalized}')
        return 'AutoPortfolio asset not found.', 404

    if target.suffix.lower() == '.html':
        return _serve_auto_portfolio_html(normalized, f'/auto-portfolio/{normalized.removesuffix(".html")}')

    return send_from_directory(AUTO_PORTFOLIO_BUILD_DIR, normalized)


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
                'persistenceMode': DATA_STORE.mode,
            },
        }
    )


@app.get('/favicon.ico')
def favicon():
    return redirect(url_for('static', filename='images/logo.png'), code=302)


@app.get('/api/portfolios')
def list_portfolios_api():
    user, error = _require_auth()
    if error:
        return jsonify({'ok': False, 'error': error}), 401
    return jsonify({'ok': True, 'portfolios': DATA_STORE.list_portfolios(user.get('localId', ''))})


@app.post('/api/portfolios')
def create_portfolio_api():
    user, error = _require_auth()
    if error:
        return jsonify({'ok': False, 'error': error}), 401

    payload = request.get_json(silent=True) or {}
    portfolio_id = uuid.uuid4().hex[:12]
    now = _utc_now_iso()
    item = {
        'id': portfolio_id,
        'owner_uid': user.get('localId', ''),
        'owner_email': user.get('email', ''),
        'visibility': 'public',
        'name': (payload.get('name') or '').strip(),
        'headline': (payload.get('headline') or '').strip(),
        'bio': (payload.get('bio') or '').strip(),
        'skills': payload.get('skills') or [],
        'projects': payload.get('projects') or [],
        'experience': payload.get('experience') or [],
        'contact': payload.get('contact') or {},
        'template': (payload.get('template') or 'classic').strip().lower(),
        'photoURL': (payload.get('photoURL') or '').strip(),
        'createdAt': now,
        'updatedAt': now,
    }
    if not item['name']:
        return jsonify({'ok': False, 'error': 'Name is required.'}), 400
    DATA_STORE.create_portfolio(item)
    return jsonify({'ok': True, 'portfolio': item})


@app.get('/api/portfolios/<portfolio_id>')
def get_portfolio_api(portfolio_id: str):
    portfolio = DATA_STORE.get_portfolio(portfolio_id)
    if not portfolio:
        return jsonify({'ok': False, 'error': 'Portfolio not found.'}), 404

    user, _ = _require_auth()
    if portfolio.get('visibility') != 'public':
        if not user or user.get('localId') != portfolio.get('owner_uid'):
            return jsonify({'ok': False, 'error': 'Access denied.'}), 403
    return jsonify({'ok': True, 'portfolio': portfolio})


@app.put('/api/portfolios/<portfolio_id>')
def update_portfolio_api(portfolio_id: str):
    user, error = _require_auth()
    if error:
        return jsonify({'ok': False, 'error': error}), 401
    portfolio = DATA_STORE.get_portfolio(portfolio_id)
    if not portfolio:
        return jsonify({'ok': False, 'error': 'Portfolio not found.'}), 404
    if portfolio.get('owner_uid') != user.get('localId'):
        return jsonify({'ok': False, 'error': 'Access denied.'}), 403

    payload = request.get_json(silent=True) or {}
    updates = {
        'name': (payload.get('name') or '').strip(),
        'headline': (payload.get('headline') or '').strip(),
        'bio': (payload.get('bio') or '').strip(),
        'skills': payload.get('skills') or [],
        'projects': payload.get('projects') or [],
        'experience': payload.get('experience') or [],
        'contact': payload.get('contact') or {},
        'template': (payload.get('template') or portfolio.get('template') or 'classic').strip().lower(),
        'photoURL': (payload.get('photoURL') or '').strip(),
        'updatedAt': _utc_now_iso(),
    }
    item = DATA_STORE.update_portfolio(portfolio_id, updates)
    return jsonify({'ok': True, 'portfolio': item})


@app.delete('/api/portfolios/<portfolio_id>')
def delete_portfolio_api(portfolio_id: str):
    user, error = _require_auth()
    if error:
        return jsonify({'ok': False, 'error': error}), 401
    deleted = DATA_STORE.delete_portfolio(user.get('localId', ''), portfolio_id)
    if not deleted:
        return jsonify({'ok': False, 'error': 'Portfolio not found.'}), 404
    return jsonify({'ok': True})


@app.post('/api/portfolios/photo')
def upload_portfolio_photo_api():
    user, error = _require_auth()
    if error:
        return jsonify({'ok': False, 'error': error}), 401

    file = request.files.get('photo')
    if not file or not file.filename:
        return jsonify({'ok': False, 'error': 'Photo file is required.'}), 400

    ext = Path(file.filename).suffix.lower()
    if ext not in {'.png', '.jpg', '.jpeg', '.webp'}:
        return jsonify({'ok': False, 'error': 'Unsupported photo format.'}), 400

    user_dir = PORTFOLIO_PHOTO_DIR / user.get('localId', 'anonymous')
    user_dir.mkdir(parents=True, exist_ok=True)
    filename = f'{uuid.uuid4().hex[:16]}{ext}'
    destination = user_dir / filename
    file.save(destination)
    relative = destination.relative_to(PORTFOLIO_PHOTO_DIR).as_posix()
    return jsonify({'ok': True, 'photoURL': f'/portfolio-assets/photos/{relative}'})


@app.get('/api/health')
def health():
    user, auth_error = _require_auth()
    if not user:
        return jsonify({'ok': False, 'message': auth_error}), 401

    try:
        generator = _fresh_generator()
        response = generator.health_check()
        response['auth'] = {'email': user.get('email', ''), 'uid': user.get('localId', '')}
        response['persistence_mode'] = DATA_STORE.mode
        return jsonify(response)
    except Exception:
        return jsonify({'ok': False, 'message': 'Health check failed unexpectedly.'}), 500


@app.post('/api/converter/upload')
def converter_upload():
    user, auth_error = _require_auth()
    if not user:
        return jsonify({'ok': False, 'error': auth_error}), 401
    rate_error = _check_rate_limit(user, 'upload', 20, 3600)
    if rate_error:
        return jsonify({'ok': False, 'error': rate_error}), 429
    files = request.files.getlist('files')
    if not files:
        return jsonify({'ok': False, 'error': 'At least one file is required.'}), 400
    saved = CONVERTER_SERVICE.save_uploads(files, user.get('localId', ''), user.get('email', ''))
    if not saved:
        return jsonify({'ok': False, 'error': 'No supported files were uploaded.'}), 400
    return jsonify({'ok': True, 'uploads': saved})


@app.get('/api/converter/jobs')
def converter_jobs():
    user, auth_error = _require_auth()
    if not user:
        return jsonify({'ok': False, 'error': auth_error}), 401
    return jsonify({'ok': True, 'jobs': CONVERTER_SERVICE.list_jobs(user.get('localId', ''))})


@app.get('/api/converter/jobs/<job_id>')
def converter_job_detail(job_id: str):
    user, auth_error = _require_auth()
    if not user:
        return jsonify({'ok': False, 'error': auth_error}), 401
    job = CONVERTER_SERVICE.get_job(job_id)
    if not job:
        return jsonify({'ok': False, 'error': 'Conversion job not found.'}), 404
    if job.get('owner_uid') != user.get('localId', '') and not _is_admin(user):
        return jsonify({'ok': False, 'error': 'Access denied.'}), 403
    return jsonify({'ok': True, 'job': job})


@app.delete('/api/converter/jobs/<job_id>')
def converter_delete_job(job_id: str):
    user, auth_error = _require_auth()
    if not user:
        return jsonify({'ok': False, 'error': auth_error}), 401
    deleted = CONVERTER_SERVICE.delete_job(job_id, owner_uid=user.get('localId', ''), is_admin=_is_admin(user))
    if not deleted:
        return jsonify({'ok': False, 'error': 'Conversion job not found or access denied.'}), 404
    return jsonify({'ok': True})


@app.get('/api/converter/uploads/<upload_id>')
def converter_upload_detail(upload_id: str):
    user, auth_error = _require_auth()
    if not user:
        return jsonify({'ok': False, 'error': auth_error}), 401
    upload = CONVERTER_SERVICE.get_upload(upload_id)
    if not upload:
        return jsonify({'ok': False, 'error': 'Uploaded file not found.'}), 404
    if upload.get('owner_uid') != user.get('localId', '') and not _is_admin(user):
        return jsonify({'ok': False, 'error': 'Access denied.'}), 403
    return jsonify({'ok': True, 'upload': upload})


@app.post('/api/converter/convert')
def converter_convert():
    user, auth_error = _require_auth()
    if not user:
        return jsonify({'ok': False, 'error': auth_error}), 401
    rate_error = _check_rate_limit(user, 'convert', 30, 3600)
    if rate_error:
        return jsonify({'ok': False, 'error': rate_error}), 429
    payload = request.get_json(silent=True) or {}
    upload_id = (payload.get('upload_id') or '').strip()
    target_format = (payload.get('target_format') or '').strip().lower()
    ai_mode = (payload.get('ai_mode') or 'balanced').strip().lower()
    ocr_enabled = bool(payload.get('ocr_enabled', True))
    structure_fix = bool(payload.get('structure_fix', True))
    keep_layout = bool(payload.get('keep_layout', True))
    priority = (payload.get('priority') or 'standard').strip().lower()

    if not upload_id or not target_format:
        return jsonify({'ok': False, 'error': 'upload_id and target_format are required.'}), 400

    try:
        job = CONVERTER_SERVICE.convert(
            upload_id=upload_id,
            owner_uid=user.get('localId', ''),
            owner_email=user.get('email', ''),
            target_format=target_format,
            ai_mode=ai_mode,
            ocr_enabled=ocr_enabled,
            structure_fix=structure_fix,
            keep_layout=keep_layout,
            priority=priority,
        )
        return jsonify({'ok': True, 'job': job})
    except ValueError as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 400
    except Exception:
        return jsonify({'ok': False, 'error': 'Document conversion failed unexpectedly.'}), 500


@app.get('/api/converter/preview/<job_id>')
def converter_preview(job_id: str):
    user, auth_error = _require_auth()
    if not user:
        return jsonify({'ok': False, 'error': auth_error}), 401
    job = CONVERTER_SERVICE.get_job(job_id)
    if not job:
        return jsonify({'ok': False, 'error': 'Conversion job not found.'}), 404
    if job.get('owner_uid') != user.get('localId', '') and not _is_admin(user):
        return jsonify({'ok': False, 'error': 'Access denied.'}), 403
    return jsonify({'ok': True, 'preview': job.get('preview') or {}, 'job': job})


@app.get('/api/converter/download/<job_id>')
def converter_download(job_id: str):
    user, auth_error = _require_auth()
    if not user:
        return jsonify({'ok': False, 'error': auth_error}), 401
    job = CONVERTER_SERVICE.get_job(job_id)
    if not job:
        return jsonify({'ok': False, 'error': 'Conversion job not found.'}), 404
    if job.get('owner_uid') != user.get('localId', '') and not _is_admin(user):
        return jsonify({'ok': False, 'error': 'Access denied.'}), 403
    path = Path(job.get('downloadPath') or '')
    if not path.exists():
        return jsonify({'ok': False, 'error': 'Converted file not found on server.'}), 404
    return send_file(path, as_attachment=True, download_name=job.get('downloadName') or path.name)


@app.get('/api/converter/admin/metrics')
def converter_admin_metrics():
    user, auth_error = _require_auth()
    if not user:
        return jsonify({'ok': False, 'error': auth_error}), 401
    if not _is_admin(user):
        return jsonify({'ok': False, 'error': 'Admin access required.'}), 403
    jobs = CONVERTER_SERVICE.list_all_jobs(500)
    total = len(jobs)
    by_status = {}
    by_format = {}
    for job in jobs:
        by_status[job.get('status', 'unknown')] = by_status.get(job.get('status', 'unknown'), 0) + 1
        key = f"{job.get('sourceFormat', '?')}->{job.get('targetFormat', '?')}"
        by_format[key] = by_format.get(key, 0) + 1
    return jsonify({'ok': True, 'metrics': {'total_jobs': total, 'by_status': by_status, 'by_format': by_format, 'recent_jobs': jobs[:20]}})


@app.post('/api/converter/cleanup')
def converter_cleanup():
    user, auth_error = _require_auth()
    if not user:
        return jsonify({'ok': False, 'error': auth_error}), 401
    payload = request.get_json(silent=True) or {}
    max_age_days = int(payload.get('max_age_days') or 7)
    scope = (payload.get('scope') or 'mine').strip().lower()
    if scope == 'all':
        if not _is_admin(user):
            return jsonify({'ok': False, 'error': 'Admin access required.'}), 403
        result = CONVERTER_SERVICE.cleanup_jobs(max_age_days=max_age_days, owner_uid=None)
    else:
        result = CONVERTER_SERVICE.cleanup_jobs(max_age_days=max_age_days, owner_uid=user.get('localId', ''))
    return jsonify({'ok': True, 'cleanup': result})


@app.get('/api/converter/assets/<asset_name>')
def converter_asset(asset_name: str):
    user, auth_error = _require_auth()
    if not user:
        return jsonify({'ok': False, 'error': auth_error}), 401
    safe_name = Path(asset_name).name
    owner_uid = user.get('localId', '')
    owned_jobs = CONVERTER_SERVICE.list_jobs(owner_uid)
    owned_uploads = CONVERTER_SERVICE.list_uploads(owner_uid)
    owned_upload_paths = []
    for job in owned_jobs:
        job_path = Path(job.get('downloadPath') or '')
        if job_path.exists():
            if job_path.is_file() and job_path.name == safe_name:
                return send_file(job_path)
            if job_path.is_dir():
                matches = list(job_path.rglob(safe_name))
                if matches:
                    return send_file(matches[0])
            sibling_dir = CONVERTER_SERVICE.outputs_dir / f"{job.get('id')}-pages"
            if sibling_dir.exists():
                matches = list(sibling_dir.rglob(safe_name))
                if matches:
                    return send_file(matches[0])
        upload = CONVERTER_SERVICE.get_upload(job.get('uploadId') or '')
        if upload and upload.get('owner_uid') == owner_uid:
            owned_upload_paths.append(Path(upload.get('storedPath') or ''))
    for upload in owned_uploads:
        upload_path = Path(upload.get('storedPath') or '')
        if upload_path.exists() and upload_path.name == safe_name:
            return send_file(upload_path)
    for upload_path in owned_upload_paths:
        if upload_path.exists() and upload_path.name == safe_name:
            return send_file(upload_path)
    candidate_paths = [
        CONVERTER_SERVICE.uploads_dir / safe_name,
        CONVERTER_SERVICE.outputs_dir / safe_name,
        CONVERTER_SERVICE.previews_dir / safe_name,
    ]
    for path in candidate_paths:
        if path.exists() and _is_admin(user):
            return send_file(path)
    for root in (CONVERTER_SERVICE.outputs_dir, CONVERTER_SERVICE.previews_dir, CONVERTER_SERVICE.uploads_dir):
        matches = list(root.rglob(safe_name))
        if matches and _is_admin(user):
            return send_file(matches[0])
    return 'Asset not found.', 404


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
    title = (payload.get('title') or 'Generated Output').strip()
    prompt = (payload.get('prompt') or '').strip()
    style = (payload.get('style') or 'modern saas').strip()
    pages = int(payload.get('pages') or 1)
    permission = (payload.get('permission') or 'view').strip().lower()
    if permission not in {'view', 'edit'}:
        permission = 'view'
    if not result or not isinstance(result, dict) or not result.get('pages'):
        return jsonify({'ok': False, 'error': 'Generated result payload is required.'}), 400

    share_id = uuid.uuid4().hex[:12]
    DATA_STORE.create_share(
        share_id,
        {
            'id': share_id,
            'owner_uid': user.get('localId', ''),
            'owner_email': user.get('email', ''),
            'permission': permission,
            'title': title,
            'prompt': prompt,
            'style': style,
            'pages': max(1, min(pages, 5)),
            'result': result,
            'createdAt': datetime.now(timezone.utc).isoformat(),
            'updatedAt': datetime.now(timezone.utc).isoformat(),
        },
    )

    public_link = f"{request.host_url.rstrip('/')}/share/{share_id}"
    edit_link = f"{request.host_url.rstrip('/')}/app?share={share_id}&perm=edit"
    share_link = edit_link if permission == 'edit' else public_link
    return jsonify(
        {
            'ok': True,
            'share_id': share_id,
            'permission': permission,
            'share_link': share_link,
            'public_share_link': public_link,
            'edit_share_link': edit_link,
        }
    )


@app.get('/api/share/<share_id>')
def get_share(share_id: str):
    mode = (request.args.get('perm') or 'view').strip().lower()
    if mode not in {'view', 'edit'}:
        mode = 'view'

    item = DATA_STORE.get_share(share_id)
    if not item:
        return jsonify({'ok': False, 'error': 'Share link not found.'}), 404

    if mode == 'edit':
        user, auth_error = _require_auth()
        if not user:
            return jsonify({'ok': False, 'error': auth_error}), 401
    else:
        user = None

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
                'public_share_link': f"{request.host_url.rstrip('/')}/share/{share_id}",
                'edit_share_link': f"{request.host_url.rstrip('/')}/app?share={share_id}&perm=edit",
            },
            'result': item.get('result') or {},
            'workspace': {
                'title': item.get('title', 'Generated Output'),
                'prompt': item.get('prompt', ''),
                'style': item.get('style', 'modern saas'),
                'pages': item.get('pages', 1),
            },
        }
    )


@app.post('/api/share/<share_id>/save')
def save_share(share_id: str):
    user, auth_error = _require_auth()
    if not user:
        return jsonify({'ok': False, 'error': auth_error}), 401

    payload = request.get_json(silent=True) or {}
    result = payload.get('result') or {}
    title = (payload.get('title') or 'Generated Output').strip()
    prompt = (payload.get('prompt') or '').strip()
    style = (payload.get('style') or 'modern saas').strip()
    pages = int(payload.get('pages') or 1)

    if not isinstance(result, dict) or not result.get('pages'):
        return jsonify({'ok': False, 'error': 'Generated result is required.'}), 400

    item = DATA_STORE.get_share(share_id)
    if not item:
        return jsonify({'ok': False, 'error': 'Share link not found.'}), 404
    if item.get('permission') != 'edit':
        return jsonify({'ok': False, 'error': 'This share link is view-only.'}), 403

    DATA_STORE.update_share(
        share_id,
        {
            'title': title,
            'prompt': prompt,
            'style': style,
            'pages': max(1, min(pages, 5)),
            'result': result,
            'last_editor_uid': user.get('localId', ''),
            'last_editor_email': user.get('email', ''),
            'updatedAt': datetime.now(timezone.utc).isoformat(),
        },
    )

    return jsonify(
        {
            'ok': True,
            'share': {
                'id': share_id,
                'public_share_link': f"{request.host_url.rstrip('/')}/share/{share_id}",
                'edit_share_link': f"{request.host_url.rstrip('/')}/app?share={share_id}&perm=edit",
                'last_editor_email': user.get('email', ''),
            },
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

    DATA_STORE.create_project(project)
    return jsonify({'ok': True, 'project': project})


@app.get('/api/projects')
def list_projects():
    user, auth_error = _require_auth()
    if not user:
        return jsonify({'ok': False, 'error': auth_error}), 401

    owner_uid = user.get('localId', '')
    projects = DATA_STORE.list_projects(owner_uid)
    return jsonify({'ok': True, 'projects': projects})


@app.delete('/api/projects/<project_id>')
def delete_project(project_id: str):
    user, auth_error = _require_auth()
    if not user:
        return jsonify({'ok': False, 'error': auth_error}), 401

    owner_uid = user.get('localId', '')
    deleted = DATA_STORE.delete_project(owner_uid, project_id)
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
    if not html.strip():
        return jsonify({'ok': False, 'error': 'Selected page HTML is empty.'}), 400

    published_id = uuid.uuid4().hex[:14]
    document = _compose_page_document(page)

    DATA_STORE.create_published(
        published_id,
        {
            'id': published_id,
            'owner_uid': user.get('localId', ''),
            'owner_email': user.get('email', ''),
            'createdAt': datetime.now(timezone.utc).isoformat(),
            'document': document,
        },
    )

    live_url = f"{request.host_url.rstrip('/')}/published/{published_id}"
    return jsonify({'ok': True, 'deploy_url': live_url, 'deploy_id': published_id, 'provider': 'viru-local'})


@app.get('/published/<published_id>')
def render_published_page(published_id: str):
    item = DATA_STORE.get_published(published_id)
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
