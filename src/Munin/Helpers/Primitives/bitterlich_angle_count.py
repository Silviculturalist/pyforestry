# ------------------------------------------------------------------------------
# Bitterlich (Angle count) Sampling
# ------------------------------------------------------------------------------
import math
import statistics
from typing import Optional, List, Tuple, Dict, Set, Union
from Munin.Helpers.TreeSpecies import TreeName
from Munin.Helpers.Primitives import StandBasalArea, Stems

class AngleCount:
    """
    Holds parameters for angle-count (relascope) sampling,
    along with species-specific tally counts.

    Attributes:
    -----------
    ba_factor : float
        Basal Area Factor (m²/ha) per count.
    value : list[float]
        Parallel list of float counts, each entry matching a species in 'species'.
    species : list[TreeName]
        Parallel list of species, each matching an entry in 'value'.
    point_id : str | None
        Identifies the sampling point location (e.g., 'P1', 'P2', etc.).
    slope : float
        Slope correction factor or slope angle, if desired (default: 0.0).
    """
    def __init__(self,
                 ba_factor: float,
                 value: Optional[List[float]] = None,
                 species: Optional[List[TreeName]] = None,
                 point_id: Optional[str] = None,
                 slope: float = 0.0):
        self.ba_factor = ba_factor
        self.value: List[float] = value if value is not None else []
        self.species: List[TreeName] = species if species is not None else []
        self.point_id = point_id
        self.slope = slope

        if len(self.species) != len(self.value):
            raise ValueError(f"Length mismatch for point {point_id}")

    def add_observation(self, sp: TreeName, count: float):
        """
        Add (or update) the tally count for the given species by `count`.
        Example:
            add_observation(TreeSpecies.Sweden.Picea_abies, 2)
            increments the Picea_abies count by 2.
        """
        if sp in self.species:
            idx = self.species.index(sp)
            self.value[idx] += count
        else:
            self.species.append(sp)
            self.value.append(count)

class AngleCountAggregator:
    """
    Aggregates multiple AngleCount objects, correctly handling per-plot BAF.
    Handles merging records with the same point_id and computes stand-level metrics.
    """
    def __init__(self, records: List[AngleCount]):
        self.records = records

    def merge_by_point_id(self) -> List[AngleCount]:
        """
        Merge records with the same point_id.
        Crucially, this now validates that BAF is consistent for a given point.
        """
        merged_records: Dict[Union[str, int], AngleCount] = {}
        for rec in self.records:
            key = rec.point_id if rec.point_id is not None else id(rec)
            if key in merged_records:
                existing_rec = merged_records[key]
                # --- SAFETY CHECK ---
                # Ensure BAFs match before merging counts for the same point.
                if existing_rec.ba_factor != rec.ba_factor:
                    raise ValueError(
                        f"Inconsistent BAF for point_id '{rec.point_id}': "
                        f"found {existing_rec.ba_factor} and {rec.ba_factor}."
                    )
                # Add observations from the new record to the existing one
                for sp, count in zip(rec.species, rec.value):
                    existing_rec.add_observation(sp, count)
            else:
                # Create a fresh copy to avoid modifying original objects
                merged_records[key] = AngleCount(rec.ba_factor, list(rec.value), list(rec.species), rec.point_id, rec.slope)
        
        return list(merged_records.values())
    
    def aggregate_stand_metrics(self) -> Tuple[Dict[TreeName, StandBasalArea],
                                             Dict[TreeName, Stems]]:
        """
        Aggregates records to compute per-species stand-level metrics,
        correctly applying the BAF for each individual plot before aggregation.
        """
        merged_records = self.merge_by_point_id()
        if not merged_records:
            return {}, {}

        n_total_points = len(merged_records)

        all_species: Set[TreeName] = set()
        for rec in merged_records:
            all_species.update(rec.species)

        # --- Create two separate dictionaries for data collection ---
        # 1. For basal area, we store the converted BA estimate (count * BAF)
        species_ba_estimates: Dict[TreeName, List[float]] = {sp: [] for sp in all_species}
        # 2. For stems, we store the raw counts
        species_stems_counts: Dict[TreeName, List[float]] = {sp: [] for sp in all_species}

        # --- Populate the dictionaries on a per-plot basis ---
        for rec in merged_records:
            # The BAF is now specific to each record in the loop
            current_baf = rec.ba_factor
            counts_in_rec = dict(zip(rec.species, rec.value))
            
            for sp in all_species:
                raw_count = counts_in_rec.get(sp, 0.0)
                
                # Append the raw count for stem calculations
                species_stems_counts[sp].append(raw_count)

                # Convert to BA for this plot and append the estimate
                ba_estimate = raw_count * current_baf
                species_ba_estimates[sp].append(ba_estimate)
        
        basal_area_by_species: Dict[TreeName, StandBasalArea] = {}
        stems_by_species: Dict[TreeName, Stems] = {}

        # --- Calculate final metrics for each species ---
        for sp in all_species:
            # --- Basal Area Calculations (on already converted values) ---
            ba_estimates = species_ba_estimates[sp]
            ba_mean = statistics.mean(ba_estimates)
            ba_var = statistics.variance(ba_estimates) if n_total_points > 1 else 0.0
            ba_sem = math.sqrt(ba_var / n_total_points) if n_total_points > 0 else 0.0

            basal_area_by_species[sp] = StandBasalArea(
                value=ba_mean,
                species=sp,
                precision=ba_sem,
                over_bark=True,
                direct_estimate=True
            )

            # --- Stems Calculations (on raw count values) ---
            stems_counts = species_stems_counts[sp]
            stems_mean = statistics.mean(stems_counts)
            stems_var = statistics.variance(stems_counts) if n_total_points > 1 else 0.0
            stems_sem = math.sqrt(stems_var / n_total_points) if n_total_points > 0 else 0.0

            stems_by_species[sp] = Stems(
                value=stems_mean,
                species=sp,
                precision=stems_sem
            )

        return basal_area_by_species, stems_by_species