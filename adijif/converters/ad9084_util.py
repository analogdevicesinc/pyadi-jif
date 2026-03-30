"""AD9084 MxFE Utility Functions."""

import json
import os
from typing import Dict, Union

import pandas as pd

from ..utils import get_jesd_mode_from_params
from .converter import converter


def _convert_to_config(
    mode: str,
    L: Union[int, float],
    M: Union[int, float],
    F: Union[int, float],
    S: Union[int, float],
    HD: Union[int, float],
    K: Union[int, float],
    N: Union[int, float],
    Np: Union[int, float],
    CS: Union[int, float],
    E: Union[int, float],
    global_index: Union[int, float],
    jesd_class: str,
) -> Dict:
    return {
        "L": L,
        "M": M,
        "F": F,
        "S": S,
        # "HD": 1 if F == 1 else 0,
        "Np": Np,
        "K": K,
        "HD": HD,
        "CS": CS,
        "E": E,
        "jesd_class": jesd_class,
        "global_index": global_index,
    }


def _load_rx_config_modes(part: str) -> Dict:
    """Load RX JESD configuration tables from file.

    Args:
        part (str): Part name, either "AD9084" or "AD9088".

    Returns:
        Dict: Dictionary of JESD configuration modes.

    Raises:
        AssertionError: If the part is not supported.
    """
    assert part in ["AD9084", "AD9088"], f"Unsupported part: {part}"
    return _read_table_xlsx(
        "AD9084_JTX_JRX.xlsx", part, sheet_name="JTX_RxPath"
    )


def _load_tx_config_modes(part: str) -> Dict:
    """Load TX JESD configuration tables from file.

    Args:
        part (str): Part name, either "AD9084" or "AD9088".

    Returns:
        Dict: Dictionary of JESD configuration modes.

    Raises:
        AssertionError: If the part is not supported.
    """
    assert part in ["AD9084", "AD9088"], f"Unsupported part: {part}"
    return _read_tx_table_xlsx(
        "AD9084_JTX_JRX.xlsx", part, sheet_name="JRX_TxPath"
    )


def _read_tx_table_xlsx(filename: str, part: str, sheet_name: str) -> Dict:
    r"""Parse TX-path JESD configuration table from an Excel file.

    The TX sheet uses different column names than the RX sheet
    ('Parameter\\n/Mode' instead of 'Mode', 'M ' instead of 'M',
    and \"N'\" instead of 'Np'), so it needs its own reader.

    Args:
        filename (str): Excel filename inside the resources directory.
        part (str): Part name, either "AD9084" or "AD9088".
        sheet_name (str): Worksheet name to read.

    Returns:
        Dict: Nested dict keyed by jesd class then mode number string.
    """
    loc = os.path.dirname(__file__)
    fn = os.path.join(loc, "resources", filename)
    table = pd.read_excel(open(fn, "rb"), sheet_name=sheet_name)

    # Normalize TX-specific column names to match the shared field names used
    # throughout the rest of the codebase.
    table = table.rename(
        columns={
            "Parameter\n/Mode": "Mode",
            "M ": "M",
            "N\u2019": "Np",
        }
    )

    modes_204b = {}
    modes_204c = {}
    for prow in table.iterrows():
        row = prow[1].to_dict()

        field = "8T8R" if part == "AD9088" else "4T4R"
        data = str(row[field])

        if "nan" in data:
            continue
        if "Not Supported" in data:
            continue

        modes_204c[str(int(row["Mode"]))] = {
            "L": row["L"],
            "M": row["M"],
            "F": row["F"],
            "S": row["S"],
            "HD": 1,
            "Np": row["Np"],
            "jesd_class": "jesd204c",
        }

    for mode, config in modes_204c.items():
        modes_204b[mode] = config.copy()
        modes_204b[mode]["jesd_class"] = "jesd204b"

    return {"jesd204b": modes_204b, "jesd204c": modes_204c}


def _read_table_xlsx(filename: str, part: str, sheet_name: str) -> Dict:
    loc = os.path.dirname(__file__)
    fn = os.path.join(loc, "resources", filename)
    table = pd.read_excel(open(fn, "rb"), sheet_name=sheet_name)

    # strip out unique JESD modes
    # table = table.drop_duplicates(subset=["JTX_MODE NUMBER"])
    jrx_modes_204b = {}
    jrx_modes_204c = {}
    for prow in table.iterrows():
        row = prow[1].to_dict()

        field = "8T8R" if part == "AD9088" else "4T4R"
        data = str(row[field])

        if "nan" in data:
            continue
        if "Not Supported" in data:
            continue

        jrx_modes_204c[str(row["Mode"])] = {
            "L": row["L"],
            "M": row["M"],
            "F": row["F"],
            "S": row["S"],
            "HD": 1,
            # 'K': row['K'],
            "Np": row["Np"],
            "DL": row["DL"],
            "jesd_class": "jesd204c",
        }

    # Copy settings to 204b
    for mode, config in jrx_modes_204c.items():
        jrx_modes_204b[mode] = config.copy()
        jrx_modes_204b[mode]["jesd_class"] = "jesd204b"
        # jrx_modes_204b[mode]["HD"] = 0  # HD is always 0 for 204b

    return {"jesd204b": jrx_modes_204b, "jesd204c": jrx_modes_204c}


