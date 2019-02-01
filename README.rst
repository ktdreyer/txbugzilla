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
    from twisted.internet import defer
    from twisted.internet.task import react

    @defer.inlineCallbacks
    def example(reactor):
        # connect() defaults to https://bugzilla.redhat.com/xmlrpc.cgi
        bz = yield connect()

        # fetch a bug
        try:
            bug = yield bz.get_bug_simple(10000)
            print(bug.summary)
        except BugzillaException as e:
            print(e)

    if __name__ == '__main__':
        react(example)


Example: Authentication
-----------------------

By default, connections to Bugzilla are anonymous, so you cannot do fun things
like update bugs or view private bugs or private information.  If you wish to
authenticate your connection to Bugzilla, you can pass an API key to
``connect()``. The deferred that ``connect()`` returns will fire a callback
with an authenticated connection.

.. code-block:: python

    from txbugzilla import connect
    from twisted.internet import defer

    @defer.inlineCallbacks
    def example():
        # Authenticate with an API key
        bz = yield connect(api_key='123456abcdef')

        # Do something as this logged-in user, for example:
        # bug = yield bz.getbugsimple(...)

(Previous versions of txbugzilla supported the older username/password and
token methods for authenticating. These methods are deprecated in Bugzilla 5
and the latest version of txbugzilla no longer supports these. You must use
API keys now.)

Side note: bugzillarc
~~~~~~~~~~~~~~~~~~~~~

If you pass no parameters to ``connect()``, the resulting connection will be
anonymous *unless* you have a special ``.config/python-bugzilla/bugzillarc``
file in your home directory. This file should look something like this::

    $ cat ~/.config/python-bugzilla/bugzillarc
    [bugzilla.redhat.com]
    api_key=ABCDEFGHIJK

txbugzilla will look for this file and attempt to use the API key there if one
exists.

To construct this ``bugzillarc`` file:

1. Log into Bugzilla's web UI with your browser.
2. Go to "Preferences" -> "`API Keys
   <https://bugzilla.redhat.com/userprefs.cgi?tab=apikey>`_".
3. Generate a new API key.
4. Make the ``.config/python-bugzilla`` directory in your home directory::

     mkdir -p ~/.config/python-bugzilla

5. Edit the ``bugzillarc`` file in your text editor::

     cat ~/.config/python-bugzilla/bugzillarc
     [buzilla.example.com]
     api_key=YOUR_API_KEY


Example: Assigning bugs
-----------------------

This will definitely earn you friends.

.. code-block:: python

    from txbugzilla import connect, BugzillaException
    from twisted.internet import defer

    @defer.inlineCallbacks
    def example():
        bz = yield connect(api_key='123456abcdef')

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
Use the ``call()`` method to make raw XML-RPC calls. It will take care of API
key authentication for you, too.

For example, to see a list of all the groups of which you are a member:

.. code-block:: python

    from txbugzilla import connect, BugzillaException
    from twisted.internet import defer
    from pprint import pprint

    @defer.inlineCallbacks
    def example():
        bz = yield connect(api_key='123456abcdef')

        try:
            result = yield bz.call('User.get', {'names': [bz.username],
                                                'include_fields': ['groups']})
            pprint(result['users'][0]['groups'])
        except BugzillaException as e:
            print(e)

License
-------
MIT (see ``LICENSE``)

Packages that use this package
------------------------------

* `helga-bugzilla <https://pypi.org/project/helga-bugzilla/>`_
