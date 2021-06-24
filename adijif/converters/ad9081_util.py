"""AD9081 MxFE Utility Functions."""
import csv
import os
from typing import Dict, Union


def _convert_to_config(
    L: Union[int, float],
    M: Union[int, float],
    F: Union[int, float],
    S: Union[int, float],
    # HD: Union[int, float],
    N: Union[int, float],
    Np: Union[int, float],
    # CS: Union[int, float],
    DualLink: bool,
    jesd_class: str,
) -> Dict:
    return {
        "L": L,
        "M": M,
        "F": F,
        "S": S,
        "HD": 1 if F == 1 else 0,
        "Np": Np,
        "CS": 0,
        "DualLink": DualLink,
        "jesd_class": jesd_class,
    }


def _load_rx_config_modes() -> Dict:
    """Load RX JESD configuration tables from file."""
    return _read_table("full_rx_mode_table_ad9081.csv")


def _load_tx_config_modes() -> Dict:
    """Load TX JESD configuration tables from file."""
    return _read_table("full_tx_mode_table_ad9081.csv")


def _read_table(fn: str) -> Dict:
    loc = os.path.dirname(__file__)
    fn = os.path.join(loc, "resources", fn)
    with open(fn) as f:
        records = csv.DictReader(f)
        quick_configuration_modes = {}
        for row in records:
            d = dict(row)
            mode = d["Mode"]
            del d["Mode"]
            DL = d["DualLink"] in ["True", True]
            jmode = "jesd204c" if "c" in d["jesd_mode"].lower() else "jesd204b"
            quick_configuration_modes[mode] = _convert_to_config(
                L=int(d["L"]),
                M=int(d["M"]),
                F=int(d["F"]),
                S=int(d["S"]),
                N=int(d["Np"]),
                Np=int(d["Np"]),
                DualLink=DL,
                jesd_class=jmode,
            )
    return quick_configuration_modes

    # def read_table_org(self,fn:str):
    #     dlk = "Dual Link DV Verfied" if "rx" in fn else "Dual link"
    #     mk = "\ufeffTXFE mode" if "rx" in fn else "TXFE mode"
    #     loc = os.path.dirname(__file__)
    #     fn = os.path.join(loc, "resources", fn)
    #     with open(fn) as f:
    #         records = csv.DictReader(f)
    #         quick_configuration_modes = {}
    #         for row in records:
    #             d = dict(row)
    #             mode = d[mk]
    #             del d[mk]
    #             quick_configuration_modes[mode] = _convert_to_config(
    #                 L=int(d["L"]),
    #                 M=int(d["M"]),
    #                 F=int(d["F"]),
    #                 S=int(d["S"]),
    #                 N=int(d["NP"]),
    #                 Np=int(d["NP"]),
    #                 DualLink=d[dlk] in ["YES", 1, '1'],
    #                 jesd_mode=d['JESD 204 Mode'],
    #             )

    #     return quick_configuration_modes

    # def _write_out(self):
    #     with open("full_tx_mode_table_ad9081.csv", 'w') as csvfile:
    #         csv_columns = list(self.quick_configuration_modes_tx['0'].keys())
    #         csv_columns.append("Mode")
    #         writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
    #         writer.writeheader()
    #         for mode in self.quick_configuration_modes_tx:
    #             d = self.quick_configuration_modes_tx[mode]
    #             d['Mode'] = mode
    #             writer.writerow(d)


# au = ad9081_utils()
# au._load_tx_config_modes()
# au._write_out()
