"""
Normalizer utility for pharmacological entities, CYP enzymes, transporters, and relations.
Maps diverse clinical synonyms to canonical identifiers.
"""
import re
from typing import Dict

# Canonical mapping for drug names and physiological entities
ENTITY_SYNONYMS: Dict[str, str] = {
    # Enzymes & Transporters
    "cyp3a4": "CYP3A4",
    "cyp3a": "CYP3A4",
    "cytochrome p450 3a4": "CYP3A4",
    "cyp3a5": "CYP3A5",
    "cyp2c19": "CYP2C19",
    "cyp2c9": "CYP2C9",
    "p-gp": "P-GP",
    "p-glycoprotein": "P-GP",
    "abcb1": "P-GP",
    "pgp": "P-GP",
    "bcrp": "BCRP",
    "abcg2": "BCRP",
    "oat1": "OAT1",
    "oat3": "OAT3",
    "herg": "HERG",
    "ikr": "HERG",
    "k_v11.1": "HERG",
    "potassium channel": "HERG",
    "proximal_tubule_reabsorption": "PROXIMAL_TUBULE_REABSORPTION",
    "glomerular_filtration": "GLOMERULAR_FILTRATION",

    # Drugs
    "rivaroxaban": "RIVAROXABAN",
    "xarelto": "RIVAROXABAN",
    "ketoconazole": "KETOCONAZOLE",
    "nizoral": "KETOCONAZOLE",
    "clopidogrel": "CLOPIDOGREL",
    "plavix": "CLOPIDOGREL",
    "omeprazole": "OMEPRAZOLE",
    "prilosec": "OMEPRAZOLE",
    "pantoprazole": "PANTOPRAZOLE",
    "protonix": "PANTOPRAZOLE",
    "sotalol": "SOTALOL",
    "betapace": "SOTALOL",
    "levofloxacin": "LEVOFLOXACIN",
    "levaquin": "LEVOFLOXACIN",
    "doxycycline": "DOXYCYCLINE",
    "methotrexate": "METHOTREXATE",
    "trexall": "METHOTREXATE",
    "naproxen": "NAPROXEN",
    "aleve": "NAPROXEN",
    "acetaminophen": "ACETAMINOPHEN",
    "paracetamol": "ACETAMINOPHEN",
    "simvastatin": "SIMVASTATIN",
    "zocor": "SIMVASTATIN",
    "amlodipine": "AMLODIPINE",
    "norvasc": "AMLODIPINE",
    "rosuvastatin": "ROSUVASTATIN",
    "crestor": "ROSUVASTATIN",
    "tacrolimus": "TACROLIMUS",
    "prograf": "TACROLIMUS",
    "voriconazole": "VORICONAZOLE",
    "vfend": "VORICONAZOLE",
    "warfarin": "WARFARIN",
    "coumadin": "WARFARIN",
    "s-warfarin": "S-WARFARIN",
    "r-warfarin": "R-WARFARIN",
    "metronidazole": "METRONIDAZOLE",
    "flagyl": "METRONIDAZOLE",
    "lithium": "LITHIUM",
    "lithobid": "LITHIUM",
    "lisinopril": "LISINOPRIL",
    "zestril": "LISINOPRIL",
    "furosemide": "FUROSEMIDE",
    "lasix": "FUROSEMIDE",
    "atorvastatin": "ATORVASTATIN",
    "lipitor": "ATORVASTATIN",
    "azithromycin": "AZITHROMYCIN",
    "zithromax": "AZITHROMYCIN",
    "z-pak": "AZITHROMYCIN",
    "clarithromycin": "CLARITHROMYCIN",
    "biaxin": "CLARITHROMYCIN",
    "ceftriaxone": "CEFTRIAXONE",
    "rocephin": "CEFTRIAXONE",
    "tmp-smx": "TMP_SMX",
    "bactrim": "TMP_SMX",
    "septra": "TMP_SMX",
    "vitamin_k_flora": "VITAMIN_K_FLORA",
    "gut_flora": "VITAMIN_K_FLORA",

    # TASK-11: Codeine + CYP2D6 UM
    "codeine": "CODEINE",
    "cyp2d6": "CYP2D6",
    "cytochrome p450 2d6": "CYP2D6",
    "morphine": "MORPHINE",
    "mu_opioid_receptor": "MU_OPIOID_RECEPTOR",
    "opioid_receptor": "MU_OPIOID_RECEPTOR",
    "morphine_sulfate": "MORPHINE",

    # TASK-12: Azathioprine + TPMT
    "azathioprine": "AZATHIOPRINE",
    "imuran": "AZATHIOPRINE",
    "tpmt": "TPMT",
    "thiopurine_methyltransferase": "TPMT",
    "6_thioguanine_nucleotides": "6_THIOGUANINE_NUCLEOTIDES",
    "6_tgn": "6_THIOGUANINE_NUCLEOTIDES",
    "thioguanine_nucleotides": "6_THIOGUANINE_NUCLEOTIDES",
    "bone_marrow": "BONE_MARROW",
    "myeloid_lineage": "BONE_MARROW",

    # TASK-13: Abacavir + HLA-B*57:01
    "abacavir": "ABACAVIR",
    "ziagen": "ABACAVIR",
    "hla_b5701": "HLA_B5701",
    "hla_b_5701": "HLA_B5701",
    "hla_b57_01": "HLA_B5701",
    "cd8_t_cell": "CD8_T_CELL_ACTIVATION",
    "cd8_t_cell_activation": "CD8_T_CELL_ACTIVATION",
    "cytotoxic_t_cell": "CD8_T_CELL_ACTIVATION",
    "hypersensitivity_syndrome": "HYPERSENSITIVITY_SYNDROME",
    "abacavir_hypersensitivity": "HYPERSENSITIVITY_SYNDROME",

    # TASK-14: Irinotecan + UGT1A1
    "irinotecan": "IRINOTECAN",
    "camptosar": "IRINOTECAN",
    "carboxylesterase": "CARBOXYLESTERASE",
    "ces": "CARBOXYLESTERASE",
    "sn38": "SN38",
    "sn_38": "SN38",
    "7_ethyl_10_hydroxycamptothecin": "SN38",
    "ugt1a1": "UGT1A1",
    "udp_glucuronosyltransferase": "UGT1A1",
    "sn38_glucuronide": "SN38_GLUCURONIDE",
    "sn_38_glucuronide": "SN38_GLUCURONIDE",
    "sn38g": "SN38_GLUCURONIDE",
}

