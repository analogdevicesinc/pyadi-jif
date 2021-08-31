from typing import List, Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

import api.jif.models as models

import adijif
import adidt

app = FastAPI(title="JESD Interface Framework API", version="0.0.1")


@app.get("/parts")
async def parts():
    """Get list of supported data converters"""
    return adijif.converters.supported_parts


@app.get("/clocks")
async def clocks():
    """Get list of supported data converters"""
    return adijif.clocks.supported_parts


@app.get("/part/{part}/jesd_mode_table")
async def root(part: str):
    """
    Get JESD mode table for converter:

    - **part**: Data converter part name (ex: AD9680)
    """
    if part not in adijif.converters.supported_parts:
        raise HTTPException(
            status_code=404, detail="Part not supported or found: " + part
        )

    dev = eval("adijif." + part.lower())
    return dev.quick_configuration_modes


@app.get("/valid_modes/{part}/{sample_rate}/{decint}")
async def check_all_modes_at_rate(part: str, sample_rate: int, decint: int):
    """
    Get valid JESD modes for specific converter configuration:

    - **part**: Data converter part name (ex: AD9680)
    - **sample_rate**: Interface sample rate in samples per second
    - **decint**: Internal decimation or interpolation between converter and interface
    """
    if part not in adijif.converters.supported_parts:
        raise HTTPException(
            status_code=404, detail="Part not supported or found: " + part
        )

    dev = eval("adijif." + part.lower() + "()")
    dev.sample_clock = sample_rate
    results = {}
    maxConverters = 0
    print("QCM: ", dev.quick_configuration_modes)
    for mode in dev.quick_configuration_modes:
        print("mode", mode, "sample_rate", sample_rate)
        dev.set_quick_configuration_mode(mode=mode)
        if dev.M > maxConverters:
            maxConverters = dev.M
        print("M", dev.M)
        # Check
        try:
            dev.validate_config()
            results[mode] = True
            print("Valid")
        except:
            results[mode] = False
            print("InValid")

    return {
        "results": results,
        "modes": dev.quick_configuration_modes,
        "maxConverters": maxConverters,
    }


@app.get("/part/{part}/rates/{jesd_mode}/{sample_rate}/{decint}")
async def rates(part: str, jesd_mode: str, sample_rate: int, decint: int):
    """Validate JESD mode and lane rate based on samples rate and decimation

    - **part**: Data converter name
    - **jesd_mode**: JESD mode of configuration
    - **sample_rate**: Rate at SERDES interface in samples per second
    - **decint**: Decimation or interpolation between ADC/DAC and SERDES
    """
    if part not in adijif.converters.supported_parts:
        raise HTTPException(
            status_code=404, detail="Part not supported or found: " + part
        )

    dev = eval("adijif." + part.lower())
    dev.sample_clock = sample_rate
    dev.set_quick_configuration_mode(jesd_mode)
    # Check
    try:
        dev.validate_config()
    except:
        return {"Message": "Invalid config"}

    return {"bit_clock": dev.bit_clock}


@app.post("/clock/solve/")
def clock_chip_solve(search: models.ClockSearch):
    """Solve for clock chip configuration based on desired output clock rates

    - **search**: Decimation or interpolation between ADC/DAC and SERDES
    """

    if search.part not in adijif.clocks.supported_parts:
        raise HTTPException(
            status_code=404, detail="Part not supported or found: " + search.part
        )

    clk = eval("adijif.{}()".format(search.part.lower()))

    if hasattr(search, "custom_props") and search.custom_props:
        for prop in search.custom_props:
            if not hasattr(clk, prop):
                raise HTTPException(
                    status_code=404, detail="Part class does not have property: " + prop
                )
            setattr(clk, prop, search.custom_props[prop])

    output_clocks = list(map(int, search.output_clocks))  # force to be ints
    clock_names = ["clock_{}".format(n) for n in range(len(search.output_clocks))]
    clk.set_requested_clocks(search.vcxo, search.output_clocks, clock_names)

    try:
        clk.solve()
    except:
        raise HTTPException(status_code=400, detail="No solution found")

    return {"part": search.part, "config": clk.get_config()}


@app.post("/clock/update_sd_dt/")
def update_dt(config: models.ClockUpdate):
# def update_dt():

    import os

    loc = os.path.dirname(__file__)
    dtb = os.path.join(loc, "ad9081_hmc7044.dtb")

    d = adidt.hmc7044_dt(dt_source="local_file", local_dt_filepath=dtb)
    node = d.get_node_by_compatible("adi,hmc7044")
    try:
        assert len(node) == 1

        node = node[0]
        config = {"vcxo": clock["vcxo"], "clock": clock}
        d.set_dt_node_from_config(node, config)
        d.write_out_dts("out.dts")
        return {"Status": "Passed"}
    except Exception as ex:
        print(ex)

        return {"Status": "Failed"}

