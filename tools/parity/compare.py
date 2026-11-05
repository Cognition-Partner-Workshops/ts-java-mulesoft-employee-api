#!/usr/bin/env python3
"""Compare employee endpoint status and JSON without masking contract differences."""
import argparse
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.parse
import urllib.request

ENDPOINTS = ['goals', 'learning-status', 'next-pay-date', 'pto/balance', 'pto/schedule']
EMPLOYEES = ['EMP001', 'EMP002', 'EMP003']


def request(base, path, method='GET', data=None, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    req = urllib.request.Request(base.rstrip('/') + path, method=method, headers=headers,
                                 data=None if data is None else json.dumps(data).encode())
    try:
        response = urllib.request.urlopen(req, timeout=10)
    except urllib.error.HTTPError as exc:
        response = exc
    with response:
        raw = response.read().decode()
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = {'nonJsonBody': raw}
        return response.status, body


def get_token(base, client, secret):
    status, body = request(base, '/oauth/token', 'POST',
                           {'client_id': client, 'client_secret': secret, 'grant_type': 'client_credentials'})
    if status != 200 or not body.get('access_token'):
        raise RuntimeError(f'Token request failed: HTTP {status}')
    return body['access_token']


def normalized(response):
    # Object key order and JSON whitespace are immaterial; array order is not.
    return response[0], json.dumps(response[1], sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def compare(old, new, employees, credentials, verbose=False):
    rows = []
    for emp in employees:
        for endpoint in ENDPOINTS:
            path = '/api/employee/' + urllib.parse.quote(emp, safe='') + '/' + endpoint
            method = 'POST' if endpoint == 'pto/schedule' else 'GET'
            data = {'startDate': '2024-02-05', 'endDate': '2024-02-09'} if method == 'POST' else None
            results = []
            for base, (client, secret) in zip((old, new), credentials):
                try:
                    # Acquire immediately before use: same-URL comparisons must not
                    # invalidate the first side's token by issuing the second first.
                    access = get_token(base, client, secret)
                    results.append(request(base, path, method, data, access))
                except (OSError, ValueError, RuntimeError) as exc:
                    results.append((0, {'transportError': type(exc).__name__}))
            # A 401 on an employee call means the token check failed, so the row proves nothing.
            matched = all(r[0] not in (0, 401) for r in results) and normalized(results[0]) == normalized(results[1])
            rows.append((emp, endpoint, results[0][0], results[1][0], matched))
            if verbose:
                print(f'{method} {path}: {results[0][0]} {json.dumps(results[0][1], sort_keys=True)}')
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('old')
    parser.add_argument('new')
    parser.add_argument('--employees', nargs='+', default=EMPLOYEES)
    parser.add_argument('--output', type=Path, default=Path('parity-report.md'))
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()
    credentials = [(os.getenv(prefix + '_CLIENT_ID', 'demo_client'),
                    os.getenv(prefix + '_CLIENT_SECRET', 'demo_secret')) for prefix in ('OLD', 'NEW')]
    rows = compare(args.old, args.new, args.employees, credentials, args.verbose)
    matches = sum(r[4] for r in rows)
    report = ['| Employee | Endpoint | Old HTTP | New HTTP | Result |',
              '| --- | --- | --- | --- | --- |']
    report.extend(f'| {emp} | {endpoint} | {old} | {new} | {"MATCH" if ok else "MISMATCH"} |'
                  for emp, endpoint, old, new, ok in rows)
    report.append(f'\n{matches}/{len(rows)} matches ({100 * matches / len(rows):.0f}%).')
    args.output.write_text('\n'.join(report) + '\n')
    print('\n'.join(report))
    return 0 if matches == len(rows) else 1


if __name__ == '__main__':
    sys.exit(main())
