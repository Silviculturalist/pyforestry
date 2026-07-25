"""Primary citation for every competition index and competitor-selection rule.

Each index is attributed to the paper that proposed it, not to the review that
tabulated it. Maleki, Kiviste & Korjus (2015) are the reason this particular set
of eighteen is collected here and are cited for that -- see
:data:`INDEX_SET_REVIEW` -- but they are not the source of any of the science.

A handful of entries carry ``note`` text recording that the citation is as given
by that review and has not been checked against an independent record; the rest
were verified against the publisher or an indexing service.
"""

from pyforestry.base.contracts import SourceReference

__all__ = ["INDEX_SET_REVIEW", "INDEX_SOURCES", "SELECTOR_SOURCES"]

#: The review this particular set of eighteen indices is drawn from. It supplies
#: the selection, the abbreviations and the comparison, not the indices.
INDEX_SET_REVIEW = SourceReference(
    author="Maleki, K., Kiviste, A. & Korjus, H.",
    year=2015,
    title=(
        "Analysis of individual tree competition effect on diameter growth of "
        "silver birch in Estonia"
    ),
    appendix="Table 2",
    note=(
        "Forest Systems 24(2), e023, 13 pp. doi:10.5424/fs/2015242-05742. Cited as the "
        "review that assembled and compared this set of indices; each index is "
        "attributed to its own author in INDEX_SOURCES."
    ),
)

#: Primary citation for each index, keyed by its abbreviation.
INDEX_SOURCES = {
    # -- non-spatial ---------------------------------------------------------
    "BA-gj": SourceReference(
        author="Steneker, G.A. & Jarvis, J.M.",
        year=1963,
        title="A preliminary study to assess competition in a white spruce-trembling aspen stand",
        note="The Forestry Chronicle 39(3):334-336. doi:10.5558/tfc39334-3",
    ),
    "BAL": SourceReference(
        author="Wykoff, W.R., Crookston, N.L. & Stage, A.R.",
        year=1982,
        title="User's guide to the Stand Prognosis Model",
        note=(
            "USDA Forest Service, Intermountain Forest and Range Experiment Station, "
            "General Technical Report INT-133, Ogden, Utah."
        ),
    ),
    "Sdr": SourceReference(
        author="Lorimer, C.G.",
        year=1983,
        title="Tests of age-independent competition indices for individual trees in natural "
        "hardwood stands",
        note="Forest Ecology and Management 6:343-360.",
    ),
    "drg": SourceReference(
        author="Hamilton, D.A.",
        year=1986,
        title=(
            "A logistic model of mortality in thinned and unthinned mixed conifer stands "
            "of northern Idaho"
        ),
        note=(
            "Forest Science 32(4):989-1000. Citation as given by Maleki et al. (2015) "
            "Table 2; not verified against an independent record."
        ),
    ),
    "BAr": SourceReference(
        author="Corona, P. & Ferrara, A.",
        year=1989,
        title="Individual competition indices for conifer plantations",
        note="Agriculture, Ecosystems and Environment 27:429-437.",
    ),
    "BALr": SourceReference(
        author="Vanclay, J.K.",
        year=1991,
        title="Aggregating tree species to develop diameter increment equations for "
        "tropical rainforests",
        note="Forest Ecology and Management 42:143-168.",
    ),
    "BALMOD": SourceReference(
        author="Schroder, J. & von Gadow, K.",
        year=1999,
        title="Testing a new competition index for Maritime pine in northwestern Spain",
        note="Canadian Journal of Forest Research 29:280-283.",
    ),
    # -- influence-zone overlap ---------------------------------------------
    "Sl": SourceReference(
        author="Staebler, G.R.",
        year=1951,
        title="Growth and spacing in an even-aged stand of Douglas-fir",
        note="MSc thesis, University of Michigan, Ann Arbor.",
    ),
    "SOr": SourceReference(
        author="Gerrard, D.J.",
        year=1969,
        title=(
            "Competition quotient: a new measure of the competition affecting individual "
            "forest trees"
        ),
        note=("Michigan State University, Agricultural Experiment Station, Research Bulletin 20."),
    ),
    "SOdr": SourceReference(
        author="Bella, I.E.",
        year=1971,
        title="A new competition model for individual trees",
        note="Forest Science 17:364-372.",
    ),
    # -- size-ratio spatial --------------------------------------------------
    "SBAr": SourceReference(
        author="Daniels, R.F., Burkhart, H.E. & Clason, T.R.",
        year=1986,
        title="A comparison of competition measures for predicting growth of loblolly pine trees",
        note="Canadian Journal of Forest Research 16:1230-1237.",
    ),
    "Heg": SourceReference(
        author="Hegyi, F.",
        year=1974,
        title="A simulation model for managing jack-pine stands",
        note=(
            "In: Fries, J. (ed.) Growth models for tree and stand simulation. Royal "
            "College of Forestry, Stockholm, pp. 74-90."
        ),
    ),
    "SAng1": SourceReference(
        author="Lin, J.Y.",
        year=1974,
        title=(
            "Stand growth simulation models for Douglas-fir and western hemlock in the "
            "northwestern United States"
        ),
        note=(
            "In: Fries, J. (ed.) Growth models for tree and stand simulation. Royal "
            "College of Forestry, Stockholm. Citation as given by Maleki et al. (2015) "
            "Table 2; not verified against an independent record."
        ),
    ),
    "SAng2": SourceReference(
        author="Rouvinen, S. & Kuuluvainen, T.",
        year=1997,
        title=(
            "Structure and asymmetry of tree crowns in relation to local competition in a "
            "natural mature Scots pine forest"
        ),
        note=(
            "Canadian Journal of Forest Research 27:890-902. Maleki et al. (2015) Table 2 "
            "dates this 1977; the work is 1997."
        ),
    ),
    "Almdg": SourceReference(
        author="Alemdag, I.S.",
        year=1978,
        title=(
            "Evaluation of some competition indexes for the prediction of diameter "
            "increment in planted white spruce"
        ),
        note=(
            "Canadian Forestry Service, Forest Management Institute, Information Report "
            "FMR-X-108, Ottawa."
        ),
    ),
    "Sdrl1": SourceReference(
        author="Lorimer, C.G.",
        year=1983,
        title=(
            "Tests of age-independent competition indices for individual trees in natural "
            "hardwood stands"
        ),
        note="Forest Ecology and Management 6:343-360.",
    ),
    "Sdrl2": SourceReference(
        author="Martin, G.L. & Ek, A.R.",
        year=1984,
        title=(
            "A comparison of competition measures and growth models for predicting "
            "plantation red pine diameter and height growth"
        ),
        note=(
            "Forest Science 30(3):731-743. The distance term decays: implemented as "
            "exp(-16*l/(d_i+d_j)), against the positive exponent printed by Maleki et al. "
            "(2015) Table 2 and Wang et al. (2012) Table 1."
        ),
    ),
}
INDEX_SOURCES["SdrAng"] = INDEX_SOURCES["SAng2"]  # same paper, second index

