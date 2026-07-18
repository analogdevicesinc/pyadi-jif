import pytest

from adijif.converters.ad9081_dp import ad9081_dp_rx
from adijif.converters.ad9088_dp import ad9088_dp_rx


@pytest.mark.parametrize(
    "datapath_type, cddc_count, fddc_index, source_cddc",
    [
        (ad9081_dp_rx, 4, 0, 1),
        (ad9088_dp_rx, 8, 8, 5),
    ],
)
def test_enabled_fddc_requires_enabled_source_cddc(
    datapath_type, cddc_count, fddc_index, source_cddc
):
    datapath = datapath_type()
    datapath.cddc_enabled = [True] * cddc_count
    datapath.cddc_enabled[source_cddc - 1] = False
    datapath.fddc_enabled = [False] * len(datapath.fddc_enabled)
    datapath.fddc_enabled[fddc_index] = True

    with pytest.raises(
        Exception,
        match=rf"Source CDDC {source_cddc} not enabled for FDDC {fddc_index}",
    ):
        _ = datapath.decimation_overall


def test_ad9088_default_cddc_settings_have_consistent_width():
    datapath = ad9088_dp_rx()

    assert len(datapath.cddc_enabled) == 8
    assert len(datapath.cddc_decimations) == 8
    assert len(datapath.cddc_nco_frequencies) == 8
    assert len(datapath.cddc_nco_phases) == 8
