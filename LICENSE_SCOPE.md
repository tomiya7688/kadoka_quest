# Provisional license scope

This file defines the current license boundary while Kadoka Quest is being
reorganized. It is intentionally conservative because the player game,
Developer Tools, runtime, shared Python modules, and game content are not yet
fully separated.

## 1. MIT-licensed Developer Tools

The following paths are licensed under the MIT License in
`LICENSES/MIT.txt`:

- `tools/**`
- `developer_launcher.py`
- `block_editor.py`
- `data_creator.py`
- `map_editor.py`
- `monster_editor.py`
- `run_developer.bat`
- `build_developer.bat`
- `src/kadoka_quest/developer/**`
- `src/kadoka_quest/apps/developer_launcher.py`
- `src/kadoka_quest/apps/block_editor.py`
- `src/kadoka_quest/apps/data_creator.py`
- `src/kadoka_quest/apps/map_editor.py`
- `src/kadoka_quest/apps/monster_editor.py`
- `src/kadoka_quest/data/developer_monster_creator.py`
- `src/kadoka_quest/data/species_creator.py`
- `src/kadoka_quest/ui/pixel_editor.py`
- `src/kadoka_quest/ui/pixel_operations.py`

Files added later are not automatically MIT-licensed merely because they are
Python files or because they are useful during development. Add them to this
list, or place a more specific license notice in their directory, when their
role is clear.

## 2. Kadoka Quest Game material

Unless a more specific license notice applies, all paths not listed in the MIT
section above are provisionally treated as Kadoka Quest Game material and are
governed by `LICENSES/KADOKA-GAME.txt` when dealing with Kadoka Quest itself.

This currently includes the game runtime, player-facing applications, game
data, maps, character/game assets, save/runtime support, documentation, and
shared modules whose final ownership boundary has not yet been decided.

## 3. Created Games

The repository-source classification above does not prevent use of Kadoka Quest
material in another game.

`LICENSES/KADOKA-GAME-CREATION.txt` grants additional rights to use Kadoka
Quest first-party material as part of a qualifying Created Game.

A Created Game may remain very close to Kadoka Quest. A meaningful change to
only the characters, only the maps, only the story/content, or another
meaningful part of the game may qualify while the remaining systems and content
stay the same or very similar.

A mere rename, rebrand, packaging change, launcher change, or other superficial
relabeling of an otherwise unchanged Kadoka Quest copy does not qualify.

Created Games may be distributed and sold commercially without royalty under
the terms of the Game Creation License.

## 4. Modified Developer Tools do not expand game-content rights

The Developer Tools may be modified under the MIT License.

However, a modified tool does not gain authority to convert additional Kadoka
Quest material into unrestricted content merely by copying, exporting,
generating, or embedding it.

Rights in Kadoka Quest material remain governed by
`LICENSES/KADOKA-GAME.txt`,
`LICENSES/KADOKA-GAME-CREATION.txt`, this scope file, and any more specific
notice.

## 5. Third-party material

A third-party license notice always remains applicable to the material it
covers. This scope file cannot grant rights that the Kadoka Quest project does
not own.

## 6. Planned replacement after physical separation

After the repository is physically separated, replace this provisional
path-by-path list with component-local licenses, for example:

- Developer Tools / editor component: MIT License
- Reusable runtime/template used for game creation: MIT or another explicitly
  reusable license as appropriate
- Kadoka Quest original game/content component: Kadoka Quest Game License
- Created-game permissions: Kadoka Quest Game Creation License

At that point the top-level LICENSE should become a short index to those
component licenses rather than a path-by-path transition list.
