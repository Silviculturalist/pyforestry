"""Utilities for generating and querying precomputed bucking solutions."""

import hashlib
import json
import time
import warnings
from datetime import datetime, timezone
from functools import partial
from multiprocessing import Pool, cpu_count
from typing import Any, Dict, Optional, Tuple, Type

import numpy as np
import pandas as pd
import xarray as xr
from tqdm import tqdm

from pyforestry.base.pricelist.pricelist import create_pricelist_from_data
from pyforestry.base.taper.taper import Taper
from pyforestry.base.timber.timber_base.timber import Timber

# ``nasberg_1985`` imports ``pyforestry.base.pricelist``, which imports this module, so a
# module-level import here is a cycle. It only bites when ``nasberg_1985`` is imported
# first (as model discovery does), which left it silently undiscoverable. Imported inside
# the worker instead.


def _hash_pricelist(price_data: Dict[str, Any]) -> str:
    """Creates a SHA256 hash of a pricelist dictionary for validation."""
    # Using json.dumps with sort_keys ensures a consistent string representation
    dhash = hashlib.sha256()
    encoded = json.dumps(price_data, sort_keys=True).encode()
    dhash.update(encoded)
    return dhash.hexdigest()


def _worker_buck_one_tree(
    tree_params: Tuple[str, int, int],
    pricelist_data: Dict,
    taper_model_class: Type[Taper],
    timber_class: Type[Timber] = Timber,
):
    """
    A top-level function for a single tree optimization.
    This is what each parallel process will execute.
    """
    from pyforestry.base.timber_bucking.nasberg_1985 import (  # circular import; see module head
        BuckingConfig,
        Nasberg_1985_BranchBound,
    )

    species, dbh_cm, height_dm = tree_params
    height_m = height_dm / 10.0

    try:
        timber = timber_class(species=species, diameter_cm=dbh_cm, height_m=height_m)
        pricelist = create_pricelist_from_data(
            pricelist_data,
            species,
        )
        optimizer = Nasberg_1985_BranchBound(timber, pricelist, taper_model_class)

        # We need the full result to get the sections
        result = optimizer.calculate_tree_value(
            min_diam_dead_wood=99, config=BuckingConfig(save_sections=True)
        )

        if result.sections is None:
            sections_data = []
        else:
            sections_data = [s.__dict__ for s in result.sections]

        sections_json = json.dumps(
            sections_data, default=lambda o: o.item() if isinstance(o, np.generic) else str(o)
        )

        return {
            "species": species,
            "dbh": dbh_cm,
            "height": height_m,
            "total_value": result.total_value,
            "solution_sections": sections_json,
        }
    except Exception as e:
        # Log or handle errors for specific tree combinations
        warnings.warn(f"Error processing {species} DBH={dbh_cm} H={height_m}: {e}", stacklevel=2)
        return {
            "species": species,
            "dbh": dbh_cm,
            "height": height_m,
            "total_value": np.nan,
            "solution_sections": "[]",
        }


