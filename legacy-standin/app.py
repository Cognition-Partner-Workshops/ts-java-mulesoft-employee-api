"""Local translation of the checked-in flow contracts, not a Mule runtime."""
import base64
import datetime as dt
import decimal
import json
import os
from pathlib import Path
import re
import threading
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import psycopg
from psycopg.rows import dict_row

DB = 'http://www.mulesoft.org/schema/mule/db'
DOC = 'http://www.mulesoft.org/schema/mule/documentation'
QUERIES = {}
for node in ET.parse(os.environ.get('FLOWS_XML', '/app/flows.xml')).iter():
    sql = node.find(f'{{{DB}}}sql')
    if sql is not None:
        QUERIES[node.get(f'{{{DOC}}}name')] = re.sub(
            r':([A-Za-z]\w*)', r'%(\1)s', sql.text)


def query(name, **params):
    with psycopg.connect(os.environ['DATABASE_URL'], row_factory=dict_row,
                         connect_timeout=3) as conn:
        with conn.cursor() as cur:
            cur.execute(QUERIES[name], params)
            return cur.fetchall() if cur.description else cur.rowcount


def now():
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


def token(prefix=''):
    return prefix + str(uuid.uuid4()) + '-' + now().isoformat() + 'Z'


def error(status, code, description):
    return status, {'error': code, 'error_description': description}


