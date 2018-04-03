# The MIT License (MIT)
#
# Copyright (c) 2018 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
"""
Statigen is a minimal, customizable static site generator.
"""

__version__ = '1.0.0'
__author__ = 'Niklas Rosenstein <rosensteinniklas@gmail.com>'

from nr import path
from nr.datastructures.mappings import ChainDict
from distutils.dir_util import copy_tree

import abc
import io
import jinja2
import markdown
import os
import posixpath
import shutil
import six
import sys
import toml
import types

##
# Abstract Interfaces
##

class ContentLoader(six.with_metaclass(abc.ABCMeta)):

  @abc.abstractmethod
  def load_content(self, context, name):
    """
    Load the content for the specified *name* and return a #Content object.
    """

  @abc.abstractmethod
  def load_content_from_directory(self, context, directory):
    """
    Load all content in the specified *directory*.
    """


class ContentRenderer(six.with_metaclass(abc.ABCMeta)):

  @abc.abstractmethod
  def render_content(self, context, content):
    """
    Render the #Content object *content* to HTML.
    """


class TemplateRenderer(six.with_metaclass(abc.ABCMeta)):

  @abc.abstractmethod
  def render_template(self, context, template, vars):
    """
    Render the template from the specified *template* to HTML. The renderer
    may search the template in the #Context.template_directory.
    """


class SiteTemplate(six.with_metaclass(abc.ABCMeta)):
  """
  This interface represents a site template.
  """

  @abc.abstractmethod
  def get_main_directory(self, context):
    """
    Return the templates main directory, where #copy() instructions will be
    handled from.
    """

  @abc.abstractmethod
  def get_template_directory(self, context):
    """
    Return the directory where the #TemplateLoader can look for templates.
    """

  @abc.abstractmethod
  def init(self, context):
    """
    Called when the #Context is created.
    """

  @abc.abstractmethod
  def content_loaded(self, context, content):
    """
    Called when a #Content object was loaded.
    """

  @abc.abstractmethod
  def render(self, context):
    """
    This method should do calls to #Context.render() to build the static site.
    """


##
# Concrete Implementations
##

class MarkdownTomlContentLoader(ContentLoader):

  def _load_file(self, context, filename, name):
    with io.open(filename, encoding=context.content_encoding) as fp:
      content = fp.read()
    if content.lstrip().startswith('+++'):
      index = content.find('+++') + 3
      lines = content[index:].split('\n')
      toml_content = ''
      while lines and lines[0].strip() != '+++':
        toml_content += lines.pop(0) + '\n'
      lines.pop(0)
      content = '\n'.join(lines)
      config = toml.loads(toml_content)
    else:
      config = {}
    return Content(context, filename, name, config, content)

  def load_content(self, context, name):
    filename = path.join(context.config['statigen.contentDirectory'], name + '.md')
    return self._load_file(context, filename, path.base(name))

  def load_content_from_directory(self, context, directory):
    for filename in os.listdir(directory):
      if filename.endswith('.md'):
        name = filename[:-3]
        filename = path.join(directory, filename)
        yield self._load_file(context, filename, name)


class MarkdownJinjaContentRenderer(ContentRenderer):

  # TODO: Support some special syntax for Jinja execution in the
  #       markdown file.

  def render_content(self, context, content):
    return markdown.markdown(content.body, ['extra'])


class JinjaTemplateRenderer(TemplateRenderer):

  def render_template(self, context, template, vars):
    loader = jinja2.FileSystemLoader([context.get_template_directory()])
    env = jinja2.Environment(loader=loader)
    template = env.get_template(template)
    return template.render(vars)


class PythonSiteTemplate(SiteTemplate):

  def __init__(self, module):
    self.module = module

  def get_main_directory(self, context):
    return path.dir(self.module.__file__)

  def get_template_directory(self, context):
    directory = getattr(self.module, 'template_directory', None)
    if directory is None:
      directory = path.join(path.dir(self.module.__file__), 'templates')
    return directory

  def init(self, context):
    if hasattr(self.module, 'init'):
      self.module.init(context)

  def content_loaded(self, context, content):
    if hasattr(self.module, 'content_loaded'):
      self.module.content_loaded(context, content)

  def render(self, context):
    return self.module.render(context)

  @classmethod
  def load(cls, name, parent_dir=None):
    """
    Loads a Python site template from a Python source file. Ensures that the
    loaded module has a `render()` function. The template will be searched for
    in the statigen templates directory or relative to the *parent_dir*.
    """

    parent_dir = parent_dir or os.getcwd()
    templates_dir = path.join(path.dir(__file__), 'templates')

    def find_template():
      for dirname in [parent_dir, templates_dir]:
        for choice in [name, name + '.py', path.join(name, 'site-template.py')]:
          filename = path.join(dirname, choice)
          if path.isfile(filename):
            return filename

    filename = find_template()
    if not filename:
      # TODO: Proper exception type
      raise ValueError('Template not found: {!r}'.format(name))

    with open(filename) as fp:
      code = fp.read()

    module = types.ModuleType(path.base(name))
    module.__file__ = filename

    six.exec_(compile(code, filename, 'exec'), vars(module))
    if not callable(getattr(module, 'render', None)):
      # TODO: Proper exception type
      raise ValueError('Template {!r} has no render() function or render is not callable'.format(name))

    return cls(module)


