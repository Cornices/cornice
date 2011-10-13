
import re
import socket

from zope.interface import implements
from pyramid.interfaces import IAuthenticationPolicy
from pyramid.security import Everyone, Authenticated

from netaddr import IPAddress, IPNetwork, IPGlob, IPRange, IPSet


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
        proxies = parse_ip_set(proxies)
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
        ipaddrs = parse_ip_set(ipaddrs)
    ipaddr = get_ip_address(request, proxies)
    return (ipaddr in ipaddrs)


_COMMA_OR_WHITESPACE = re.compile(r"[,\s]")

def parse_ip_set(ipaddrs):
    """Parse a variety of IP specifications into an IPSet object.

    This is a convenience function that allows you to specify a set of
    IP addresses in a variety of ways:

        * as an IPSet, IPAddress, IPNetwork, IPGlob or IPRange object
        * as a string parsable by any of the above:
            * A.B.C.D            <- IPAddress
            * A.B.C.D/N          <- IPNetwork
            * A.B.C.*            <- IPGlob
            * A.B.C.D-A.B.C.E    <- IPRange
        * as an int parsable by IPAddress
        * as the special strings "local" or "all"
        * the literal None for the empty set
        * as a whitespace- or comma-separated string of IP specifications
        * as an iterable of IP specifications

    """
    # convert other things into one of the netaddr types
    if ipaddrs is None:
        ipaddrs = IPSet()
    elif isinstance(ipaddrs, (int, long)):
        ipaddrs = IPAddress(ipaddrs)
    elif isinstance(ipaddrs, basestring):
        if ipaddrs == "local":
            ipaddrs = IPSet((IPNetwork("127.0.0.0/8"),))
            # XXX: can we enumerate all interfaces on the machine?
            # or should this just be the interface the server is on?
            localaddrs = socket.gethostbyname_ex(socket.gethostname())[2]
            for localaddr in localaddrs:
                ipaddrs.add(IPAddress(localaddr))
        elif ipaddrs == "all":
            ipaddrs = IPSet((IPNetwork("0.0.0.0/0"),))
            ipaddrs.add(IPNetwork("::"))
        else:
            ipspecs = _COMMA_OR_WHITESPACE.split(ipaddrs)
            ipaddrs = IPSet()
            for ipspec in ipspecs:
                ipspec = ipspec.strip()
                if ipspec:
                    if "/" in ipspec:
                        ipaddrs.add(IPNetwork(ipspec))
                    elif "*" in ipspec:
                        for cidr in IPGlob(ipspec).cidrs():
                            ipaddrs.add(cidr)
                    elif "-" in ipspec:
                        start, end = ipspec.split("-", 1)
                        for cidr in IPRange(start, end).cidrs():
                            ipaddrs.add(cidr)
                    else:
                        ipaddrs.add(IPAddress(ipspec))
    # convert the other netaddr types into an IPSet
    if isinstance(ipaddrs, (IPAddress, IPNetwork)):
        return IPSet((ipaddrs,))
    if isinstance(ipaddrs, (IPGlob, IPRange)):
        return IPSet(ipaddrs.cidrs())
    if isinstance(ipaddrs, IPSet):
        return ipaddrs
    # if it's a generic iterable, try to map over it
    try:
        subsets = iter(ipaddrs)
    except Exception:
        pass
    else:
        ipaddrs = IPSet()
        for subset in subsets:
            ipaddrs = ipaddrs | parse_ip_set(subset)
        return ipaddrs
    # anything else is an error
    raise ValueError("can't convert to IPSet: %r" % (ipaddrs,))


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
        self.ipaddrs = parse_ip_set(ipaddrs)
        self.userid = userid
        self.principals = principals
        self.proxies = parse_ip_set(proxies)

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
