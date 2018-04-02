+++
title = "Getting Started"
ordering = 1
+++

## Installing Statigen

  [PyPI]: https://pypi.python.org/pypi

Statigen can be installed from [PyPI] via Pip.

    pip install statigen

Once the installation is complete, try the following command to see if it
worked:

    statigen --version

## Starting a project

Create a directory where you want your page source and configuration files to
live in, then create a `.statigen.toml` file and specify your site template
and title.

```
$ mkdir mysite && cd mysite
$ cat > .statigen.toml <<EOF
[statigen]
template = "default/docs"

[site]
title = "My Site"
EOF
```

> Statigen comes with the following templates out of the box:
>
> * [default/blog](./templates/blog)
> * [default/docs](./templates/docs) (the one you are looking at right now)

Now create a bunch of `.md` files in the same directory. The section enclosed
in `+++` will be parsed as TOML and allows you to define properties in a file
that may be respected by the template.

```
$ cat > index.md <<EOF
+++
title = "Home"
renderTitle = false
ordering = 0
+++
# Welcome to my page!
EOF
$ cat > another.md <<EOF
+++
title = "Another Page"
ordering = 1
+++
Here's another page!
EOF
```

## Building the site

Producing the static HTML site is as simple as running `statigen` from the
command-line.

```
$ statigen
rendering build/index.html (/)
rendering build/another.html (/another)
copying static ==> build/static (/static)
  from /home/niklas/.local/lib/python3.6/site-packages/statigen/templates/default/docs/static
```
