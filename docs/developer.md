+++
title = "Developer Documentation"
+++

## Site Templates

Site templates define the structure and looks of the generated static HTML
page. A site template is usually a Python script that implements at least
a `render(context)` function. It may also implement the following functions:

* `init(context)`
* `content_loaded(context, content)`

The `render()` function, when called, must use the `statigen.Context` API
to produce HTML pages. Below is a simple template that renders all content
files with the same `page.html` template (not recursive).

```python
def render(context):
  pages = context.load_content_from_directory('.')
  pages.sort(key=lambda p: (
    p.config.get('ordering', 999), p.config.get('title', p.name)))
  for i, page in enumerate(pages):
    url = '/' if i == 0 else '/' + p.name
    context.render(url, 'page.html', page=page, pages=pages)
  context.copy('/static', 'static')
```

## Template Renderers

Template renderers implement the rendering of the HTML template files that a
Site Template delivers. The default renderer expects Jinja templates. Below is
a simple template that plays with the site-template displayed above.

{% raw %}
```html
<!DOCTYPE html>
<html>
  <head>
    <title>{{ page.config.get('title', p.name) }}</title>
    <link href="{{ url_for('/static/style.css') }}" rel="stylesheet">
  </head>
  <body>
    <ul>
      {% for p in pages %}
      <li class="{{ 'active' if p == page else '' }}">
        <a href="{{ url_to('/' + p.name) }}">{{ p.config.get('title', p.name) }}</a>
      </li>
      {% endfor %}
    </ul>
    <h1>{{ page.config.get('title', p.name) }}</h1>
    {{ page.render()|safe }}
  </body>
</html>
```
{% endraw %}

## Content Loaders

Content loaders implement loading `statigen.Content` objects from a Content ID
or from a directory relative to the content directory. The default loader
expects `.md` (Markdown) files and passes the first section enclosed in `+++`
to TOML.

Below is an example content file `home.md` which could be used with the
site-template and template renderer displayed above.

```
+++
title = "Home"
ordering = 0
+++

Welcome to my first site generated with Statigen!
```

## Content Renderers

Content renderers take the content delivered by a Content loader and renders
it. The default renderer uses the Python Markdown module and renders it with
all extensions enabled.
