"""Exception types raised by adijif.

Every exception here derives from :class:`Exception`, so code that already
catches broad exceptions keeps working unchanged. The point is to let callers
that *want* to react differently do so, instead of being forced into a single
``except Exception`` that cannot tell a user's infeasible request apart from a
missing solver engine or a bug in the library.

That distinction matters most in long-running or user-facing callers. A web UI
asking for 14 output frequencies wants to report "those frequencies have no
solution" to the operator, log a missing engine for the administrator, and let
anything unexpected surface as a real error rather than be reported as bad user
input.
"""


class JIFError(Exception):
    """Base class for every error adijif raises deliberately."""


class SolverError(JIFError):
    """Something went wrong in the constraint solver layer."""


class InfeasibleError(SolverError):
    """The requested configuration has no valid solution.

    This is the expected outcome of asking for something the hardware cannot
    do - an output frequency no divider can reach, a reference the PLL cannot
    lock to - and is normally a message to show the user, not a defect.
    """


class UnsupportedSolverError(SolverError):
    """The named solver backend is not recognised or not installed."""


class UnsupportedPartError(JIFError):
    """The requested part is not modelled by adijif."""


class InvalidConfigurationError(JIFError):
    """The inputs are contradictory or out of range before solving begins."""
