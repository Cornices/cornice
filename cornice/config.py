# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Sync Server
#
# The Initial Developer of the Original Code is the Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2010
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Tarek Ziade (tarek@mozilla.com)
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****
""" Configuration file reader / writer

https://wiki.mozilla.org/index.php?title=Services/Sync/Server/GlobalConfFile
"""
import re
import os
from ConfigParser import RawConfigParser, Error

_IS_NUMBER = re.compile('^-?[0-9].*')
_IS_ENV_VAR = re.compile('\$\{(\w.*)?\}')


class EnvironmentNotFoundError(Error):
    """Raised when an environment variable is not found"""

    def __init__(self, varname):
        Error.__init__(self, 'Variable not found %r' % varname)
        self.varname = varname


def convert(value):
    """Converts a config value"""
    def _get_env(matchobj):
        var = matchobj.groups()[0]
        if var not in os.environ:
            raise EnvironmentNotFoundError(var)
        return os.environ[var]

    def _convert(value):
        if not isinstance(value, basestring):
            # already converted
            return value

        value = value.strip()
        if _IS_NUMBER.match(value):
            try:
                return int(value)
            except ValueError:
                pass
        elif value.startswith('"') and value.endswith('"'):
            return value[1:-1]
        elif value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        return _IS_ENV_VAR.sub(_get_env, value)

    if isinstance(value, basestring) and '\n' in value:
        return [line for line in [_convert(line)
                                  for line in value.split('\n')]
                if line != '']

    return _convert(value)


class Config(RawConfigParser):

    def __init__(self, filename):
        # let's read the file
        RawConfigParser.__init__(self)
        if isinstance(filename, basestring):
            self.read(filename)
        else:
            self.readfp(filename)

    def _read(self, fp, filename):
        # first pass
        RawConfigParser._read(self, fp, filename)

        # let's expand it now if needed
        defaults = self.defaults()

        if'extends' in defaults:
            extends = defaults['extends']
            if not isinstance(extends, list):
                extends = [extends]
            for file_ in extends:
                self._extend(file_)

    def _serialize(self, value):
        """values are serialized on every set"""
        if isinstance(value, bool):
            value = str(value).lower()
        elif isinstance(value, (int, long)):
            value = str(value)
        elif isinstance(value, (list, tuple)):
            value = '\n'.join(['    %s' % line for line in value]).strip()
        else:
            value = str(value)
        return value

    def _unserialize(self, value):
        """values are serialized on every get"""
        return convert(value)

    def get_map(self, section=None):
        """returns a dict representing the config set"""
        if section:
            return dict(self.items(section))

        res = {}
        for section in self.sections():
            for option, value in self.items(section):
                option = '%s.%s' % (section, option)
                res[option] = self._unserialize(value)
        return res

    def set(self, section, option, value):
        value = self._serialize(value)
        RawConfigParser.set(self, section, option, value)

    def mget(self, section, option):
        value = self.get(section, option)
        if not isinstance(value, list):
            value = [value]
        return value

    def get(self, section, option):
        value = RawConfigParser.get(self, section, option)
        return self._unserialize(value)

    def items(self, section):
        items = RawConfigParser.items(self, section)
        return [(option, self._unserialize(value)) for option, value in items]

    def _extend(self, filename):
        """Expand the config with another file."""
        if not os.path.isfile(filename):
            raise IOError('No such file: %s' % filename)
        parser = RawConfigParser()
        parser.read([filename])
        for section in parser.sections():
            if not self.has_section(section):
                self.add_section(section)
            for option, value in parser.items(section):
                if self.has_option(section, option):
                    continue
                RawConfigParser.set(self, section, option, value)
