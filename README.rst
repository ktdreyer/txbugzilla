Async interface to Bugzilla, using Twisted
==========================================

Access Bugzilla's XML-RPC API asyncronously (non-blocking) using the Twisted
framework.

.. image:: https://travis-ci.org/ktdreyer/txbugzilla.svg?branch=master
             :target: https://travis-ci.org/ktdreyer/txbugzilla

.. image:: https://badge.fury.io/py/txbugzilla.svg
          :target: https://badge.fury.io/py/txbugzilla

Simple Example: Fetching a bug
------------------------------

.. code-block:: python

    from txbugzilla import connect, BugzillaException
    from twisted.internet import defer, reactor

    @defer.inlineCallbacks
    def example():
        # connect() defaults to https://bugzilla.redhat.com/xmlrpc.cgi
        bz = yield connect()

        # fetch a bug
        try:
            bug = yield bz.get_bug_simple(10000)
            print(bug.summary)
        except BugzillaException as e:
            print(e)

    if __name__ == '__main__':
        example().addCallback(lambda ign: reactor.stop())
        reactor.run()


Example: Authentication
-----------------------

By default, connections to Bugzilla are anonymous, so you cannot do fun things
like update bugs or view private bugs or private information.  If you wish to
authenticate your connection to Bugzilla, you can pass a username and password
to ``connect()``. The deferred that ``connect()`` returns will fire a callback
when the authentication succeeds.

.. code-block:: python

    from txbugzilla import connect
    from twisted.internet import defer

    @defer.inlineCallbacks
    def example():
        # Authenticate via username and password
        bz = yield connect(username='user@example.com', password='foo')

        # Do something as this logged-in username, for example:
        # bug = yield bz.getbugsimple(...)


Example: Re-using Authentication token
--------------------------------------

Authenticating to Bugzilla with a username and password involves one XML-RPC
roundtrip during ``connect()`` in order to obtain a token and use that token on
subsequent actions.

If you've already authenticated one time, you can save the token offline and
re-use it when your program runs again.

.. code-block:: python

    from txbugzilla import connect
    from twisted.internet import defer

    @defer.inlineCallbacks
    def example():
        # Authenticate via username and password
        bz = yield connect(username='user@example.com', password='foo')

        # Save bz.token to a file or database to reuse it later and avoid
        # having to re-authenticate.
        print(bz.token)
        # prints "123456-abcdef987"

And then, to re-use this token later:

.. code-block:: python

    from txbugzilla import Connection
    from twisted.internet import defer

    @defer.inlineCallbacks
    def some_time_later():
        # Re-connect using that saved token
        bz = Connection(username='user@example.com', token='123456-abcdef987')

        # Do something as this logged-in username, for example assign a bug
        # to someone:
        yield bz.assign(1234, 'someone@redhat.com')


Side note: bugzillatoken
~~~~~~~~~~~~~~~~~~~~~~~~

If you pass no parameters to ``connect()``, the resulting connection will be
anonymous *unless* you have a special ``.cache/python-bugzilla/bugzillatoken``
file in your home directory. This file should look something like this::

    $ cat ~/.cache/python-bugzilla/bugzillatoken
    [bugzilla.redhat.com]
    token = 123456-abcdef987

txbugzilla will look for this file and attempt to use the token there if one
exists. (It will also fall back to checking the older ``~/.bugzillatoken``
location, if the ``~/.cache`` one is unavailable.)

To construct this ``bugzillatoken`` file, you can use the `python-bugzilla
<https://pypi.python.org/pypi/python-bugzilla>`_ module, like so::

    $ pip install python-bugzilla
    $ bugzilla login
    Bugzilla Username: user@example.com
    Bugzilla Password: **********
    Login successful.


Example: Assigning bugs
-----------------------

This will definitely earn you friends.

.. code-block:: python

    from txbugzilla import connect, BugzillaException
    from twisted.internet import defer

    @defer.inlineCallbacks
    def example():
        bz = yield connect(username='user@example.com', password='foo')

        try:
            result = yield bz.assign(1234, 'someone@redhat.com')
            if result:
               print('assigned bz #1234 to someone@redhat.com')
            else:
               print('bz #1234 is already assigned to someone@redhat.com')
        except BugzillaException as e:
            print(e)

Example: Searching with an upstream bug
---------------------------------------

Quickly find out "What BZ matches this external tracker ticket?"

.. code-block:: python

    from txbugzilla import connect, BugzillaException
    from twisted.internet import defer

    @defer.inlineCallbacks
    def example():
        bz = yield connect()
        try:
            result = yield bz.find_by_external_tracker(
                'http://tracker.ceph.com', '16673')
            for b in result:
                print(b.weburl + ' ' + b.summary)
        except BugzillaException as e:
            print(e)


Example: Raw XML-RPC calls
--------------------------

Want to make some `API call
<https://bugzilla.redhat.com/docs/en/html/api/index.html>`_ not mentioned here?
Use the ``call()`` method to make raw XML-RPC calls. It will take care of token
authentication for you, too.

For example, to see a list of all the groups of which you are a member:

.. code-block:: python

    from txbugzilla import connect, BugzillaException
    from twisted.internet import defer
    from pprint import pprint

    @defer.inlineCallbacks
    def example():
        bz = yield connect(username='user@example.com', password='foo')

        try:
            result = yield bz.call('User.get', {'names': [bz.username],
                                                'include_fields': ['groups']})
            pprint(result['users'][0]['groups'])
        except BugzillaException as e:
            print(e)

License
-------
MIT (see ``LICENSE``)
