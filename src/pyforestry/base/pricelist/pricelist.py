"""Pricelist utilities and interfaces.

A price list is where a projection's money comes from, so it carries a
:class:`PricelistIdentity` -- a name, the currency its prices are quoted in, and
who published it -- alongside the prices themselves. That is what lets a run
manifest state what its revenue figures are in and which list produced them,
rather than leaving two runs' money columns indistinguishable.
"""

from dataclasses import dataclass
from enum import IntEnum
from typing import Dict, Iterable, List, Optional, Sequence, Union

from pyforestry.base.contracts import SourceReference
from pyforestry.base.helpers.tree_species import TreeName, parse_tree_species


@dataclass(frozen=True)
class PricelistIdentity:
    """Which price list a figure of money came from, and what money it is in.

    A price list is what turns a volume into a sum, so every monetary figure a run
    reports is a figure *in this list's currency, against this list's prices*. Two
    runs' revenues are comparable only under the same list, which is why a run that
    reports money records this:
    :func:`~pyforestry.simulation.scenario.run_scenario` writes it into its
    manifest's ``valuation`` block.

    Args:
        name: What the list is called, e.g. ``"Mellanskog 2013"``.
        currency: The currency its prices are quoted in, e.g. ``"SEK"``. Per cubic
            metre; which volume basis is each timber table's own business, declared
            in :attr:`TimberPricelist.volume_type`, so it is not repeated here.
        source: Who published it, and when. A price list is regional market data
            with a publisher and a year, so this is a genuine citation rather than
            a stated choice -- and a table assembled by whoever ran the model says
            so through the ``(none)``/year-0 sentinel that
            :data:`UNATTRIBUTED_PRICELIST_IDENTITY` carries.

    Raises:
        ValueError: If the name or the currency is blank. An unnamed list is a real
            state, and :data:`UNATTRIBUTED_PRICELIST_IDENTITY` names itself as one;
            an empty string in a manifest names nothing.
    """

    name: str
    currency: str
    source: SourceReference

    def __post_init__(self) -> None:
        """Reject a blank name or currency."""
        if not self.name.strip():
            raise ValueError(
                "A price list's name must not be blank: it is what a run manifest "
                "identifies the money columns by. Use UNATTRIBUTED_PRICELIST_IDENTITY "
                "for a table nobody published."
            )
        if not self.currency.strip():
            raise ValueError(
                f"The price list {self.name!r} must say what currency its prices are in: "
                "a revenue figure without one is not a figure anyone can compare."
            )

    @property
    def is_cited(self) -> bool:
        """Whether this list traces to a publisher rather than to whoever ran the model."""
        return self.source.author != "(none)"


#: What a price list carries when nobody has said whose it is -- a hand-built table
#: in a test, or a caller's own figures. It is a real state rather than a missing
#: one, so it is named: a run manifest reporting money against this says plainly
#: that the prices are the analyst's, which is what keeps it apart from a run
#: priced against a published list. The ``(none)``/year-0 form is the one the rest
#: of the package uses for anything authored rather than published.
UNATTRIBUTED_PRICELIST_IDENTITY = PricelistIdentity(
    name="(unnamed price list)",
    currency="(unspecified)",
    source=SourceReference(
        author="(none)",
        year=0,
        title="Prices supplied by whoever configured the run",
        note=(
            "No publisher named, so the figures this list produces are the caller's "
            "own. year=0 is a sentinel for 'not applicable', not a citation date."
        ),
    ),
)


@dataclass
class DiameterRange:
    """The inclusive top-diameter span, in cm, over which an assortment is priced."""

    Min: float
    Max: float


@dataclass
class LengthRange:
    """The inclusive log-length span, in decimetres, an assortment accepts."""

    Min: float
    Max: float


class TimberPriceForDiameter:
    """
    Represents the set of prices for a given diameter, for each log part type.
    E.g. an entry might store: PriceButt, PriceMiddle, PriceTop, ...
    """

    def __init__(self, butt_price: float, middle_price: float, top_price: float):
        """Init."""
        self.butt_price = butt_price
        self.middle_price = middle_price
        self.top_price = top_price

    def price_for_log_part(self, part_type: int) -> float:
        """Return the price (in e.g. SEK/m3) for the given part type index."""
        if part_type == 0:  # butt
            return self.butt_price
        elif part_type == 1:  # middle
            return self.middle_price
        elif part_type == 2:  # top
            return self.top_price
        else:
            return 0.0


