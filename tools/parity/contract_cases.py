#!/usr/bin/env python3
"""Compare fixed edge/auth contracts between disposable employee API fixtures."""
import argparse
import base64
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request
import uuid

from compare import ENDPOINTS, get_token

TOKEN = r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}-\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?Z'
TIMESTAMP = r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?Z'


def request(base, path, method='GET', data=None, headers=None, raw=None):
    headers = {'Content-Type': 'application/json', **(headers or {})}
    payload = raw if raw is not None else None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(base.rstrip('/') + path, data=payload, headers=headers, method=method)
    try:
        response = urllib.request.urlopen(req, timeout=10)
    except urllib.error.HTTPError as exc:
        response = exc
    with response:
        text = response.read().decode()
        body = json.loads(text) if text and response.headers.get('Content-Type') == 'application/json' else text
        cors = {k: response.headers.get(k) for k in (
            'Access-Control-Allow-Origin', 'Access-Control-Allow-Methods',
            'Access-Control-Allow-Headers', 'Access-Control-Max-Age')}
        return response.status, body, response.headers.get('Content-Type'), cors


def normalize(response, username):
    status, body, content_type, cors = response
    if isinstance(body, dict):
        body = body.copy()
        for field, pattern in [('access_token', TOKEN), ('refresh_token', 'refresh_' + TOKEN),
                               ('timestamp', TIMESTAMP)]:
            if field in body:
                if not isinstance(body[field], str) or not re.fullmatch(pattern, body[field]):
                    raise ValueError('Invalid shape: ' + field)
                body[field] = '<' + field + ':valid-shape>'
        for field in ('username', 'user_id', 'userId', 'client_id', 'clientId'):
            if field in body and body[field] == username:
                if not re.fullmatch(r'fixture_[0-9a-f]{32}', body[field]):
                    raise ValueError('Invalid generated username')
                body[field] = '<generated-username:valid-shape>'
    return status, json.dumps(body, sort_keys=True, separators=(',', ':'), ensure_ascii=False), content_type, cors


