"""Treadmill module."""

from __future__ import absolute_import

import os
import pkgutil


__path__ = pkgutil.extend_path(__path__, __name__)


def __root_join(*path):
    """Joins path with location of the current file."""
    mydir = os.path.dirname(os.path.realpath(__file__))
    return os.path.realpath(os.path.join(mydir, *path))


# Global pointing to root of the source distribution.
#
# TODO: how will it work if packaged as single zip file?
TREADMILL = __root_join('..', '..', '..')

TREADMILL_BIN = os.path.join(TREADMILL, 'bin', 'treadmill')

TREADMILL_LDAP = os.environ.get('TREADMILL_LDAP')
