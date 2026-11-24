#!/usr/bin/env python3
"""Extracts license metadata/text from every wheel in a directory.

Invoked by scripts/collect-licenses.mjs (Node has no zip-reading in the
stdlib without a dependency; python3 is already a hard build-time
prerequisite for fetch-wheels.mjs's cross-platform wheel resolution, so
this reuses it rather than adding an npm dependency).

Prints a JSON array to stdout: one object per wheel with whatever license
metadata/text could be found. Embedded license text (when present) is
authoritative; collect-licenses.mjs falls back to a small bundled table of
full license texts keyed by SPDX identifier for wheels that only carry a
License/Classifier field with no embedded file.
"""

import glob
import json
import os
import re
import sys
import zipfile

LICENSE_FILE_RE = re.compile(r"(^|/)(LICENSE|LICENCE|COPYING|NOTICE)(\.[A-Za-z0-9]+)?$", re.IGNORECASE)


def parse_metadata(text):
    name = version = license_expr = None
    classifiers = []
    license_files = []
    for line in text.splitlines():
        if line.startswith("Name:"):
            name = line.split(":", 1)[1].strip()
        elif line.startswith("Version:"):
            version = line.split(":", 1)[1].strip()
        elif line.startswith("License:"):
            value = line.split(":", 1)[1].strip()
            if value and value.lower() not in ("unknown", ""):
                license_expr = value
        elif line.startswith("Classifier: License"):
            classifiers.append(line.split(":", 1)[1].strip())
        elif line.startswith("License-File:"):
            license_files.append(line.split(":", 1)[1].strip())
    return name, version, license_expr, classifiers, license_files


def find_license_text(zf, names, dist_info_prefix, license_files):
    # Modern wheels (PEP 639 / recent setuptools-scm etc.): dist-info/licenses/*
    # - but that directory can also hold non-license files (AUTHORS.rst,
    # NOTICE, etc., e.g. pyadi-jif's own wheel ships both LICENSE and
    # AUTHORS.rst there) - filter to actual license-looking filenames first,
    # only falling back to "everything in that directory" if none match.
    licenses_dir = [n for n in names if n.startswith(dist_info_prefix + "/licenses/")]
    candidates = [n for n in licenses_dir if LICENSE_FILE_RE.search(n)]
    if not candidates:
        candidates = licenses_dir
    # Explicit License-File metadata entries relative to dist-info.
    if not candidates:
        for lf in license_files:
            candidate = f"{dist_info_prefix}/{lf}"
            if candidate in names:
                candidates.append(candidate)
    # Older convention: a LICENSE/COPYING file at the wheel/package root.
    if not candidates:
        candidates = [n for n in names if LICENSE_FILE_RE.search(n) and n.count("/") <= 2]
    texts = []
    for candidate in candidates:
        try:
            texts.append(zf.read(candidate).decode("utf-8", errors="replace"))
        except KeyError:
            pass
    return "\n\n".join(texts) if texts else None


def main(wheel_dir):
    results = []
    for whl_path in sorted(glob.glob(os.path.join(wheel_dir, "*.whl"))):
        try:
            with zipfile.ZipFile(whl_path) as zf:
                names = zf.namelist()
                metadata_name = next((n for n in names if n.endswith(".dist-info/METADATA")), None)
                if metadata_name is None:
                    continue
                metadata_text = zf.read(metadata_name).decode("utf-8", errors="replace")
                name, version, license_expr, classifiers, license_files = parse_metadata(metadata_text)
                dist_info_prefix = metadata_name.rsplit("/", 1)[0]
                license_text = find_license_text(zf, names, dist_info_prefix, license_files)
                results.append(
                    {
                        "name": name,
                        "version": version,
                        "license_expr": license_expr,
                        "classifiers": classifiers,
                        "license_text": license_text,
                        "wheel": os.path.basename(whl_path),
                    }
                )
        except zipfile.BadZipFile:
            continue
    print(json.dumps(results))


if __name__ == "__main__":
    main(sys.argv[1])
