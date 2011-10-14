"""
IP-based authentication plugin for pyramid.
"""

import re
import socket

from zope.interface import implements
from pyramid.interfaces import IAuthenticationPolicy
from pyramid.security import Everyone, Authenticated

from netaddr import IPAddress, IPNetwork, IPGlob, IPRange, IPSet


class IPAuthenticationPolicy(object):
    """An IP-based authentication policy for pyramid.

    This pyramid authentication policy assigns userid and/or effective
    principals based on the originating IP address of the request.

    You must specify a set of IP addresses against which to match, and may
    specify a userid and/or list of principals to apply.  For example, the
    following would authenticate all requests from the 192.168.0.* range as
    userid "myuser":

        IPAuthenticationPolicy(["192.168.0.0/24"], "myuser")

    The following would not authenticate as a particular userid, but would add
    "local" as an effective principal for the request (along with Everyone
    and Authenticated):

        IPAuthenticationPolicy(["127.0.0.0/24"], principals=["local"])

    By default this policy does not respect the X-Forwarded-For header since
    it can be easily spoofed.  If you want to respect X-Forwarded-For then you
    must specify a list of trusted proxies, and only forwarding declarations
    from these proxies will be respected:

        IPAuthenticationPolicy(["192.168.0.0/24"], "myuser",
                               proxies=["192.168.0.2"])

    """

    implements(IAuthenticationPolicy)

    def __init__(self, ipaddrs, userid=None, principals=None, proxies=None):
        self.ipaddrs = make_ip_set(ipaddrs)
        self.userid = userid
        self.principals = principals
        self.proxies = make_ip_set(proxies)

    def authenticated_userid(self, request):
        return self.unauthenticated_userid(request)

    def unauthenticated_userid(self, request):
        if not check_ip_address(request, self.ipaddrs, self.proxies):
            return None
        return self.userid

    def effective_principals(self, request):
        principals = [Everyone]
        if check_ip_address(request, self.ipaddrs, self.proxies):
            if self.userid is not None:
                principals.insert(0, self.userid)
            principals.append(Authenticated)
            if self.principals is not None:
                principals.extend(self.principals)
        return principals

    def remember(self, request, principal, **kw):
        pass

    def forget(self, request):
        pass


def get_ip_address(request, proxies=None):
    """Get the originating IP address from the given request.

    This function resolves and returns the originating IP address of the
    given request, by looking up the REMOTE_ADDR and HTTP_X_FORWARDED_FOR
    entries from the request environment.

    If the "proxies" argument is not specified, then the X-Forwarded-For
    header is ignored and REMOTE_ADDR is returned directly.  If "proxies" is
    given then it must be an IPAddrSet listing trusted proxies.  The entries
    in X-Forwarded-For will be traversed back through trusted proxies, stopping
    stopping either at the first untrusted proxy or at the claimed original IP.
    """
    if proxies is None:
        proxies = IPSet()
    elif not isinstance(proxies, IPSet):
        proxies = make_ip_set(proxies)
    # Get the chain of proxied IP addresses, most recent proxy last.
    addr_chain = []
    try:
        xff = request.environ["HTTP_X_FORWARDED_FOR"]
    except KeyError:
        pass
    else:
        addr_chain.extend(IPAddress(a.strip()) for a in xff.split(","))
    addr_chain.append(IPAddress(request.environ["REMOTE_ADDR"]))
    # Pop trusted proxies from the list until we get the original addr,
    # or until we hit an untrusted proxy.
    while len(addr_chain) > 1:
        addr = addr_chain.pop()
        if addr not in proxies:
            return addr
    return addr_chain[0]


def check_ip_address(request, ipaddrs, proxies=None):
    """Check whether request originated within the given ip addresses.

    This function checks whether the originating IP address of the request
    is within the given set of IP addresses.  If given, the argument
    "proxies" must be a set of trusted proxy IP addresses, which will be
    used to determine the originating IP as per the get_ip_address function.
    """
    if not isinstance(ipaddrs, IPSet):
        ipaddrs = make_ip_set(ipaddrs)
    ipaddr = get_ip_address(request, proxies)
    return (ipaddr in ipaddrs)


