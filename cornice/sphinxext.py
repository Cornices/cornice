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
# The Original Code is Cornice (Sagrada)
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
"""
Sphinx extension that displays the API documentation.
"""
from collections import defaultdict
from docutils import nodes
from docutils.parsers.rst import directives

from sphinx.util.compat import Directive

from cornice.util import rst2node


def _dedent(text):
    if text is None:
        return

    text = text.strip()

    # if, starting at line 2, every line starts with
    # the same amount of space, we strip it.
    lines = text.split('\n')
    if len(lines) < 2 or (lines[1] != '' and len(lines[1]) == 0):
        return text

    def _space_count(line):
        indent = 0
        while indent < len(line) and line[indent] == ' ':
            indent += 1
        return indent

    # first indent ?
    first_line = 1
    while lines[first_line] == '':
        first_line += 1

    first_indent = _space_count(lines[first_line])
    if first_indent == 0:
        return text

    new_text = [line for line in lines[:first_line]]

    # now loooking at other lines
    for line in lines[first_line:]:
        if line != '' and _space_count(line) < first_indent:
            return text
        new_text.append(line[first_indent:])

    # we're good
    return '\n'.join(new_text)


class ServiceDirective(Directive):
    """ Service directive.

    Will inject sections in the documentation.
    """
    has_content = True
    option_spec = {'package': directives.unchanged,
                   'service': directives.unchanged}

    def _render_service(self, path, service, methods):
        env = self.state.document.settings.env
        service_id = "service-%d" % env.new_serialno('service')
        service_node = nodes.section(ids=[service_id])
        service_node += nodes.title(text='Service at %s' %
                                    service.route_name)
        if service.description is not None:
            service_node += rst2node(_dedent(service.description))

        for method, info in methods.items():
            method_id = '%s-%s' % (service_id, method)
            method_node = nodes.section(ids=[method_id])
            method_node += nodes.title(text=method)

            node = rst2node(_dedent(info['docstring']))
            if node is not None:
                method_node += node

            renderer = info['renderer']
            if renderer == 'simplejson':
                renderer = 'json'

            response = nodes.paragraph()
            response += nodes.strong(text='Response: %s' % renderer)
            method_node += response
            service_node += method_node

        return service_node

    def _get_services(self, package):
        from pyramid.config import Configurator
        conf = Configurator()
        conf.include('cornice')
        conf.scan(package)
        by_service = defaultdict(dict)
        apidocs = conf.registry.settings.get('apidocs', [])

        for (path, method), apidoc in apidocs.items():
            service = apidoc['service']
            by_service[path, service][method] = apidoc

        return by_service

    def run(self):
        env = self.state.document.settings.env
        # getting the options
        pkg = self.options['package']
        service_name = self.options.get('service')
        all_services = service_name is None

        # listing the services for the package
        services = self._get_services(pkg)

        if all_services:
            # we want to list all of them
            services_id = "services-%d" % env.new_serialno('services')
            services_node = nodes.section(ids=[services_id])
            services_node += nodes.title(text='Services')

            for (path, service), methods in services.items():
                services_node += self._render_service(path, service, methods)

            return [services_node]
        else:
            # we just want a single service
            #
            # XXX not efficient
            for (path, service), methods in services.items():
                if service.name != service_name:
                    continue
                return [self._render_service(path, service, methods)]
            return []


def setup(app):
    """Sphinx setup."""
    app.add_directive('services', ServiceDirective)
