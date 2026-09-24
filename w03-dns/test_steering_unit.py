import unittest
from unittest.mock import patch
import dns.message
import dns.rrset
import task2_steering as m


def response(name, kind, answer=(), authority=()):
    msg = dns.message.make_response(dns.message.make_query(name, kind))
    for section, rows in [(msg.answer, answer), (msg.authority, authority)]:
        for owner, rtype, value in rows:
            section.append(dns.rrset.from_text(owner, 60, 'IN', rtype, value))
    return msg


class SteeringTests(unittest.TestCase):
    def test_complete_chain_and_zone(self):
        replies = [response('www.example.', 'A', [('www.example.', 'CNAME', 'edge.other.')]),
                   response('edge.other.', 'A', [('edge.other.', 'A', '192.0.2.1')]),
                   response('edge.other.', 'SOA', authority=[('other.', 'SOA', 'ns.other. hostmaster.other. 1 2 3 4 5')])]
        with patch.object(m, 'exchange', side_effect=replies):
            result = m.measure('www.example', 'google', ['8.8.8.8'], 'test', 'test')
        self.assertEqual(result['chain'], ['www.example', 'edge.other'])
        self.assertEqual(result['final_zone'], 'other')
        self.assertEqual(result['addresses'], ['192.0.2.1'])

    def test_loop_and_timeout_are_not_empty_success(self):
        loop = response('www.example.', 'A', [('www.example.', 'CNAME', 'www.example.')])
        with patch.object(m, 'exchange', return_value=loop):
            self.assertEqual(m.measure('www.example', 'google', ['8.8.8.8'], 'test', 'test')['status'], 'error')
        with patch.object(m, 'exchange', side_effect=RuntimeError('timeout')):
            self.assertEqual(m.measure('www.example', 'google', ['8.8.8.8'], 'test', 'test')['status'], 'error')

    def test_same_operator_false_positive(self):
        naive, verdict, cdn, _ = m.classify('www.wikipedia.org', ['www.wikipedia.org', 'dyna.wikimedia.org'])
        self.assertTrue(naive)
        self.assertTrue(cdn)
        self.assertTrue(verdict.startswith('아니오'))


if __name__ == '__main__':
    unittest.main()
