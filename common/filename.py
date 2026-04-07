import os
import re

# Known character names — longest first for greedy matching
CHARACTER_NAMES = [
    "CorruptedKnight", "FacelessKnight", "BlackKnight",
    "CerberusIV", "Cerberus4", "CerberusV", "Cerberus5",
    "Commissar", "Inquisitor", "Minibeast", "Seraphim", "Theophan",
    "SoldierPH", "Soldier",
    "Arystan", "Anders", "Luther", "Yanagi", "Yuriko", "Viktor",
    "Walter", "Nikolai",
    "Alysa", "Beast", "Igor", "Miraz", "Maria", "Elsa", "Liza",
    "Mike", "Troll",
    # Minigame
    "DogLion", "Werewolf", "Traveller", "Merchant", "Hunter",
    "Knight", "Witch", "Withch", "Ogre", "Kids",
]

ARC_NAMES = [
    "SuicideMission", "TheShatteredShell", "InversionImpulse",
    "ScoutingMission", "OneLastTime", "LongWinter", "WaywardSon",
    "TrainStation", "Surrounded", "Verdinar", "TheNews",
    "Purpose", "Payback",
]


def clean_character_filename(file_path: str) -> str:
    """Preprocess Ch_ filenames: strip animation state, add Canned if no arc.

    Transforms: Ch_AlysaBrainwashedTheNews_(74M80)_(50M0)_(10).png
    Into:       Ch_Alysa_TheNews_(74M80)_(50M0)_(10).png

    Transforms: Ch_AlysaConfident_(76M94)_(p38M0)_(10).png
    Into:       Ch_Alysa_Canned_(76M94)_(p38M0)_(10).png
    """
    basename = os.path.basename(file_path)

    if not basename.startswith("Ch_"):
        return file_path

    # Split off the prefix and the metadata suffix (everything from first _( onward)
    match = re.match(r'^(Ch_)(.+?)(_\(.+)$', basename)
    if not match:
        return file_path

    prefix = match.group(1)       # "Ch_"
    name_block = match.group(2)   # "AlysaBrainwashedTheNews"
    suffix = match.group(3)       # "_(74M80)_(50M0)_(10).png" etc

    # Find the character name
    char_name = None
    for name in CHARACTER_NAMES:
        if name_block.startswith(name):
            char_name = name
            break

    if not char_name:
        return file_path

    remainder = name_block[len(char_name):]  # "BrainwashedTheNews" or "Confident"

    # Find arc name in the remainder
    arc_name = None
    for arc in ARC_NAMES:
        if arc in remainder:
            arc_name = arc
            break

    if arc_name:
        cleaned = f"{prefix}{char_name}_{arc_name}{suffix}"
    else:
        cleaned = f"{prefix}{char_name}_Canned{suffix}"

    # Replace basename in full path
    return file_path.replace(basename, cleaned)
