import os
from twisted.web.xmlrpc import Proxy
from twisted.internet import defer
from attrdict import AttrDict
try:
    from configparser import SafeConfigParser
    from urllib.parse import urlparse
    import xmlrpc
except ImportError:
    from ConfigParser import SafeConfigParser
    from urlparse import urlparse
    import xmlrpclib as xmlrpc


__version__ = '1.2.0'

REDHAT = 'https://bugzilla.redhat.com/xmlrpc.cgi'


def connect(url=REDHAT, username=None, password=None):
    token = token_from_file(url)
    if username is None and password is None and token is None:
        # anonymous connection.
        return defer.succeed(Connection(url))
    if username is None and password is None and token is not None:
        # use the token we got from the ~/.bugzillatoken file.
        return defer.succeed(Connection(url, username, token))
    if username is not None and password is None:
        # Incorrect parameters
        raise ValueError('specify a password for %s' % username)
    # The caller provided a username and password string. Use these to obtain a
    # new token.
    proxy = Proxy(url.encode())
    d = proxy.callRemote('User.login', {'login': username,
                                        'password': password})
    d.addCallback(login_callback, url, username)
    return d


def login_callback(value, url, username):
    return Connection(url, username, value['token'])


def token_from_file(url):
    """ Check ~/.bugzillatoken for a token for this Bugzilla URL. """
    path = os.path.expanduser('~/.bugzillatoken')
    cfg = SafeConfigParser()
    cfg.read(path)
    domain = urlparse(url)[1]
    if domain not in cfg.sections():
        return None
    if not cfg.has_option(domain, 'token'):
        return None
    return cfg.get(domain, 'token')


class Connection(object):

    def __init__(self, url=REDHAT, username=None, token=None):
        self.proxy = Proxy(url.encode())
        self.url = url
        self.username = username
        self.token = token

    def call(self, action, payload):
        """
        Make an XML-RPC call to the server. This method will automatically
        authenticate the call with self.token, if that is set.

        returns: deferred that when fired returns a dict with data from this
                 XML-RPC call.
        """
        if self.token:
            payload['Bugzilla_token'] = self.token
        d = self.proxy.callRemote(action, payload)
        d.addErrback(self._parse_errback)
        return d

    def get_bug_simple(self, bugid):
        """
        Get a single bug object. Similar to python-bugzilla's getbugsimple().

        param bugid: integer, a bug's number.
        returns: deferred that when fired returns an AttrDict representing this
                 bug.
        """
        payload = {'ids': bugid}
        d = self.call('Bug.get', payload)
        d.addCallback(self._parse_bug_callback)
        return d

    def get_bugs_simple(self, bugids):
        """
        Get multiple bug objects. Similar to python-bugzilla's getbugssimple().

        param bugids: ``list`` of ``int``, bug numbers.
        returns: deferred that when fired returns a list of ``AttrDict``s
                 representing these bugs.
        """
        payload = {'ids': bugids}
        d = self.call('Bug.get', payload)
        d.addCallback(self._parse_bugs_callback)
        return d

    def get_bugs_summaries(self, bugids):
        """
        Get multiple bug objects' summaries only (faster).

        param bugids: ``list`` of ``int``, bug numbers.
        returns: deferred that when fired returns a list of ``AttrDict``s
                 representing these bugs.
        """
        payload = {'ids': bugids, 'include_fields': ['id', 'summary']}
        d = self.call('Bug.get', payload)
        d.addCallback(self._parse_bugs_callback)
        return d

    def assign(self, bugids, user):
        """
        Assign a bug to a user.

        param bugid: ``int``, bug ID number.
        param user: ``str``, the login name of the user to whom the bug is
                    assigned
        returns: deferred that when fired returns True if the change succeeded,
                 False if the change was unnecessary (because the user is
                 already assigned.)
        """
        payload = {'ids': (bugids,), 'assigned_to': user}
        d = self.call('Bug.update', payload)
        d.addCallback(self._parse_bug_assigned_callback)
        return d

    def find_by_external_tracker(self, url, id_):
        """
        Find a list of bugs by searching an external tracker URL and ID.

        param url: ``str``, the external ticket URL, eg
                   "http://tracker.ceph.com". (Note this is the base URL.)
        param id_: ``str``, the external ticket ID, eg "18812".
        returns: deferred that when fired returns a list of ``AttrDict``s
                 representing these bugs.
        """
        payload = {
            'include_fields': ['id', 'summary', 'status'],
            'f1': 'external_bugzilla.url',
            'o1': 'substring',
            'v1': url,
            'f2': 'ext_bz_bug_map.ext_bz_bug_id',
            'o2': 'equals',
            'v2': id_,
        }
        d = self.call('Bug.search', payload)
        d.addCallback(self._parse_bugs_callback)
        return d

    def _parse_bug_callback(self, value):
        """
        Fires when we get bug information back from the XML-RPC server.

        param value: dict of data from XML-RPC server. The "bugs" dict element
                     contains a list of bugs.
        returns: ``AttrDict``
        """
        return self._parse_bug(value['bugs'][0])

    def _parse_bugs_callback(self, value):
        """
        Fires when we get bug information back from the XML-RPC server.

        param value: dict of data from XML-RPC server. The "bugs" dict element
                     contains a list of bugs.
        returns: ``list`` of ``AttrDict``
        """
        return list(map(lambda x: self._parse_bug(x), value['bugs']))

    def _parse_bug_assigned_callback(self, value):
        """
        Fires when we get bug update information back from the XML-RPC server.

        param value: dict of data from XML-RPC server. The "bugs" dict element
                     contains a list of bugs, and we only care about the first
                     one in this list.
        returns: ``bool``, True if the change succeeded, or False if there was
                  no change (because it was not needed; the user is already
                  assigned.)
        """
        return 'assigned_to' in value['bugs'][0]['changes']

    def _parse_errback(self, error):
        """
        Parse an error from an XML-RPC call.

        raises: ``IOError`` when the Twisted XML-RPC connection times out.
        raises: ``BugzillaNotFoundException``
        raises: ``BugzillaNotAuthorizedException``
        raises: ``BugzillaException`` if we got a response from the XML-RPC
                server but it is not one of the ``xmlrpc.Fault``s above that
                we know about.
        raises: ``Exception`` if it is not one of the above.
        """
        if isinstance(error.value, IOError):
            raise error.value
        if isinstance(error.value, xmlrpc.Fault):
            if error.value.faultCode == 101:
                raise BugzillaNotFoundException(error.value.faultString)
            if error.value.faultCode == 102:
                raise BugzillaNotAuthorizedException(error.value.faultString)
            if error.value.faultCode == 32000:
                raise BugzillaTokenExpiredException(error.value.faultString)
            raise BugzillaException(error.value)
        # We don't know what this is, so just raise it.
        raise error

    def _parse_bug(self, data):
        """
        param data: dict of data from XML-RPC server, representing a bug.
        returns: AttrDict
        """
        if 'id' in data:
            data['weburl'] = self.url.replace('xmlrpc.cgi', str(data['id']))
        bug = AttrDict(data)
        return bug


class BugzillaException(Exception):
    pass


class BugzillaNotFoundException(BugzillaException):
    pass


class BugzillaNotAuthorizedException(BugzillaException):
    pass


class BugzillaTokenExpiredException(BugzillaException):
    pass
