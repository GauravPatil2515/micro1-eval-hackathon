"""
Normalizer utility for pharmacological entities, CYP enzymes, transporters, and relations.
Maps diverse clinical synonyms to canonical identifiers.
"""
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
    "lasix": "FUROSEMIDE"
}

# Relation mapping to canonical verbs
RELATION_SYNONYMS: Dict[str, str] = {
    "inhibits": "INHIBITS",
    "inhibited_by": "INHIBITS",
    "blockade": "INHIBITS",
    "blocks": "INHIBITS",
    "induces": "INDUCES",
    "stimulated_by": "INDUCES",
    "upregulates": "INDUCES",
    "competitively_blocks": "COMPETITIVELY_BLOCKS",
    "competes_with": "COMPETITIVELY_BLOCKS",
    "stereoselectively_inhibits": "STEREOSELECTIVELY_INHIBITS",
    "selective_inhibition": "STEREOSELECTIVELY_INHIBITS",
    "increases_exposure": "INCREASES_EXPOSURE",
    "elevates_auc": "INCREASES_EXPOSURE",
    "increases_auc": "INCREASES_EXPOSURE",
    "decreases_clearance": "INCREASES_EXPOSURE",
    "decreases_exposure": "DECREASES_EXPOSURE",
    "blocks_bioactivation": "BLOCKS_BIOACTIVATION",
    "reduces_active_metabolite": "BLOCKS_BIOACTIVATION",
    "produces_additive_block": "PRODUCES_ADDITIVE_BLOCK",
    "additive_inhibition": "PRODUCES_ADDITIVE_BLOCK"
}

def normalize_entity(name: str) -> str:
    """Normalize drug/protein/target entity string."""
    if not name:
        return ""
    clean = name.strip().lower()
    return ENTITY_SYNONYMS.get(clean, clean.upper())

def normalize_relation(rel: str) -> str:
    """Normalize pharmacological interaction relationship verb."""
    if not rel:
        return ""
    clean = rel.strip().lower()
    return RELATION_SYNONYMS.get(clean, clean.upper())
