import unittest
import socket

from pyramid.testing import DummyRequest
from pyramid.security import Everyone, Authenticated

from cornice.auth.ipauth import IPAuthenticationPolicy, make_ip_set, IPAddress


class IPAuthPolicyTests(unittest.TestCase):

    def test_remote_addr(self):
        policy = IPAuthenticationPolicy(["123.123.0.0/16"], "user")
        # Addresses outside the range don't authenticate
        request = DummyRequest(environ={"REMOTE_ADDR": "192.168.0.1"})
        self.assertEquals(policy.authenticated_userid(request), None)
        # Addresses inside the range do authenticate
        request = DummyRequest(environ={"REMOTE_ADDR": "123.123.0.1"})
        self.assertEquals(policy.authenticated_userid(request), "user")
        request = DummyRequest(environ={"REMOTE_ADDR": "123.123.1.2"})
        self.assertEquals(policy.authenticated_userid(request), "user")

    def test_noncontiguous_ranges(self):
        policy = IPAuthenticationPolicy(["123.123.0.0/16", "124.124.1.0/24"],
                                        "user")
        # Addresses outside the range don't authenticate
        request = DummyRequest(environ={"REMOTE_ADDR": "192.168.0.1"})
        self.assertEquals(policy.authenticated_userid(request), None)
        request = DummyRequest(environ={"REMOTE_ADDR": "124.124.0.1"})
        self.assertEquals(policy.authenticated_userid(request), None)
        # Addresses inside the range do authenticate
        request = DummyRequest(environ={"REMOTE_ADDR": "123.123.0.1"})
        self.assertEquals(policy.authenticated_userid(request), "user")
        request = DummyRequest(environ={"REMOTE_ADDR": "124.124.1.2"})
        self.assertEquals(policy.authenticated_userid(request), "user")

    def test_x_forwarded_for(self):
        policy = IPAuthenticationPolicy(["123.123.0.0/16"], "user",
                              proxies=["124.124.0.0/24"])
        # Requests without X-Forwarded-For work as normal
        request = DummyRequest(environ={"REMOTE_ADDR": "192.168.0.1"})
        self.assertEquals(policy.authenticated_userid(request), None)
        request = DummyRequest(environ={"REMOTE_ADDR": "123.123.0.1"})
        self.assertEquals(policy.authenticated_userid(request), "user")
        # Requests with untrusted X-Forwarded-For don't authenticate
        request = DummyRequest(environ={"REMOTE_ADDR": "192.168.0.1",
                               "HTTP_X_FORWARDED_FOR": "123.123.0.1"})
        self.assertEquals(policy.authenticated_userid(request), None)
        # Requests from single trusted proxy do authenticate
        request = DummyRequest(environ={"REMOTE_ADDR": "124.124.0.1",
                               "HTTP_X_FORWARDED_FOR": "123.123.0.1"})
        self.assertEquals(policy.authenticated_userid(request), "user")
        # Requests from chain of trusted proxies do authenticate
        request = DummyRequest(environ={"REMOTE_ADDR": "124.124.0.2",
                          "HTTP_X_FORWARDED_FOR": "123.123.0.1, 124.124.0.1"})
        self.assertEquals(policy.authenticated_userid(request), "user")
        # Requests with untrusted proxy in chain don't authenticate
        request = DummyRequest(environ={"REMOTE_ADDR": "124.124.0.1",
                          "HTTP_X_FORWARDED_FOR": "123.123.0.1, 192.168.0.1"})
        self.assertEquals(policy.authenticated_userid(request), None)

    def test_principals(self):
        policy = IPAuthenticationPolicy(["123.123.0.0/16"],
                                        principals=["test"])
        # Addresses outside the range don't get metadata set
        request = DummyRequest(environ={"REMOTE_ADDR": "192.168.0.1"})
        self.assertEquals(policy.effective_principals(request), [Everyone])
        # Addresses inside the range do get metadata set
        request = DummyRequest(environ={"REMOTE_ADDR": "123.123.0.1"})
        self.assertEquals(policy.effective_principals(request),
                          [Everyone, Authenticated, "test"])

    def test_make_ip_set(self):
        def is_in(ipaddr, ipset):
            ipset = make_ip_set(ipset)
            return IPAddress(ipaddr) in ipset
        #  Test individual IPs
        self.assertTrue(is_in("127.0.0.1", "127.0.0.1"))
        self.assertFalse(is_in("127.0.0.2", "127.0.0.1"))
        #  Test globbing
        self.assertTrue(is_in("127.0.0.1", "127.0.0.*"))
        self.assertTrue(is_in("127.0.1.2", "127.0.*.*"))
        self.assertTrue(is_in("127.0.0.1", "127.0.0.*"))
        self.assertFalse(is_in("127.0.1.2", "127.0.0.*"))
        self.assertTrue(is_in("127.0.0.1", "127.0.0.1-5"))
        self.assertTrue(is_in("127.0.0.5", "127.0.0.1-5"))
        self.assertFalse(is_in("127.0.0.6", "127.0.0.1-5"))
        #  Test networks
        self.assertTrue(is_in("127.0.0.1", "127.0.0.0/8"))
        self.assertTrue(is_in("127.0.0.1", "127.0.0.0/16"))
        self.assertTrue(is_in("127.0.0.1", "127.0.0.0/24"))
        self.assertFalse(is_in("127.0.1.2", "127.0.0.0/24"))
        #  Test literal None
        self.assertFalse(is_in("127.0.0.1", None))
        #  Test special strings
        self.assertTrue(is_in("127.0.0.1", "local"))
        self.assertTrue(is_in("127.0.0.1", "all"))
        try:
            goog_ip = socket.gethostbyname("www.google.com")
        except socket.error:
            pass
        else:
            self.assertFalse(is_in(goog_ip, "local"))
            self.assertTrue(is_in(goog_ip, "all"))
        #  Test with a list of stuff
        ips = ["127.0.0.1", "127.0.1.*"]
        self.assertTrue(is_in("127.0.0.1", ips))
        self.assertTrue(is_in("127.0.1.1", ips))
        self.assertFalse(is_in("127.0.0.2", ips))
        self.assertTrue(is_in("127.0.1.2", ips))
        #  Test with a string-list of stuff
        ips = "123.123.0.0/16 local"
        self.assertTrue(is_in("127.0.0.1", ips))
        self.assertTrue(is_in("127.0.1.1", ips))
        self.assertTrue(is_in("123.123.1.1", ips))
        self.assertFalse(is_in("124.0.0.1", ips))
