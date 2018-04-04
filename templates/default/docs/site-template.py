
def _load_page_tree(context):
  root_pages = context.load_content_from_directory('.')
  sort_key = lambda p: (p.config.get('ordering', 9999), p.config['title'].lower())
  def recursion(parent, page):
    path = '{}/{}'.format(parent, page.name)
    try:
      page.children = context.load_content_from_directory(path)
    except FileNotFoundError:
      page.children = []
    for child in page.children:
      child.parent = page
      child.url = page.url + '/' + child.name
      recursion(path, child)
    page.children.sort(key=sort_key)
  for page in root_pages:
    page.parent = None
    page.url = '/' + page.name
    recursion('.', page)
  root_pages.sort(key=sort_key)
  return root_pages

def _traverse(pages):
  yield from pages
  for page in pages:
    yield from _traverse(page.children)

def render(context):
  pages = _load_page_tree(context)
  index_page = next((p for p in pages if p.name == 'index'), None)
  if not index_page:
    raise Exception('no index page')
  index_page.url = '/'

  for page in _traverse(pages):
    context.render(page.url, 'page.html', page=page, pages=pages)
  context.copy('/static', 'static')

def content_loaded(context, page):
  page.config.setdefault('title', page.name)
