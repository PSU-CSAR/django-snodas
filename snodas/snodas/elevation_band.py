from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Self, overload

from snodas.snodas.constants import (
    DEM_MAX_M,
    DEM_MIN_M,
    FT_TO_M,
    M_TO_FT,
)


@dataclass
class ElevationBand:
    min: int | float
    max: int | float

    @property
    def min_meters(self: Self) -> float:
        return self.min * FT_TO_M

    @property
    def max_meters(self: Self) -> float:
        return self.max * FT_TO_M

    def __str__(self: Self) -> str:
        return f'{self.min}_{self.max}'

    def __hash__(self: Self) -> int:
        return hash((self.min, self.max))

    def __eq__(self: Self, other: Any) -> bool:
        return (
            isinstance(other, ElevationBand)
            and self.min == other.min
            and self.max == other.max
        )

    def __lt__(self: Self, other: Self) -> bool:
        return (self.min == other.min and self.max < other.max) or self.min < other.min

    def __gt__(self: Self, other: Self) -> bool:
        return not self < other

    @overload
    @classmethod
    def generate(
        cls: type[Self],
        size_ft: int,
        min_elevation: int | float = DEM_MIN_M,
        max_elevation: int | float = DEM_MAX_M,
    ) -> Iterator[Self]: ...

    @overload
    @classmethod
    def generate(
        cls: type[Self],
        size_ft: float,
        min_elevation: int | float = DEM_MIN_M,
        max_elevation: int | float = DEM_MAX_M,
    ) -> Iterator[Self]: ...

    @classmethod
    def generate(
        cls: type[Self],
        size_ft: int | float = 1000,
        min_elevation: int | float = DEM_MIN_M,
        max_elevation: int | float = DEM_MAX_M,
    ) -> Iterator[Self]:
        """
        Yields elevation bands of size_ft (default 1000), aligned to 0,
        sufficient to capture elevation range of AOI.

        For example, if an AOI has a min / max elevation of 638.528 / 2328.196
        meters, this function will yield the following tuples given a size_ft
        of 1000:

            (2000, 3000)
            (3000, 4000)
            (4000, 5000)
            (5000, 6000)
            (6000, 7000)
            (7000, 8000)
        """
        if size_ft <= 0:
            yield cls(
                min=int(min_elevation * M_TO_FT),
                max=(int(max_elevation * M_TO_FT) + 1),
            )
        else:
            start: int = int((min_elevation * M_TO_FT) // size_ft)
            end: int = int((max_elevation * M_TO_FT) // size_ft) + 1

            yield from (
                cls(min=(idx * size_ft), max=((idx + 1) * size_ft))
                for idx in range(start, end)
            )
