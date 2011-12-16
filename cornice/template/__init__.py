from paste.script.templates import Template, var

vars = [
    var('appname', 'Application name'),
    var('description', 'One-line description of the project'),
    var('author', 'Author name')]


class AppTemplate(Template):

    _template_dir = 'cornice'
    summary = "A Cornice application"
    vars = vars

    def post(self, command, output_dir, vars):
        if command.verbose:
            print('Generating Application...')