class LengthCorrections:
    """
    Holds logic for how the length modifies price (absolute or percent).

    Now accepts a dictionary of corrections in the form::

        {diameter: {length: correction_percentage, ...}, ...}
    """

    def __init__(self, corrections: Optional[Dict[int, Dict[int, int]]] = None):
        """Init."""
        self.corrections = corrections or {}

    def get_length_correction(self, diameter: int, log_part: Optional[int], length: int) -> int:
        """
        Returns the correction percentage for a given diameter and log length.
        Looks up the corrections dictionary for the closest available length (floored).
        Returns 0 if no correction applies.
        """
        if diameter not in self.corrections:
            return 0
        length_dict = self.corrections[diameter]
        # Get all lengths that are <= provided length
        available_lengths = sorted(
            length_val for length_val in length_dict.keys() if length_val <= length
        )
        if available_lengths:
            nearest_length = max(available_lengths)
            return length_dict[nearest_length]
        return 0  # no suitable correction


class TimberPricelist:
    """Stores the entire set of timber prices by diameter class, etc."""

    # Using your code's idea of enumerations: Butt = 0, Middle = 1, Top = 2 ...
    class LogParts(IntEnum):
        """Where along the stem a log came from, which is what it is priced by.

        A butt log, a middle log and a top log of the same dimensions fetch
        different prices, so every price lookup is keyed by this alongside the
        diameter class. The integer values are the column order the price tables
        use.
        """

        Butt = 0
        Middle = 1
        Top = 2

    def __init__(self, min_diameter: int, max_diameter: int, volume_type: str = "m3to"):
        """Init."""
        self.min_diameter = min_diameter
        self.max_diameter = max_diameter
        self.volume_type = volume_type  # e.g. "m3to" or "m3fub"
        self._price_by_diameter: Dict[int, TimberPriceForDiameter] = {}
        # Default length corrections (can be replaced when data is loaded)
        self.length_corrections = LengthCorrections()
        # Placeholders for additional data:
        self.quality_outcome: Dict[str, List[float]] = {}
        self.downgrade_proportions: Dict[str, float] = {}

        # Example maximum heights for different quality logs
        self.max_height_quality1 = 99.9  # in meters
        self.max_height_quality2 = 99.9
        self.max_height_quality3 = 99.9

    def __getitem__(self, diameter: int) -> TimberPriceForDiameter:
        """Return the price structure for a given diameter."""
        return self._price_by_diameter.get(diameter, TimberPriceForDiameter(0, 0, 0))

    def set_price_for_diameter(self, diameter: int, price_struct: TimberPriceForDiameter):
        """Store a price entry for a certain diameter class."""
        self._price_by_diameter[diameter] = price_struct

    def get_timber_weight(self, log_part: "TimberPricelist.LogParts"):
        """
        If you're applying downgrading or certain proportions for pulp/fuel/cull,
        this returns an object with attributes like ``.PulpwoodPercentage``,
        ``.FuelWoodPercentage`` and ``.LogCullPercentage``.
        This is a placeholder.
        """

        class LogWeights:
            """Container for derived log-quality weight percentages."""

            pulpwoodPercentage = 0.0
            fuelWoodPercentage = 0.0
            logCullPercentage = 0.0

        return LogWeights()

    def price_for_log_part(
        self, log_part: "TimberPricelist.LogParts", diameter_cm: float
    ) -> float:
        """
        Get the price for a given log part (Butt, Middle, Top) at a given diameter (cm).
        Rounds or floors the diameter to the nearest available diameter class.
        """
        diameter_class = self.get_nearest_diameter_class(diameter_cm)
        price_struct = self[diameter_class]
        return price_struct.price_for_log_part(log_part)

    def get_nearest_diameter_class(self, diameter_cm: float) -> int:
        """
        Returns the closest available diameter class (floored down to available class).
        If the requested diameter is smaller than ``min``, returns ``min``.
        If larger than ``max``, returns ``max``.
        """
        available_classes = sorted(self._price_by_diameter.keys())
        suitable_classes = [d for d in available_classes if d <= diameter_cm]

        if suitable_classes:
            return max(suitable_classes)
        else:
            return 0  # smallest available class


