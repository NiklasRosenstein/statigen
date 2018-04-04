
import setuptools

with open('requirements.txt') as fp:
  requirements = fp.readlines()

setuptools.setup(
  name = 'statigen',
  version = '1.0.1',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  license = 'MIT',
  description = 'Statigen is a minimal, customizable static site generator.',
  url = 'https://github.com/NiklasRosenstein/statigen',
  install_requires = requirements,
  entry_points = dict(
    console_scripts = [
      'statigen = statigen:_entry_point'
    ]
  )
)
