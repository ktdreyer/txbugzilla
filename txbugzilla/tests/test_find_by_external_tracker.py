import os
import pytest
from txbugzilla import connect
from twisted.internet import defer


class _StubProxy(object):
    def __init__(self, url):
        pass

    def callRemote(self, action, payload):
        """ Return a deferred that always fires successfully """
        assert action == 'Bug.search'
        result = {'bugs': [{
            'id': 1422893,
            'status': 'ASSIGNED',
            'summary': '[RFE] rgw: add suport for Swift-at-root',
            'weburl': 'https://bugzilla.redhat.com/1422893',
        }]}
        return defer.succeed(result)


class TestFindByExternalTracker(object):

    @pytest.inlineCallbacks
    def test_find_by_external_tracker(self, monkeypatch):
        monkeypatch.setenv('HOME', os.getcwd())
        monkeypatch.setattr('txbugzilla.Proxy', _StubProxy)

        external_tracker_url = 'http://tracker.ceph.com'
        external_tracker_id = '16673'

        bz = yield connect()
        result = yield bz.find_by_external_tracker(external_tracker_url,
                                                   external_tracker_id)
        assert len(result) == 1
        assert result[0].id == 1422893
