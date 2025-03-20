# Example structured data for easy readability and maintenance
# Use of TreeSpecies shorthand to avoid typos and situations e.g. Betula != Betula pendula.

from Munin.Helpers.TreeSpecies import TreeSpecies

Mellanskog_2013_price_data = {
    "Common": {
        "MaximumTreeHeight": 450,
        "SawlogLengthRange": (3.4, 5.5),
        "PulpwoodLengthRange": (2.7, 5.5),
        "PulpLogDiameterRange": (5, 60),
        "TopDiameter": 5,
        "PulpwoodPrices": {
            TreeSpecies.Sweden.pinus_sylvestris.full_name: 250,
            TreeSpecies.Sweden.picea_abies.full_name: 265,
            TreeSpecies.Sweden.betula.full_name: 250
        },
        "PulpwoodCullProportion": 0.05,
        "FuelwoodProportion": 0.0,
        "HarvestResiduePrice": 380,
        "FuelwoodLogPrice": 200,
        "StumpPrice": 380,
        "ApplyPriceTrends": False,
        "HighStumpHeight": 4
    },

    TreeSpecies.Sweden.pinus_sylvestris.full_name: {
        "VolumeType": "m3to",
        "DiameterPrices": {
            # Diameter: [Butt, Middle, Top]
            13: [300, 300, 300],
            14: [415, 365, 325],
            16: [440, 390, 325],
            18: [475, 425, 340],
            20: [575, 460, 340],
            22: [625, 485, 340],
            24: [675, 500, 340],
            26: [700, 525, 340],
            28: [735, 545, 365],
            30: [750, 565, 365],
            32: [750, 570, 365],
            34: [750, 575, 365],
            36: [700, 475, 300],
        },
        "LengthCorrectionsPercent": {
            14: {34: 80, 37: 85, 40: 90, 43: 95, 46: 100, 49: 102, 52: 104, 55: 106}
        },
        "QualityOutcome": {
            "Butt":   [0.31, 0.00, 0.57, 0.12],
            "Middle": [0.00, 0.31, 0.57, 0.12],
            "Top":    [0.00, 0.31, 0.57, 0.12],
        },
        "DowngradeProportions": {
            "Pulpwood": 0.10, "Fuelwood": 0.0, "HarvestResidue": 0.02
        },
        "MaxHeight": {"Butt": 5.5, "Middle": 11.0, "Top": 99.0}
    },

    TreeSpecies.Sweden.picea_abies.full_name: {
        "VolumeType": "m3to",
        "DiameterPrices": {
            # Diameter: [Butt, Middle, Top] (only two qualities, replicate middle price)
            13: [300, 300, 300],
            14: [425, 375, 375],
            16: [450, 375, 375],
            18: [485, 400, 400],
            20: [510, 400, 400],
            22: [535, 400, 400],
            24: [555, 400, 400],
            26: [575, 400, 400],
            28: [590, 425, 425],
            30: [605, 425, 425],
            32: [620, 425, 425],
            34: [625, 425, 425],
            36: [525, 350, 350],
        },
        "LengthCorrectionsPercent": {
            14: {34: 80, 37: 85, 40: 90, 43: 95, 46: 100, 49: 102, 52: 104, 55: 106}
        },
        "QualityOutcome": {
            "Butt":   [0.86, 0.14],
            "Middle": [0.86, 0.14],
            "Top":    [0.86, 0.14],
        },
        "DowngradeProportions": {
            "Pulpwood": 0.10, "Fuelwood": 0.0, "HarvestResidue": 0.02
        },
        "MaxHeight": {"Butt": 5.5, "Middle": 11.0, "Top": 99.0}
    }
}