def cases(base, client, secret):
    username = 'fixture_' + uuid.uuid4().hex
    results = []

    def add(name, path, method='GET', data=None, headers=None, raw=None):
        response = request(base, path, method, data, headers, raw)
        results.append((name, normalize(response, username)))
        return response[1]

    for endpoint in ('goals', 'learning-status'):
        path = '/api/employee/EMP001/' + endpoint
        add(endpoint + ': missing token', path)
        add(endpoint + ': malformed bearer', path, headers={'Authorization': 'bearer invalid'})
        add(endpoint + ': invalid token', path, headers={'Authorization': 'Bearer invalid'})
        expired = get_token(base, client, secret)
        get_token(base, client, secret)
        add(endpoint + ': replaced token', path, headers={'Authorization': 'Bearer ' + expired})
    for endpoint in ('next-pay-date', 'pto/balance', 'pto/schedule'):
        add(endpoint + ': no token', '/api/employee/EMP001/' + endpoint,
            'POST' if endpoint == 'pto/schedule' else 'GET',
            {'startDate': 'ignored', 'endDate': '2024-02-09'} if endpoint == 'pto/schedule' else None)
    for endpoint in ENDPOINTS:
        token = get_token(base, client, secret)
        add(endpoint + ': ABSENT', '/api/employee/ABSENT/' + endpoint,
            'POST' if endpoint == 'pto/schedule' else 'GET',
            {'endDate': '2024-02-09'} if endpoint == 'pto/schedule' else None,
            {'Authorization': 'Bearer ' + token})
    add('wrong employee method', '/api/employee/EMP001/goals', 'POST', {})
    add('wrong auth method', '/auth/login')
    add('schedule text/plain', '/api/employee/EMP001/pto/schedule', 'POST', {}, {'Content-Type': 'text/plain'})
    add('schedule bad date', '/api/employee/EMP001/pto/schedule', 'POST', {'endDate': 'bad'})
    add('unknown route', '/unknown')
    add('bad JSON', '/auth/register', 'POST', raw=b'{')
    add('oauth bad JSON', '/oauth/token', 'POST', raw=b'{')
    add('oauth bad client', '/oauth/token', 'POST', {'client_id': 'bad', 'client_secret': 'bad'})
    form = urllib.parse.urlencode({'client_id': client, 'client_secret': secret}).encode()
    add('oauth form', '/oauth/token', 'POST', headers={'Content-Type': 'application/x-www-form-urlencoded'}, raw=form)
    basic = base64.b64encode((client + ':' + secret).encode()).decode()
    add('oauth Basic', '/oauth/token', 'POST', headers={'Authorization': 'Basic ' + basic}, raw=b'')
    add('oauth malformed Basic', '/oauth/token', 'POST', headers={'Authorization': 'Basic !!!'}, raw=b'')
    add('health', '/health')
    for path in ('/web/', '/web/login', '/web/register', '/web/missing'):
        add(path, path)
    add('register missing', '/auth/register', 'POST', {})
    user = {'username': username, 'email': username + '@example.invalid', 'password': 'synthetic',
            'firstName': 'Test', 'lastName': 'User'}
    add('register created', '/auth/register', 'POST', user)
    add('register duplicate', '/auth/register', 'POST', user)
    add('login missing', '/auth/login', 'POST', {})
    for label, value in [('zero int', 0), ('zero float', 0.0), ('empty string', ''),
                         ('empty list', []), ('empty map', {}), ('false', False), ('null', None)]:
        add('login clientId ' + label, '/auth/login', 'POST',
            {'username': username, 'password': 'synthetic', 'clientId': value})
    login = {'username': username, 'password': 'bad', 'clientId': username, 'userId': username}
    add('login wrong password', '/auth/login', 'POST', login)
    login['password'] = 'synthetic'
    body = add('login success', '/auth/login', 'POST', login)
    add('refresh missing', '/auth/refresh-token', 'POST', {})
    add('refresh invalid', '/auth/refresh-token', 'POST', {'refresh_token': 'bad'})
    add('refresh success', '/auth/refresh-token', 'POST', {'refresh_token': body['refresh_token']})
    add('disconnect missing', '/api/disconnect', 'POST', {})
    add('disconnect success', '/api/disconnect', 'POST', {'clientId': username, 'userId': username})
    add('disconnect absent', '/api/disconnect', 'POST', {'clientId': username, 'userId': username})
    add('OPTIONS', '/api/employee/EMP001/goals', 'OPTIONS')
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('old')
    parser.add_argument('new')
    parser.add_argument('--output', type=Path, default=Path('contract-parity.md'))
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()
    try:
        results = [cases(base, os.getenv(prefix + '_CLIENT_ID', 'demo_client'),
                         os.getenv(prefix + '_CLIENT_SECRET', 'demo_secret'))
                   for base, prefix in ((args.old, 'OLD'), (args.new, 'NEW'))]
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        print('Contract comparison failed: ' + type(exc).__name__, file=sys.stderr)
        return 1
    report = ['| Case | Old HTTP | New HTTP | Result |', '| --- | --- | --- | --- |']
    matches = 0
    for (name, old), (new_name, new) in zip(*results):
        ok = name == new_name and old == new
        matches += ok
        report.append(f'| {name} | {old[0]} | {new[0]} | {"MATCH" if ok else "MISMATCH"} |')
        if args.verbose and not ok:
            print(name, old, new)
    report.append(f'\n{matches}/{len(results[0])} matches.')
    report.append('\nMasks: access_token (UUIDv4 + UTC timestamp), refresh_token (refresh_ + same shape), '
                  'timestamp (UTC ISO); generated username echoes only in username/user_id/userId/client_id/clientId. '
                  'Every masked value must match its shape. No other fields masked. '
                  'Content-Type and CORS headers compared; static HTML compared unchanged.')
    args.output.write_text('\n'.join(report) + '\n')
    print('\n'.join(report))
    return 0 if matches == len(results[0]) else 1


if __name__ == '__main__':
    sys.exit(main())
