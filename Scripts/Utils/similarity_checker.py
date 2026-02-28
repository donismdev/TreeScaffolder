import difflib
import re
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple

def _get_rules():
    """Load similarity rules from resource file."""
    try:
        # Default path relative to this script
        base_dir = Path(__file__).parent.parent.parent
        rules_path = base_dir / "Resources" / "similarity_rules.json"
        if rules_path.exists():
            with open(rules_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data
    except Exception:
        pass
    return {}

def _is_allowed_pairing(name1: str, name2: str) -> bool:
    """Check if two filenames are allowed pairings (e.g., file.h and file.cpp)."""
    rules = _get_rules()
    pairings = rules.get("allowed_extension_pairs", [])
    
    def get_matching_pair_and_stem(filename):
        # Sort pairs by length of extensions descending to match longest first (e.g. .test.ts before .ts)
        for pair in pairings:
            for ext in pair:
                if filename.lower().endswith(ext.lower()):
                    stem = filename[:-len(ext)]
                    return stem.lower(), ext.lower(), pair
        # Fallback to standard Path suffix if no multi-dot matches
        p = Path(filename)
        return p.stem.lower(), p.suffix.lower(), None

    stem1, ext1, pair1 = get_matching_pair_and_stem(name1)
    stem2, ext2, pair2 = get_matching_pair_and_stem(name2)
    
    # Must have the same base name
    if stem1 != stem2 or not stem1:
        return False
        
    # If they matched the same allowed pair, it's a valid pairing
    if pair1 and pair2 and pair1 == pair2:
        # Just ensure they aren't the exact same extension
        return ext1 != ext2
            
    return False

def normalize_filename(name: str, config: dict) -> str:
    n = name
    if config.get("NORMALIZE_LOWER", True): n = n.lower()
    if config.get("NORMALIZE_REMOVE_NONALNUM", True): n = re.sub(r"[^a-z0-9]", "", n)
    return n

def find_similar_candidates(existing_map: Dict[str, List[Path]], target_name: str, config: dict) -> List[Tuple[str, float, List[Path]]]:
    if not config.get("ENABLE_SIMILARITY_SCAN", True): 
        return []
        
    threshold = config.get("SIMILARITY_RATIO_THRESHOLD", 0.86)
    target_norm = normalize_filename(target_name, config)
    if not target_norm: 
        return []
        
    out = []
    for exist_name, paths in existing_map.items():
        # 1. Skip if they are allowed pairings (e.g. MyFile.h and MyFile.cpp)
        if _is_allowed_pairing(target_name, exist_name):
            continue
            
        # 2. Skip exact matches (these are handled by overwrite/identical logic)
        if target_name == exist_name:
            continue

        exist_norm = normalize_filename(exist_name, config)
        if not exist_norm: 
            continue
            
        ratio = difflib.SequenceMatcher(a=target_norm, b=exist_norm).ratio()
        if ratio >= threshold:
            out.append((exist_name, ratio, paths))
            
    out.sort(key=lambda x: x[1], reverse=True)
    return out
