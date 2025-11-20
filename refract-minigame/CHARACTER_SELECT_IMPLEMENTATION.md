# Character Selection Menu Implementation

## Overview
Added a character selection menu that appears before connecting to the game server. Players can choose between three character types (one default and two placeholder options for future implementation).

## Changes Made

### 1. Game State (`game/core/game_state.py`)
- Added `CHARACTER_SELECT` phase to `GamePhase` enum
- Changed initial game phase from `MENU` to `CHARACTER_SELECT`
- Added `selected_character_type` field to `GameState` (0 = default, 1 = type 2, 2 = type 3)

### 2. Game Renderer (`game/game_renderer.py`)
- Added `render_character_select_menu(selected_index)` method
- Displays three character boxes with:
  - Visual preview (colored squares)
  - Character names
  - Selection highlighting (yellow border for selected)
  - Lock indicators for unavailable characters
  - Navigation instructions

### 3. Main Game Client (`game/main.py`)
- Modified `run()` method to delay server connection until after character selection
- Added character selection input handling in event loop:
  - LEFT/RIGHT arrow keys to navigate between characters
  - ENTER to confirm selection (only default character is unlocked)
- Updated `render()` method to handle `CHARACTER_SELECT` phase
- Updated `handle_input()` method to handle character select phase
- Modified game loop to render character select screen before connecting

## How It Works

1. **Game Start**: Game begins in `CHARACTER_SELECT` phase
2. **Navigation**: Player uses LEFT/RIGHT arrows to browse characters
3. **Selection**: Player presses ENTER to confirm (only default character works)
4. **Transition**: After selection, game transitions to `MENU` phase
5. **Connection**: Server connection is established during transition to `MENU`
6. **Gameplay**: Normal game flow continues from `MENU` → `PLAYING`

## Character Types

- **Character 0 (Default)**: Available and functional
- **Character 1**: Placeholder - displays "Character Type 2 (Coming Soon)"
- **Character 2**: Placeholder - displays "Character Type 3 (Coming Soon)"

## Future Implementation

To add new character types:
1. Implement character-specific behavior in `entities/player.py`
2. Update the selection validation in `main.py` event handler
3. Add character-specific sprites/animations
4. Update `selected_character_type` usage to apply different character properties

## Testing

Run the game normally:
```bash
./run_refactored_game.sh
```

You should see the character selection menu first, then the normal multiplayer menu after selecting the default character.
