"""Utility classes and helpers for defining tree species.

This module exposes two related concepts:
``TreeName`` represents a single biological species (genus + species name),
while ``TreeSpecies`` is a namespace that groups ``TreeName`` instances for a
given region.  For example ``TreeSpecies.Sweden.pinus_sylvestris`` returns the
``TreeName`` object for Scots pine.
"""

from dataclasses import dataclass
from typing import Any, Dict, Iterator, List, Union

# --------------------------------------------------------------------
# Global Taxonomy: Genera and Species (renamed to TreeName)


@dataclass(frozen=True)
class TreeGenus:
    """Represents a botanical genus."""

    name: str
    code: str  # A unique code for the genus


@dataclass(frozen=True)
class TreeName:
    """A specific tree species within a genus."""

    genus: TreeGenus
    species_name: str
    code: str  # A unique code for the species

    @property
    def full_name(self) -> str:
        return f"{self.genus.name.lower()} {self.species_name.lower()}"

    @property
    def tree_type(self) -> str:
        return get_tree_type_by_genus(self.genus.name.lower())


# --------------------------------------------------------------------
# Helper function to determine tree type based on the genus name


def get_tree_type_by_genus(genus: str) -> str:
    DECIDUOUS_LIST = {
        "betula",
        "alnus",
        "populus",
        "sorbus",
        "salix",
        "ulmus",
        "fraxinus",
        "carpinus",
        "quercus",
        "tilia",
        "fagus",
        "prunus",
        "acer",
        "robinia",
        "corylus",
        "aesculus",
    }
    CONIFEROUS_LIST = {
        "abies",
        "picea",
        "larix",
        "pseudotsuga",
        "tsuga",
        "pinus",
        "seqouia",
        "sequoiadendron",
        "chamaecyparis",
        "cupressaceae",
        "juniperus",
        "thuja",
        "taxus",
        "cedrus",
        "cathaya",
        "pseudolarix",
        "keteleeria",
        "nothotsuga",
    }
    g = genus.lower()
    if g in CONIFEROUS_LIST:
        return "Coniferous"
    elif g in DECIDUOUS_LIST:
        return "Deciduous"
    else:
        raise ValueError(f"Unknown tree type for genus '{genus}'.")


# --------------------------------------------------------------------
# Global Genera

PICEA = TreeGenus(name="Picea", code="PICEA")
FAGUS = TreeGenus(name="Fagus", code="FAGUS")
QUERCUS = TreeGenus(name="Quercus", code="QUERCUS")
BETULA = TreeGenus(name="Betula", code="BETULA")
PINUS = TreeGenus(name="Pinus", code="PINUS")
LARIX = TreeGenus(name="Larix", code="LARIX")
PSEUDOTSUGA = TreeGenus(name="Pseudotsuga", code="PSEUDO")
TAXUS = TreeGenus(name="Taxus", code="TAXUS")
JUNIPERUS = TreeGenus(name="Juniperus", code="JUNIPERUS")
ALNUS = TreeGenus(name="Alnus", code="ALNUS")
ULMUS = TreeGenus(name="Ulmus", code="ULMUS")
FRAXINUS = TreeGenus(name="Fraxinus", code="FRAXINUS")
POPULUS = TreeGenus(name="Populus", code="POPULUS")
CARPINUS = TreeGenus(name="Carpinus", code="CARPINUS")
PRUNUS = TreeGenus(name="Prunus", code="PRUNUS")
CORYLUS = TreeGenus(name="Corylus", code="CORYLUS")
TILIA = TreeGenus(name="Tilia", code="TILIA")
ACER = TreeGenus(name="Acer", code="ACER")
SORBUS = TreeGenus(name="Sorbus", code="SORBUS")
SALIX = TreeGenus(name="Salix", code="SALIX")

