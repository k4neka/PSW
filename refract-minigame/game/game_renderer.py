"""
Game renderer module for handling all drawing and display logic.
"""

import pygame
import os
from game_constants import *
from map_system import MapRenderer


class GameRenderer:
    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.SysFont('arial', 24)
        self.status_font = pygame.font.SysFont('arial', 36)
        
        self.camera_x = 0
        self.camera_y = 0
        
        self.target_camera_x = 0
        self.target_camera_y = 0
        
        self.map_renderer = MapRenderer()
        
        # Load player sprite for character select
        self.player_sprite = None
        self._load_player_sprite()
    
    def update_camera(self, player_x, player_y):
        """Update camera to follow player with smooth scrolling."""
        # Calculate target camera position (center player on screen)
        self.target_camera_x = player_x - WIDTH // 2 + PLAYER_VISUAL_SIZE // 2
        self.target_camera_y = player_y - HEIGHT // 2 + PLAYER_VISUAL_SIZE // 2
        
        # Clamp camera to world bounds
        self.target_camera_x = max(0, min(self.target_camera_x, WORLD_WIDTH - WIDTH))
        self.target_camera_y = max(0, min(self.target_camera_y, WORLD_HEIGHT - HEIGHT))
        
        # Smooth camera movement
        self.camera_x += (self.target_camera_x - self.camera_x) * CAMERA_SMOOTHING
        self.camera_y += (self.target_camera_y - self.camera_y) * CAMERA_SMOOTHING
    
    def world_to_screen(self, world_x, world_y):
        """Convert world coordinates to screen coordinates."""
        return (world_x - self.camera_x, world_y - self.camera_y)
    
    def screen_to_world(self, screen_x, screen_y):
        """Convert screen coordinates to world coordinates."""
        return (screen_x + self.camera_x, screen_y + self.camera_y)
    
    def _draw_world_borders(self):
        """Draw world map (floor and walls)."""
        self.map_renderer.render(self.screen, self.camera_x, self.camera_y)
    
    def _draw_connection_status(self, connected, player_count):
        """Draw connection status and player count."""
        status_text = f"Connected: {connected} | Players: {player_count}"
        status_surface = self.status_font.render(status_text, True, WHITE)
        self.screen.blit(status_surface, (10, 10))
    
    def draw_disconnect_screen(self):
        """Draw a screen when disconnected."""
        self.screen.fill(BLACK)
        
        # Draw disconnected message
        disconnect_text = self.status_font.render("Disconnected from server", True, WHITE)
        text_rect = disconnect_text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        self.screen.blit(disconnect_text, text_rect)
        
        # Draw instructions
        instruction_text = self.font.render("Press ESC to quit", True, WHITE)
        instruction_rect = instruction_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 40))
        self.screen.blit(instruction_text, instruction_rect)
        
        pygame.display.flip()
    
    def _load_player_sprite(self):
        """Load the default player sprite for character selection (first frame only)."""
        try:
            # Load the front idle sprite animation data
            import json
            assets_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'entities', 'main_c')
            json_path = os.path.join(assets_path, 'f_idle.json')
            sprite_path = os.path.join(assets_path, 'f_idle.png')
            
            if os.path.exists(json_path) and os.path.exists(sprite_path):
                # Load the sprite sheet
                sprite_sheet = pygame.image.load(sprite_path).convert_alpha()
                
                # Load the animation data to get first frame
                with open(json_path, 'r') as f:
                    data = json.load(f)
                
                # Extract the first frame
                first_frame = data['frames'][0]['frame']
                
                # Create surface with first frame only
                self.player_sprite = pygame.Surface((first_frame['w'], first_frame['h']), pygame.SRCALPHA)
                self.player_sprite.blit(sprite_sheet, (0, 0), 
                                       (first_frame['x'], first_frame['y'], 
                                        first_frame['w'], first_frame['h']))
            else:
                print(f"Player sprite or animation data not found at: {assets_path}")
                # Create a fallback sprite
                self.player_sprite = pygame.Surface((100, 100), pygame.SRCALPHA)
                self.player_sprite.fill((0, 255, 0))
        except Exception as e:
            print(f"Error loading player sprite: {e}")
            # Create a fallback sprite
            self.player_sprite = pygame.Surface((100, 100), pygame.SRCALPHA)
            self.player_sprite.fill((0, 255, 0))
    
    def render_character_select_menu(self, selected_index):
        """
        Render the character selection menu.
        
        Args:
            selected_index: Currently selected character index (0, 1, or 2)
        """
        self.screen.fill(BLACK)
        
        # Title
        title_font = pygame.font.SysFont('arial', 64)
        title_text = title_font.render("Select Your Character", True, WHITE)
        title_rect = title_text.get_rect(center=(WIDTH // 2, 80))
        self.screen.blit(title_text, title_rect)
        
        # Character options
        character_names = [
            "Default Character",
            "Character Type 2 (Coming Soon)",
            "Character Type 3 (Coming Soon)"
        ]
        
        character_colors = [
            (0, 255, 0),    # Green for default
            (150, 150, 150),  # Gray for locked
            (150, 150, 150)   # Gray for locked
        ]
        
        # Calculate positions for three character boxes
        box_width = 200
        box_height = 250
        spacing = 50
        total_width = (box_width * 3) + (spacing * 2)
        start_x = (WIDTH - total_width) // 2
        box_y = 200
        
        for i in range(3):
            x = start_x + (box_width + spacing) * i
            
            # Determine box color based on selection and availability
            if i == selected_index:
                if i == 0:
                    border_color = (255, 255, 0)  # Yellow for selected available
                else:
                    border_color = (100, 100, 0)  # Dim yellow for selected locked
                border_width = 5
            else:
                border_color = (100, 100, 100)  # Gray for unselected
                border_width = 2
            
            # Draw character box
            box_rect = pygame.Rect(x, box_y, box_width, box_height)
            pygame.draw.rect(self.screen, BLACK, box_rect)
            pygame.draw.rect(self.screen, border_color, box_rect, border_width)
            
            # Draw character preview
            preview_size = 100
            preview_x = x + (box_width - preview_size) // 2
            preview_y = box_y + 30
            
            if i == 0 and self.player_sprite:
                # For default character, show actual player sprite
                sprite_rect = self.player_sprite.get_rect()
                scale_factor = min(preview_size / sprite_rect.width, preview_size / sprite_rect.height)
                scaled_width = int(sprite_rect.width * scale_factor)
                scaled_height = int(sprite_rect.height * scale_factor)
                scaled_sprite = pygame.transform.scale(self.player_sprite, (scaled_width, scaled_height))
                
                # Center the sprite in the preview area
                sprite_x = preview_x + (preview_size - scaled_width) // 2
                sprite_y = preview_y + (preview_size - scaled_height) // 2
                self.screen.blit(scaled_sprite, (sprite_x, sprite_y))
            else:
                # For locked characters, show colored square
                preview_rect = pygame.Rect(preview_x, preview_y, preview_size, preview_size)
                pygame.draw.rect(self.screen, character_colors[i], preview_rect)
            
            # Draw character name
            name_font = pygame.font.SysFont('arial', 18)
            name_lines = []
            
            # Word wrap the character names
            words = character_names[i].split()
            current_line = ""
            for word in words:
                test_line = current_line + word + " "
                if name_font.size(test_line)[0] <= box_width - 20:
                    current_line = test_line
                else:
                    if current_line:
                        name_lines.append(current_line.strip())
                    current_line = word + " "
            if current_line:
                name_lines.append(current_line.strip())
            
            # Draw each line of text
            name_y = preview_y + preview_size + 20
            for line in name_lines:
                name_text = name_font.render(line, True, WHITE if i == 0 else (150, 150, 150))
                name_rect = name_text.get_rect(center=(x + box_width // 2, name_y))
                self.screen.blit(name_text, name_rect)
                name_y += 25
        
        # Instructions
        instruction_font = pygame.font.SysFont('arial', 24)
        instruction_text = instruction_font.render("Use LEFT/RIGHT arrows to select, ENTER to confirm", True, WHITE)
        instruction_rect = instruction_text.get_rect(center=(WIDTH // 2, HEIGHT - 80))
        self.screen.blit(instruction_text, instruction_rect)
        
        # Lock notice for unavailable characters
        if selected_index != 0:
            lock_text = instruction_font.render("This character is not yet available", True, (255, 100, 100))
            lock_rect = lock_text.get_rect(center=(WIDTH // 2, HEIGHT - 40))
            self.screen.blit(lock_text, lock_rect)
