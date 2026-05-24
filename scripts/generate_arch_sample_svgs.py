"""Generate the per-architecture sample SVGs embedded in the docs.

Run from the repo root with the project's venv activated:

    .venv/bin/python scripts/generate_arch_sample_svgs.py

Writes four SVGs into doc/source/clocking/imgs/. Safe to re-run; the
files are overwritten each time.
"""

from pathlib import Path

from adijif.plls.utils.adf4030_arch import (
    ARCHITECTURES,
    Adf4030Architecture,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "doc" / "source" / "clocking" / "imgs"

COMMON = {"N": 16, "N_Apollo": 8, "N_FPGA": 1}


def main() -> None:
    """Render one per-Unit-Board SVG per architecture."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for arch in ARCHITECTURES:
        extra = {"N_branch": 2} if arch != "cascade" else {}
        a = Adf4030Architecture(architecture=arch, **COMMON, **extra)
        out = OUT_DIR / f"adf4030_{arch}_ub.svg"
        a.draw(scope="ub", path=str(out))
        print(f"wrote {out.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
