import math 
from Munin.Volume import Timber

class BrandelVolume:
    @staticmethod
    def volume_birch(timber):
        """Calculate Brandel 1990 volume for Birch."""
        if timber.latitude > 60:
            return 10 ** (
                -0.44224
                + 2.47580 * math.log10(timber.diameter_cm)
                - 1.40854 * math.log10(timber.diameter_cm + 20)
                + 5.16863 * math.log10(timber.height_m)
                - 3.77147 * math.log10(timber.height_m - 1.3)
            )
        else:
            return 10 ** (
                -0.89359
                + 2.27954 * math.log10(timber.diameter_cm)
                - 1.18672 * math.log10(timber.diameter_cm + 20)
                + 7.07362 * math.log10(timber.height_m)
                - 5.45175 * math.log10(timber.height_m - 1.3)
            )

    @staticmethod
    def volume_pine(timber):
        """Calculate Brandel 1990 volume for Scots Pine."""
        if timber.latitude > 60:
            return 10 ** (
                -1.20914
                + 1.94740 * math.log10(timber.diameter_cm)
                - 0.05947 * math.log10(timber.diameter_cm + 20)
                + 1.40958 * math.log10(timber.height_m)
                - 0.45810 * math.log10(timber.height_m - 1.3)
            )
        else:
            return 10 ** (
                -1.38903
                + 1.84493 * math.log10(timber.diameter_cm)
                + 0.06563 * math.log10(timber.diameter_cm + 20)
                + 2.02122 * math.log10(timber.height_m)
                - 1.01095 * math.log10(timber.height_m - 1.3)
            )

    @staticmethod
    def volume_spruce(timber):
        """Calculate Brandel 1990 volume for Norway Spruce."""
        if timber.latitude > 60:
            return 10 ** (
                -0.79783
                + 2.07157 * math.log10(timber.diameter_cm)
                - 0.73882 * math.log10(timber.diameter_cm + 20)
                + 3.16332 * math.log10(timber.height_m)
                - 1.82622 * math.log10(timber.height_m - 1.3)
            )
        else:
            return 10 ** (
                -1.02039
                + 2.00128 * math.log10(timber.diameter_cm)
                - 0.47473 * math.log10(timber.diameter_cm + 20)
                + 2.87138 * math.log10(timber.height_m)
                - 1.61803 * math.log10(timber.height_m - 1.3)
            )

    @staticmethod
    def calculate_volume(timber):
        """Dispatch volume calculation based on the species."""
        species = timber.species.lower()  # Convert to lowercase for case-insensitive comparison
        if species.startswith("betula"):
            return BrandelVolume.volume_birch(timber)/1000
        elif species == "pinus sylvestris":
            return BrandelVolume.volume_pine(timber)/1000
        elif species == "picea abies":
            return BrandelVolume.volume_spruce(timber)/1000
        else:
            raise ValueError(f"Species '{timber.species}' not supported.")

#Test
BrandelVolume.calculate_volume(timber_birch)