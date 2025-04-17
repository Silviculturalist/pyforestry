# This file provides a second access point for users to get the height trajectory for planted Scots Pine in Norway from Kuehne 2022.

from Munin.Models.norway.Kuehne_2022 import KuehnePineModel, HeightTrajectoryWrapper
from Munin.Helpers.TreeSpecies import PINUS_SYLVESTRIS

class Kuehne2022:
    """
    Provides access to Kuehne et al. (2022) height trajectory / site index functions
    for Scots Pine in Norway.

    Usage:
        # Requires TOTAL age. Output defaults to height at age2.
        height_val = Kuehne2022.height_trajectory.pinus_sylvestris(
            age=Age.TOTAL(50),
            age2=Age.TOTAL(100),
            dominant_height=20.0
        )

        si_h100 = Kuehne2022.height_trajectory.pinus_sylvestris(
             age=Age.TOTAL(50),
             age2=Age.TOTAL(100), # age2 is needed to find curve, but ignored for SIH100 output
             dominant_height=20.0,
             output="SIH100"
        )
         height_val_obj, si_h100_float = Kuehne2022.height_trajectory.pinus_sylvestris(
             age=Age.TOTAL(50),
             age2=Age.TOTAL(100),
             dominant_height=20.0,
             output="Both"
        )

    """
    _pine_wrapper_ht = HeightTrajectoryWrapper(KuehnePineModel)

    height_trajectory = type("HeightTrajectoryContainer", (), {
        "pinus_sylvestris": _pine_wrapper_ht # Use the instantiated wrapper
    })()

    # Set the caller reference on the wrapper instance *after* the container is built
    _pine_wrapper_ht._caller_ref = height_trajectory.pinus_sylvestris
