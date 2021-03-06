"""Unit test for treadmill.schema
"""

import unittest

# Disable W0611: Unused import
import tests.treadmill_test_deps  # pylint: disable=W0611

import jsonschema

from treadmill import schema


class SchemaTest(unittest.TestCase):
    """treadmill.schema tests."""

    def test_schema_decorator(self):
        """schema decorator test."""

        @schema.schema({'type': 'number'}, {'type': 'string'})
        def _simple(_number, _string):
            """sample function."""
            pass

        _simple(1, '1')
        self.assertRaises(
            jsonschema.exceptions.ValidationError,
            _simple, '1', '1')

        @schema.schema({'type': 'number'}, {'type': 'string'},
                       num_arg={'type': 'number'},
                       str_arg={'type': 'string'})
        def _kwargs(_number, _string, num_arg=None, str_arg=None):
            """sample function with default args."""
            return num_arg, str_arg

        self.assertEquals((None, None), _kwargs(1, '1'))
        self.assertEquals((1, None), _kwargs(1, '1', num_arg=1))
        self.assertEquals((None, '1'), _kwargs(1, '1', str_arg='1'))
        self.assertRaises(
            jsonschema.exceptions.ValidationError,
            _kwargs, '1', '1', str_arg=1)


if __name__ == '__main__':
    unittest.main()