#: Primary citation for each competitor-selection rule that has one.
SELECTOR_SOURCES = {
    "MeanHeightRadius": SourceReference(
        author="Sims, A., Kiviste, A., Hordo, M., Laarmann, D. & von Gadow, K.",
        year=2009,
        title=(
            "Estimating tree survival: a study based on the Estonian Forest Research Plots Network"
        ),
        note=(
            "Annales Botanici Fennici 46:336-352. Source of the 0.4 * mean height "
            "influence-zone radius; the influence-zone concept itself is Staebler (1951)."
        ),
    ),
    "LeeGadowRadius": SourceReference(
        author="Lee, W.K. & von Gadow, K.",
        year=1997,
        title="Iterative Bestimmung der Konkurrenzbaeume in Pinus densiflora Bestaenden",
        note="Allgemeine Forst- und Jagdzeitung 168(3-4):41-44.",
    ),
    "SearchCone": SourceReference(
        author="Pretzsch, H.",
        year=2009,
        title="Forest dynamics, growth and yield: from measurement to model",
        note=(
            "Springer, Berlin. The reversed search-cone method; Maleki et al. (2015) "
            "also cite Richards et al. (2008) for the equivalent angular-height "
            "method. Their equations 4 and 5 print the subject's height where the "
            "competitor's is meant -- see SearchCone."
        ),
    ),
    "BitterlichBAF": SourceReference(
        author="Bitterlich, W.",
        year=1952,
        title="Die Winkelzaehlmessung",
        note=(
            "Allgemeine Forst- und Holzwirtschaftliche Zeitung 63:33-36. Variable-radius "
            "competitor selection. Citation as given by Maleki et al. (2015); not verified "
            "against an independent record. The angle-count principle itself is Bitterlich "
            "(1948), 'Die Winkelzaehlprobe'."
        ),
    ),
}