##
# Static site generation logic and configuration
##

class Config(object):
  """
  Wraps a dictionary that may contain nested values. Values in nested
  dictionaries can be retrieved by separating keys by dots.
  """

  class _Item(object):
    def __init__(self, full_key, last_part, container):
      self._full_key = full_key
      self._last_part = last_part
      self._container = container
    def __repr__(self):
      return '<Config._Item {!r}>'.format(self._full_key)
    def __bool__(self):
      if self._last_part is None:
        return False
      else:
        return self._last_part in self._container
    def get(self, default=NotImplemented):
      if self._last_part is None:
        if self._container is None:
          return default
        return self._container
      else:
        try:
          return self._container[self._last_part]
        except KeyError:
          if default is NotImplemented:
            raise KeyError(self._full_key)
      return default
    def set(self, value):
      if self._last_part is not None:
        self._container[self._last_part] = value
      else:
        raise KeyError(self._full_key)
    def pop(self, default=NotImplemented):
      if self._last_part is not None:
        if default is NotImplemented:
          return self._container.pop(self._last_part)
        else:
          return self._container.pop(self._last_part, default)
      else:
        raise KeyError(self._full_key)
    @classmethod
    def invalid(cls, full_key):
      return cls(full_key, None, None)

  def __init__(self, data):
    self._data = data

  def option(self, key, create_intermediate=False):
    container = self._data
    parts = key.split('.')
    for part in parts[:-1]:
      if part not in container:
        if not create_intermediate:
          return Config._Item.invalid(key)
        container[part] = {}
      container = container[part]
      if not isinstance(container, dict):
        return Config._Item.invalid(key)
    return Config._Item(key, parts[-1] if parts else None, container)

  def __getitem__(self, key):
    return self.option(key).get()

  def __setitem__(self, key, value):
    self.option(key, True).set(value)

  def __delitem__(self, key):
    self.option(key).pop()

  def __contains__(self, key):
    return bool(self.option(key))

  def setdefault(self, key, value):
    item = self.option(key, True)
    if item:
      return item.get()
    else:
      item.set(value)
      return value

  def get(self, key, default=None):
    return self.option(key).get(default)

  def pop(self, key, default=NotImplemented):
    return self.option(key).pop(default)


class Content(object):
  """
  A Content object represents a content source file that can be rendered and
  embedded into the body of a template. It may contain properties that can be
  taken into account by the template.
  """

  def __init__(self, context, filename, name, config, body):
    if not isinstance(config, Config):
      config = Config(config)
    self.context = context
    self.filename = path.norm(filename)
    self.name = name
    self.config = config
    self.body = body

  def __repr__(self):
    return 'Content(name={!r}, filename={!r})'.format(self.name, self.filename)

  def render(self):
    return self.context.content_renderer.render_content(self.context, self)


