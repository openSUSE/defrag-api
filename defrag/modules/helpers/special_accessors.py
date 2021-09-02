from typing import List, Tuple
from functools import reduce


def user_keys(o: object, atts_names: List[str], keys: List[str] = []):
    current_keys = o.__dict__
    keys += current_keys
    for k in current_keys:
        if k in atts_names:
            return user_keys(getattr(o, k), atts_names, keys)
    return keys


def validate_all_user_attributes(o: object, atts_names: List[str]) -> Tuple[List[str], List[str]]:
    keys = user_keys(o, atts_names)
    missing = list(filter(lambda x: not x in keys, atts_names))
    excess = list(filter(lambda x: not x in atts_names, keys))
    return missing, excess