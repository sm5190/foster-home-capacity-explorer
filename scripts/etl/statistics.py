"""Shared statistical calculations for analytical ETL."""

from __future__ import annotations

import math
from typing import Final


PERCENTILE_METHOD: Final = "linear_interpolation_position_(n-1)*p"


def linear_percentile(
    values: list[float],
    percentile: float,
) -> float:
    """Calculate a percentile using linear interpolation.

    The percentile position is:

        (number of values - 1) * percentile
    """

    if not 0 <= percentile <= 1:
        raise ValueError("Percentile must be between zero and one.")

    if not values:
        raise ValueError("Cannot calculate a percentile from no values.")

    ordered_values = sorted(values)

    if len(ordered_values) == 1:
        return ordered_values[0]

    position = (len(ordered_values) - 1) * percentile

    lower_index = math.floor(position)
    upper_index = math.ceil(position)

    if lower_index == upper_index:
        return ordered_values[lower_index]

    interpolation_fraction = position - lower_index

    lower_value = ordered_values[lower_index]
    upper_value = ordered_values[upper_index]

    return lower_value + (upper_value - lower_value) * interpolation_fraction