def parse_json_config(
    profile_json: str, bypass_version_check: bool = False
) -> Dict:
    """Parse Apollo profiles and extract desired part information.

    Args:
        profile_json (str): Path to the profile JSON file.
        bypass_version_check (bool): If True, bypasses the version check for
            the profile.

    Returns:
        Dict: A dictionary containing parsed configuration data.

    Raises:
        FileNotFoundError: If the summary or profile JSON file does not exist.
        KeyError: If required keys are missing in the JSON data.
        Exception: If the profile is not supported or if it is a JESD204B profile.
    """
    use_summary = False  # cannot use summary for now as its broken in ACE
    summary_json = None  # Needed for lint
    if use_summary:
        if not os.path.exists(summary_json):
            raise FileNotFoundError(
                f"Summary JSON file does not exist: {summary_json}"
            )
    if not os.path.exists(profile_json):
        raise FileNotFoundError(
            f"Profile JSON file does not exist: {profile_json}"
        )
    full_profile_filename = os.path.abspath(profile_json)

    with open(full_profile_filename, "r") as f:
        profile_data = json.load(f)

    # Check version
    if not bypass_version_check:
        if (
            "profile_cfg" not in profile_data
            or "profile_version" not in profile_data["profile_cfg"]
        ):
            raise KeyError(
                f"ERROR {profile_json} because 'profile_cfg' "
                + f"key is missing in {profile_json}"
            )

        profile_version = profile_data["profile_cfg"]["profile_version"]
        if (
            profile_version["major"] != 9
            or profile_version["minor"] != 1
            or profile_version["patch"] != 0
        ):
            raise KeyError(
                f"ERROR {profile_json} because 'profile_version' is not "
                + f"supported: {profile_version}"
            )

    if use_summary:
        with open(summary_json, "r") as f:
            summary_data = json.load(f)

        summary_file = summary_json

    iduc = os.path.basename(profile_json)
    iduc = iduc.replace(".json", "")

    df_row = {
        "id": iduc,
        "profile_name": None,
        "device_clock_Hz": None,
        "core_clock_Hz": None,
        "common_lane_rate_Hz": None,
        "rx_jesd_mode": None,
        "tx_jesd_mode": None,
        # "failed_reason": None,
        "is_8t8r": None,
        "jesd_settings": None,
        "datapath": None,
        # "jif_model": None,
        # "dts_file": None,
        # "bin_filename": None,
        # "hdl_build_id": None,
    }

    if use_summary:
        if "is_8t8r" not in summary_data:
            raise Exception("AD9088 is not supported")

        if "is_8t8r" in summary_data and summary_data["is_8t8r"]:
            raise Exception("AD9088 is not supported")

    else:
        df_row["is_8t8r"] = profile_data["profile_cfg"]["is_8t8r"]
        if df_row["is_8t8r"]:
            raise Exception("AD9088 is not supported")

    if use_summary:
        device_clock_Hz = summary_data["general_info"]["device_clock_Hz"]
    else:
        device_clock_Hz = profile_data["clk_cfg"]["dev_clk_freq_kHz"] * 1000
    if device_clock_Hz is None:
        raise KeyError(
            f"Skipping {profile_data} because 'device_clock_Hz' key is missing"
        )
    df_row["device_clock_Hz"] = device_clock_Hz

    if use_summary:
        core_clock_Hz = summary_data["general_info"]["fpga_clock_Hz"]
        if core_clock_Hz is None:
            raise KeyError(
                f"Skipping {profile_data} because 'core_clock_Hz' key is missing"
            )
        df_row["core_clock_Hz"] = core_clock_Hz

    if use_summary:
        common_lane_rate_Hz = summary_data["general_info"][
            "common_lane_rate_Hz"
        ]
        if common_lane_rate_Hz is None:
            raise KeyError(
                f"Skipping {profile_data} because 'common_lane_rate_Hz' key is missing"
            )
    else:
        common_lane_rate_Hz = (
            profile_data["jtx"][0]["common_link_cfg"]["lane_rate_kHz"] * 1000
        )

    df_row["common_lane_rate_Hz"] = common_lane_rate_Hz

    # Parse datapath config
    path = 0
    if use_summary:
        cddc_decimation = summary_data["rx_routes"][path]["cdrc"]
        fddc_decimation = summary_data["rx_routes"][path]["fdrc"]
        cduc_interpolation = summary_data["tx_routes"][path]["cdrc"]
        fduc_interpolation = summary_data["tx_routes"][path]["fdrc"]
    else:
        cddc_decimation = profile_data["rx_path"][0]["rx_cddc"][0]["drc_ratio"]
        fddc_decimation = profile_data["rx_path"][0]["rx_fddc"][0]["drc_ratio"]
        cduc_interpolation = profile_data["tx_path"][0]["tx_cduc"][0][
            "drc_ratio"
        ]
        fduc_interpolation = profile_data["tx_path"][0]["tx_fduc"][0][
            "drc_ratio"
        ]

        if cddc_decimation == 0:
            cddc_decimation = 1
        elif cddc_decimation == 1:
            cddc_decimation = 2
        elif cddc_decimation == 2:
            cddc_decimation = 3
        elif cddc_decimation == 3:
            cddc_decimation = 4
        elif cddc_decimation == 4:
            cddc_decimation = 6
        elif cddc_decimation == 5:
            cddc_decimation = 12

        fddc_decimation = int(fddc_decimation)
        fddc_decimation = 2**fddc_decimation

        cduc_interpolation = int(cduc_interpolation)

        # THIS IS REALLY BIZARRE but how the profile gen works
        fduc_interpolation = int(fduc_interpolation)

    df_row["datapath"] = {
        "cddc_decimation": cddc_decimation,
        "fddc_decimation": fddc_decimation,
        "cduc_interpolation": cduc_interpolation,
        "fduc_interpolation": fduc_interpolation,
    }

    # Parse JESD204 config
    link_index = 0
    lane_index = 0
    rx_jesd_mode = profile_data["jtx"][link_index]["tx_link_cfg"][lane_index][
        "quick_mode_id"
    ]
    tx_jesd_mode = profile_data["jrx"][link_index]["rx_link_cfg"][lane_index][
        "quick_mode_id"
    ]

    if profile_data["jtx"][link_index]["common_link_cfg"]["ver"] == 0:
        # JESD204B
        raise Exception(
            f"Skipping {summary_file} because it is a JESD204B profile"
        )
    if profile_data["jrx"][link_index]["common_link_cfg"]["ver"] == 0:
        # JESD204B
        raise Exception(
            f"Skipping {summary_file} because it is a JESD204B profile"
        )

    df_row["jesd_settings"] = {}
    for rtx, cfg in zip(["jtx", "jrx"], ["tx_link_cfg", "rx_link_cfg"]):
        df_row["jesd_settings"][rtx] = {}
        for setting, jesd_setting_key in zip(
            ["L", "F", "M", "S", "HD", "K", "N", "Np"],
            [
                "l_minus1",
                "f_minus1",
                "m_minus1",
                "s_minus1",
                "high_dens",
                "k_minus1",
                "n_minus1",
                "np_minus1",
            ],
        ):
            if setting in ["N", "K"]:
                continue
            if (
                jesd_setting_key
                not in profile_data[rtx][link_index][cfg][lane_index]
            ):
                raise KeyError(
                    f"Skipping {summary_file} because {jesd_setting_key} "
                    + f"key is missing in {rtx} {cfg}"
                )
            if setting == "HD":
                df_row["jesd_settings"][rtx][setting] = profile_data[rtx][
                    link_index
                ][cfg][lane_index][jesd_setting_key]
            else:
                df_row["jesd_settings"][rtx][setting] = (
                    int(
                        profile_data[rtx][link_index][cfg][lane_index][
                            jesd_setting_key
                        ]
                    )
                    + 1
                )

    if rx_jesd_mode is None:
        raise KeyError(
            f"Skipping {summary_file} because 'rx_jesd_mode' key is missing"
        )
    df_row["rx_jesd_mode"] = rx_jesd_mode
    if tx_jesd_mode is None:
        raise KeyError(
            f"Skipping {summary_file} because 'tx_jesd_mode' key is missing"
        )
    df_row["tx_jesd_mode"] = tx_jesd_mode
    profile_name = os.path.basename(full_profile_filename)
    df_row["profile_name"] = profile_name.replace(".json", "")

    return df_row


