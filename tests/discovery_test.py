"""
Unit test for appwatch.
"""

import unittest

# Disable W0611: Unused import
import tests.treadmill_test_deps  # pylint: disable=W0611

import kazoo
import kazoo.zkutils
import mock

from treadmill import discovery
from treadmill.test import mockzk


class DiscoveryTest(mockzk.MockZookeeperTestCase):
    """Mock test for treadmill.appwatch."""

    def setUp(self):
        super(DiscoveryTest, self).setUp()

    def tearDown(self):
        super(DiscoveryTest, self).tearDown()

    @mock.patch('treadmill.zkutils.connect', mock.Mock(
        return_value=kazoo.client.KazooClient()))
    @mock.patch('kazoo.client.KazooClient.get', mock.Mock(
        return_value=('xxx:111', None)))
    @mock.patch('kazoo.client.KazooClient.get_children', mock.Mock())
    @mock.patch('kazoo.client.KazooClient.exists', mock.Mock())
    @mock.patch('treadmill.utils.rootdir', mock.Mock(return_value='/some'))
    def test_sync(self):
        """Checks event processing and state sync."""
        zkclient = kazoo.client.KazooClient()
        app_discovery = discovery.Discovery(zkclient, 'appproid.foo.*', 'http')

        kazoo.client.KazooClient.get_children.return_value = [
            'foo.1#0:http',
            'foo.2#0:http',
            'foo.2#0:tcp',
            'bar.1#0:http'
        ]

        kazoo.client.KazooClient.get.return_value = ('xxx:123', None)

        # Need to call sync first, then put 'exit' on the queue to terminate
        # the loop.
        #
        # Calling run will drain event queue and populate state.
        app_discovery.sync()
        kazoo.client.KazooClient.get_children.assert_called_with(
            '/endpoints/appproid', watch=mock.ANY)
        app_discovery.exit_loop()

        expected = {}
        for (endpoint, hostport) in app_discovery.iteritems():
            expected[endpoint] = hostport

        self.assertEquals(expected, {'appproid.foo.1#0:http': 'xxx:123',
                                     'appproid.foo.2#0:http': 'xxx:123'})

    @mock.patch('treadmill.zkutils.connect', mock.Mock(
        return_value=kazoo.client.KazooClient()))
    @mock.patch('kazoo.client.KazooClient.exists', mock.Mock(
        return_value=('xxx:111', None)))
    @mock.patch('kazoo.client.KazooClient.get_children', mock.Mock(
        side_effect=kazoo.exceptions.NoNodeError))
    @mock.patch('treadmill.utils.rootdir', mock.Mock(return_value='/some'))
    def test_noexists(self):
        """Check that discovery establishes watch for non-existing proid."""
        zkclient = kazoo.client.KazooClient()
        app_discovery = discovery.Discovery(zkclient, 'appproid.foo.*', 'http')
        app_discovery.sync()
        kazoo.client.KazooClient.exists.assert_called_with(
            '/endpoints/appproid', watch=mock.ANY)

    def test_pattern(self):
        """Checks instance aware pattern construction."""
        app_discovery = discovery.Discovery(None, 'appproid.foo', 'http')
        self.assertEquals('foo#*', app_discovery.pattern)

        app_discovery = discovery.Discovery(None, 'appproid.foo#1', 'http')
        self.assertEquals('foo#1', app_discovery.pattern)


if __name__ == '__main__':
    unittest.main()
