# flake8: noqa
import pathlib
import runpy

import pytest

ignore = ["daq2_rx_dt_example.py"]

examples_in_dir = pathlib.Path(__file__).parent.parent / "examples"
examples = [str(p) for p in examples_in_dir.glob("*.py")]
examples = [e for e in examples for i in ignore if i not in e]


@pytest.mark.parametrize("script", examples)
def test_example_execution(script):
    runpy.run_path(script)
