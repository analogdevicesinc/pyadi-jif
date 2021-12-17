"""AD9081 MxFE Utility Functions."""
import csv
import os
from typing import Dict, Union


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
    coarse: Union[int, float],
    fine: Union[int, float],
    global_index: Union[int, float],
    conv_min: float,
    conv_max: float,
    lane_min: float,
    lane_max: float,
    jesd_class: str,
) -> Dict:
    return {
        "mode": mode,
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
        "coarse": coarse,
        "fine": fine,
        "global_index": global_index,
        "conv_min": conv_min,
        "conv_max": conv_max,
        "lane_min": lane_min,
        "lane_max": lane_max,
    }


def _load_rx_config_modes() -> Dict:
    """Load RX JESD configuration tables from file."""
    t = _read_table("ad9081_JTx_204B.csv", True)
    return _read_table("ad9081_JTx_204C.csv", False, t)


def _load_tx_config_modes() -> Dict:
    """Load TX JESD configuration tables from file."""
    t = _read_table("ad9081_JRx_204B.csv", True)
    return _read_table("ad9081_JRx_204C.csv", False, t)


def _read_table(fn: str, jesd204b: bool, qcm: Union[Dict, None] = None) -> Dict:
    loc = os.path.dirname(__file__)
    fn = os.path.join(loc, "resources", fn)
    with open(fn) as f:
        records = csv.DictReader(f)
        if qcm:
            quick_configuration_modes = qcm
        else:
            quick_configuration_modes = {}
        for row in records:
            d = dict(row)
            if "_JTx_" in fn:
                HD = int(float(d["HD"]))
                conv_min = float(d["FADC Min (GSPS)"])
                conv_max = float(d["FADC Max (GSPS)"])
                lane_min = float(d["Lane Rate Min (GSPS)"])
                lane_max = float(d["Lane Rate Max (GSPS)"])
            else:
                HD = 0
                conv_min = -1
                conv_max = -1
                lane_min = -1
                lane_max = -1
            if jesd204b:
                k = "JESD204B Mode Number"
                jmode = "jesd204b"
                E = 0
            else:
                k = "JESD204C Mode Number"
                jmode = "jesd204c"
                E = int(float(d["E"]))
            mode = d[k]
            del d[k]
            if not mode:
                continue
            gi = int(float(d["global_index"]))
            quick_configuration_modes[mode + f"_{gi}"] = _convert_to_config(
                mode=mode,
                L=int(float(d["L"])),
                M=int(float(d["M"])),
                F=int(float(d["F"])),
                S=int(float(d["S"])),
                N=int(float(d["NP"])),
                Np=int(float(d["NP"])),
                CS=int(0),
                HD=HD,
                K=int(float(d["K"])),
                E=E,
                global_index=gi,
                coarse=int(float(d["Coarse"])),
                fine=int(float(d["Fine"])),
                jesd_class=jmode,
                conv_min=conv_min,
                conv_max=conv_max,
                lane_min=lane_min,
                lane_max=lane_max,
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

if __name__ == "__main__":
    _load_rx_config_modes()
    _load_tx_config_modes()
