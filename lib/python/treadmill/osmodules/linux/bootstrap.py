"""Bootstrap implementation for linux."""
from __future__ import absolute_import

import errno

import abc
import logging
import os
import tempfile

import jinja2

import treadmill

from .. import _bootstrap_base

from ... import admin
from ... import context
from ... import fs


_LOGGER = logging.getLogger(__name__)


def default_install_dir():
    """Gets the base install directory."""
    return '/var/tmp'


class LinuxBootstrap(_bootstrap_base.BootstrapBase):
    """Base interface for bootstrapping on linux."""

    @property
    @abc.abstractproperty
    def _bin_path(self):
        """Gets the bin path."""

    def _render(self, value, params):
        """Renders text, interpolating params."""
        return str(jinja2.Template(value).render(params))

    def _interpolate_dict(self, value, params):
        """Recursively interpolate each value in parameters."""
        result = {}
        target = dict(value)
        counter = 0
        while counter < 100:
            counter += 1
            result = {k: self._interpolate(v, params) for k, v in
                      target.iteritems()}
            if result == target:
                break
            target = dict(result)
        else:
            raise Exception('Too many recursions: %s %s', value, params)

        return result

    def _interpolate_list(self, value, params):
        """Interpolate each of the list element."""
        return [self._interpolate(member, params) for member in value]

    def _interpolate_scalar(self, value, params):
        """Interpolate string value by rendering the template."""
        if isinstance(value, str):
            return self._render(value, params)
        else:
            # Do not interpolate numbers.
            return value

    def _interpolate(self, value, params=None):
        """Interpolate the value, switching by the value type."""
        if params is None:
            params = value

        try:
            if isinstance(value, list):
                return self._interpolate_list(value, params)
            if isinstance(value, dict):
                return self._interpolate_dict(value, params)
            return self._interpolate_scalar(value, params)
        except Exception:
            _LOGGER.critical('error interpolating: %s %s', value, params)
            raise

    def _update(self, filename, content):
        """Updates file with content if different."""
        _LOGGER.debug('Updating %s', filename)
        try:
            with open(filename) as f:
                current = f.read()
                if current == content:
                    return

        except OSError as os_err:
            if os_err.errno != errno.ENOENT:
                raise
        except IOError as io_err:
            if io_err.errno != errno.ENOENT:
                raise

        with tempfile.NamedTemporaryFile(dir=os.path.dirname(filename),
                                         prefix='.tmp',
                                         delete=False) as tmp_file:
            tmp_file.write(content)
            tmp_file.flush()

        os.rename(tmp_file.name, filename)

    def _update_stat(self, src_file, tgt_file):
        """chmod target file to match the source file."""
        src_stat = os.stat(src_file)
        tgt_stat = os.stat(tgt_file)

        if src_stat.st_mode != tgt_stat.st_mode:
            _LOGGER.debug('chmod %s %s', tgt_file, src_stat.st_mode)
            os.chmod(tgt_file, src_stat.st_mode)

    def _install(self, params):
        """Interpolate source directory into target directory with params."""
        for root, _dirs, files in os.walk(self.src_dir):
            subdir = root.replace(self.src_dir, self.dst_dir)
            if not os.path.exists(subdir):
                fs.mkdir_safe(subdir)
            for filename in files:
                if filename.startswith('.'):
                    continue

                src_file = os.path.join(root, filename)
                tgt_file = os.path.join(subdir, filename)
                if os.path.islink(src_file):
                    link = self._render(os.readlink(src_file), params)
                    os.symlink(link, tgt_file)
                    if not os.path.exists(tgt_file):
                        _LOGGER.critical('Broken symlink: %s -> %s, %r',
                                         src_file, tgt_file, params)
                        raise Exception('Broken symlink, aborting install.')
                else:
                    with open(src_file) as src:
                        self._update(tgt_file, self._render(src.read(),
                                                            params))
                    self._update_stat(src_file, tgt_file)

    @property
    def _params(self):
        """Parameters for both node and master."""
        cellname = context.GLOBAL.cell
        admin_cell = admin.Cell(context.GLOBAL.ldap.conn)
        params = {}
        params.update(self.defaults)
        params.update(admin_cell.get(cellname))
        params.update({
            'cell': cellname,
            'zookeeper': context.GLOBAL.zk.url,
            'ldap': context.GLOBAL.ldap.url,
            'dns_domain': context.GLOBAL.dns_domain,
            'ldap_search_base': context.GLOBAL.ldap.search_base,
            'treadmill': treadmill.TREADMILL,
            'treadmillid': params['username'],
            'dir': self.dst_dir
        })
        return params

    def install(self):
        """Installs the services."""
        params = self._params
        params = self._interpolate(params, params)
        self._install(params)

    def run(self):
        """Runs the services."""
        args = [os.path.join(self.dst_dir, self._bin_path)]
        os.execvp(args[0], args)


class NodeBootstrap(LinuxBootstrap):
    """For bootstrapping the node on linux."""

    def __init__(self, dst_dir, defaults):
        super(NodeBootstrap, self).__init__(
            os.path.join(treadmill.TREADMILL, 'local', 'linux', 'node'),
            dst_dir,
            defaults
        )

    @property
    def _bin_path(self):
        return os.path.join('bin', 'run.sh')

    def install(self):
        if os.path.exists(os.path.join(self.src_dir, 'wipe_me')):
            os.system(os.path.join(self.src_dir, 'bin', 'wipe_node.sh'))

        super(NodeBootstrap, self).install()


class MasterBootstrap(LinuxBootstrap):
    """For bootstrapping the master on linux."""

    def __init__(self, dst_dir, defaults, master_id):
        super(MasterBootstrap, self).__init__(
            os.path.join(treadmill.TREADMILL, 'local', 'linux', 'master'),
            os.path.join(dst_dir, context.GLOBAL.cell, str(master_id)),
            defaults
        )
        self.master_id = int(master_id)
        self.defaults.update({'master-id': self.master_id})

    @property
    def _bin_path(self):
        return os.path.join('treadmill', 'bin', 'run.sh')

    @property
    def _params(self):
        """Overrides master params with current master."""
        params = super(MasterBootstrap, self)._params  # pylint: disable=W0212
        for master in params['masters']:  # pylint: disable=E1136
            if master['idx'] == self.master_id:
                params.update({'me': master})
        return params
