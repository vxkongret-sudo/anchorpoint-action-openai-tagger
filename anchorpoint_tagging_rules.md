# Tagging Rules

Tag by filename + folder path. 5 categories. No duplicate tags across categories. Never tag animation states (Idle, Run, Attack, Angry, Confident, Sitting, Clap, etc.). For `Ch_` files: NEVER use `sprite`, `spritesheet`, or `CutsceneNPC` as tags — use `animation`, `character`, and `npc` instead.

## Character filename structure
Filenames are pre-cleaned: `Ch_[Name]_[Arc or Canned]_(...)`.
- `Canned` means no specific arc — tag it as `Canned`
- Otherwise the arc name is already extracted — tag it as the arc

## 1. Asset Type
- `character` + `animation`: `Ch_` prefix (never use `sprite` for these)
- `boss`: Beast, Commissar, Inquisitor, Nikolai, Walter, CerberusIV, CerberusV
- `enemy`: Soldier, Minibeast, Troll, Ogre, Werewolf, Knight (not Black/Faceless/Corrupted), DogLion, Witch, Ghost
- `npc`: Alysa, Anders, Arystan, Elsa, Liza, Luther, Maria, Mike, Miraz, Nikolai, Seraphim, Theophan, Viktor, Yanagi, Yuriko, FacelessKnight, BlackKnight
- `player`: Igor, IgorPlayable
- `portrait`: `DialoguePortrait/` folder or `portrait` in name
- `environment`: `Environment/` folder or suffix `_BG`, `_D`, `_L`, `_AB`
- `ui`: `UI/`/`UISprites/`/`UIAnimations/` folder or `UI_` prefix
- `vfx`: `FX_`/`Vfx_`/`HitFX_`/`WaveFX_` prefix or `FXs/`/`FX/`/`Emission map/` folder
- `cutscene`: `Cutscenes/` or `ScenesAndCutscenes/` folder
- `spritesheet`: contains `spritesheet` or grid `_3x3`/`_2x1` (NOT for `Ch_` files)
- `prop`: `Props/` folder
- `particle`: `Particles/` folder or `Snowflake`/`spark`/`particle` in name
- `minigame`: `Minigame/` folder
- `source`: `.psd` extension or `Redactable/` folder

Boss/enemy/npc always pair with `character` when `Ch_` prefix present.

## 2. Character Names
Match longest name first from: Alysa, Anders, Arystan, Beast, BlackKnight, CerberusIV (also Cerberus4), CerberusV (also Cerberus5), Commissar, CorruptedKnight, Elsa, FacelessKnight, Igor, Inquisitor, Liza, Luther, Maria, Mike, Minibeast, Miraz, Nikolai, Seraphim, Soldier (also SoldierPH), Theophan, Troll, Viktor, Walter, Yanagi, Yuriko.
Minigame-only: DogLion, Hunter, Knight, Ogre, Werewolf, Witch (also Withch), Merchant, Traveller, Kids.
If no `Ch_` prefix but known name in filename/parent folder, still tag it.

## 3. Location
From `ScenesAndCutscenes/[Arc]/[Location]`, `Environment/` subfolders, or filename suffixes.
Locations: ArtificialDome, ArystanRoom, AzureLab, AzureLab1stFloor, AzureLab2ndFloor, AzureCorridor, BeastFight, Bibliothec, BlackIceGates, Blizzard, CommissarOffice, Crossroads, DoorsDimension, DropPod, Elevator, FlowerField, Forest, FrozenLake, Graveyard, Hangar, HospitalIncinerator, HQ, IgorsMind, MikeRoom, RadioTower, RiverOfBlood, Roof, SeraphimPrison, SoldiersRoom, Surrounded_MainSquare, Surrounded_SideStreet, TrainStation, Verdinar.
Corridor subfolders (e.g. `CorridorToBeast`) → tag destination location.

## 4. Arc
Only if filename contains an exact arc name, otherwise skip entirely.
Arcs: SuicideMission, Purpose, LongWinter, OneLastTime, Payback, Verdinar, Surrounded, TheNews, InversionImpulse, ScoutingMission, TheShatteredShell, TrainStation, WaywardSon.

## 5. Status
- `Final`: only if `Final` in name/folder
- `WIP`: `WIP` in name/folder
- `Layout`: `Layout`/`MainLayout` in name/folder
- `Old`: `Old`/`OLD`/`OldVersion`/`CG_Old` in path
- `TBD`: `TBD`/`Z_zTBD`/`04_TBD_Unknown` in path
- `Archive`: folder starts with `Z_`/`Z_z`
- `Ref`: `Ref/` folder
Priority: Old > TBD > Archive > Layout > WIP > Final

## Folder shortcuts
`Characters/CutsceneNPC/`→npc, `Enemies/Bosses/`→boss+enemy, `Enemies/Minions/`→enemy, `Environment/`→environment, `UI/`→ui, `FX/`→vfx, `Cutscenes/`→cutscene, `ScenesAndCutscenes/`→cutscene+arc, `Minigame/`→minigame, `Emission map/`→vfx, `Redactable/`→source, `DialoguePortrait/`→portrait, `04_TBD_Unknown/`→TBD.
