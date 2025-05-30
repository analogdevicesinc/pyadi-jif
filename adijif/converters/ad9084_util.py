"""AD9084 MxFE Utility Functions."""

import os
from typing import Dict, Union

import pandas as pd


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


def _load_rx_config_modes() -> Dict:
    """Load RX JESD configuration tables from file."""
    return _read_table_xlsx("AD9084_JTX_JRX.xlsx")


def _read_table_xlsx(filename: str) -> Dict:
    loc = os.path.dirname(__file__)
    fn = os.path.join(loc, "resources", filename)
    table = pd.read_excel(open(fn, "rb"), sheet_name="JTX_RxPath")

    # strip out unique JESD modes
    # table = table.drop_duplicates(subset=["JTX_MODE NUMBER"])
    jrx_modes_204b = {}
    jrx_modes_204c = {}
    for prow in table.iterrows():
        row = prow[1].to_dict()
        # print(row)
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


if __name__ == "__main__":
    data = _load_rx_config_modes()
    # _load_tx_config_modes()