#  This is used to split a string on an optional comma,
#  followed by any amount of whitespace.
_COMMA_OR_WHITESPACE = re.compile(r",?\s*")


def make_ip_set(ipaddrs):
    """Parse a variety of IP specifications into an IPSet object.

    This is a convenience function that allows you to specify a set of
    IP addresses in a variety of ways:

        * as an IPSet, IPAddress, IPNetwork, IPGlob or IPRange object
        * as the literal None for the empty set
        * as an int parsable by IPAddress
        * as a string parsable by make_ip_set
        * as an iterable of IP specifications

    """
    # If it's already an IPSet, well, that's easy.
    if isinstance(ipaddrs, IPSet):
        return ipaddrs
    # None represents the empty set.
    if ipaddrs is None:
        return IPSet()
    # Integers represent a single address.
    if isinstance(ipaddrs, (int, long)):
        return IPSet((IPAddress(ipaddrs),))
    # Strings get parsed as per make_ip_set
    if isinstance(ipaddrs, basestring):
        return parse_ip_set(ipaddrs)
    # Other netaddr types can be converted into a set.
    if isinstance(ipaddrs, (IPAddress, IPNetwork)):
        return IPSet((ipaddrs,))
    if isinstance(ipaddrs, (IPGlob, IPRange)):
        return IPSet(ipaddrs.cidrs())
    # Anything iterable can be mapped over and unioned.
    try:
        ipspecs = iter(ipaddrs)
    except Exception:
        pass
    else:
        ipset = IPSet()
        for ipspec in ipspecs:
            ipset |= make_ip_set(ipspec)
        return ipset
    # Anything else is an error
    raise ValueError("can't convert to IPSet: %r" % (ipaddrs,))


def parse_ip_set(ipaddrs):
    """Parse a string specification into an IPSet.

    This function takes a string representing a set of IP addresses, and
    parses it into an IPSet object.  Acceptable formats for the string
    include:

        * "all":        all possible IPv4 and IPv6 addresses
        * "local":      all local addresses of the machine
        * "A.B.C.D"     a single IP address
        * "A.B.C.D/N"   a network address specification
        * "A.B.C.*"     a glob matching against all possible numbers
        * "A.B.C.D-E"   a glob matching against a range of numbers
        * a whitespace- or comma-separated string of the above

    """
    ipset = IPSet()
    ipaddrs = ipaddrs.lower().strip()
    if not ipaddrs:
        return ipset
    for ipspec in _COMMA_OR_WHITESPACE.split(ipaddrs):
        # The string "local" maps to all local addresses on the machine.
        if ipspec == "local":
            ipset.add(IPNetwork("127.0.0.0/8"))
            for addr in get_local_ip_addresses():
                ipset.add(addr)
        # The string "all" maps to app IPv4 and IPv6 addresses.
        elif ipspec == "all":
            ipset.add(IPNetwork("0.0.0.0/0"))
            ipset.add(IPNetwork("::"))
        # Strings containing a "/" are assumed to be network specs
        elif "/" in ipspec:
            ipset.add(IPNetwork(ipspec))
        # Strings containing a "*" or "-" are assumed to be glob patterns
        elif "*" in ipspec or "-" in ipspec:
            for cidr in IPGlob(ipspec).cidrs():
                ipset.add(cidr)
        # Anything else must be a single address
        else:
            ipset.add(IPAddress(ipspec))
    return ipset


def get_local_ip_addresses():
    """Iterator yielding all local IP addresses on the machine."""
    # XXX: how can we enumerate all interfaces on the machine?
    # I don't really want to shell out to `ifconfig`
    for addr in socket.gethostbyname_ex(socket.gethostname())[2]:
        yield IPAddress(addr)
