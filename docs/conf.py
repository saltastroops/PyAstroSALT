import os
import sys
sys.path.insert(0, os.path.abspath("../src"))

project = 'saltastro'
copyright = '2022, Southern African Large Telescope'
author = 'Southern African Large Telescope'
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "myst_nb"
]
templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']
html_static_path = ['_static']
default_role = 'py:obj'
myst_enable_extensions = [
    "colon_fence"
]
myst_url_schemes = ["http", "https"]
html_theme = "sphinx_book_theme"
html_sidebars = {
    "**": ["sbt-sidebar-nav.html", "sbt-sidebar-footer.html"]
}
intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'numpy': ('https://numpy.org/doc/stable/', None),
    'scipy': ('https://docs.scipy.org/doc/scipy/reference/', None),
    'matplotlib': ('https://matplotlib.org/', None),
    'astropy': ('https://docs.astropy.org/en/stable/', None)
}
