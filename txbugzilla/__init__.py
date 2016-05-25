from twisted.web.xmlrpc import Proxy
from twisted.internet import defer
from attrdict import AttrDict
import xmlrpclib


__version__ = '0.0.1'

REDHAT = 'https://bugzilla.redhat.com/xmlrpc.cgi'


def connect(url=REDHAT, username=None, password=None):
    if username is None:
        return defer.succeed(Connection(url))
    if password is None:
        raise ValueError('specify a password for %s' % username)
    proxy = Proxy(url)
    d = proxy.callRemote('User.login', {'login': username,
                                        'password': password})
    d.addCallback(connect_callback, url, username)
    return d


def connect_callback(value, url, username):
    return Connection(url, username, value['token'])


class Connection(object):

    def __init__(self, url, username=None, token=None):
        self.proxy = Proxy(url)
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
        payload = {'ids': bugids, 'include_fields': ['summary']}
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
        return map(lambda x: self._parse_bug(x), value['bugs'])

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
                server but it is not one of the ``xmlrpclib.Fault``s above that
                we know about.
        raises: ``Exception`` if it is not one of the above.
        """
        if isinstance(error.value, IOError):
            raise error.value
        if isinstance(error.value, xmlrpclib.Fault):
            if error.value.faultCode == 101:
                raise BugzillaNotFoundException(error.value.faultString)
            if error.value.faultCode == 102:
                raise BugzillaNotAuthorizedException(error.value.faultString)
            raise BugzillaException(error.value)
        # We don't know what this is, so just raise it.
        raise error

    def _parse_bug(self, data):
        """
        param data: dict of data from XML-RPC server, representing a bug.
        returns: AttrDict
        """
        bug = AttrDict(data)
        return bug


class BugzillaException(xmlrpclib.Fault):
    pass


class BugzillaNotFoundException(BugzillaException):
    pass


class BugzillaNotAuthorizedException(BugzillaException):
    pass