# Relation mapping to canonical verbs
RELATION_SYNONYMS: Dict[str, str] = {
    # INHIBITS variants
    "inhibits": "INHIBITS",
    "inhibited_by": "INHIBITS",
    "blockade": "INHIBITS",
    "blocks": "INHIBITS",
    "strongly_inhibits": "INHIBITS",
    "potently_inhibits": "INHIBITS",
    "significantly_inhibits": "INHIBITS",
    "partially_inhibits": "INHIBITS",
    "weakly_inhibits": "INHIBITS",
    "reversibly_inhibits": "INHIBITS",
    "irreversibly_inhibits": "INHIBITS",
    "competitively_inhibits": "INHIBITS",
    "noncompetitively_inhibits": "INHIBITS",
    "uncompetitively_inhibits": "INHIBITS",
    "mixed_inhibits": "INHIBITS",
    "allosterically_inhibits": "INHIBITS",
    "suicide_inhibits": "INHIBITS",
    "mechanism_based_inhibits": "INHIBITS",
    "time_dependent_inhibits": "INHIBITS",
    "inhibition": "INHIBITS",
    "inhibitory_effect": "INHIBITS",
    "reduces_activity": "INHIBITS",
    "decreases_activity": "INHIBITS",
    "suppresses": "INHIBITS",
    "attenuates": "INHIBITS",
    "dampens": "INHIBITS",
    "negatively_regulates": "INHIBITS",
    "downregulates": "INHIBITS",

    # INDUCES variants
    "induces": "INDUCES",
    "stimulated_by": "INDUCES",
    "upregulates": "INDUCES",
    "strongly_induces": "INDUCES",
    "potently_induces": "INDUCES",
    "significantly_induces": "INDUCES",
    "activates": "INDUCES",
    "stimulates": "INDUCES",
    "enhances": "INDUCES",
    "potentiates": "INDUCES",
    "positively_regulates": "INDUCES",
    "up_regulates": "INDUCES",

    # COMPETITIVELY_BLOCKS variants
    "competitively_blocks": "COMPETITIVELY_BLOCKS",
    "competes_with": "COMPETITIVELY_BLOCKS",
    "competitive_antagonist": "COMPETITIVELY_BLOCKS",
    "competes_for_binding": "COMPETITIVELY_BLOCKS",
    "displaces": "COMPETITIVELY_BLOCKS",

    # STEREOSELECTIVELY_INHIBITS variants
    "stereoselectively_inhibits": "STEREOSELECTIVELY_INHIBITS",
    "selective_inhibition": "STEREOSELECTIVELY_INHIBITS",
    "stereospecific_inhibition": "STEREOSELECTIVELY_INHIBITS",
    "enantioselective_inhibition": "STEREOSELECTIVELY_INHIBITS",
    "selectively_inhibits": "STEREOSELECTIVELY_INHIBITS",
    "preferentially_inhibits": "STEREOSELECTIVELY_INHIBITS",

    # INCREASES_EXPOSURE variants
    "increases_exposure": "INCREASES_EXPOSURE",
    "elevates_auc": "INCREASES_EXPOSURE",
    "increases_auc": "INCREASES_EXPOSURE",
    "decreases_clearance": "INCREASES_EXPOSURE",
    "elevates_plasma_levels": "INCREASES_EXPOSURE",
    "raises_plasma_concentration": "INCREASES_EXPOSURE",
    "causes_accumulation": "INCREASES_EXPOSURE",
    "increases_plasma_concentration": "INCREASES_EXPOSURE",
    "raises_auc": "INCREASES_EXPOSURE",
    "increases_cmax": "INCREASES_EXPOSURE",
    "prolongs_half_life": "INCREASES_EXPOSURE",
    "reduces_elimination": "INCREASES_EXPOSURE",
    "impairs_clearance": "INCREASES_EXPOSURE",
    "reduces_metabolism": "INCREASES_EXPOSURE",
    "inhibits_metabolism": "INCREASES_EXPOSURE",
    "inhibits_clearance": "INCREASES_EXPOSURE",

    # DECREASES_EXPOSURE variants
    "decreases_exposure": "DECREASES_EXPOSURE",
    "reduces_exposure": "DECREASES_EXPOSURE",
    "lowers_auc": "DECREASES_EXPOSURE",
    "reduces_auc": "DECREASES_EXPOSURE",
    "decreases_cmax": "DECREASES_EXPOSURE",
    "reduces_cmax": "DECREASES_EXPOSURE",
    "accelerates_clearance": "DECREASES_EXPOSURE",
    "increases_clearance": "DECREASES_EXPOSURE",
    "enhances_metabolism": "DECREASES_EXPOSURE",
    "induces_metabolism": "DECREASES_EXPOSURE",

    # BLOCKS_BIOACTIVATION variants
    "blocks_bioactivation": "BLOCKS_BIOACTIVATION",
    "reduces_active_metabolite": "BLOCKS_BIOACTIVATION",
    "prevents_bioactivation": "BLOCKS_BIOACTIVATION",
    "inhibits_bioactivation": "BLOCKS_BIOACTIVATION",
    "blocks_activation": "BLOCKS_BIOACTIVATION",
    "prevents_activation": "BLOCKS_BIOACTIVATION",
    "reduces_formation_of_active_metabolite": "BLOCKS_BIOACTIVATION",
    "impaired_bioactivation": "BLOCKS_BIOACTIVATION",
    "bioactivation_blocked": "BLOCKS_BIOACTIVATION",
    "reduces_active_thiol": "BLOCKS_BIOACTIVATION",

    # PRODUCES_ADDITIVE_BLOCK variants
    "produces_additive_block": "PRODUCES_ADDITIVE_BLOCK",
    "additive_inhibition": "PRODUCES_ADDITIVE_BLOCK",
    "additive_effect": "PRODUCES_ADDITIVE_BLOCK",
    "synergistic_inhibition": "PRODUCES_ADDITIVE_BLOCK",
    "potentiates_blockade": "PRODUCES_ADDITIVE_BLOCK",
    "enhances_inhibition": "PRODUCES_ADDITIVE_BLOCK",

    # NO_INHIBITION / NO_INTERACTION variants (for safe controls)
    "no_inhibition": "NO_INHIBITION",
    "does_not_inhibit": "NO_INHIBITION",
    "lacks_inhibition": "NO_INHIBITION",
    "no_effect_on": "NO_INHIBITION",
    "no_interaction": "NO_INHIBITION",
    "no_clinically_meaningful_inhibition": "NO_INHIBITION",
    "minimal_effect": "NO_INHIBITION",
    "negligible_inhibition": "NO_INHIBITION",
    "does_not_induce": "NO_INHIBITION",
    "lacks_induction": "NO_INHIBITION",

    # MINIMAL_DECREASE / WEAK_EFFECT variants
    "minimal_decrease": "MINIMAL_DECREASE",
    "weak_decrease": "MINIMAL_DECREASE",
    "slight_decrease": "MINIMAL_DECREASE",
    "marginal_decrease": "MINIMAL_DECREASE",
    "minimal_effect": "MINIMAL_DECREASE",
    "weakly_decreases": "MINIMAL_DECREASE",
    "slightly_decreases": "MINIMAL_DECREASE",

    # REQUIRES_FOR_BIOACTIVATION variants
    "requires_for_bioactivation": "REQUIRES_FOR_BIOACTIVATION",
    "requires_cyp2d6_for_bioactivation": "REQUIRES_FOR_BIOACTIVATION",
    "bioactivation_requires": "REQUIRES_FOR_BIOACTIVATION",
    "converted_by": "REQUIRES_FOR_BIOACTIVATION",
    "activated_by": "REQUIRES_FOR_BIOACTIVATION",
    "prodrug_activated_by": "REQUIRES_FOR_BIOACTIVATION",

    # BINDS_AND_ALTERS_PEPTIDE_REPERTOIRE variants
    "binds_and_alters_peptide_repertoire": "BINDS_AND_ALTERS_PEPTIDE_REPERTOIRE",
    "alters_peptide_repertoire": "BINDS_AND_ALTERS_PEPTIDE_REPERTOIRE",
    "binds_hla": "BINDS_AND_ALTERS_PEPTIDE_REPERTOIRE",
    "binds_hla_b5701": "BINDS_AND_ALTERS_PEPTIDE_REPERTOIRE",
    "alters_self_peptide_presentation": "BINDS_AND_ALTERS_PEPTIDE_REPERTOIRE",

    # INCREASES_EXPOSURE additional for specific pathways
    "elevates_exposure": "INCREASES_EXPOSURE",
    "increases_systemic_exposure": "INCREASES_EXPOSURE",
    "increases_bioavailability": "INCREASES_EXPOSURE",
    "reduces_first_pass_metabolism": "INCREASES_EXPOSURE",
    "inhibits_first_pass": "INCREASES_EXPOSURE",

    # NEUTRAL / MAINTAINS variants
    "no_change_in_exposure": "NO_CHANGE_IN_EXPOSURE",
    "maintains_exposure": "NO_CHANGE_IN_EXPOSURE",
    "unchanged_exposure": "NO_CHANGE_IN_EXPOSURE",
    "maintains_levels": "NO_CHANGE_IN_EXPOSURE",

    # DECREASES_EXPOSURE additional
    "reduces_plasma_levels": "DECREASES_EXPOSURE",
    "lowers_plasma_concentration": "DECREASES_EXPOSURE",
    "decreases_bioavailability": "DECREASES_EXPOSURE",
}

