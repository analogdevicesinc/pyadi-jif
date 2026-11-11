"""Page definitions for PyADI-JIF Tools Explorer."""

from typing import Dict, Type

from ..utils import Page
from .adf4030_system_designer import Adf4030SystemDesigner
from .clockconfigurator import ClockConfigurator
from .frequencyplanner import FrequencyPlanner
from .jesdbasic import JESDBasic
from .jesdmodeselector import JESDModeSelector
from .landing import Landing
from .systemconfigurator import SystemConfigurator

PAGE_MAP: Dict[str, Type[Page]] = {
    "Tool Index": Landing,
    "JESD204 Mode Selector": JESDModeSelector,
    "Clock Configurator": ClockConfigurator,
    "System Configurator": SystemConfigurator,
    "ADF4030 System Designer": Adf4030SystemDesigner,
    "Basic JESD204 Calculator": JESDBasic,
    "Frequency Planner": FrequencyPlanner,
}

__all__ = ["PAGE_MAP"]
