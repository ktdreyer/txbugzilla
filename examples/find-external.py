from pprint import pprint
import re
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse
from txbugzilla import connect, BugzillaException
from twisted.internet import defer
from twisted.internet.task import react


EXTERNAL_TRACKER_ID_REGEX = re.compile(r'\d+$')


def find_tracker_url(ticket_url):
    """
    Given http://tracker.ceph.com/issues/16673 or
    tracker.ceph.com/issues/16673, return "http://tracker.ceph.com".
    """
    if ticket_url.startswith('http://') or ticket_url.startswith('https://'):
        o = urlparse(ticket_url)
        scheme, netloc = o.scheme, o.netloc
    else:
        scheme = 'http'
        (netloc, _) = ticket_url.split('/', 1)
    return '%s://%s' % (scheme, netloc)


def find_tracker_id(ticket_url):
    matches = EXTERNAL_TRACKER_ID_REGEX.findall(ticket_url)
    try:
        return matches[0]
    except KeyError:
        raise RuntimeError('Could not discover ticket ID in %s' % ticket_url)


@defer.inlineCallbacks
def example(reactor):
    bz = yield connect()

    upstream = 'http://tracker.ceph.com/issues/16673'
    external_tracker_url = find_tracker_url(upstream)
    external_tracker_id = find_tracker_id(upstream)
    print(external_tracker_url)
    print(external_tracker_id)
    try:
        result = yield bz.find_by_external_tracker(external_tracker_url,
                                                   external_tracker_id)
        print('Result is:')
        for b in result:
            pprint(dict(b))
    except BugzillaException as e:
        print('BugzillaException:')
        print(e)


if __name__ == '__main__':
    react(example)
