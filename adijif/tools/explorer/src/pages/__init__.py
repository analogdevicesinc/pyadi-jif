"""Page definitions for PyADI-JIF Tools Explorer."""

from typing import Dict, Type

from ..utils import Page
from .clockconfigurator import ClockConfigurator
from .jesdbasic import JESDBasic
from .jesdmodeselector import JESDModeSelector
from .systemconfigurator import SystemConfigurator

PAGE_MAP: Dict[str, Type[Page]] = {
    "JESD204 Mode Selector": JESDModeSelector,
    "Clock Configurator": ClockConfigurator,
    "System Configurator": SystemConfigurator,
    "Basic JESD204 Calculator": JESDBasic,
}

__all__ = ["PAGE_MAP"]