# Trailing biological nouns to strip (e.g., "CYP3A4 enzyme" -> "CYP3A4")
_TRAILING_NOUNS = (
    "channel", "enzyme", "protein", "transporter", "receptor",
    "pump", "carrier", "subunit", "complex", "isoform", "gene"
)

def _clean_entity_token(token: str) -> str:
    """Strip parentheticals and trailing biological nouns from entity token."""
    if not token:
        return ""
    # Strip parentheticals: "P-gp (ABCB1)" -> "P-gp"
    cleaned = re.sub(r"\s*\([^)]*\)\s*", " ", token)
    # Strip trailing biological nouns: "CYP3A4 enzyme" -> "CYP3A4"
    words = cleaned.strip().split()
    while words and words[-1].lower() in _TRAILING_NOUNS:
        words.pop()
    return " ".join(words).strip()

def normalize_entity(name: str) -> str:
    """Normalize drug/protein/target entity string."""
    if not name:
        return ""
    clean = _clean_entity_token(name.strip().lower())
    return ENTITY_SYNONYMS.get(clean, clean.upper())

def normalize_relation(rel: str) -> str:
    """Normalize pharmacological interaction relationship verb."""
    if not rel:
        return ""
    clean = rel.strip().lower()
    return RELATION_SYNONYMS.get(clean, clean.upper())
