"""
Game state management.
"""

class GamePhase:
    """Game phase enumeration."""
    CHARACTER_SELECT = "character_select"
    MENU = "menu"
    PLAYING = "playing"
    DEAD = "dead"
    GAME_OVER = "game_over"


class GameState:
    """Manages the current game state and all game objects."""
    
    def __init__(self):
        """Initialize the game state."""
        self.game_objects = []
        self.player_id = None
        self.player_object = None
        self.other_players = {}  # player_id -> GameObject mapping
        self.projectiles = {}  # projectile_id -> GameObject mapping
        self.connected = False
        
        # Game flow state
        self.game_phase = GamePhase.CHARACTER_SELECT
        self.is_host = False  # True if this player is the host
        self.current_wave = 0
        self.alive_players = set()  # Set of alive player IDs
        self.dead_players = set()  # Set of dead player IDs
        self.game_over_reason = None  # "all_dead" or "victory"
        
        # Character selection
        self.selected_character_type = 0  # 0 = default, 1 = type 2, 2 = type 3
        
        # Spawn positions
        self.spawn_x = 0
        self.spawn_y = 0
    
    def add_object(self, game_object):
        """
        Add a game object to the state.
        
        Args:
            game_object: GameObject instance to add
        """
        self.game_objects.append(game_object)
        return game_object
    
    def remove_object(self, game_object):
        """
        Remove a game object from the state.
        
        Args:
            game_object: GameObject instance to remove
        """
        if game_object in self.game_objects:
            game_object.destroy()
            self.game_objects.remove(game_object)
    
    def get_objects_with_tag(self, tag):
        """
        Get all objects with a specific tag.
        
        Args:
            tag: Tag to search for
            
        Returns:
            List of GameObjects with the tag
        """
        return [obj for obj in self.game_objects if obj.has_tag(tag) and obj.active]
    
    def get_objects_with_component(self, component_type):
        """
        Get all objects that have a specific component.
        
        Args:
            component_type: Type of component to search for
            
        Returns:
            List of GameObjects with the component
        """
        return [obj for obj in self.game_objects 
                if obj.has_component(component_type) and obj.active]
    
    def update(self, dt):
        """
        Update all game objects.
        
        Args:
            dt: Delta time in milliseconds
        """
        # Update all active objects
        for obj in list(self.game_objects):
            if obj.active:
                obj.update(dt)
        
        # Clean up destroyed objects
        self.game_objects = [obj for obj in self.game_objects if obj.active]
    
    def clear(self):
        """Clear all game objects."""
        for obj in list(self.game_objects):
            obj.destroy()
        self.game_objects.clear()
        self.other_players.clear()
        self.projectiles.clear()
    
    def set_phase(self, phase):
        """Set the current game phase."""
        self.game_phase = phase
        print(f"Game phase changed to: {phase}")
    
    def is_player_alive(self, player_id):
        """Check if a player is alive."""
        return player_id in self.alive_players
    
    def mark_player_dead(self, player_id):
        """Mark a player as dead."""
        if player_id in self.alive_players:
            self.alive_players.remove(player_id)
        self.dead_players.add(player_id)
    
    def mark_player_alive(self, player_id):
        """Mark a player as alive (respawn)."""
        if player_id in self.dead_players:
            self.dead_players.remove(player_id)
        self.alive_players.add(player_id)
