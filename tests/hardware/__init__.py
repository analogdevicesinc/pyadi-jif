"""Hardware-in-the-loop validation tests for pyadi-jif JESD models.

These tests boot (or attach to) real ADI evaluation systems exposed by a
labgrid coordinator, read the JESD link + clock facts the running hardware
reports, and assert that pyadi-jif's solver reproduces those facts.

They are marked ``@pytest.mark.hardware`` and skipped unless ``--run-hardware``
is given. See ``conftest.py`` for options.
"""
