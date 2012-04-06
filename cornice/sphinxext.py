# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# Contributors: Vincent Fretin
"""
Sphinx extension that displays the API documentation.
"""
import sys

from collections import defaultdict
from docutils import nodes
from docutils.parsers.rst import Directive, directives

from sphinx.util.docfields import DocFieldTransformer

from cornice.util import rst2node, to_list


def trim(docstring):
    """Implementation taken from
    http://www.python.org/dev/peps/pep-0257/
    """
    if not docstring:
        return ''
    # Convert tabs to spaces (following the normal Python rules)
    # and split into a list of lines:
    lines = docstring.expandtabs().splitlines()
    # Determine minimum indentation (first line doesn't count):
    indent = sys.maxint
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = min(indent, len(line) - len(stripped))
    # Remove indentation (first line is special):
    trimmed = [lines[0].strip()]
    if indent < sys.maxint:
        for line in lines[1:]:
            trimmed.append(line[indent:].rstrip())
    # Strip off trailing and leading blank lines:
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    while trimmed and not trimmed[0]:
        trimmed.pop(0)
    # Return a single string:
    res = '\n'.join(trimmed)
    if not isinstance(res, unicode):
        res = res.decode('utf8')
    return res

from sphinx.locale import l_
from sphinx.util.docfields import Field, GroupedField, TypedField


class ServiceDirective(Directive):
    """ Service directive.

    Will inject sections in the documentation.
    """
    has_content = True
    option_spec = {'package': directives.unchanged,
                   'service': directives.unchanged,
                   'ignore': directives.unchanged}
    domain = 'py'
    # copied from sphinx.domains.python.PyObject
    doc_field_types = [
        TypedField('parameter', label=l_('Parameters'),
                   names=('param', 'parameter', 'arg', 'argument',
                          'keyword', 'kwarg', 'kwparam'),
                   typerolename='obj', typenames=('paramtype', 'type'),
                   can_collapse=True),
        TypedField('variable', label=l_('Variables'), rolename='obj',
                   names=('var', 'ivar', 'cvar'),
                   typerolename='obj', typenames=('vartype',),
                   can_collapse=True),
        GroupedField('exceptions', label=l_('Raises'), rolename='exc',
                     names=('raises', 'raise', 'exception', 'except'),
                     can_collapse=True),
        Field('returnvalue', label=l_('Returns'), has_arg=False,
              names=('returns', 'return')),
        Field('returntype', label=l_('Return type'), has_arg=False,
              names=('rtype',)),
    ]

    def _render_service(self, path, service, methods):
        env = self.state.document.settings.env
        service_id = "service-%d" % env.new_serialno('service')
        service_node = nodes.section(ids=[service_id])
        service_node += nodes.title(text='Service at %s' %
                                    service.route_name)

        if service.description is not None:
            service_node += rst2node(trim(service.description))

        for method, info in methods.items():
            method_id = '%s-%s' % (service_id, method)
            method_node = nodes.section(ids=[method_id])
            method_node += nodes.title(text=method)

            if 'attr' in info:
                docstring = getattr(info['func'], info['attr']).__doc__ or ""
            else:
                docstring = info['func'].__doc__ or ""

            docstring = trim(docstring) + '\n'

            if method in service.schemas:
                schema = service.schemas[method]

                attrs_node = nodes.inline()
                for location in ('headers', 'querystring', 'body'):
                    attributes = schema.get_attributes(location=location)
                    if attributes:
                        attrs_node += nodes.inline(
                                text='values in the %s' % location)
                        location_attrs = nodes.bullet_list()

                        for attr in attributes:
                            temp = nodes.list_item()
                            desc = "%s : " % attr.name

                            if hasattr(attr, 'type'):
                                desc += " %s, " % attr.type

                            if attr.required:
                                desc += "required "
                            else:
                                desc += "optional "

                            temp += nodes.inline(text=desc)
                            location_attrs += temp

                        attrs_node += location_attrs
                method_node += attrs_node

            if 'validators' in info:
                for validator in info['validators']:
                    if validator.__doc__ is not None:
                        if docstring is not None:
                            doc = trim(validator.__doc__)
                            docstring += '\n' + doc

            if 'accept' in info:
                accept = info['accept']

                if callable(accept):
                    if accept.__doc__ is not None:
                        docstring += accept.__doc__.strip()
                else:
                    accept = to_list(accept)

                    accept_node = nodes.strong(text='Accepted content types:')
                    node_accept_list = nodes.bullet_list()
                    accept_node += node_accept_list

                    for item in accept:
                        temp = nodes.list_item()
                        temp += nodes.inline(text=item)
                        node_accept_list += temp

                    method_node += accept_node

            node = rst2node(docstring)
            DocFieldTransformer(self).transform_all(node)
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

    def _get_services(self, package, ignore):
        from pyramid.config import Configurator
        conf = Configurator()
        conf.include('cornice')
        conf.scan(package, ignore=ignore)
        by_service = defaultdict(dict)
        apidocs = conf.registry.settings.get('apidocs', {})

        for (path, method), apidoc in apidocs.items():
            service = apidoc['service']
            by_service[path, service][method] = apidoc

        return by_service

    def run(self):
        env = self.state.document.settings.env
        # getting the options
        pkg = self.options['package']
        service_name = self.options.get('service')
        ignore = self.options.get('ignore', '')
        ignore = [str(ign.strip()) for ign in ignore.split(',')]
        all_services = service_name is None

        # listing the services for the package
        services = self._get_services(pkg, ignore)

        if all_services:
            # we want to list all of them
            services_id = "services-%d" % env.new_serialno('services')
            services_node = nodes.section(ids=[services_id])
            services_node += nodes.title(text='Services')

            services_ = [(service.index, path, service, methods) \
                         for (path, service), methods in services.items()]
            services_.sort()

            for _, path, service, methods in services_:
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
