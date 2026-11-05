import unittest
from unittest.mock import patch

from compare import compare
from contract_cases import normalize


class Comparators(unittest.TestCase):
    def test_filter_keeps_post_last(self):
        with patch('compare.get_token', return_value='token'), patch(
                'compare.request', return_value=(200, {})) as request:
            rows = compare('old', 'new', ['EMP001'], [('x', 'y')] * 2,
                           endpoints=['pto/schedule', 'goals'])
        self.assertEqual([row[1] for row in rows], ['goals', 'pto/schedule'])
        self.assertEqual([c.args[2] for c in request.call_args_list], ['GET', 'GET', 'POST', 'POST'])

    def test_empty_filter(self):
        self.assertEqual(compare('old', 'new', ['EMP001'], [], endpoints=[]), [])

    def test_transport_failure(self):
        with patch('compare.get_token', side_effect=OSError('offline')):
            rows = compare('old', 'new', ['EMP001'], [('x', 'y')] * 2, endpoints=['goals'])
        self.assertFalse(rows[0][4])

    def test_masks_require_shapes_and_preserve_other_values(self):
        user = 'fixture_' + 'a' * 32
        base = (200, {'username': user, 'timestamp': '2024-01-01T12:00:00Z',
                      'access_token': '12345678-1234-4123-8123-123456789abc-2024-01-01T12:00:00.123456Z',
                      'expires_in': 3600}, 'application/json', {})
        value = normalize(base, user)
        self.assertIn('valid-shape', value[1])
        self.assertIn('3600', value[1])
        with self.assertRaises(ValueError):
            normalize((200, {'access_token': 'anything'}, 'application/json', {}), user)
        self.assertNotEqual(value, normalize((201, base[1], base[2], base[3]), user))
        self.assertNotEqual(value, normalize((200, base[1], 'text/html', base[3]), user))

    def test_empty_and_array_response(self):
        self.assertEqual(normalize((200, '', None, {}), ''), (200, '""', None, {}))
        self.assertNotEqual(normalize((200, [1, 2], None, {}), ''),
                            normalize((200, [2, 1], None, {}), ''))


if __name__ == '__main__':
    unittest.main()
