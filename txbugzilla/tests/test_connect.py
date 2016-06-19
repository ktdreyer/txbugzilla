import os
import pytest
from txbugzilla import connect, Connection
from twisted.internet import defer


class _StubProxy(object):
    def __init__(self, url):
        pass

    def callRemote(self, action, payload):
        """ Return a deferred that always fires successfully """
        assert action == 'User.login'
        result = {'token': 'ABC-123'}
        return defer.succeed(result)


class TestConnect(object):

    @pytest.inlineCallbacks
    def test_anonymous_connect(self, monkeypatch):
        monkeypatch.setenv('HOME', os.getcwd())
        bz = yield connect()
        assert isinstance(bz, Connection)

    @pytest.inlineCallbacks
    def test_wrong_args_connect(self):
        with pytest.raises(ValueError) as e:
            yield connect(username='nopassword@example.com')
        assert 'specify a password' in str(e.value)

    @pytest.inlineCallbacks
    def test_authentication_connect(self, monkeypatch):
        monkeypatch.setattr('txbugzilla.Proxy', _StubProxy)
        bz = yield connect(username='ktdreyer@example.com', password='foobar')
        assert isinstance(bz, Connection)
