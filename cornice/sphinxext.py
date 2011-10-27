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

from sphinx.util.compat import Directive, make_admonition
from cornice.util import rst2node


class ServiceDirective(Directive):
    # this enables content in the directive
    has_content = True
    option_spec = {'package': directives.unchanged,
                   'service': directives.unchanged}

    def run(self):
        env = self.state.document.settings.env

        # composing our little rendering
        service = nodes.title('Some services')

        pkg = self.options['package']
        from pyramid.config import Configurator
        conf = Configurator()
        conf.include('cornice')
        conf.scan(pkg)

        by_service = defaultdict(dict)
        apidocs = conf.registry.settings.get('apidocs', [])
        for (path, method), apidoc in apidocs.items():
            service = apidoc['service']
            by_service[path, service][method] = apidoc

        # ordered injection
        services_id = "services-%d" % env.new_serialno('services')
        services_node = nodes.section(ids=[services_id])
        services_node += nodes.title(text='Services')

        for (path, service), methods in by_service.items():
            service_id = "service-%d" % env.new_serialno('service')
            service_node = nodes.section(ids=[service_id])
            service_node += nodes.title(text='Service at %s' %
                                        service.route_name)

            for method, info in methods.items():
                # title, e.g. GET /blablablaba
                title = '%s %s' % (method, service.route_pattern)
                method_node = make_admonition(ServiceNode, self.name, [title],
                                              self.options,
                                              self.content, self.lineno,
                                              self.content_offset,
                                              self.block_text, self.state,
                                              self.state_machine)

                service_node += method_node

                node = rst2node(info['docstring'])
                if node is not None:
                    service_node += node

            services_node += service_node

        return [services_node]


class ServiceNode(nodes.Admonition, nodes.Element):
    pass


def visit_todo_node(self, node):
    self.visit_admonition(node)


def depart_todo_node(self, node):
    self.depart_admonition(node)


def setup(app):
    app.add_node(ServiceNode,
                 html=(visit_todo_node, depart_todo_node),
                 text=(visit_todo_node, depart_todo_node),
                 latex=(visit_todo_node, depart_todo_node))

    app.add_directive('services', ServiceDirective)