class PulpPricelist:
    """Placeholder for pulp prices per species."""

    def __init__(self):
        """Init."""
        self._prices = {}

    def get_pulpwood_price(self, species: Union[str, TreeName]) -> int:
        """
        Try to find the price for a species by first looking for a full name match.
        If none is found, look for a match on just the genus.
        Returns a default price if no match is found.
        """
        # Ensure we have a TreeName object
        if isinstance(species, str):
            try:
                species_obj = parse_tree_species(species)
            except ValueError:
                # Could not parse full species; treat the string as a genus.
                species_obj = None
        else:
            species_obj = species

        if species_obj:
            full_name_key = species_obj.full_name.lower()
            if full_name_key in self._prices:
                return self._prices[full_name_key]
            else:
                # Fallback: look up by genus
                genus_key = species_obj.genus.name.lower()
                if genus_key in self._prices:
                    return self._prices[genus_key]
        else:
            # species_obj is None (the string could not be parsed as a species).
            # Genus-only lookup is not implemented yet, so fall through to the
            # default price below.
            # TODO: match the input string as a genus and return its pulp price.
            pass

        # Default price if no match is found.
        return 200


class Pricelist:
    """Holds the combined pulpwood, timber, etc. prices and constraints.

    Alongside the prices it carries its :class:`PricelistIdentity`: what the list
    is called, what money its prices are in, and who published it. Every monetary
    figure a projection reports comes from here, so a run that records what it
    earned records that too.
    """

    def __init__(self, *, identity: Optional[PricelistIdentity] = None):
        """Init.

        Args:
            identity: Which list this is, what currency its prices are in, and who
                published it. Defaults to
                :data:`UNATTRIBUTED_PRICELIST_IDENTITY`, so a list built up
                attribute by attribute -- which is what this constructor is for --
                is visibly unattributed rather than silently so.
        """
        self.identity: PricelistIdentity = identity or UNATTRIBUTED_PRICELIST_IDENTITY
        self.Timber: Dict[str, TimberPricelist] = {}
        self.PulpLogDiameter = DiameterRange(5, 70)
        self.Pulp = PulpPricelist()
        self.TopDiameter: int = 5
        self.LogCullPrice: float = 50
        self.FuelWoodPrice: float = 25
        self.HighStumpHeight: float = 0.0
        self.PulpLogLength = LengthRange(30, 50)
        self.TimberLogLength = LengthRange(31, 55)

    def load_from_dict(self, price_data: dict):
        """Loads and configures the entire pricelist from a dictionary."""
        try:
            # Load common parameters
            common = price_data["Common"]
            self.PulpLogDiameter = DiameterRange(*common["PulpLogDiameterRange"])
            self.TopDiameter = common["TopDiameter"]
            self.LogCullPrice = common["HarvestResiduePrice"]
            self.FuelWoodPrice = common["FuelwoodLogPrice"]
            self.HighStumpHeight = common["HighStumpHeight"]
            self.PulpLogLength = LengthRange(*common["PulpwoodLengthRange"])
            self.TimberLogLength = LengthRange(*common["SawlogLengthRange"])
            self.Pulp._prices = common["PulpwoodPrices"]

            # Load timber data for all species in the pricelist
            for species_key in [key for key in price_data if key != "Common"]:
                self._load_species_specific_data(price_data, species_key)

        except KeyError as e:
            raise KeyError(f"Missing key in price data: {e}") from e
        except Exception as e:
            raise ValueError(f"Error loading price data: {e}") from e

    def _load_species_specific_data(self, price_data: dict, species_key: str):
        """Helper to load data for a single species."""
        timber_data = price_data[species_key]
        diameters = list(timber_data["DiameterPrices"].keys())

        timber_pricelist = TimberPricelist(
            min_diameter=min(diameters),
            max_diameter=max(diameters),
            volume_type=timber_data["VolumeType"],
        )

        for diameter, prices in timber_data["DiameterPrices"].items():
            price_struct = TimberPriceForDiameter(*prices)
            timber_pricelist.set_price_for_diameter(diameter, price_struct)

        if "LengthCorrectionsPercent" in timber_data:
            timber_pricelist.length_corrections = LengthCorrections(
                timber_data["LengthCorrectionsPercent"]
            )
        if "QualityOutcome" in timber_data:
            timber_pricelist.quality_outcome = timber_data["QualityOutcome"]
        if "DowngradeProportions" in timber_data:
            timber_pricelist.downgrade_proportions = timber_data["DowngradeProportions"]

        timber_pricelist.max_height_quality1 = timber_data["MaxHeight"]["Butt"]
        timber_pricelist.max_height_quality2 = timber_data["MaxHeight"]["Middle"]
        timber_pricelist.max_height_quality3 = timber_data["MaxHeight"]["Top"]

        self.Timber[species_key] = timber_pricelist

    def get_pulpwood_waste_proportion(self, species: Union[str, TreeName]) -> float:
        """Proportion (0-1) of a pulpwood log downgraded to waste/harvest residue.

        Placeholder returning ``0.0`` (no downgrade), mirroring the timber-side
        :meth:`TimberPricelist.get_timber_weight` hook. Consumed by the pulp branch of
        the Näsberg (1985) bucking optimiser when ``BuckingConfig.use_downgrading`` is
        set; override per species once real downgrade data is available.
        """
        return 0.0

    def get_pulpwood_fuelwood_proportion(self, species: Union[str, TreeName]) -> float:
        """Proportion (0-1) of a pulpwood log downgraded to fuelwood.

        Placeholder returning ``0.0`` (no downgrade); override per species as needed.
        See :meth:`get_pulpwood_waste_proportion`.
        """
        return 0.0


