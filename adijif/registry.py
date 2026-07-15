"""Validated registry for constructing supported device models."""

from typing import Dict, Literal, Type, Union, overload

from adijif.clocks.ad9523 import ad9523_1
from adijif.clocks.ad9528 import ad9528
from adijif.clocks.ad9545 import ad9545
from adijif.clocks.clock import clock
from adijif.clocks.hmc7044 import hmc7044
from adijif.clocks.ltc6952 import ltc6952
from adijif.clocks.ltc6953 import ltc6953
from adijif.converters.ad9081 import (
    ad9081,
    ad9081_rx,
    ad9081_tx,
    ad9082,
    ad9082_rx,
    ad9082_tx,
)
from adijif.converters.ad9084 import (
    ad9084,
    ad9084_rx,
    ad9084_tx,
    ad9088_rx,
    ad9088_tx,
)
from adijif.converters.ad9144 import ad9144
from adijif.converters.ad9152 import ad9152
from adijif.converters.ad9680 import ad9680
from adijif.converters.adrv9009 import adrv9009, adrv9009_rx, adrv9009_tx
from adijif.converters.converter import converter
from adijif.fpgas.fpga import fpga
from adijif.fpgas.xilinx import xilinx
from adijif.fpgas.xilinx.bf import xilinx_bf
from adijif.plls.adf4030 import adf4030
from adijif.plls.adf4371 import adf4371
from adijif.plls.adf4382 import adf4382
from adijif.plls.pll import pll

ComponentType = Union[Type[converter], Type[clock], Type[fpga], Type[pll]]

COMPONENT_REGISTRY: Dict[str, Dict[str, ComponentType]] = {
    "converter": {
        cls.__name__.lower(): cls
        for cls in (
            ad9081,
            ad9081_rx,
            ad9081_tx,
            ad9082,
            ad9082_rx,
            ad9082_tx,
            ad9084,
            ad9084_rx,
            ad9084_tx,
            ad9088_rx,
            ad9088_tx,
            ad9144,
            ad9152,
            ad9680,
            adrv9009,
            adrv9009_rx,
            adrv9009_tx,
        )
    },
    "clock": {
        cls.__name__.lower(): cls
        for cls in (ad9523_1, ad9528, ad9545, hmc7044, ltc6952, ltc6953)
    },
    "fpga": {cls.__name__.lower(): cls for cls in (xilinx, xilinx_bf)},
    "pll": {cls.__name__.lower(): cls for cls in (adf4030, adf4371, adf4382)},
}

_COMPONENT_BASES = {
    "converter": converter,
    "clock": clock,
    "fpga": fpga,
    "pll": pll,
}


@overload
def get_component_class(
    kind: Literal["converter"], name: str
) -> Type[converter]: ...


@overload
def get_component_class(kind: Literal["clock"], name: str) -> Type[clock]: ...


@overload
def get_component_class(kind: Literal["fpga"], name: str) -> Type[fpga]: ...


@overload
def get_component_class(kind: Literal["pll"], name: str) -> Type[pll]: ...


@overload
def get_component_class(kind: str, name: str) -> ComponentType: ...


def get_component_class(kind: str, name: str) -> ComponentType:
    """Resolve a supported component name without evaluating user input."""
    normalized_kind = kind.lower()
    if normalized_kind not in COMPONENT_REGISTRY:
        raise ValueError(f"Unknown component kind {kind!r}")
    if not isinstance(name, str):
        raise TypeError("Component name must be a string")

    normalized_name = name.lower()
    try:
        component = COMPONENT_REGISTRY[normalized_kind][normalized_name]
    except KeyError as exc:
        supported = ", ".join(sorted(COMPONENT_REGISTRY[normalized_kind]))
        raise ValueError(
            f"Unknown {normalized_kind} {name!r}. Supported values: {supported}"
        ) from exc

    if not issubclass(component, _COMPONENT_BASES[normalized_kind]):
        raise TypeError(
            f"Registered {normalized_kind} {name!r} has an invalid component type"
        )
    return component
