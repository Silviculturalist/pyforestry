# tests/conftest.py
import matplotlib

# 1) Use the Agg backend (renders to a buffer, no display needed)
matplotlib.use("Agg")

import pytest


@pytest.fixture(autouse=True)
def close_figures_after_test():
    """
    Automatically close all figures once each test function finishes.
    Prevents matplotlib from accumulating open figures.
    """
    yield
    import matplotlib.pyplot as plt

    plt.close("all")
