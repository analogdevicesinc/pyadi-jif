from .jesdmodeselector import JESDModeSelector
from .clockconfigurator import ClockConfigurator
from ..utils import Page

from typing import Dict, Type


PAGE_MAP: Dict[str, Type[Page]] = {
    "JESD204 Mode Selector": JESDModeSelector,
    "Clock Configurator": ClockConfigurator,
}

__all__ = ["PAGE_MAP"]
