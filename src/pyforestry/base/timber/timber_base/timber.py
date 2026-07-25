"""Basic container class for individual tree parameters."""

from typing import Optional


class Timber:
    """Representation of a single tree with minimal attributes."""

    def __init__(
        self,
        species: str,
        diameter_cm: float,
        height_m: float,
        double_bark_mm: Optional[float] = None,
        crown_base_height_m: Optional[float] = None,
        over_bark: Optional[bool] = None,
        stump_height_m: Optional[float] = 0.3,
    ):
        """Init.

        Args:
            species: Parameter for `Timber.__init__`.
            diameter_cm: Parameter for `Timber.__init__`.
            height_m: Parameter for `Timber.__init__`.
            double_bark_mm: Parameter for `Timber.__init__`.
            crown_base_height_m: Parameter for `Timber.__init__`.
            over_bark: Parameter for `Timber.__init__`.
            stump_height_m: Parameter for `Timber.__init__`.

        Source:
            Internal pyforestry implementation.
        """
        self.species = species.lower()
        self.diameter_cm = diameter_cm
        self.height_m = height_m
        self.double_bark_mm = double_bark_mm
        self.crown_base_height_m = crown_base_height_m
        self.over_bark = over_bark
        self.stump_height_m = stump_height_m

        self.validate()

    def validate(self) -> None:
        """Validate that the provided tree attributes are sensible."""

        if self.height_m <= 0:
            raise ValueError(f"Height must be larger than 0 m: {self.height_m}")

        if self.diameter_cm < 0:
            raise ValueError(f"Diameter must be larger than or equal to 0 cm: {self.diameter_cm}")

        if (
            self.crown_base_height_m is not None
            and self.height_m is not None
            and self.crown_base_height_m >= self.height_m
        ):
            raise ValueError(
                (
                    f"Crown base height ({self.crown_base_height_m} m) cannot be "
                    f"higher than tree height: {self.height_m} m"
                )
            )

        if self.stump_height_m is not None and self.stump_height_m < 0:
            raise ValueError(f"Stump height must be larger or equal to 0 m: {self.stump_height_m}")
