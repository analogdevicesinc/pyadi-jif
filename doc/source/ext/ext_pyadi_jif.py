"""Repository Sphinx extension.

* Make a copy of the logos with only the pyadi-jif section.
"""

from os import chdir, listdir, mkdir, path

from PIL import Image
from sphinx.application import Sphinx
from sphinx.util import logging
from sphinx.util.fileutil import copy_asset_file

logger = logging.getLogger(__name__)


def builder_inited(app: Sphinx) -> None:
    """Extract pyadi-jif section of the logo and save it."""
    chdir(app.builder.srcdir)

    outdir = app.builder.outdir
    for p in ["_static", "logos"]:
        outdir = path.join(outdir, p)
        if not path.exists(outdir):
            mkdir(outdir)

    def copy_asset(app: Sphinx, src: str, fname: str) -> str:
        src_uri = path.abspath(path.join(src, fname))
        build_uri = path.join(outdir, fname)
        copy_asset_file(src_uri, build_uri)
        return build_uri

    # Move logos over to doc build directory
    for filename in listdir("imgs"):
        if "logo" not in filename or not filename.endswith(".png"):
            continue

        fn = copy_asset(app, "imgs", filename)

        im = Image.open(fn)
        # Remove left 30% of image
        im = im.crop((int(im.size[0] * 0.45), 0, int(im.size[0] * 1), im.size[1]))
        im.save(fn.replace(".png", "_cropped.png"))


def setup(app: Sphinx) -> None:
    """Add repository extension."""
    app.connect("builder-inited", builder_inited)

    return {
        "parallel_read_safe": True,
        "parallel_write_safe": True,
        "version": "0.1",
    }
