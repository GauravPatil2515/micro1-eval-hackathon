# TASK-01: Dual Elimination Shutdown: Rivaroxaban + Ketoconazole in Moderate Renal Impairment

## Ground Truth Causal Graph
```mermaid
graph LR
  %% Ground Truth
  classDef perpetrator fill:#ff6b6b,color:#fff;
  classDef intermediate fill:#ffd93d,color:#000;
  classDef victim fill:#6bcb77,color:#fff;
  classDef drug fill:#4d96ff,color:#fff;
  classDef enzyme fill:#ffd93d,color:#000;
  classDef transporter fill:#a8e6cf,color:#000;
  classDef physiological fill:#ffaaa5,color:#000;
  class KETOCONAZOLE drug;
  class P-GP enzyme;
  class RIVAROXABAN drug;
  class CYP3A4 enzyme;
  CYP3A4[CYP3A4] -->|INCREASES_EXPOSURE| RIVAROXABAN[RIVAROXABAN]
  KETOCONAZOLE[KETOCONAZOLE] -->|INHIBITS| CYP3A4[CYP3A4]
  KETOCONAZOLE[KETOCONAZOLE] -->|INHIBITS| P_GP[P-GP]
  P_GP[P-GP] -->|INCREASES_EXPOSURE| RIVAROXABAN[RIVAROXABAN]
```


# TASK-02: Prodrug Bioactivation Defeat: Clopidogrel + Omeprazole with Unknown CYP2C19 Genotype

## Ground Truth Causal Graph
```mermaid
graph LR
  %% Ground Truth
  classDef perpetrator fill:#ff6b6b,color:#fff;
  classDef intermediate fill:#ffd93d,color:#000;
  classDef victim fill:#6bcb77,color:#fff;
  classDef drug fill:#4d96ff,color:#fff;
  classDef enzyme fill:#ffd93d,color:#000;
  classDef transporter fill:#a8e6cf,color:#000;
  classDef physiological fill:#ffaaa5,color:#000;
  class CLOPIDOGREL drug;
  class CYP2C19 enzyme;
  class OMEPRAZOLE drug;
  CYP2C19[CYP2C19] -->|BLOCKS_BIOACTIVATION| CLOPIDOGREL[CLOPIDOGREL]
  OMEPRAZOLE[OMEPRAZOLE] -->|INHIBITS| CYP2C19[CYP2C19]
```


# TASK-03: Electrolyte-Gated Proarrhythmic Cascade: Sotalol + HCTZ + Levofloxacin

## Ground Truth Causal Graph
```mermaid
graph LR
  %% Ground Truth
  classDef perpetrator fill:#ff6b6b,color:#fff;
  classDef intermediate fill:#ffd93d,color:#000;
  classDef victim fill:#6bcb77,color:#fff;
  classDef drug fill:#4d96ff,color:#fff;
  classDef enzyme fill:#ffd93d,color:#000;
  classDef transporter fill:#a8e6cf,color:#000;
  classDef physiological fill:#ffaaa5,color:#000;
  class LEVOFLOXACIN drug;
  class HERG enzyme;
  class SOTALOL drug;
  LEVOFLOXACIN[LEVOFLOXACIN] -->|PRODUCES_ADDITIVE_BLOCK| HERG[HERG]
  SOTALOL[SOTALOL] -->|INHIBITS| HERG[HERG]
```


# TASK-04: Renal Transporter Secretion Blockade: Methotrexate + Naproxen in Borderline Clearance

## Ground Truth Causal Graph
```mermaid
graph LR
  %% Ground Truth
  classDef perpetrator fill:#ff6b6b,color:#fff;
  classDef intermediate fill:#ffd93d,color:#000;
  classDef victim fill:#6bcb77,color:#fff;
  classDef drug fill:#4d96ff,color:#fff;
  classDef enzyme fill:#ffd93d,color:#000;
  classDef transporter fill:#a8e6cf,color:#000;
  classDef physiological fill:#ffaaa5,color:#000;
  class METHOTREXATE drug;
  class OAT1 enzyme;
  class NAPROXEN drug;
  class OAT3 enzyme;
  NAPROXEN[NAPROXEN] -->|COMPETITIVELY_BLOCKS| OAT1[OAT1]
  NAPROXEN[NAPROXEN] -->|COMPETITIVELY_BLOCKS| OAT3[OAT3]
  OAT1[OAT1] -->|INCREASES_EXPOSURE| METHOTREXATE[METHOTREXATE]
  OAT3[OAT3] -->|INCREASES_EXPOSURE| METHOTREXATE[METHOTREXATE]
```


# TASK-05: Substrate Competition & Regulatory Dose Ceiling: Simvastatin + Amlodipine

## Ground Truth Causal Graph
```mermaid
graph LR
  %% Ground Truth
  classDef perpetrator fill:#ff6b6b,color:#fff;
  classDef intermediate fill:#ffd93d,color:#000;
  classDef victim fill:#6bcb77,color:#fff;
  classDef drug fill:#4d96ff,color:#fff;
  classDef enzyme fill:#ffd93d,color:#000;
  classDef transporter fill:#a8e6cf,color:#000;
  classDef physiological fill:#ffaaa5,color:#000;
  class SIMVASTATIN drug;
  class AMLODIPINE drug;
  class CYP3A4 enzyme;
  AMLODIPINE[AMLODIPINE] -->|INHIBITS| CYP3A4[CYP3A4]
  CYP3A4[CYP3A4] -->|INCREASES_EXPOSURE| SIMVASTATIN[SIMVASTATIN]
```


