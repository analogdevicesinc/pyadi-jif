"""Session state management for Streamlit application."""

from copy import deepcopy
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional

from streamlit.runtime import get_instance
from streamlit.runtime.legacy_caching.hashing import _CodeHasher
from streamlit.runtime.scriptrunner import get_script_run_ctx

if TYPE_CHECKING:
    from streamlit.runtime.state.session_state import SessionState as Session


class _SessionState:
    """Internal session state management class."""

    def __init__(
        self, session: "Session", hash_funcs: Optional[Dict[type, Callable[[Any], str]]]
    ) -> None:
        """Initialize SessionState instance."""
        self.__dict__["_state"] = {
            "data": {},
            "hash": None,
            "hasher": _CodeHasher(hash_funcs),
            "is_rerun": False,
            "session": session,
        }

    def __call__(self, **kwargs: Dict[str, Any]) -> None:  # type: ignore[misc]
        """Initialize state data once."""
        for item, value in kwargs.items():
            if item not in self._state["data"]:
                self._state["data"][item] = value

    def __getitem__(self, item: str) -> Any:  # noqa: ANN401
        """Return a saved state value, None if item is undefined."""
        return self._state["data"].get(item, None)

    def __getattr__(self, item: str) -> Any:  # noqa: ANN401
        """Return a saved state value, None if item is undefined."""
        return self._state["data"].get(item, None)

    def __setitem__(self, item: str, value: Any) -> None:  # noqa: ANN401
        """Set state value."""
        self._state["data"][item] = value

    def __setattr__(self, item: str, value: Any) -> None:  # noqa: ANN401
        """Set state value."""
        self._state["data"][item] = value

    def clear(self) -> None:
        """Clear session state and request a rerun."""
        self._state["data"].clear()
        self._state["session"].request_rerun()

    def sync(self) -> None:
        """Rerun the app with all state values up to date.

        This fixes rollbacks from the beginning.
        """
        # Ensure to rerun only once to avoid infinite loops
        # caused by a constantly changing state value at each run.
        #
        # Example: state.value += 1
        if self._state["is_rerun"]:
            self._state["is_rerun"] = False

        elif self._state["hash"] is not None:
            if self._state["hash"] != self._state["hasher"].to_bytes(
                self._state["data"], None
            ):
                self._state["is_rerun"] = True
                self._state["session"].request_rerun(None)

        self._state["hash"] = self._state["hasher"].to_bytes(self._state["data"], None)


def _get_session() -> Any:  # noqa: ANN401
    """Get the current Streamlit session."""
    runtime = get_instance()
    session_id = get_script_run_ctx().session_id
    session_info = runtime._session_mgr.get_session_info(session_id)

    if session_info is None:
        raise RuntimeError("Couldn't get your Streamlit Session object.")

    return session_info.session


def get_state(
    hash_funcs: Optional[Dict[type, Callable[[Any], str]]] = None,
) -> _SessionState:
    """Get or create session state.

    Args:
        hash_funcs: Optional hash functions for state comparison

    Returns:
        Session state object
    """
    session = _get_session()

    if not hasattr(session, "_custom_session_state"):
        session._custom_session_state = _SessionState(session, hash_funcs)

    return session._custom_session_state


# Only used for separating namespace
# Everything can be saved at state variable as well.
CONFIG_DEFAULTS: Dict[str, Any] = {"slider_value": 0}


def provide_state(
    hash_funcs: Optional[Dict[type, Callable[[Any], str]]] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to provide state to a function.

    Args:
        hash_funcs: Optional hash functions for state comparison

    Returns:
        Decorator function
    """

    def inner(func: Callable[..., Any]) -> Callable[..., Any]:  # noqa: ANN401
        """Inner decorator function."""

        def wrapper(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
            """Wrapper function that injects state."""
            state = get_state(hash_funcs=hash_funcs)
            if state.client_config is None:
                state.client_config = deepcopy(CONFIG_DEFAULTS)

            return_value = func(*args, state=state, **kwargs)  # noqa: B026
            state.sync()
            return return_value

        return wrapper

    return inner
