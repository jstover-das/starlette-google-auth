from datetime import datetime
import os
from functools import wraps
from pathlib import Path
from tkinter.constants import S
from typing import Callable
from urllib.parse import urlparse

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from authlib.integrations.starlette_client import OAuth
from mangum import Mangum

from . import settings
from .aws_helpers import scan_table, get_presigned_url

APP_DIR = Path(__file__).parent

oauth = OAuth(settings.config)
oauth.register(
    name='google',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile',
    }
)

def login_required(fn: Callable):
    @wraps(fn)
    async def decorated(request: Request, *args, **kwargs) -> Response:
        if request.session.get('authenticated', False):
            return await fn(request, *args, **kwargs)
        else:
            request.session['redirect_to'] = str(request.url_for(fn.__name__, **request.path_params))
            return RedirectResponse(request.url_for('login'))
    return decorated


async def index(request: Request):
    context = {
        'platform_reports': [],
        'hullscrubber_reports': [],
        'messages': [],
    }
    if request.session.get('authenticated', False):
        try:
            context['platform_reports'] = sorted(
                scan_table(settings.PLATFORM_RESULTS_TABLE_NAME),
                key=lambda row: row['timestamp'],
                reverse=True,
            )

        except Exception as ex:
            context['messages'].append({'msg': f'Unable to fetch platform reports.\n{str(ex)}', 'category': 'error'})
        try:
            context['hullscrubber_reports'] = scan_table(settings.HULLSCRUBBER_RESULTS_TABLE_NAME)
        except Exception as ex:
            context['messages'].append({'msg': f'Unable to fetch hullscrubber reports.\n{str(ex)}', 'category': 'error'})

    return templates.TemplateResponse(request, 'index.html', context=context)


async def login(request: Request):
    redirect_uri = request.url_for('login_callback')
    return await oauth.google.authorize_redirect(request, redirect_uri)


async def login_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    userinfo = token.get('userinfo', {})
    if not userinfo.get('email_verified', False):
        return Response(content='Could not validate credentials', status_code=401, headers={'WWW-Authenticate': 'Bearer'})

    request.session['authenticated'] = True
    # Once logged in, redirect back to index page or to a path saved in session by `login_required`
    return RedirectResponse(request.session.pop('redirect_to', request.url_for('index')))


async def logout(request: Request):
    request.session.pop('authenticated', None)
    return RedirectResponse(url='/')


@login_required
async def s3_redirect(request: Request) -> Response | RedirectResponse:
    """
    Redirect to a file on S3 using a presigned URL
    """
    uri = urlparse(str(request.path_params['uri']))
    key = uri.path.lstrip('./')
    bucket = uri.netloc if uri.scheme == 's3' else settings.REPORTS_BUCKET
    if bucket != settings.REPORTS_BUCKET:
        return Response('Permission Denied', status_code=403)
    try:
        return RedirectResponse(get_presigned_url(bucket=bucket, key=key))
    except Exception:
        return Response('Unable to generate presigned URL', status_code=429)



# Configure Templating
templates = Jinja2Templates(
    directory=APP_DIR / 'templates',
    autoescape=True,
    context_processors=[
        lambda r: {
            'authenticated': r.session.get('authenticated', False),
        }
    ]
)
templates.env.filters['format_timestamp'] = lambda s: datetime.fromtimestamp(int(s) / 1000).strftime('%Y-%m-%d, %H:%M:%S')

# Create application
app = Starlette(
    debug=settings.DEBUG,
    routes=[
        Mount('/static', app=StaticFiles(directory=APP_DIR / 'static', check_dir=True), name='static'),
        Route('/', index),
        Route('/login', login),
        Route('/login/callback', login_callback),
        Route('/logout', logout),
        Route('/-/{uri:path}', s3_redirect),
    ],
    middleware=[
        Middleware(SessionMiddleware, secret_key=settings.SECRET_KEY),
    ],
)

# Lambda handler for API Gateway
stage = '/' + os.environ.get('STAGE', '')
lambda_handler = Mangum(app, api_gateway_base_path=stage)
