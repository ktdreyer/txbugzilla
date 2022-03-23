import os
import re
from txbugzilla.proxy import BearerProxy
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


__version__ = '2.0.0'

REDHAT = 'https://bugzilla.redhat.com/xmlrpc.cgi'


def connect(url=REDHAT, api_key=None):
    if not api_key:
        api_key = api_key_from_file(url)
    return defer.succeed(Connection(url, api_key))


def api_key_from_file(url):
    """ Check bugzillarc for an API key for this Bugzilla URL. """
    path = os.path.expanduser('~/.config/python-bugzilla/bugzillarc')
    cfg = SafeConfigParser()
    cfg.read(path)
    domain = urlparse(url)[1]
    if domain not in cfg.sections():
        return None
    if not cfg.has_option(domain, 'api_key'):
        return None
    return cfg.get(domain, 'api_key')


class Connection(object):

    def __init__(self, url=REDHAT, api_key=None):
        self.url = url
        self.api_key = api_key
        if 'redhat.com' in url:
            self.proxy = BearerProxy(url.encode(), api_key=api_key)
        else:
            self.proxy = BearerProxy(url.encode())

    def call(self, action, payload):
        """
        Make an XML-RPC call to the server. This method will automatically
        authenticate the call with self.api_key if that is set and the
        bugzilla instance is not at redhat.com.

        returns: deferred that when fired returns a dict with data from this
                 XML-RPC call.
        """
        if self.api_key and 'redhat.com' not in self.url:
            payload['Bugzilla_api_key'] = self.api_key
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
        if hasattr(xmlrpc, 'Fault'):  # Python 2:
            fault = xmlrpc.Fault
        else:
            fault = xmlrpc.client.Fault
        if isinstance(error.value, fault):
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
    @property
    def id(self):
        """ Bug ID number that caused this error """
        m = re.match(r'Bug #(\d+) does not exist', self.message)
        return m.group(1)


class BugzillaNotAuthorizedException(BugzillaException):
    @property
    def id(self):
        """ Bug ID number that caused this error """
        m = re.match(r'You are not authorized to access bug #(\d+)',
                     self.message)
        return m.group(1)


class BugzillaTokenExpiredException(BugzillaException):
    pass