def _apply_rx_settings(
    conv: converter, profile_settings: Dict, jesd_class: str
) -> None:
    """Apply RX (ADC) path settings from a profile to a converter.

    Args:
        conv (converter): The AD9084 RX converter object.
        profile_settings (Dict): The profile settings dictionary.
        jesd_class (str): JESD class to use.
    """
    cddc_dec = int(profile_settings["datapath"]["cddc_decimation"])
    fddc_dec = int(profile_settings["datapath"]["fddc_decimation"])
    converter_rate = int(profile_settings["device_clock_Hz"])

    conv.sample_clock = converter_rate / (cddc_dec * fddc_dec)
    conv.datapath.cddc_decimations = [cddc_dec] * 4
    conv.datapath.fddc_decimations = [fddc_dec] * 8
    conv.datapath.fddc_enabled = [True] * 8

    # jtx = JESD Transmitter path = ADC output
    M = profile_settings["jesd_settings"]["jtx"]["M"]
    L = profile_settings["jesd_settings"]["jtx"]["L"]
    S = profile_settings["jesd_settings"]["jtx"]["S"]
    Np = profile_settings["jesd_settings"]["jtx"]["Np"]

    mode = get_jesd_mode_from_params(
        conv, M=M, L=L, S=S, Np=Np, jesd_class=jesd_class
    )
    assert mode, (
        f"Could not find {jesd_class} mode for M={M}, L={L}, S={S}, Np={Np}"
    )
    conv.set_quick_configuration_mode(mode[0]["mode"], jesd_class)


