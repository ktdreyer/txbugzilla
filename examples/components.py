from txbugzilla import connect, BugzillaException
from twisted.internet import defer
from twisted.internet.task import react
from pprint import pprint

# Print the raw component data for the Red Hat Ceph Storage product.
# Useful for seeing what components are defined for a product.
# https://bugzilla.redhat.com/docs/en/html/api/Bugzilla/WebService/Product.html#get
# I wrote this when playing around with python-bugzilla's getcomponents() call,
# https://github.com/python-bugzilla/python-bugzilla/issues/49


@defer.inlineCallbacks
def example(reactor):
    bz = yield connect()

    payload = {'names': ['Red Hat Ceph Storage']}
    try:
        result = yield bz.call('Product.get', payload)
        pprint(result)
    except BugzillaException as e:
        print(e)


if __name__ == '__main__':
    react(example)