# TASK-06: CYP3A4/5 Multi-Enzyme Collapse: Tacrolimus + Voriconazole with CYP3A5*3/*3 Genotype

## Ground Truth Causal Graph
```mermaid
graph LR
  %% Ground Truth
  classDef perpetrator fill:#ff6b6b,color:#fff;
  classDef intermediate fill:#ffd93d,color:#000;
  classDef victim fill:#6bcb77,color:#fff;
  classDef drug fill:#4d96ff,color:#fff;
  classDef enzyme fill:#ffd93d,color:#000;
  classDef transporter fill:#a8e6cf,color:#000;
  classDef physiological fill:#ffaaa5,color:#000;
  class TACROLIMUS drug;
  class CYP3A5 enzyme;
  class VORICONAZOLE drug;
  class CYP3A4 enzyme;
  CYP3A4[CYP3A4] -->|INCREASES_EXPOSURE| TACROLIMUS[TACROLIMUS]
  VORICONAZOLE[VORICONAZOLE] -->|INHIBITS| CYP3A4[CYP3A4]
  VORICONAZOLE[VORICONAZOLE] -->|INHIBITS| CYP3A5[CYP3A5]
```


# TASK-07: Stereoselective Enantiomeric Clearance Blockade: Warfarin + Metronidazole

## Ground Truth Causal Graph
```mermaid
graph LR
  %% Ground Truth
  classDef perpetrator fill:#ff6b6b,color:#fff;
  classDef intermediate fill:#ffd93d,color:#000;
  classDef victim fill:#6bcb77,color:#fff;
  classDef drug fill:#4d96ff,color:#fff;
  classDef enzyme fill:#ffd93d,color:#000;
  classDef transporter fill:#a8e6cf,color:#000;
  classDef physiological fill:#ffaaa5,color:#000;
  class S-WARFARIN drug;
  class METRONIDAZOLE drug;
  class CYP2C9 enzyme;
  CYP2C9[CYP2C9] -->|INCREASES_EXPOSURE| S_WARFARIN[S-WARFARIN]
  METRONIDAZOLE[METRONIDAZOLE] -->|STEREOSELECTIVELY_INHIBITS| CYP2C9[CYP2C9]
```


# TASK-08: Renal Proximal Tubule Sodium-Mimic Synergy: Lithium + Lisinopril + Furosemide

## Ground Truth Causal Graph
```mermaid
graph LR
  %% Ground Truth
  classDef perpetrator fill:#ff6b6b,color:#fff;
  classDef intermediate fill:#ffd93d,color:#000;
  classDef victim fill:#6bcb77,color:#fff;
  classDef drug fill:#4d96ff,color:#fff;
  classDef enzyme fill:#ffd93d,color:#000;
  classDef transporter fill:#a8e6cf,color:#000;
  classDef physiological fill:#ffaaa5,color:#000;
  class LISINOPRIL drug;
  class LITHIUM drug;
  class GLOMERULAR_FILTRATION physiological;
  class FUROSEMIDE drug;
  class PROXIMAL_TUBULE_REABSORPTION physiological;
  FUROSEMIDE[FUROSEMIDE] -->|INDUCES| PROXIMAL_TUBULE_REABSORPTION[PROXIMAL_TUBULE_REABSORPTION]
  LISINOPRIL[LISINOPRIL] -->|DECREASES_EXPOSURE| GLOMERULAR_FILTRATION[GLOMERULAR_FILTRATION]
  PROXIMAL_TUBULE_REABSORPTION[PROXIMAL_TUBULE_REABSORPTION] -->|INCREASES_EXPOSURE| LITHIUM[LITHIUM]
```


# TASK-09: Safe Combination Control: Atorvastatin + Azithromycin

## Ground Truth Causal Graph
```mermaid
graph LR
  %% Ground Truth
  classDef perpetrator fill:#ff6b6b,color:#fff;
  classDef intermediate fill:#ffd93d,color:#000;
  classDef victim fill:#6bcb77,color:#fff;
  classDef drug fill:#4d96ff,color:#fff;
  classDef enzyme fill:#ffd93d,color:#000;
  classDef transporter fill:#a8e6cf,color:#000;
  classDef physiological fill:#ffaaa5,color:#000;
  class AZITHROMYCIN drug;
  class CYP3A4 enzyme;
  AZITHROMYCIN[AZITHROMYCIN] -->|DECREASES_EXPOSURE| CYP3A4[CYP3A4]
```


# TASK-10: Safe Combination Control: Warfarin + Ceftriaxone

## Ground Truth Causal Graph
```mermaid
graph LR
  %% Ground Truth
  classDef perpetrator fill:#ff6b6b,color:#fff;
  classDef intermediate fill:#ffd93d,color:#000;
  classDef victim fill:#6bcb77,color:#fff;
  classDef drug fill:#4d96ff,color:#fff;
  classDef enzyme fill:#ffd93d,color:#000;
  classDef transporter fill:#a8e6cf,color:#000;
  classDef physiological fill:#ffaaa5,color:#000;
  class VITAMIN_K_FLORA physiological;
  class CEFTRIAXONE drug;
  CEFTRIAXONE[CEFTRIAXONE] -->|DECREASES_EXPOSURE| VITAMIN_K_FLORA[VITAMIN_K_FLORA]
```