def _apply_tx_settings(
    conv: converter, profile_settings: Dict, jesd_class: str
) -> None:
    """Apply TX (DAC) path settings from a profile to a converter.

    Args:
        conv (converter): The AD9084 TX converter object.
        profile_settings (Dict): The profile settings dictionary.
        jesd_class (str): JESD class to use.
    """
    cduc_interp = int(profile_settings["datapath"]["cduc_interpolation"])
    fduc_interp = int(profile_settings["datapath"]["fduc_interpolation"])
    converter_rate = int(profile_settings["device_clock_Hz"])

    conv.sample_clock = converter_rate / (cduc_interp * fduc_interp)
    conv.datapath.cduc_interpolation = cduc_interp
    conv.datapath.fduc_interpolation = fduc_interp
    conv.datapath.fduc_enabled = [True] * 8

    # jrx = JESD Receiver path = DAC input
    M = profile_settings["jesd_settings"]["jrx"]["M"]
    L = profile_settings["jesd_settings"]["jrx"]["L"]
    S = profile_settings["jesd_settings"]["jrx"]["S"]
    Np = profile_settings["jesd_settings"]["jrx"]["Np"]

    mode = get_jesd_mode_from_params(
        conv, M=M, L=L, S=S, Np=Np, jesd_class=jesd_class
    )
    assert mode, (
        f"Could not find {jesd_class} mode for M={M}, L={L}, S={S}, Np={Np}"
    )
    conv.set_quick_configuration_mode(mode[0]["mode"], jesd_class)


def apply_settings(conv: converter, profile_settings: Dict) -> None:
    """Apply settings to the AD9084 converter.

    Handles ADC-only, DAC-only, and combined (adc_dac) converters.

    Args:
        conv (converter): The AD9084 converter object.
        profile_settings (Dict): The profile settings dictionary
            containing configuration data.

    Raises:
        ValueError: If the TX and RX JESD204C modes do not match (ADC path).
    """
    jesd_class = "jesd204c"  # only JESD204C is supported for AD9084 right now

    ctype = getattr(conv, "converter_type", "adc").lower()

    if ctype == "adc_dac":
        # Combined model: apply RX settings to adc sub-converter and TX to dac
        _apply_rx_settings(conv.adc, profile_settings, jesd_class)
        _apply_tx_settings(conv.dac, profile_settings, jesd_class)
        return

    if ctype == "dac":
        _apply_tx_settings(conv, profile_settings, jesd_class)
        return

    # ADC path: verify TX/RX mode consistency first (preserves original ordering)
    M = profile_settings["jesd_settings"]["jtx"]["M"]
    L = profile_settings["jesd_settings"]["jtx"]["L"]
    S = profile_settings["jesd_settings"]["jtx"]["S"]
    Np = profile_settings["jesd_settings"]["jtx"]["Np"]
    M_tx = profile_settings["jesd_settings"]["jrx"]["M"]
    L_tx = profile_settings["jesd_settings"]["jrx"]["L"]
    S_tx = profile_settings["jesd_settings"]["jrx"]["S"]
    Np_tx = profile_settings["jesd_settings"]["jrx"]["Np"]
    if M != M_tx or L != L_tx or S != S_tx or Np != Np_tx:
        raise ValueError(
            f"TX and RX JESD204C modes do not match: "
            f"TX (M={M_tx}, L={L_tx}, S={S_tx}, Np={Np_tx}), "
            f"RX (M={M}, L={L}, S={S}, Np={Np})"
        )

    _apply_rx_settings(conv, profile_settings, jesd_class)


if __name__ == "__main__":
    data = _load_rx_config_modes(part="AD9084")
    # _load_tx_config_modes()
