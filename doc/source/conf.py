# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import datetime
import os
import sys


sys.path.insert(0, os.path.abspath("../.."))
sys.setrecursionlimit(1500)

# p = os.path.join("_static", "imgs")
# if not os.path.exists(p):
#     os.mkdir("_static/imgs")

# for filename in os.listdir(os.path.join("_static", "imgs")):
#     if filename.endswith(".png") and "PyADI-JIF_logo" in filename:
#         fn = os.path.join("_static", "imgs", filename)
#         from PIL import Image

#         im = Image.open(fn)
#         # Remove left 30% of image
#         im = im.crop((int(im.size[0] * 0.45), 0, int(im.size[0] * 1), im.size[1]))

#         # Add 10% of space to bottom
#         im = im.crop(
#             (
#                 int(im.size[0] * 0),
#                 0,
#                 int(im.size[0] * 1),
#                 int(im.size[1] * 1.50),
#             )
#         )
#         im.save(fn.replace(".png", "_cropped.png"))


project = 'pyadi-jif'

year = datetime.datetime.now().year
copyright = f'2020-{year}, Analog Devices Inc.'
author = 'Travis F. Collins, PhD'
release = 'v0.0.1'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.coverage",
    "sphinx.ext.githubpages",
    "myst_parser",
    "sphinxcontrib.mermaid",
    "adi_doctools",
    "sphinx_exec_code",
]

needs_extensions = {"adi_doctools": "0.3.36"}

myst_enable_extensions = ["colon_fence"]

templates_path = ['_templates']
exclude_patterns = []

# -- External docs configuration ----------------------------------------------

interref_repos = ["doctools"]

# -- Custom extensions configuration ------------------------------------------

hide_collapsible_content = True

# -- Options for PDF output --------------------------------------------------
if os.path.exists(os.path.join("_themes", "pdf_theme")):
    extensions.append("sphinx_simplepdf")
    html_theme_path = ["_themes"]
    simplepdf_theme = "pdf_theme"

# -- Options for HTML output -------------------------------------------------

html_theme = "cosmic"
html_favicon = os.path.join("_static", "favicon.png")


# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

html_css_files = [
    "css/style.css",
]

html_theme_options = {
    "light_logo": os.path.join("imgs", "PyADI-JIF_logo_cropped.png"),
    "dark_logo": os.path.join("imgs", "PyADI-PyADI-JIF_logo_w_cropped.png"),
}