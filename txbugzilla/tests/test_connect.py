import os
import pytest_twisted
from txbugzilla import connect, Connection


class TestConnect(object):

    @pytest_twisted.inlineCallbacks
    def test_anonymous_connect(self, monkeypatch):
        monkeypatch.setenv('HOME', os.getcwd())
        bz = yield connect()
        assert isinstance(bz, Connection)
        assert bz.api_key is None

    @pytest_twisted.inlineCallbacks
    def test_authentication_connect(self, monkeypatch):
        monkeypatch.setenv('HOME', os.getcwd())
        bz = yield connect(api_key='123456abcdef')
        assert isinstance(bz, Connection)
        assert bz.api_key == '123456abcdef'
