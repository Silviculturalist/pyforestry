import warnings

import pytest

from pyforestry.sweden.models.elfving_hagglund_1975 import ElfvingHagglundInitialStand


def test_validate_age_structure():
    with pytest.raises(ValueError):
        ElfvingHagglundInitialStand._validate_age_structure(True, True)

    # Should not raise
    ElfvingHagglundInitialStand._validate_age_structure(False, False)
    ElfvingHagglundInitialStand._validate_age_structure(True, False)


def test_validate_broadleaves():
    with warnings.catch_warnings(record=True) as rec:
        ElfvingHagglundInitialStand._validate_broadleaves(50)
        assert rec

    ElfvingHagglundInitialStand._validate_broadleaves(20)
    with pytest.raises(ValueError):
        ElfvingHagglundInitialStand._validate_broadleaves(-1)
