import base64
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request
import json
import uuid

import app
from compare import compare, get_token, normalized, request

BASE = 'http://localhost:8081'


class Contract(unittest.TestCase):
    def test_oauth_and_database_validation(self):
        self.assertEqual(request(BASE, '/oauth/token', 'POST', {})[0], 401)
        first = get_token(BASE, 'demo_client', 'demo_secret')
        second = get_token(BASE, 'demo_client', 'demo_secret')
        self.assertEqual(request(BASE, '/api/employee/EMP001/goals', token=first)[0], 401)
        self.assertEqual(request(BASE, '/api/employee/EMP001/goals', token=second),
                         (200, ['Complete Q4 Sales Target']))
        app.query('Store Token in DB', clientId='demo_client', clientSecret='demo_secret',
                  accessToken=second, expiresAt=app.now() - app.dt.timedelta(seconds=1), callbackUrl=None)
        self.assertEqual(request(BASE, '/api/employee/EMP001/goals', token=second)[0], 401)

    def test_basic_and_form_credentials(self):
        credentials = base64.b64encode(b'demo_client:demo_secret').decode()
        req = urllib.request.Request(BASE + '/oauth/token', data=b'',
                                     headers={'Authorization': 'Basic ' + credentials})
        with urllib.request.urlopen(req) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(json.load(response)['expires_in'], 3600)
        req = urllib.request.Request(BASE + '/oauth/token',
            data=b'client_id=demo_client&client_secret=demo_secret',
            headers={'Content-Type': 'application/x-www-form-urlencoded'})
        with urllib.request.urlopen(req) as response:
            self.assertEqual(response.status, 200)

    def test_endpoint_auth_gates(self):
        for endpoint in ('goals', 'learning-status'):
            self.assertEqual(request(BASE, '/api/employee/EMP001/' + endpoint),
                             (401, {'error': 'missing_token',
                                    'error_description': 'Authorization header is missing or invalid'}))
        self.assertEqual(request(BASE, '/api/employee/EMP001/pto/balance'),
                         (200, {'employeeId': 'EMP001', 'status': 'success', 'ptoBalance': 120}))

    def test_missing_employee_and_empty_goals(self):
        access = get_token(BASE, 'demo_client', 'demo_secret')
        self.assertEqual(request(BASE, '/api/employee/ABSENT/goals', token=access),
                         (200, {'message': 'No goals found for employee ABSENT'}))
        for endpoint, message in [('learning-status', 'Learning records not found'),
                                  ('next-pay-date', 'Pay date not found'),
                                  ('pto/balance', 'Employee PTO record not found')]:
            self.assertEqual(request(BASE, '/api/employee/ABSENT/' + endpoint, token=access),
                             (404, {'error': message, 'employeeId': 'ABSENT'}))

    def test_learning_shape_and_null_balance(self):
        access = get_token(BASE, 'demo_client', 'demo_secret')
        self.assertEqual(request(BASE, '/api/employee/EMP001/learning-status', token=access),
            (200, {'employeeId': 'EMP001', 'status': 'success', 'learningStatus':
                   [{'course': 'Advanced Sales Techniques', 'status': 'In Progress'}]}))
        self.assertEqual(request(BASE, '/api/employee/EMP002/pto/balance')[1]['ptoBalance'], 0)
        self.assertIsNone(request(BASE, '/api/employee/EMP002/next-pay-date')[1]['nextPayDate'])

    def test_schedule_mutation_and_error(self):
        status, body = request(BASE, '/api/employee/EMP001/pto/schedule', 'POST',
                               {'startDate': '2024-02-05', 'endDate': '2024-02-09'})
        self.assertEqual(status, 200)
        self.assertEqual(body['message'], 'PTO scheduled successfully')
        self.assertEqual(request(BASE, '/api/employee/EMP001/next-pay-date')[1]['nextPayDate'], '2024-02-09')
        self.assertEqual(request(BASE, '/api/employee/EMP001/pto/balance')[1]['ptoBalance'], 120)
        self.assertEqual(request(BASE, '/api/employee/EMP001/pto/schedule', 'POST', {'endDate': 'bad'}),
                         (500, {'error': 'Failed to schedule PTO', 'employeeId': 'EMP001'}))

    def test_database_error_mapping(self):
        for endpoint in ('goals', 'pto/balance'):
            with patch.object(app, 'authenticate', return_value=None), patch.object(
                    app, 'query', side_effect=app.psycopg.OperationalError('offline')):
                self.assertEqual(app.employee('EMP001', endpoint, {}, '')[0], 503)
        with patch.object(app, 'query', side_effect=app.psycopg.OperationalError('offline')):
            self.assertEqual(app.authenticate('Bearer synthetic'),
                             (401, {'error': 'invalid_token', 'error_description': 'Token validation failed'}))

    def test_registration_login_refresh_disconnect(self):
        username = 'fixture_' + uuid.uuid4().hex
        data = {'username': username, 'email': username + '@example.invalid',
                'password': 'synthetic', 'firstName': 'Test', 'lastName': 'User'}
        self.assertEqual(request(BASE, '/auth/register', 'POST', {})[0], 400)
        self.assertEqual(request(BASE, '/auth/register', 'POST', data)[0], 201)
        self.assertEqual(request(BASE, '/auth/register', 'POST', data)[0], 409)
        login = {'username': username, 'password': 'synthetic', 'clientId': username, 'userId': username}
        status, body = request(BASE, '/auth/login', 'POST', login)
        self.assertEqual(status, 200)
        self.assertEqual(request(BASE, '/auth/refresh-token', 'POST', {'refresh_token': 'bad'})[0], 401)
        self.assertEqual(request(BASE, '/auth/refresh-token', 'POST',
                                 {'refresh_token': body['refresh_token']})[0], 200)
        self.assertEqual(request(BASE, '/api/disconnect', 'POST',
                                 {'clientId': username, 'userId': username})[0], 200)

    def test_comparator_normalization_and_failures(self):
        self.assertEqual(normalized((200, {'b': 2, 'a': 1})), normalized((200, {'a': 1, 'b': 2})))
        self.assertNotEqual(normalized((200, [1, 2])), normalized((200, [2, 1])))
        with patch('compare.get_token', return_value='synthetic'), patch('compare.request',
                side_effect=[(200, {}) , (404, {})] * 5):
            self.assertFalse(any(row[4] for row in compare(BASE, BASE, ['EMP001'], [('x', 'x')] * 2)))
        with patch('compare.get_token', side_effect=OSError('offline')):
            self.assertFalse(any(row[4] for row in compare(BASE, BASE, ['EMP001'], [('x', 'x')] * 2)))


if __name__ == '__main__':
    unittest.main()
