# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# Contributors: Vincent Fretin
"""
Sphinx extension that is able to convert a service into a documentation.
"""
import sys
from importlib import import_module

from docutils import nodes
from docutils.parsers.rst import Directive, directives

from sphinx.util.docfields import DocFieldTransformer

from cornice.util import rst2node, to_list
from cornice.service import get_services


def convert_to_list(argument):
    """Convert a comma separated list into a list of python values"""
    if argument is None:
        return []
    else:
        return [i.strip() for i in argument.split(',')]


def convert_to_list_required(argument):
    if argument is None:
        raise ValueError('argument required but none supplied')
    return convert_to_list(argument)


class ServiceDirective(Directive):
    """ Service directive.

    Injects sections in the documentation about the services registered in the
    given module.

    Usage, in a sphinx documentation::

        .. service::
            :modules: your.module
            :services: name1, name2
            :service: name1 # no need to specify both services and service.
            :ignore: a comma separated list of services names to ignore
    """
    has_content = True
    option_spec = {'modules': convert_to_list_required,
                   'service': directives.unchanged,
                   'services': convert_to_list,
                   'ignore': convert_to_list}
    domain = 'cornice'
    doc_field_types = []

    def __init__(self, *args, **kwargs):
        super(ServiceDirective, self).__init__(*args, **kwargs)
        self.env = self.state.document.settings.env

    def run(self):
        # import the modules, which will populate the SERVICES variable.
        for module in self.options.get('modules'):
            import_module(module)

        names = self.options.get('services')

        service = self.options.get('service')
        if service is not None:
            names.append(service)

        # filter the services according to the options we got
        services = get_services(names=names,
                                exclude=self.options.get('exclude'))

        for service in services:
            self._render_service(service)

        return [self._render_service(s) for s in services]

    def _render_service(self, service):
        service_id = "service-%d" % self.env.new_serialno('service')
        service_node = nodes.section(ids=[service_id])
        service_node += nodes.title(text='Service at %s' % service.path)

        if service.description is not None:
            service_node += rst2node(trim(service.description))

        for method, view, args in service.definitions:
            method_id = '%s-%s' % (service_id, method)
            method_node = nodes.section(ids=[method_id])
            method_node += nodes.title(text=method)

            docstring = trim(view.__doc__ or "") + '\n'

            if 'schema' in args:
                schema = args['schema']

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

            for validator in args.get('validators', ()):
                if validator.__doc__ is not None:
                    docstring += trim(validator.__doc__)

            if 'accept' in args:
                accept = to_list(args['accept'])

                if callable(accept):
                    if accept.__doc__ is not None:
                        docstring += accept.__doc__.strip()
                else:
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

            renderer = args['renderer']
            if renderer == 'simplejson':
                renderer = 'json'

            response = nodes.paragraph()

            response += nodes.strong(text='Response: %s' % renderer)
            method_node += response

            service_node += method_node

        return service_node


# Utils


def trim(docstring):
    """
    Remove the tabs to spaces, and remove the extra spaces / tabs that are in
    front of the text in docstrings.

    Implementation taken from http://www.python.org/dev/peps/pep-0257/
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


def setup(app):
    """Sphinx setup."""
    app.add_directive('services', ServiceDirective)