class SolutionCube:
    """Container for precomputed bucking solutions."""

    def __init__(self, dataset: xr.Dataset):
        """
        Initializes the SolutionCube with a loaded xarray Dataset.
        It's recommended to use the `load` classmethod to create instances.
        """
        self.dataset = dataset
        self.pricelist_hash = dataset.attrs.get("pricelist_hash")
        self.taper_model = dataset.attrs.get("taper_model")

    @classmethod
    def generate(
        cls,
        pricelist_data: Dict[str, Any],
        taper_model: Type[Taper],
        species_list: list[str],
        dbh_range: Tuple[float, float],
        height_range: Tuple[float, float],
        dbh_step: int = 2,
        height_step: float = 0.2,
        timber_class: Type[Timber] = Timber,
        workers: int = -1,
    ):
        """
        Generates the solution cube by running the optimizer in parallel.
        """
        if workers == -1:
            workers = cpu_count()
        print(f"Generating Solution Cube using {workers} parallel processes...")

        pricelist_hash = _hash_pricelist(pricelist_data)
        print(f"Pricelist hash: {pricelist_hash}")

        # Create the grid of all tree parameters to compute
        dbh_coords = np.arange(dbh_range[0], dbh_range[1] + dbh_step, dbh_step)
        height_coords = np.arange(height_range[0], height_range[1] + height_step, height_step)

        tasks = [
            (sp, int(dbh), int(h * 10))
            for sp in species_list
            for dbh in dbh_coords
            for h in height_coords
        ]

        print(f"Total trees to process: {len(tasks)}")

        # Use a partial function to pass the static pricelist and taper model to the worker
        worker_func = partial(
            _worker_buck_one_tree,
            pricelist_data=pricelist_data,
            taper_model_class=taper_model,
            timber_class=timber_class,
        )

        # Run the optimizations in parallel (or sequentially for single-worker setups).
        start_time = time.time()
        if workers <= 1:
            results = list(
                tqdm(
                    (worker_func(task) for task in tasks),
                    total=len(tasks),
                    desc="Generating Solution Cube",
                )
            )
        else:
            try:
                with Pool(processes=workers) as pool:
                    # imap_unordered is great for getting results as they complete
                    results = list(
                        tqdm(
                            pool.imap_unordered(worker_func, tasks, chunksize=10),
                            total=len(tasks),
                            desc="Generating Solution Cube",
                        )
                    )
            except (OSError, PermissionError):
                results = list(
                    tqdm(
                        (worker_func(task) for task in tasks),
                        total=len(tasks),
                        desc="Generating Solution Cube",
                    )
                )
        end_time = time.time()
        print(f"\nFinished parallel computation in {end_time - start_time:.2f} seconds.")

        # --- Structure the results into an xarray Dataset ---
        # Convert flat list of dicts to a DataFrame for easier manipulation
        df = pd.DataFrame(results)
        df = df.set_index(["species", "height", "dbh"])

        # Convert to an xarray Dataset
        ds = xr.Dataset.from_dataframe(df)

        # Add metadata as attributes
        ds.attrs["pricelist_hash"] = pricelist_hash
        ds.attrs["taper_model"] = taper_model.__name__
        ds.attrs["creation_date_utc"] = datetime.now(timezone.utc).isoformat()
        ds.attrs["dbh_range"] = f"{dbh_range[0]}-{dbh_range[1]} cm"
        ds.attrs["height_range"] = f"{height_range[0]}-{height_range[1]} m"

        print("Successfully created xarray Dataset.")
        return cls(ds)

    def save(self, path: str):
        """Saves the dataset to a netCDF file."""
        print(f"Saving solution cube to {path}...")
        self.dataset.to_netcdf(path)
        print("Save complete.")

    @classmethod
    def load(cls, path: str, pricelist_to_verify: Optional[Dict] = None):
        """Loads a solution cube from a netCDF file."""
        print(f"Loading solution cube from {path}...")
        ds = xr.open_dataset(path)

        if pricelist_to_verify:
            new_hash = _hash_pricelist(pricelist_to_verify)
            if ds.attrs.get("pricelist_hash") != new_hash:
                raise ValueError(
                    "Pricelist hash mismatch! "
                    "The loaded cube was not generated with the provided pricelist."
                )
            print("Pricelist hash verified.")

        print("Cube loaded successfully.")
        return cls(ds)

    def lookup(self, species: str, dbh: float, height: float) -> Tuple[float, list]:
        """
        Performs a fast lookup for a given tree's properties.
        Uses nearest-neighbor interpolation.
        """
        try:
            if "species" in self.dataset.coords:
                if species not in self.dataset.coords["species"].values:
                    raise KeyError
            # Select species exactly (string axis), then apply nearest-neighbor on numeric axes.
            species_slice = self.dataset.sel(species=species)
            solution = species_slice.sel(dbh=float(dbh), height=float(height), method="nearest")

            total_value = float(solution["total_value"].values)
            if not np.isfinite(total_value):
                total_value = 0.0

            sections_json = str(solution["solution_sections"].values)
            sections = json.loads(sections_json)
            if not isinstance(sections, list):
                sections = []

            return total_value, sections

        except KeyError:
            warnings.warn(f"Species '{species}' not found in the solution cube.", stacklevel=2)
            return 0.0, []
        except Exception as e:
            warnings.warn(f"An error occurred during lookup: {e}", stacklevel=2)
            return 0.0, []

    def lookup_timber_pricelist(self, species: str) -> Tuple[float, list]:
        """Return an arbitrary timber value for ``species`` or warn if missing."""

        try:
            if species not in self.dataset.coords["species"].values:
                raise KeyError

            # Use the first dbh/height combination as a representative value
            dbh = float(self.dataset.coords["dbh"].values[0])
            height = float(self.dataset.coords["height"].values[0])
            return self.lookup(species, dbh, height)

        except KeyError:
            warnings.warn(f"Species '{species}' not found in the solution cube.", stacklevel=2)
            return 0.0, []
        except Exception as e:
            warnings.warn(f"An error occurred during lookup: {e}", stacklevel=2)
            return 0.0, []
