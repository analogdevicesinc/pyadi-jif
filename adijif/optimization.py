"""Cohesive lexicographic optimization framework for JIF components.

Components register objectives with tier and sense metadata via
``core._add_objective``. ``system.initialize`` then walks every component,
collects the objectives, groups them by tier, and applies the result as a
single lexicographic objective on the shared solver model.

Tiers are integers; lower tier numbers have higher priority. Within a tier,
objectives are weighted, then summed under a uniform sense — when every
objective in the tier shares the same sense the framework calls the solver's
native ``maximize``/``minimize`` API directly; mixed-sense tiers fall back
to negating the max-sense terms so the whole tier minimizes.

CPLEX backend uses ``CpoModel.minimize_static_lex`` /
``CpoModel.maximize_static_lex`` for multi-tier objectives and a single
``minimize``/``maximize`` for one-tier. The gekko backend supports a single
tier only (summed into one ``model.Obj`` call); multi-tier objectives on
gekko raise ``NotImplementedError``.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, List, Optional

if TYPE_CHECKING:
    from adijif.system import system


@dataclass
class Objective:
    """A single optimization objective.

    Attributes:
        expr: Solver expression to optimize. Anything the active solver
            accepts as the body of a minimize/maximize call (CpoExpr,
            GKVariable, GK_Intermediate, int, float, ...).
        sense: ``"min"`` to minimize (default) or ``"max"`` to maximize.
            Maximize is implemented by negating ``expr`` before summing
            within a tier.
        tier: Lexicographic priority. Lower = higher priority. Tier 0 runs
            first; tier 1 only breaks ties left by tier 0; etc.
        weight: Multiplier applied within a tier when summing multiple
            objectives at the same priority.
        name: Optional human-readable identifier for debugging and
            introspection. Convention: ``"<component>.<short_label>"``,
            e.g. ``"hmc7044.r2_min"``.
        component: Set by the system collector to the originating
            component's class name; users do not set this directly.
    """

    expr: Any
    sense: str = "min"
    tier: int = 0
    weight: float = 1.0
    name: Optional[str] = None
    component: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate ``sense`` after dataclass field assignment."""
        if self.sense not in ("min", "max"):
            raise ValueError(
                f"Objective sense must be 'min' or 'max', got {self.sense!r}"
            )


def collect_objectives(sys_obj: "system") -> List[Objective]:
    """Walk all system components and return a flat list of Objectives.

    Each returned Objective has its ``component`` field set to the originating
    component's class name. ``system._user_objectives`` is appended last and
    tagged ``component="user"``.

    Args:
        sys_obj: The ``adijif.system`` instance owning the components.

    Returns:
        Combined list of Objective instances from clock, fpga, all PLLs,
        sysref PLLs, all converters, and any user-registered objectives.
    """
    components = []
    if getattr(sys_obj, "clock", None):
        components.append(sys_obj.clock)
    if getattr(sys_obj, "fpga", None):
        components.append(sys_obj.fpga)
    components.extend(getattr(sys_obj, "_plls", []) or [])
    components.extend(getattr(sys_obj, "_plls_sysref", []) or [])
    converter = getattr(sys_obj, "converter", None)
    if isinstance(converter, list):
        components.extend(converter)
    elif converter is not None:
        components.append(converter)

    objectives: List[Objective] = []
    for c in components:
        cname = type(c).__name__
        for obj in getattr(c, "_objectives", []) or []:
            if not isinstance(obj, Objective):
                # Tolerate legacy bare expressions; treat as min/tier=0.
                obj = Objective(expr=obj)
            obj.component = cname
            objectives.append(obj)

    for obj in getattr(sys_obj, "_user_objectives", []) or []:
        obj.component = "user"
        objectives.append(obj)

    return objectives


def apply_objectives(
    model: Any, solver: str, objectives: List[Objective]
) -> None:
    """Apply collected objectives to the solver model as a lex objective.

    Groups objectives by ``tier``; within each tier, sums ``weight * expr``
    (with ``expr`` negated for ``sense="max"``). The per-tier sums are then
    passed in tier order (lowest tier first = highest priority) to the
    solver's lexicographic minimization.

    Args:
        model: The shared solver model (CpoModel or GEKKO instance).
        solver: ``"CPLEX"`` or ``"gekko"``.
        objectives: List of Objective instances to apply. Empty list is a
            no-op.

    Raises:
        NotImplementedError: solver is ``"gekko"`` and objectives span more
            than one tier (gekko has no native lexicographic optimization).
        Exception: Unknown solver name.
    """
    if not objectives:
        return

    # Group by tier. Track the dominant sense per tier so we can pass tiers
    # whose objectives all agree on direction directly to the solver's
    # native maximize/minimize APIs (round-tripping through negation can
    # perturb CPLEX's fractional-approximation search). Mixed-sense tiers
    # are normalized to "min" via negation of the max-sense terms.
    by_tier: dict = {}
    for obj in objectives:
        scaled = obj.weight * obj.expr if obj.weight != 1.0 else obj.expr
        by_tier.setdefault(obj.tier, []).append((scaled, obj.sense))

    tiers = sorted(by_tier.keys())
    tier_sums = []
    tier_dominant_sense = []
    for t in tiers:
        items = by_tier[t]
        senses_in_tier = {s for _, s in items}
        if len(senses_in_tier) == 1 and "max" in senses_in_tier:
            # All max: pass exprs through as-is and use maximize APIs.
            exprs = [e for e, _ in items]
            tier_dominant_sense.append("max")
        else:
            # Mixed or all-min: negate any max terms so the whole tier sums
            # under "min" semantics.
            exprs = [(-e if s == "max" else e) for e, s in items]
            tier_dominant_sense.append("min")
        tier_sums.append(sum(exprs[1:], exprs[0]))

    if solver == "CPLEX":
        if len(tier_sums) == 1:
            if tier_dominant_sense[0] == "min":
                model.minimize(tier_sums[0])
            else:
                model.maximize(tier_sums[0])
        else:
            uniform = len(set(tier_dominant_sense)) == 1
            if uniform and tier_dominant_sense[0] == "min":
                model.add(model.minimize_static_lex(tier_sums))
            elif uniform and tier_dominant_sense[0] == "max":
                model.add(model.maximize_static_lex(tier_sums))
            else:
                normalized = [
                    s if sense == "min" else -s
                    for s, sense in zip(
                        tier_sums, tier_dominant_sense, strict=True
                    )
                ]
                model.add(model.minimize_static_lex(normalized))
    elif solver == "gekko":
        if len(tier_sums) > 1:
            raise NotImplementedError(
                "Lexicographic optimization with multiple tiers requires "
                "solver='CPLEX'. The gekko backend supports a single "
                f"objective tier only (got tiers={tiers})."
            )
        expr = (
            tier_sums[0] if tier_dominant_sense[0] == "min" else -tier_sums[0]
        )
        model.Obj(expr)
    else:
        raise Exception(f"Unknown solver {solver}")
