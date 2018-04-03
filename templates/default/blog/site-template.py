
from datetime import datetime
from jinja2 import Markup

def vimeo(id):
  return Markup('''
  <div style="position: relative; padding-bottom: 56.25%; padding-top: 30px; height: 0; overflow: hidden;">
    <iframe src="https://player.vimeo.com/video/{}" style="border: none; position: absolute; top: 0; left: 0; width: 100%; height: 100%;" webkitallowfullscreen mozallowfullscreen allowfullscreen></iframe>
  </div>
  '''.format(id))

def gist(user, gist_id, filename=None):
  path = '{}/{}.js'.format(user, gist_id)
  if filename:
    path += '?' + str(filename)
  code = '<script src="https://gist.github.com/{}" type="text/javascript"></script>'
  return Markup(code.format(path))

def init(context):
  context.config.setdefault('site.dateFormat', '%d %b %Y')
  context.globals['vimeo'] = vimeo
  context.globals['gist'] = gist

def content_loaded(context, content):
  if 'date' in content.config:
    content.config['date'] = datetime.strptime(content.config['date'], '%Y-%m-%d')

def render(context):
  pages = context.load_content_from_directory('.')
  pages.sort(key=lambda p: (p.config.get('ordering', 9999), p.config.get('title', p.name)))
  context.globals['pages'] = pages

  # Set the page URLs.
  if not any('/' == p.config.get('url') for p in pages):
    for page in pages:
      if 'url' not in page.config:
        page.config['url'] = '/'
        break
  for page in pages:
    page.config.setdefault('url', '/' + page.name)

  for page in pages:
    url = page.config['url']
    posts_dir = page.config.get('displayPostsFrom')
    if posts_dir:
      posts = context.load_content_from_directory(posts_dir)
      posts = [x for x in posts if not x.config.get('draft')]
      posts.sort(key=lambda p: p.config.get('date', datetime.now()), reverse=True)
      context.render(url, 'blog.html', page=page, posts=posts)
      for post in posts:
        context.render('{}/{}'.format(url, post.name), 'post.html', post=post)
        context.copy_assets('{}/{}'.format(url, post.name), post)
    else:
      context.render(url, 'page.html', page=page)

  context.copy('/static', 'static')
