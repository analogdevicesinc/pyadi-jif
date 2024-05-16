# flake8: noqa
import os
import pathlib
import runpy

import pytest

ignore = ["daq2_rx_dt_example.py", "hmc7044_example.ipynb"]

examples_dir = os.path.join(pathlib.Path(__file__).parent.parent, "examples")
examples_dir = pathlib.Path(examples_dir)
examples = [str(p) for p in examples_dir.glob("*.py")]
filenames = [os.path.basename(i) for i in examples]
filenames = [i for i in filenames if i not in ignore]
examples = [os.path.join(examples_dir, i) for i in filenames]


@pytest.mark.parametrize("script", examples)
def test_example_execution(script):
    runpy.run_path(script)
