from twisted.web.xmlrpc import Proxy
from twisted.web.xmlrpc import QueryProtocol

"""
Handle the non-standard "Bearer" authorization header that Red Hat Bugzilla
requires.
"""


class BearerQueryProtocol(QueryProtocol):
    def connectionMade(self):
        """
        # Largely copied from the QueryProtocol class in Twisted's xmlrpc.py,
        # modified to add an Authorization header for an API key.
        """
        self._response = None
        self.sendCommand(b"POST", self.factory.path)
        self.sendHeader(b"User-Agent", b"Twisted/txbugzilla")
        self.sendHeader(b"Host", self.factory.host)
        self.sendHeader(b"Content-type", b"text/xml; charset=utf-8")
        payload = self.factory.payload
        self.sendHeader(b"Content-length", b"%d" % (len(payload),))
        if self.factory.api_key:
            auth = "Bearer %s" % self.factory.api_key
            self.sendHeader(b"Authorization", auth)
        self.endHeaders()
        self.transport.write(payload)


class BearerProxy(Proxy, object):
    def __init__(self, *args, **kwargs):
        """
        This constructor takes a new "api_key" kwarg. If provided, this proxy
        will add this as an Authorization header to every HTTP request.

        See https://bugzilla.redhat.com/docs/en/html/api/core/v1/general.html#authentication
        """
        self.queryFactory.api_key = kwargs.pop('api_key', None)
        self.queryFactory.protocol = BearerQueryProtocol
        super(BearerProxy, self).__init__(*args, **kwargs)