def callback(url, access, client):
    try:
        request = urllib.request.Request(url, data=json.dumps(
            {'token': access, 'userId': client}).encode(),
            headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(request, timeout=5):
            pass
    except Exception:
        pass


def authenticate(header):
    if not header.startswith('Bearer '):
        return error(401, 'missing_token', 'Authorization header is missing or invalid')
    try:
        valid = query('Retrieve Token from DB', token=header[7:], currentTime=now())
    except psycopg.Error:
        return error(401, 'invalid_token', 'Token validation failed')
    if not valid:
        return error(401, 'invalid_token', 'Invalid or expired access token')


def oauth(data, header):
    client, secret = data.get('client_id'), data.get('client_secret')
    if header:
        client, secret = base64.b64decode(header[6:], validate=True).decode().split(':')[:2]
    if not query('Validate Client Credentials', clientId=client, clientSecret=secret):
        return error(401, 'invalid_client', 'Client authentication failed')
    access = token()
    url = data.get('callback_url') if not header else None
    query('Store Token in DB', clientId=client, clientSecret=secret,
          accessToken=access, expiresAt=now() + dt.timedelta(hours=1), callbackUrl=url)
    if url:
        threading.Thread(target=callback, args=(url, access, client), daemon=True).start()
    return 200, dict(access_token=access, token_type='Bearer', expires_in=3600, scope='read write')


def auth(path, data):
    if path == '/auth/register':
        if not all(data.get(k) for k in ('username', 'password', 'email')):
            return error(400, 'missing_fields', 'Username, password, and email are required')
        if query('Check User Exists', username=data['username'], email=data['email']):
            return error(409, 'user_exists', 'Username or email already exists')
        query('Insert New User', username=data['username'], email=data['email'],
              firstName=data.get('firstName', ''), lastName=data.get('lastName', ''),
              passwordHash=base64.b64encode((data['password'] + 'salt').encode()).decode())
        return 201, {'message': 'User created successfully', 'username': data['username']}
    if path == '/auth/login':
        client = data.get('clientId', data.get('client_id', ''))
        if not (data.get('username') and data.get('password') and client):
            return error(400, 'invalid_request', 'Missing required fields: username, password, and clientId')
        users = query('Validate User Credentials', username=data['username'],
                      passwordHash=base64.b64encode((data['password'] + 'salt').encode()).decode())
        if not users:
            return error(401, 'invalid_credentials', 'Invalid username or password')
        user_id = data.get('userId', data.get('salesforce_user_id'))
        clients = query('Check Existing API Client', userId=users[0]['user_id'])
        if clients:
            client = clients[0]['client_id']
        else:
            query('Create API Client', clientId=client, clientSecret=token(),
                  userId=users[0]['user_id'], salesforceUserId=user_id)
        access, refresh = token(), token('refresh_')
        expiry = now() + dt.timedelta(hours=1)
        query('Update Token in DB', clientId=client, accessToken=access,
              expiresAt=expiry, tokenExpiresAt=expiry, refreshToken=refresh,
              refreshExpiresAt=now() + dt.timedelta(days=30), salesforceUserId=user_id)
        return 200, dict(access_token=access, refresh_token=refresh, token_type='Bearer',
                         expires_in=3600, user_id=user_id, client_id=client, scope='read write')
    if path == '/auth/refresh-token':
        if not data.get('refresh_token'):
            return error(400, 'invalid_request', 'Refresh token is required')
        clients = query('Validate Refresh Token', refreshToken=data['refresh_token'], currentTime=now())
        if not clients:
            return error(401, 'invalid_grant', 'Invalid or expired refresh token')
        access, refresh = token(), token('refresh_')
        query('Update Tokens', clientId=clients[0]['client_id'], newAccessToken=access,
              newRefreshToken=refresh, tokenExpiresAt=now() + dt.timedelta(hours=1),
              refreshExpiresAt=now() + dt.timedelta(days=30))
        return 200, dict(access_token=access, refresh_token=refresh, token_type='Bearer', expires_in=3600)
    user = data.get('userId', data.get('salesforce_user_id', ''))
    client = data.get('clientId', data.get('client_id', ''))
    if not (user and client):
        return error(400, 'invalid_request', 'Missing required fields: userId and clientId')
    changed = query('Deactivate User Connection', salesforceUserId=user, clientId=client)
    return (200 if changed else 404), dict(
        status='success' if changed else 'not_found', userId=user, clientId=client,
        message='API connection disconnected successfully' if changed else 'No active API connection found for this user',
        timestamp=now().strftime('%Y-%m-%dT%H:%M:%SZ'))


EMPLOYEE_QUERIES = {
    'goals': 'Select Employee Goals', 'learning-status': 'Select Learning Status',
    'next-pay-date': 'Select Next Pay Date', 'pto/balance': 'Select PTO Balance',
    'pto/schedule': 'Insert or Update PTO Schedule',
}


def employee(employee_id, endpoint, data, header):
    # Only goals and learning call validate-token-subflow in the source XML.
    if endpoint in ('goals', 'learning-status'):
        failure = authenticate(header)
        if failure:
            return failure
    try:
        params = {'employeeId': employee_id}
        if endpoint == 'pto/schedule':
            params['endDate'] = data.get('endDate')
        rows = query(EMPLOYEE_QUERIES[endpoint], **params)
        if endpoint == 'goals':
            return 200, [r['goal'] for r in rows] if rows else {
                'message': 'No goals found for employee ' + employee_id}
        if endpoint == 'pto/schedule':
            return 200, dict(employeeId=employee_id, startDate=data.get('startDate'),
                             endDate=data.get('endDate'), status='success', message='PTO scheduled successfully')
        if not rows:
            messages = {'learning-status': 'Learning records not found',
                        'next-pay-date': 'Pay date not found', 'pto/balance': 'Employee PTO record not found'}
            return 404, dict(error=messages[endpoint], employeeId=employee_id)
        field, value = {
            'learning-status': ('learningStatus', rows),
            'next-pay-date': ('nextPayDate', rows[0].get('next_pay_date')),
            'pto/balance': ('ptoBalance', rows[0].get('pto_balance')),
        }[endpoint]
        return 200, dict(employeeId=employee_id, status='success', **{field: value})
    except psycopg.Error as exc:
        body = dict(error='Internal server error', employeeId=employee_id)
        status = 500
        if endpoint == 'pto/schedule':
            body['error'] = 'Failed to schedule PTO'
        elif endpoint in ('goals', 'pto/balance'):
            if isinstance(exc, psycopg.OperationalError):
                status = 503
                body.update(error='Database connection failed', details='Unable to connect to database')
            else:
                body.update(error='Database query failed', details=str(exc))
        return status, body


def encode(value):
    if isinstance(value, (dt.datetime, dt.date)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return float(value)
    raise TypeError(type(value).__name__)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        self.handle_request()

    def do_POST(self):
        self.handle_request()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Max-Age', '3600')
        self.end_headers()

    def handle_request(self):
        path = urllib.parse.urlsplit(self.path).path
        data = {}
        try:
            raw = self.rfile.read(int(self.headers.get('Content-Length', 0)))
            if raw:
                if 'application/x-www-form-urlencoded' in self.headers.get('Content-Type', ''):
                    data = dict(urllib.parse.parse_qsl(raw.decode()))
                else:
                    data = json.loads(raw)
            status, body = self.dispatch(path, data)
        except psycopg.Error as exc:
            if path == '/oauth/token':
                status, body = error(503 if isinstance(exc, psycopg.OperationalError) else 500,
                    'server_error', 'Database connection failed during authentication' if isinstance(exc, psycopg.OperationalError)
                    else 'Database error during authentication')
            else:
                context = {'/auth/register': ('registration_failed', 'registration'),
                           '/auth/login': ('login_failed', 'login'),
                           '/auth/refresh-token': ('server_error', 'token refresh'),
                           '/api/disconnect': ('server_error', 'disconnect')}.get(path, ('server_error', 'request'))
                status, body = error(500, context[0], 'Database error occurred during ' + context[1])
        except (ValueError, TypeError, KeyError, IndexError):
            status, body = error(500, 'server_error', 'An error occurred while processing the token request') if path == '/oauth/token' else (400, {'message': 'Bad request'})
        self.send_response(status)
        self.send_header('Content-Type', 'text/html' if isinstance(body, str) else 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write((body if isinstance(body, str) else json.dumps(body, default=encode)).encode())

    def dispatch(self, path, data):
        if path == '/health':
            try:
                query('Test DB Connection')
                return 200, dict(status='healthy', database='connected', timestamp=now().isoformat() + 'Z')
            except psycopg.Error:
                return 503, dict(status='unhealthy', database='disconnected', timestamp=now().isoformat() + 'Z')
        if path.startswith('/web/'):
            name = 'login' if path in ('/web/', '/web/login') else 'register' if path == '/web/register' else None
            return (200, Path('/app/web/' + name + '.html').read_text()) if name else (404, {'error': 'Page not found'})
        if path == '/oauth/token':
            return oauth(data, self.headers.get('Authorization', '')) if self.command == 'POST' else (405, {'message': 'Method not allowed'})
        if path in ('/auth/register', '/auth/login', '/auth/refresh-token', '/api/disconnect'):
            return auth(path, data) if self.command == 'POST' else (405, {'message': 'Method not allowed'})
        match = re.fullmatch(r'/api/employee/([^/]+)/(goals|learning-status|next-pay-date|pto/balance|pto/schedule)', path)
        if not match:
            return 404, {'message': 'Resource not found'}
        emp, endpoint = match.groups()
        if self.command != ('POST' if endpoint == 'pto/schedule' else 'GET'):
            return 405, {'message': 'Method not allowed'}
        if endpoint == 'pto/schedule' and 'application/json' not in self.headers.get('Content-Type', ''):
            return 415, {'message': 'Unsupported media type'}
        return employee(urllib.parse.unquote(emp), endpoint, data, self.headers.get('Authorization', ''))


if __name__ == '__main__':
    ThreadingHTTPServer(('0.0.0.0', 8081), Handler).serve_forever()