# --------------------------------------------------------------------
# Global TreeName objects (unique species)
PICEA_ABIES = TreeName(genus=PICEA, species_name="abies", code="PAB")
FAGUS_SYLVATICA = TreeName(genus=FAGUS, species_name="sylvatica", code="FSY")
QUERCUS_ROBUR = TreeName(genus=QUERCUS, species_name="robur", code="QRB")
QUERCUS_PETRAEA = TreeName(genus=QUERCUS, species_name="petraea", code="QPT")
BETULA_PENDULA = TreeName(genus=BETULA, species_name="pendula", code="BPEN")
BETULA_PUBESCENS = TreeName(genus=BETULA, species_name="pubescens", code="BPUB")
PINUS_SYLVESTRIS = TreeName(genus=PINUS, species_name="sylvestris", code="PSYL")
PINUS_CONTORTA = TreeName(genus=PINUS, species_name="contorta", code="PCON")
PINUS_MUGO = TreeName(genus=PINUS, species_name="mugo", code="PMUG")
LARIX_SIBIRICA = TreeName(genus=LARIX, species_name="sibirica", code="LSIB")
LARIX_DECIDUA = TreeName(genus=LARIX, species_name="decidua", code="LDEC")
LARIX_EUROPEA_X_LEPTOLEPIS = TreeName(
    genus=LARIX, species_name="europaea x leptolepis", code="LEXL"
)
LARIX_SUKACZEWII = TreeName(genus=LARIX, species_name="sukaczewii", code="LSUK")
PSEUDOTSUGA_MENZIESII = TreeName(genus=PSEUDOTSUGA, species_name="menziesii", code="PMEN")
PICEA_SITCHENSIS = TreeName(genus=PICEA, species_name="sitchensis", code="PSIT")
PICEA_MARIANA = TreeName(genus=PICEA, species_name="mariana", code="PMAR")
TAXUS_BACCATA = TreeName(genus=TAXUS, species_name="baccata", code="TBAC")
JUNIPERUS_COMMUNIS = TreeName(genus=JUNIPERUS, species_name="communis", code="JCOM")
ALNUS_GLUTINOSA = TreeName(genus=ALNUS, species_name="glutinosa", code="AGLU")
ALNUS_INCANA = TreeName(genus=ALNUS, species_name="incana", code="AINC")
ULMUS_GLABRA = TreeName(genus=ULMUS, species_name="glabra", code="UGLA")
FRAXINUS_EXCELSIOR = TreeName(genus=FRAXINUS, species_name="excelsior", code="FEXC")
POPULUS_TREMULA = TreeName(genus=POPULUS, species_name="tremula", code="PTRE")
POPULUS_TREMULA_X_TREMULOIDES = TreeName(
    genus=POPULUS, species_name="tremula x tremuloides", code="PTXT"
)
CARPINUS_BETULUS = TreeName(genus=CARPINUS, species_name="betulus", code="CBET")
PRUNUS_AVIUM = TreeName(genus=PRUNUS, species_name="avium", code="PAVI")
CORYLUS_AVELLANA = TreeName(genus=CORYLUS, species_name="avellana", code="CAVE")
PRUNUS_PADUS = TreeName(genus=PRUNUS, species_name="padus", code="PPAD")
TILIA_CORDATA = TreeName(genus=TILIA, species_name="cordata", code="TCOR")
ULMUS_MINOR = TreeName(genus=ULMUS, species_name="minor", code="UMIN")
ACER_PLATANOIDES = TreeName(genus=ACER, species_name="platanoides", code="APLA")
ACER_PSEUDOPLATANUS = TreeName(genus=ACER, species_name="pseudoplatanus", code="APSE")
SORBUS_INTERMEDIA = TreeName(genus=SORBUS, species_name="intermedia", code="SINT")
SORBUS_AUCUPARIA = TreeName(genus=SORBUS, species_name="aucuparia", code="SAUC")
SALIX_CAPREA = TreeName(genus=SALIX, species_name="caprea", code="SCAP")
ULMUS_LAEVIS = TreeName(genus=ULMUS, species_name="laevis", code="ULAE")
QUERCUS_RUBRA = TreeName(genus=QUERCUS, species_name="rubra", code="QRUB")

# --------------------------------------------------------------------
# Global list of trees.
GLOBAL_TREE_SPECIES: List[TreeName] = [
    PICEA_ABIES,
    FAGUS_SYLVATICA,
    QUERCUS_ROBUR,
    QUERCUS_PETRAEA,
    BETULA_PENDULA,
    BETULA_PUBESCENS,
    PINUS_SYLVESTRIS,
    PINUS_CONTORTA,
    PINUS_MUGO,
    LARIX_SIBIRICA,
    LARIX_DECIDUA,
    LARIX_EUROPEA_X_LEPTOLEPIS,
    LARIX_SUKACZEWII,
    PSEUDOTSUGA_MENZIESII,
    PICEA_SITCHENSIS,
    PICEA_MARIANA,
    TAXUS_BACCATA,
    JUNIPERUS_COMMUNIS,
    ALNUS_GLUTINOSA,
    ALNUS_INCANA,
    ULMUS_GLABRA,
    FRAXINUS_EXCELSIOR,
    POPULUS_TREMULA,
    POPULUS_TREMULA_X_TREMULOIDES,
    CARPINUS_BETULUS,
    PRUNUS_AVIUM,
    CORYLUS_AVELLANA,
    PRUNUS_PADUS,
    TILIA_CORDATA,
    ULMUS_MINOR,
    ACER_PLATANOIDES,
    ACER_PSEUDOPLATANUS,
    SORBUS_INTERMEDIA,
    SORBUS_AUCUPARIA,
    SALIX_CAPREA,
    ULMUS_LAEVIS,
    QUERCUS_RUBRA,
]