def create_pricelist_from_data(
    price_data: dict,
    species_to_load: Optional[Union[str, Sequence[str]]] = None,
    *,
    identity: Optional[PricelistIdentity] = None,
) -> Pricelist:
    """
    Build a `Pricelist` from a dictionary.

    Parameters
    ----------
    price_data : dict
        The complete price dictionary (must contain the 'Common' block).
    species_to_load : str | Sequence[str] | None, default None
        * **None**  - load *all* species that have timber price tables.
        * **str**   - load just that species.
        * **iterable** - load every species in the iterable; it is *not*
          an error if some of them have only pulp prices.
    identity : PricelistIdentity | None, default None
        Which list this data is, what currency it is in, and who published it. A
        run manifest records it, so pass it whenever the figures will be reported:
        the shipped example data publishes its own alongside the prices (see
        ``MELLANSKOG_2013_IDENTITY``). It is deliberately *not* read out of
        ``price_data``, which is hashed as-is to validate a
        :class:`~pyforestry.base.pricelist.SolutionCube` against the prices it was
        built from. Defaults to `UNATTRIBUTED_PRICELIST_IDENTITY`.

    Returns
    -------
    Pricelist
        A fully populated `Pricelist` instance.
    """
    pricelist = Pricelist(identity=identity)

    # ---- common block ---------------------------------------------------
    try:
        common = price_data["Common"]
    except KeyError as exc:
        raise ValueError("Price data is missing the mandatory 'Common' block") from exc

    pricelist.PulpLogDiameter = DiameterRange(*common["PulpLogDiameterRange"])
    pricelist.TopDiameter = common["TopDiameter"]
    pricelist.LogCullPrice = common["HarvestResiduePrice"]
    pricelist.FuelWoodPrice = common["FuelwoodLogPrice"]
    pricelist.HighStumpHeight = common["HighStumpHeight"]
    pricelist.PulpLogLength = LengthRange(*common["PulpwoodLengthRange"])
    pricelist.TimberLogLength = LengthRange(*common["SawlogLengthRange"])
    pricelist.Pulp._prices = common["PulpwoodPrices"]

    # ---- normalise parameter -------------------------------------------
    if species_to_load is None:
        species_keys: List[str] = [k for k in price_data.keys() if k != "Common"]
    elif isinstance(species_to_load, str):
        species_keys = [species_to_load]
    elif isinstance(species_to_load, Iterable):
        species_keys = list(species_to_load)
    else:
        raise TypeError("'species_to_load' must be None, a string, or an iterable of strings")

    # ---- load timber price tables --------------------------------------
    for sp in species_keys:
        if sp in price_data:
            pricelist._load_species_specific_data(price_data, sp)
        else:
            # It is OK if the species is missing in timber tables but present
            # in the pulp‑price section – we already copied those above.
            if sp not in common["PulpwoodPrices"]:
                raise ValueError(f"Species '{sp}' not found in timber prices **or** pulp prices.")

    return pricelist
