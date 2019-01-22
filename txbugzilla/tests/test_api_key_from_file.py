import os
from txbugzilla import api_key_from_file


TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
FIXTURES_DIR = os.path.join(TESTS_DIR, 'fixtures')


URL = 'https://bugzilla.example.com/xmlrpc.cgi'


def test_api_key_from_file(monkeypatch):
    monkeypatch.setenv('HOME', FIXTURES_DIR + '/home-api-key')
    assert api_key_from_file(URL) == 'abc-123-bugzillarc'
