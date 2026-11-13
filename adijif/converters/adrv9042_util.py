"""ADRV9042 transport candidates from UG-2358 Tables 19 and 21.

These are transport tuples, not ACE use-case or firmware profile numbers.
Lane crossbar limits additionally follow Figures 55-57 and 62.
"""

from functools import lru_cache
from itertools import product


@lru_cache(maxsize=5)
def transport_modes(direction: str, index: int) -> dict:
    """Generate canonical framing for each packable transport tuple."""
    receive = direction == "rx"
    max_m = (192, 96, 32)[index] if receive else (192, 96)[index]
    lanes = (
        ([1, 2, 4, 8], [1, 2, 4], [1, 2])[index]
        if receive
        else ([1, 2, 4, 8], [1, 2, 4])[index]
    )
    result = {"jesd204b": {}, "jesd204c": {}}
    for standard in result:
        for m, lane_count, np, s in product(
            range(2 if receive else 1, max_m + 1),
            lanes,
            (12, 16, 24),
            (1, 2, 4) if receive else (1, 2),
        ):
            numerator = m * np * s
            if numerator % (8 * lane_count):
                continue
            f = numerator // (8 * lane_count)
            allowed_f = (
                range(2, 33)
                if receive and standard == "jesd204c"
                else (2, 3, 4, 6, 8, 12, 16, 24, 32)
                if receive
                else (2, 3, 4, 6, 8, 12, 16, 32)
            )
            if f not in allowed_f:
                continue
            if standard == "jesd204b":
                ks = [
                    k
                    for k in range(1, 33)
                    if 20 <= f * k <= 256 and f * k % 4 == 0
                ]
                if not ks:
                    continue
                k, e = max(ks), 1
            else:
                es = (1, 3, 5) if receive else range(1, 33)
                pairs = [
                    (256 * e // f, e)
                    for e in es
                    if 256 * e % f == 0 and 256 * e // f <= 256
                ]
                if not pairs:
                    continue
                k, e = pairs[0]
            result[standard][f"M{m}L{lane_count}Np{np}S{s}"] = {
                "M": m,
                "L": lane_count,
                "Np": np,
                "N": np,
                "S": s,
                "F": f,
                "K": k,
                "E": e,
                "CS": 0,
                "CF": 0,
                "HD": int((8 * f) % np != 0),
            }
    return result