class Context(object):
  """
  The context contains all information required for the rendering process.
  """

  def __init__(self, config, site_template, content_loader=None,
               content_renderer=None, template_renderer=None):

    if not isinstance(config, Config):
      config = Config(config)
    self.config = config
    self.site_template = site_template
    self.content_loader = content_loader or MarkdownTomlContentLoader()
    self.content_renderer = content_renderer or MarkdownJinjaContentRenderer()
    self.template_renderer = template_renderer or JinjaTemplateRenderer()
    self.globals = {}

    self.config.setdefault('statigen.urlFormat', 'file')
    self.config.setdefault('statigen.contentDirectory', '.')
    self.config.setdefault('statigen.buildDirectory', 'build')
    self.config.setdefault('statigen.contentEncoding', 'utf8')
    self.config.setdefault('statigen.siteEncoding', 'utf8')

    self.content_encoding = self.config['statigen.contentEncoding']
    self.site_encoding = self.config['statigen.siteEncoding']

    self.site_template.init(self)

  def real_url(self, url, isfile=True):
    """
    Takes a basic URL and converts it to the real URL.
    """

    if not url.startswith('/'):
      raise ValueError('URL must start with a slash')
    is_dir_format = (self.config['statigen.urlFormat'] == 'directory')
    if url == '/':
      return '/' if is_dir_format else '/index.html'
    url = posixpath.normpath(url).rstrip('/')
    if is_dir_format or not isfile:
      return url
    else:
      return url + '.html'

  def url_to_filename(self, url, isfile=True):
    """
    Takes a basic URL and converts it to the actualy filename relative to
    the build directory.
    """

    url = self.real_url(url, isfile)
    if url == '/':
      return 'index.html' if isfile else '/'

    url = url.lstrip('/')
    if isfile and self.config['statigen.urlFormat'] == 'directory':
      return url + '/index.html'
    return url

  def url_to_abs_filename(self, url, isfile=True):
    build_dir = self.config['statigen.buildDirectory']
    return path.canonical(self.url_to_filename(url, isfile), build_dir)

  def url_to(self, source, target, isfile=True):
    source = self.real_url(source, isfile)
    target = self.real_url(target, isfile)
    res = posixpath.relpath(target, posixpath.dirname(source))
    #print('{} ==> {} :: {}'.format(source, target, res))
    return res

  def render(self, __url, __template, **vars):
    """
    Renders a template for a URL into the build directory.
    """

    filename = self.url_to_abs_filename(__url)
    print('rendering {} ({})'.format(filename, __url))

    vars.setdefault('context', self)
    vars.setdefault('config', self.config)
    vars.setdefault('url_to', lambda x: self.url_to(__url, x))
    vars.setdefault('url_for', lambda x: self.url_to(__url, x, False))
    vars = ChainDict(vars, self.globals)

    path.makedirs(path.dir(filename))
    with io.open(filename, 'w', encoding=self.site_encoding) as fp:
      fp.write(self.template_renderer.render_template(self, __template, vars))

  def copy(self, url, source):
    """
    Copy the file or directory *source* from the site templates main directory
    so that it is available from the specified URL.
    """

    parent_dirs = [self.site_template.get_main_directory(self)]
    parent_dirs += [self.config['statigen.contentDirectory']]

    target = self.url_to_abs_filename(url, False)
    print('copying {} ==> {} ({})'.format(source, target, url))

    for dirname in parent_dirs:
      current = path.canonical(source, dirname)
      if path.exists(current):
        print('  from {}'.format(current))
        copy_tree(current, target)

  def load_content_from_directory(self, directory):
    if not path.isabs(directory):
      content_directory = self.config['statigen.contentDirectory']
      directory = path.join(content_directory, directory)
    result = []
    for content in self.content_loader.load_content_from_directory(self, directory):
      self.site_template.content_loaded(self, content)
      result.append(content)
    return result

  def load_content(self, name):
    content = self.content_loader.load_content(self, name)
    self.site_template.content_loaded(self, content)
    return content

  def get_template_directory(self):
    return self.site_template.get_template_directory(self)


##
# Generic helpers
##

def import_class(name):
  module, class_ = name.rpartition('.')[::2]
  return getattr(__import__(module, fromlist=[None]), class_)


##
# Main
##

def get_argument_parser(prog=None):
  import argparse
  parser = argparse.ArgumentParser(prog=prog)
  parser.add_argument('--version', action='version', version=__version__, help='Display the version and exit.')
  parser.add_argument('-c', '--config', help='Alternative configuration file.')
  parser.add_argument('-b', '--build-directory', help='Override build directory.')
  parser.add_argument('-t', '--template', help='Override template name.')
  parser.add_argument('-o', '--open', action='store_true', help='Open the index page after the build completed.')
  return parser


def main(argv=None, prog=None):
  parser = get_argument_parser(prog)
  args = parser.parse_args(argv)

  if not args.config and path.isfile('.statigen.toml'):
    args.config = '.statigen.toml'
  if args.config:
    with open(args.config) as fp:
      config = toml.load(fp)
  else:
    config = {}
  config = Config(config)

  if args.build_directory:
    config['statigen.buildDirectory'] = args.build_directory
  if args.template:
    config['statigen.template'] = args.template

  site_template = PythonSiteTemplate.load(config.get('statigen.template', 'default/docs'))
  context = Context(
    config = config,
    site_template = site_template,
    content_loader = import_class(config.get('contentLoader', __name__ + '.MarkdownTomlContentLoader'))(),
    content_renderer = import_class(config.get('contentRenderer', __name__ + '.MarkdownJinjaContentRenderer'))(),
    template_renderer = import_class(config.get('templateRenderer', __name__ + '.JinjaTemplateRenderer'))()
  )
  site_template.render(context)

  if args.open:
    import webbrowser
    webbrowser.open(path.join(config['statigen.buildDirectory'], 'index.html'))


_entry_point = lambda: sys.exit(main())


if __name__ == '__main__':
  _entry_point()