# --------------------------------------------------------------------
# RegionalGenusGroup helper


class RegionalGenusGroup:
    """
    A container for a group of TreeName objects sharing the same genus.
    It is iterable and supports membership testing.
    """

    def __init__(self, genus: str, species: List[TreeName]):
        self.genus = genus
        self.species = species

    def __iter__(self) -> Iterator[TreeName]:
        return iter(self.species)

    def __contains__(self, item: Any) -> bool:
        return item in self.species

    def __repr__(self) -> str:
        return f"RegionalGenusGroup({self.genus}: {self.species})"

    @property
    def full_name(self) -> str:
        return self.genus.lower()


# --------------------------------------------------------------------
# Regional Subsets


class RegionalTreeSpecies:
    """
    Exposes a subset of globally defined TreeName objects as attributes.
    Also computes regional genus groups (e.g. 'alnus') that contain only the allowed species.
    """

    def __init__(self, region: str, allowed_species: List[TreeName]):
        self.region = region
        # Dictionary of individual species using keys like "picea_abies"
        self._species: Dict[str, TreeName] = {}
        for sp in allowed_species:
            key = f"{sp.genus.name.lower()}_{sp.species_name.lower().replace(' ', '_')}"
            self._species[key] = sp

        # Group species by genus (keyed by lower-case genus name)
        self._by_genus: Dict[str, List[TreeName]] = {}
        for sp in allowed_species:
            genus_key = sp.genus.name.lower()
            self._by_genus.setdefault(genus_key, []).append(sp)

    def __getattr__(self, attr: str) -> Any:
        # First check if the attribute matches a genus group.
        if attr in self._by_genus:
            return RegionalGenusGroup(attr, self._by_genus[attr])
        # Then check if the attribute matches an individual species.
        if attr in self._species:
            return self._species[attr]
        raise AttributeError(f"Species or genus '{attr}' not found in region '{self.region}'")


# Global Regional Species Namespace
class TreeSpecies:
    """Namespace exposing regional groups of tree species."""

    Sweden = RegionalTreeSpecies(
        "Sweden",
        allowed_species=[
            PICEA_ABIES,
            FAGUS_SYLVATICA,
            QUERCUS_ROBUR,
            QUERCUS_PETRAEA,
            BETULA_PENDULA,
            BETULA_PUBESCENS,
            PINUS_SYLVESTRIS,
            PINUS_CONTORTA,
            PINUS_MUGO,
            LARIX_SIBIRICA,
            LARIX_DECIDUA,
            LARIX_EUROPEA_X_LEPTOLEPIS,
            LARIX_SUKACZEWII,
            PSEUDOTSUGA_MENZIESII,
            PICEA_SITCHENSIS,
            PICEA_MARIANA,
            TAXUS_BACCATA,
            JUNIPERUS_COMMUNIS,
            ALNUS_GLUTINOSA,
            ALNUS_INCANA,
            ULMUS_GLABRA,
            FRAXINUS_EXCELSIOR,
            POPULUS_TREMULA,
            POPULUS_TREMULA_X_TREMULOIDES,
            CARPINUS_BETULUS,
            PRUNUS_AVIUM,
            CORYLUS_AVELLANA,
            PRUNUS_PADUS,
            TILIA_CORDATA,
            ULMUS_MINOR,
            ACER_PLATANOIDES,
            ACER_PSEUDOPLATANUS,
            SORBUS_INTERMEDIA,
            SORBUS_AUCUPARIA,
            SALIX_CAPREA,
            ULMUS_LAEVIS,
            QUERCUS_RUBRA,
        ],
    )


def parse_tree_species(species_str: Union[str, TreeName]) -> TreeName:
    """Return the :class:`TreeName` corresponding to ``species_str``.

    ``species_str`` may be either a ``TreeName`` instance or a string such as
    ``"Pinus sylvestris"``.  Strings are normalized and looked up among the
    globally defined species (for example those exposed through
    :class:`TreeSpecies`).
    """
    # Sometimes a TreeName object is passed by mistake. Return TreeName.full_name.lower()
    if isinstance(species_str, TreeName):
        return species_str

    normalized = species_str.strip().lower()
    for sp in GLOBAL_TREE_SPECIES:
        if sp.full_name.lower() == normalized:
            return sp
    raise ValueError(f"Could not find species matching '{species_str}'")
