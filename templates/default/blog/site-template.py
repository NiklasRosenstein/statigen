
from datetime import datetime

def init(context):
  context.config.setdefault('site.dateFormat', '%d %b %Y')

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
