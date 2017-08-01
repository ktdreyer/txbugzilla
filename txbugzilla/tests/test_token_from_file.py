import os
from txbugzilla import token_from_file


TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
FIXTURES_DIR = os.path.join(TESTS_DIR, 'fixtures')


URL = 'https://bugzilla.example.com/xmlrpc.cgi'


def test_token_from_file_legacy(monkeypatch):
    monkeypatch.setenv('HOME', FIXTURES_DIR + '/home-legacy-token')
    assert token_from_file(URL) == 'abc-123-legacy'


def test_token_from_file_cache(monkeypatch):
    monkeypatch.setenv('HOME', FIXTURES_DIR + '/home-cache-token')
    assert token_from_file(URL) == 'abc-123-cache'
