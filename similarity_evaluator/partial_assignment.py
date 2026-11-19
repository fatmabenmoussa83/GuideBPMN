"""Threshold-gated partial assignment. Dummy columns let every node abstain."""
import numpy as np
from scipy.optimize import linear_sum_assignment

VERSION = "partial-v2"



def partial_assignment(scores, allowed, *, floor=0.0):
    values = np.asarray(scores, dtype=float)
    permitted = np.asarray(allowed, dtype=bool) & np.isfinite(values)
    if not values.size:
        return []
    # Each row has a private unmatched option; unused real columns are unmatched.
    gains = np.full((values.shape[0], values.shape[1] + values.shape[0]), -1e6)
    gains[:, :values.shape[1]] = np.where(permitted, values - floor, -1e6)
    for i in range(values.shape[0]):
        gains[i, values.shape[1] + i] = 0.0
    rows, columns = linear_sum_assignment(gains, maximize=True)
    return [(int(i), int(j)) for i, j in zip(rows, columns)
            if j < values.shape[1] and permitted[i, j] and values[i, j] >= floor]


def ambiguity_margin(scores, allowed, i, j):
    """Nearest competing allowed counterpart in either direction."""
    competitors = [scores[i, k] for k in range(scores.shape[1]) if k != j and allowed[i, k]]
    competitors += [scores[k, j] for k in range(scores.shape[0]) if k != i and allowed[k, j]]
    return None if not competitors else float(scores[i, j] - max(competitors))
