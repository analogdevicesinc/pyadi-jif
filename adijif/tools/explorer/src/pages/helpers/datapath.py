"""Helper functions for datapath configuration UI elements."""

import streamlit as st

from adijif.converters import converter as conv


def gen_datapath(converter: conv) -> int:
    """Generate datapath configuration UI elements for Streamlit.

    Args:
        converter: The converter object to generate the datapath for.

    Returns:
        The selected decimation or interpolation value.

    Raises:
        Exception: If no interpolation setting is found for DACs.
    """
    if converter.converter_type.lower() == "adc":
        decimation = 1
        if converter.datapath:
            if hasattr(converter.datapath, "cddc_decimations_available"):
                options = converter.datapath.cddc_decimations_available
                cddc_decimation = st.selectbox(
                    "CDDC Decimation",
                    options=options,
                    format_func=lambda x: str(x),
                    key="datapath_cddc_decimation_select",
                )
                decimation = cddc_decimation
                v = len(converter.datapath.cddc_decimations)
                converter.datapath.cddc_decimations = [cddc_decimation] * v
            if hasattr(converter.datapath, "fddc_decimations_available"):
                options = converter.datapath.fddc_decimations_available
                fddc_decimation = st.selectbox(
                    "FDDC Decimation",
                    options=options,
                    format_func=lambda x: str(x),
                    key="datapath_fddc_decimation_select",
                )
                decimation *= fddc_decimation
                v = len(converter.datapath.fddc_decimations)
                converter.datapath.fddc_decimations = [fddc_decimation] * v
        elif hasattr(converter, "decimation_available"):
            decimation = st.selectbox(
                "Decimation",
                options=converter.decimation_available,
                format_func=lambda x: str(x),
                key="datapath_decimation_select",
            )
            decimation = int(decimation)
            converter.decimation = decimation
    else:
        interpolation = 1
        if converter.datapath:
            if hasattr(converter.datapath, "cduc_interpolations_available"):
                options = converter.datapath.cduc_interpolations_available
                cduc_interpolation = st.selectbox(
                    "CDUC Interpolation",
                    options=options,
                    format_func=lambda x: str(x),
                    key="datapath_cduc_interpolation_select",
                )
                interpolation = cduc_interpolation
                converter.datapath.cduc_interpolation = cduc_interpolation
            if hasattr(converter.datapath, "fduc_interpolations_available"):
                options = converter.datapath.fduc_interpolations_available
                fduc_interpolation = st.selectbox(
                    "FDUC Interpolation",
                    options=options,
                    format_func=lambda x: str(x),
                    key="datapath_fduc_interpolation_select",
                )
                interpolation *= fduc_interpolation
                converter.datapath.fduc_interpolation = fduc_interpolation
        elif hasattr(converter, "interpolation_available"):
            interpolation = st.selectbox(
                "Interpolation",
                options=converter.interpolation_available,
                format_func=lambda x: str(x),
                key="datapath_interpolation_select",
            )
            interpolation = int(interpolation)
            converter.interpolation = interpolation
        else:
            raise Exception("No interpolation setting found")

        decimation = interpolation

    return decimation
