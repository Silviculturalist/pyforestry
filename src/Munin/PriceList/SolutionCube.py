import xarray as xr
import numpy as np
import pandas as pd
import hashlib
import json
import time
from datetime import datetime, timezone
from multiprocessing import Pool, cpu_count
from typing import Dict, Any, Tuple, Type, Optional
from functools import partial
from tqdm import tqdm

# Import your project's classes
from Munin.timber.swe_timber import SweTimber
from Munin.pricelist.pricelist import Pricelist, create_pricelist_from_data
from Munin.taper.Taper import Taper
from Munin.timber_bucking.nasberg_1985 import Nasberg_1985_BranchBound, BuckingConfig

def _hash_pricelist(price_data: Dict[str, Any]) -> str:
    """Creates a SHA256 hash of a pricelist dictionary for validation."""
    # Using json.dumps with sort_keys ensures a consistent string representation
    dhash = hashlib.sha256()
    encoded = json.dumps(price_data, sort_keys=True).encode()
    dhash.update(encoded)
    return dhash.hexdigest()

def _worker_buck_one_tree(tree_params: Tuple[str, int, int], pricelist_data: Dict, taper_model_class: Type[Taper]):
    """
    A top-level function for a single tree optimization.
    This is what each parallel process will execute.
    """
    species, dbh_cm, height_dm = tree_params
    height_m = height_dm / 10.0

    try:
        timber = SweTimber(species=species, diameter_cm=dbh_cm, height_m=height_m)
        pricelist = create_pricelist_from_data(pricelist_data, species,)
        optimizer = Nasberg_1985_BranchBound(timber, pricelist, taper_model_class)
        
        # We need the full result to get the sections
        result = optimizer.calculate_tree_value(min_diam_dead_wood=99,config=BuckingConfig(save_sections=True))

        if result.sections is None:
            sections_data = []
        else:
            sections_data = [s.__dict__ for s in result.sections]

        sections_json = json.dumps(
            sections_data,
            default=lambda o: o.item() if isinstance(o, np.generic) else str(o)
        )
        
        return {
            "species": species,
            "dbh": dbh_cm,
            "height": height_m,
            "total_value": result.total_value,
            "solution_sections": sections_json
        }
    except Exception as e:
        # Log or handle errors for specific tree combinations
        print(f"Error processing {species} DBH={dbh_cm} H={height_m}: {e}")
        return {
            "species": species,
            "dbh": dbh_cm,
            "height": height_m,
            "total_value": np.nan,
            "solution_sections": '[]'
        }


class SolutionCube:
    def __init__(self, dataset: xr.Dataset):
        """
        Initializes the SolutionCube with a loaded xarray Dataset.
        It's recommended to use the `load` classmethod to create instances.
        """
        self.dataset = dataset
        self.pricelist_hash = dataset.attrs.get('pricelist_hash')
        self.taper_model = dataset.attrs.get('taper_model')

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
        workers: int = -1
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
            (sp, int(dbh), int(h*10)) for sp in species_list for dbh in dbh_coords for h in height_coords
        ]


        print(f"Total trees to process: {len(tasks)}")

        # Use a partial function to pass the static pricelist and taper model to the worker
        worker_func = partial(_worker_buck_one_tree, pricelist_data=pricelist_data, taper_model_class=taper_model)

        # Run the optimizations in parallel
        start_time = time.time()
        with Pool(processes=workers) as pool:
            # imap_unordered is great for getting results as they complete
            results = tqdm(
                list(pool.imap_unordered(worker_func, tasks, chunksize=10)),
                total=len(tasks),
                desc='Generating Solution Cube'
            )
        end_time = time.time()
        print(f"\nFinished parallel computation in {end_time - start_time:.2f} seconds.")

        # --- Structure the results into an xarray Dataset ---
        # Convert flat list of dicts to a DataFrame for easier manipulation
        df = pd.DataFrame(results)
        df = df.set_index(['species', 'height', 'dbh'])

        # Convert to an xarray Dataset
        ds = xr.Dataset.from_dataframe(df)
        
        # Add metadata as attributes
        ds.attrs['pricelist_hash'] = pricelist_hash
        ds.attrs['taper_model'] = taper_model.__name__
        ds.attrs['creation_date_utc'] = datetime.now(timezone.utc).isoformat()
        ds.attrs['dbh_range'] = f"{dbh_range[0]}-{dbh_range[1]} cm"
        ds.attrs['height_range'] = f"{height_range[0]}-{height_range[1]} m"

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
            if ds.attrs.get('pricelist_hash') != new_hash:
                raise ValueError(
                    "Pricelist hash mismatch! The loaded cube was not generated with the provided pricelist."
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
            # .sel is xarray's powerful selection method. 'nearest' finds the closest point.
            solution = self.dataset.sel(
                species=species,
                dbh=dbh,
                height=height,
                method='nearest'
            )
            
            total_value = float(solution['total_value'].values)
            sections_json = str(solution['solution_sections'].values)
            sections = json.loads(sections_json)
            
            return total_value, sections

        except KeyError:
            print(f"Warning: Species '{species}' not found in the solution cube.")
            return 0.0, []
        except Exception as e:
            print(f"An error occurred during lookup: {e}")
            return 0.0, []