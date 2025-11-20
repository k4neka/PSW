"""
Refactored game client using component-based architecture.
"""
import pygame
from game_constants import *
from network_client import NetworkClient
from game_renderer import GameRenderer
from animation_system import AnimationManager
from core.game_state import GameState
from entities.player import Player
from entities.projectile import Projectile
from entities.collision_effect import CollisionEffect
from entities.enemy import Enemy
from systems.input_system import InputComponent
from systems.movement_system import MovementComponent
from systems.render_system import AnimationComponent
from systems.collision_system import CollisionComponent
from systems.health_system import HealthComponent
import random

pygame.init()


class RefactoredGameClient:
    """Game client using component-based architecture."""
    
    def __init__(self):
        """Initialize the game client."""
        flags = pygame.RESIZABLE
        if VSYNC:
            flags |= pygame.SCALED
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags, vsync=1 if VSYNC else 0)
        pygame.display.set_caption("Multiplayer Squares Game - Refactored")
        self.clock = pygame.time.Clock()
        
        self.display_surface = pygame.Surface((WIDTH, HEIGHT))
        self.window_width = WIDTH
        self.window_height = HEIGHT
        
        self.game_state = GameState()
        self.animation_manager = AnimationManager()
        self.network_client = NetworkClient()
        self.renderer = GameRenderer(self.display_surface)
        
        self.frame_count = 0
        self.running = True
        
        # Enemy management
        self.enemies = {}
        self.enemy_id_counter = 0
        self.enemy_respawn_timer = 0
        self.waiting_for_respawn = False
        self.initial_spawn_done = False
        
        # Kill count tracking
        self.kill_count = 0
        
        # Track projectiles that have been removed to prevent duplicate effects
        self.removed_projectiles = set()
        
        # Rate limiting for network updates
        self.last_position_update_time = 0
        self.position_update_interval = 50  # milliseconds (20 updates per second)
        
        self.network_client.set_callbacks(
            on_welcome=self._on_welcome,
            on_player_update=self._on_player_update,
            on_new_player=self._on_new_player,
            on_player_left=self._on_player_left,
            on_disconnect=self._on_disconnect,
            on_projectile_update=self._on_projectile_update,
            on_projectile_remove=self._on_projectile_remove,
            on_damage=self._on_damage,
            on_respawn=self._on_respawn,
            on_game_start=self._on_game_start,
            on_enemy_spawn=self._on_enemy_spawn,
            on_enemy_update=self._on_enemy_update,
            on_enemy_death=self._on_enemy_death,
            on_player_death=self._on_player_death,
            on_wave_complete=self._on_wave_complete,
            on_game_over=self._on_game_over,
            on_host_assigned=self._on_host_assigned
        )
    
    def _on_welcome(self, player_id, x, y, color, is_host=False):
        """Handle welcome message from server."""
        print(f"Welcome! You are {player_id} at ({x}, {y}) with color {color}")
        
        # Create local player object
        local_player = Player(
            player_id=player_id,
            x=x,
            y=y,
            color=color,
            animation_manager=self.animation_manager,
            is_local=True
        )
        
        # Add to game state
        self.game_state.add_object(local_player)
        self.game_state.player_id = player_id
        self.game_state.player_object = local_player
        self.game_state.connected = True
        self.game_state.spawn_x = x
        self.game_state.spawn_y = y
        
        # Set host status from server
        self.game_state.is_host = is_host
        if is_host:
            print("You are the HOST!")
        
        # Mark player as alive
        self.game_state.mark_player_alive(player_id)
        
        print(f"Created local player object with {len(local_player.components)} components")
    
    def _on_host_assigned(self):
        """Handle being assigned as the new host."""
        print("You have been assigned as the new HOST!")
        self.game_state.is_host = True
    
    def _on_player_update(self, other_players):
        """Handle player updates from server."""
        # Update existing player positions or create new players
        for player_id, player_data in other_players.items():
            if player_id in self.game_state.other_players:
                player_obj = self.game_state.other_players[player_id]
                player_obj.set_position(player_data['x'], player_data['y'])
            else:
                # Create new player that we didn't know about
                remote_player = Player(
                    player_id=player_id,
                    x=player_data['x'],
                    y=player_data['y'],
                    color=player_data['color'],
                    animation_manager=self.animation_manager,
                    is_local=False
                )
                self.game_state.add_object(remote_player)
                self.game_state.other_players[player_id] = remote_player
                self.game_state.mark_player_alive(player_id)
    
    def _on_new_player(self, player_id, x, y, color):
        """Handle new player joining."""
        print(f"New player joined: {player_id}")
        
        # Create remote player object
        remote_player = Player(
            player_id=player_id,
            x=x,
            y=y,
            color=color,
            animation_manager=self.animation_manager,
            is_local=False
        )
        
        # Add to game state
        self.game_state.add_object(remote_player)
        self.game_state.other_players[player_id] = remote_player
        self.game_state.mark_player_alive(player_id)
        
        print(f"Created remote player object for {player_id}")
    
    def _on_player_left(self, player_id):
        """Handle player leaving."""
        print(f"Player left: {player_id}")
        
        if player_id in self.game_state.other_players:
            player_obj = self.game_state.other_players[player_id]
            self.game_state.remove_object(player_obj)
            del self.game_state.other_players[player_id]
        
        # Clean up animations
        self.animation_manager.remove_player(player_id)
    
    def _on_disconnect(self):
        """Handle disconnection from server."""
        print("Disconnected from server!")
        self.game_state.connected = False
    
    def _on_projectile_update(self, projectile_data):
        """Handle projectile update from server."""
        projectile_id = projectile_data['id']
        
        if projectile_id in self.game_state.projectiles:
            # Update existing projectile
            proj_obj = self.game_state.projectiles[projectile_id]
            proj_obj.x = projectile_data['x']
            proj_obj.y = projectile_data['y']
        else:
            # Create new projectile (unless we already removed it locally)
            if projectile_id not in self.removed_projectiles:
                projectile = Projectile(
                    projectile_id=projectile_id,
                    x=projectile_data['x'],
                    y=projectile_data['y'],
                    direction_x=projectile_data['direction_x'],
                    direction_y=projectile_data['direction_y'],
                    owner_id=projectile_data['owner_id']
                )
                
                self.game_state.add_object(projectile)
                self.game_state.projectiles[projectile_id] = projectile
    
    def _on_projectile_remove(self, projectile_id):
        """Handle projectile removal from server (may already be removed locally)."""
        # Check if we already removed this projectile locally
        if projectile_id in self.removed_projectiles:
            return
        
        # Use pop() to safely remove - returns None if doesn't exist
        proj_obj = self.game_state.projectiles.pop(projectile_id, None)
        if proj_obj:
            # Only create effect if projectile wasn't already marked inactive locally
            if proj_obj.active:
                effect = CollisionEffect(proj_obj.x, proj_obj.y, 32)
                self.game_state.add_object(effect)
            self.game_state.remove_object(proj_obj)
        
        # Track that this projectile has been removed
        self.removed_projectiles.add(projectile_id)
    
    def _on_damage(self, player_id, current_hp, max_hp):
        """Handle damage event from server."""
        # Find the player and update their health
        player = None
        if self.game_state.player_object and self.game_state.player_object.player_id == player_id:
            player = self.game_state.player_object
        elif player_id in self.game_state.other_players:
            player = self.game_state.other_players[player_id]
        
        if player:
            health_comp = player.get_component(HealthComponent)
            if health_comp:
                health_comp.current_hp = current_hp
                health_comp.max_hp = max_hp
                print(f"Player {player_id} health updated: {current_hp}/{max_hp}")
    
    def _on_respawn(self, player_id, x, y):
        """Handle player respawn from server."""
        # Find the player and respawn them
        player = None
        if self.game_state.player_object and self.game_state.player_object.player_id == player_id:
            player = self.game_state.player_object
        elif player_id in self.game_state.other_players:
            player = self.game_state.other_players[player_id]
        
        if player:
            player.respawn(x, y)
            self.game_state.mark_player_alive(player_id)
            if player_id == self.game_state.player_id:
                from core.game_state import GamePhase
                self.game_state.set_phase(GamePhase.PLAYING)
            print(f"Player {player_id} respawned at ({x}, {y})")
    
    def _on_game_start(self):
        """Handle game start message from server."""
        from core.game_state import GamePhase
        self.game_state.set_phase(GamePhase.PLAYING)
        # Clear client-side enemies since server will manage them
        for enemy_id in list(self.enemies.keys()):
            enemy = self.enemies[enemy_id]
            self.game_state.remove_object(enemy)
            self.animation_manager.remove_enemy(enemy_id)
        self.enemies.clear()
        print("Game started!")
    
    def _on_enemy_spawn(self, enemy_id, x, y, target_player_id):
        """Handle enemy spawn from server."""
        # Find target player
        target_player = None
        if self.game_state.player_object and self.game_state.player_object.player_id == target_player_id:
            target_player = self.game_state.player_object
        elif target_player_id in self.game_state.other_players:
            target_player = self.game_state.other_players[target_player_id]
        
        if not target_player:
            # Default to any player if target not found
            target_player = self.game_state.player_object
        
        # Create enemy
        enemy = Enemy(enemy_id, x, y, target_player, self.animation_manager)
        self.enemies[enemy_id] = enemy
        self.game_state.add_object(enemy)
        print(f"Enemy {enemy_id} spawned at ({x}, {y})")
    
    def _on_enemy_update(self, enemy_id, x, y, current_hp, max_hp):
        """Handle enemy update from server."""
        if enemy_id in self.enemies:
            enemy = self.enemies[enemy_id]
            
            # Set target position for smooth interpolation
            if hasattr(enemy, 'set_network_position'):
                enemy.set_network_position(x, y)
            else:
                enemy.x = x
                enemy.y = y
            
            health_comp = enemy.get_component(HealthComponent)
            if health_comp:
                health_comp.current_hp = current_hp
                health_comp.max_hp = max_hp
    
    def _on_enemy_death(self, enemy_id, killer_id):
        """Handle enemy death from server."""
        if enemy_id in self.enemies:
            enemy = self.enemies[enemy_id]
            enemy.active = False
            # Track kill if this player killed the enemy
            if killer_id == self.game_state.player_id:
                self.kill_count += 1
                print(f"You killed enemy {enemy_id}! Total kills: {self.kill_count}")
            # Remove from state
            self.game_state.remove_object(enemy)
            self.animation_manager.remove_enemy(enemy_id)
            del self.enemies[enemy_id]
    
    def _on_player_death(self, player_id):
        """Handle player death from server."""
        from core.game_state import GamePhase
        self.game_state.mark_player_dead(player_id)
        
        if player_id == self.game_state.player_id:
            self.game_state.set_phase(GamePhase.DEAD)
            print("You died!")
    
    def _on_wave_complete(self, wave_number):
        """Handle wave complete from server."""
        self.game_state.current_wave = wave_number
        print(f"Wave {wave_number} complete!")
    
    def _on_game_over(self, reason):
        """Handle game over from server."""
        from core.game_state import GamePhase
        self.game_state.set_phase(GamePhase.GAME_OVER)
        self.game_state.game_over_reason = reason
        print(f"Game over! Reason: {reason}")
    
    def connect_to_server(self):
        """Connect to the game server."""
        return self.network_client.connect()
    
    def spawn_enemies(self):
        """Spawn enemies off-screen near the player."""
        if not self.game_state.player_object:
            return
        
        from game_constants import ENEMY_SPAWN_COUNT, WIDTH, HEIGHT, WORLD_WIDTH, WORLD_HEIGHT
        
        player = self.game_state.player_object
        camera_x = self.renderer.camera_x
        camera_y = self.renderer.camera_y
        
        # Define spawn zones (off-screen but within world bounds)
        margin = 100
        spawn_zones = [
            # Top (above camera view)
            (max(margin, camera_x - 200), max(margin, camera_y - 200), WIDTH + 400, 150),
            # Bottom (below camera view)
            (max(margin, camera_x - 200), min(WORLD_HEIGHT - margin - 150, camera_y + HEIGHT), WIDTH + 400, 150),
            # Left (left of camera view)
            (max(margin, camera_x - 200), max(margin, camera_y - 200), 150, HEIGHT + 400),
            # Right (right of camera view)
            (min(WORLD_WIDTH - margin - 150, camera_x + WIDTH), max(margin, camera_y - 200), 150, HEIGHT + 400),
        ]
        
        for i in range(ENEMY_SPAWN_COUNT):
            zone = random.choice(spawn_zones)
            spawn_x = random.randint(int(zone[0]), int(min(zone[0] + zone[2], WORLD_WIDTH - margin)))
            spawn_y = random.randint(int(zone[1]), int(min(zone[1] + zone[3], WORLD_HEIGHT - margin)))
            
            # Ensure within world bounds
            spawn_x = max(margin, min(spawn_x, WORLD_WIDTH - margin))
            spawn_y = max(margin, min(spawn_y, WORLD_HEIGHT - margin))
            
            # Find nearest player as target
            target_player = self.get_nearest_player(spawn_x, spawn_y)
            
            enemy_id = f"enemy_{self.enemy_id_counter}"
            self.enemy_id_counter += 1
            
            enemy = Enemy(enemy_id, spawn_x, spawn_y, target_player, self.animation_manager)
            self.enemies[enemy_id] = enemy
            self.game_state.add_object(enemy)
        
        print(f"Spawned {ENEMY_SPAWN_COUNT} enemies")
    
    def get_nearest_player(self, x, y):
        """Find the nearest player to the given position."""
        players = [self.game_state.player_object] + list(self.game_state.other_players.values())
        players = [p for p in players if p and p.active]
        
        if not players:
            return None
        
        nearest = None
        min_dist = float('inf')
        
        for player in players:
            dx = player.x - x
            dy = player.y - y
            dist = dx * dx + dy * dy
            if dist < min_dist:
                min_dist = dist
                nearest = player
        
        return nearest
    
    def update_enemies(self, dt):
        """Update enemy animations and interpolation (server manages spawning/health)."""
        # Update existing enemies (for animation and smooth movement)
        for enemy in list(self.enemies.values()):
            if enemy.active:
                # Update enemy (handles interpolation and animation for network-controlled enemies)
                enemy.update(dt)
    
    def check_enemy_damage(self):
        """Check if enemies should damage players."""
        import pygame
        current_time = pygame.time.get_ticks()
        
        for enemy in self.enemies.values():
            if not enemy.active or not enemy.ai:
                continue
            
            player_to_damage = enemy.ai.check_damage_player(enemy, current_time)
            if player_to_damage:
                health_comp = player_to_damage.get_component(HealthComponent)
                if health_comp and health_comp.is_alive():
                    from game_constants import ENEMY_DAMAGE
                    still_alive = health_comp.take_damage(ENEMY_DAMAGE)
                    print(f"Enemy damaged player! HP: {health_comp.current_hp}/{health_comp.max_hp}")
                    
                    # Check if player died from this damage
                    if not still_alive:
                        print(f"Player {player_to_damage.player_id} killed by enemy!")
                        # For now, just respawn locally - full multiplayer death needs server support
                        # In a complete implementation, this would notify the server
                        spawn_x = self.game_state.spawn_x if hasattr(self.game_state, 'spawn_x') else WIDTH // 2
                        spawn_y = self.game_state.spawn_y if hasattr(self.game_state, 'spawn_y') else HEIGHT // 2
                        player_to_damage.respawn(spawn_x, spawn_y)
    
    def handle_input(self):
        """Handle player input based on game phase."""
        from core.game_state import GamePhase
        
        # Handle character select phase
        if self.game_state.game_phase == GamePhase.CHARACTER_SELECT:
            keys = pygame.key.get_pressed()
            # Navigation happens in the main game loop event handler
            return
        
        # Handle menu phase
        if self.game_state.game_phase == GamePhase.MENU:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_SPACE] and self.game_state.is_host:
                # Host starts the game
                self.network_client.send_start_game()
            return
        
        # Handle dead/game over phases - no input allowed
        if self.game_state.game_phase in (GamePhase.DEAD, GamePhase.GAME_OVER):
            return
        
        # Handle playing phase
        if not self.game_state.player_object:
            return
        
        player = self.game_state.player_object
        input_comp = player.get_component(InputComponent)
        if not input_comp:
            return
        
        mouse_pos = pygame.mouse.get_pos()
        scale_x = WIDTH / self.window_width
        scale_y = HEIGHT / self.window_height
        scaled_mouse_x = int(mouse_pos[0] * scale_x)
        scaled_mouse_y = int(mouse_pos[1] * scale_y)
        
        should_shoot, target_x, target_y, direction_x, direction_y = input_comp.check_shooting(
            self.renderer, scaled_mouse_x, scaled_mouse_y
        )
        
        if should_shoot:
            center_x, center_y = player.get_center()
            self.network_client.send_shoot(center_x, center_y, direction_x, direction_y)
    
    def send_position_update(self):
        """Send position update if player moved (with rate limiting)."""
        if not self.game_state.player_object:
            return
        
        # Rate limit position updates to prevent flooding the network
        import pygame
        current_time = pygame.time.get_ticks()
        if current_time - self.last_position_update_time < self.position_update_interval:
            return
        
        player = self.game_state.player_object
        movement = player.get_component(MovementComponent)
        
        if movement and (movement.velocity_x != 0 or movement.velocity_y != 0):
            self.network_client.send_move(int(player.x), int(player.y))
            self.last_position_update_time = current_time
    
    def check_collisions(self):
        if not self.game_state.projectiles:
            return
        
        hits_to_process = []
        wall_hits = []
        
        projectiles = list(self.game_state.projectiles.values())
        players = [self.game_state.player_object] + list(self.game_state.other_players.values())
        players = [p for p in players if p and p.active]
        enemies = [e for e in self.enemies.values() if e and e.active]
        
        for proj in projectiles:
            # Skip projectiles that are already marked for removal
            if not proj.active:
                continue
            
            proj_collision = proj.get_component(CollisionComponent)
            if not proj_collision:
                continue
            
            # Check wall collision first
            proj_rect = proj_collision.get_rect()
            if proj_rect and self.renderer.map_renderer.check_wall_collision(proj_rect):
                # Mark inactive immediately to prevent duplicate collision detection
                proj.active = False
                wall_hits.append((proj.projectile_id, proj.x, proj.y))
                continue
            
            # Check player collisions
            for player in players:
                if proj.owner_id == player.player_id:
                    continue
                
                player_collision = player.get_component(CollisionComponent)
                if player_collision and proj_collision.check_collision(player):
                    # Mark inactive immediately to prevent duplicate collision detection
                    proj.active = False
                    hits_to_process.append((player.player_id, proj.owner_id, proj.projectile_id, proj.x, proj.y, 'player'))
                    break
            
            # Check enemy collisions
            if proj.active:  # Only check if projectile hasn't hit anything yet
                for enemy in enemies:
                    enemy_collision = enemy.get_component(CollisionComponent)
                    if enemy_collision and proj_collision.check_collision(enemy):
                        # Mark inactive immediately and notify server
                        proj.active = False
                        hits_to_process.append((enemy.enemy_id, proj.owner_id, proj.projectile_id, proj.x, proj.y, 'enemy'))
                        break
        
        # Process wall hits: create effect and remove projectile
        for projectile_id, x, y in wall_hits:
            if projectile_id not in self.removed_projectiles:
                # Use pop() to safely remove - returns None if doesn't exist (race condition)
                proj_obj = self.game_state.projectiles.pop(projectile_id, None)
                if proj_obj:
                    # Create collision effect only once
                    effect = CollisionEffect(x, y, 32)
                    self.game_state.add_object(effect)
                    # Remove projectile from game state
                    self.game_state.remove_object(proj_obj)
                # Mark as removed to prevent duplicate effects
                self.removed_projectiles.add(projectile_id)
        
        # Process player/enemy hits: create effect, notify server, and remove projectile
        for victim_id, shooter_id, projectile_id, x, y, target_type in hits_to_process:
            # Notify server about the hit (works for both players and enemies)
            self.network_client.send_hit(victim_id, shooter_id, projectile_id)
            
            if projectile_id not in self.removed_projectiles:
                # Use pop() to safely remove - returns None if doesn't exist (race condition)
                proj_obj = self.game_state.projectiles.pop(projectile_id, None)
                if proj_obj:
                    # Create collision effect only once
                    effect = CollisionEffect(x, y, 32)
                    self.game_state.add_object(effect)
                    # Remove projectile from game state
                    self.game_state.remove_object(proj_obj)
                # Mark as removed to prevent duplicate effects
                self.removed_projectiles.add(projectile_id)
    
    def _resolve_player_collisions(self):
        """Resolve player-vs-player and player-vs-enemy collisions."""
        local_player = self.game_state.player_object
        if not local_player:
            return
            
        local_col = local_player.get_component(CollisionComponent)
        if not local_col:
            return
        
        lp_rect = local_col.get_rect()
        
        # Player vs other players
        for other in self.game_state.other_players.values():
            if not other or not other.active:
                continue
            
            other_col = other.get_component(CollisionComponent)
            if not other_col:
                continue
            
            other_rect = other_col.get_rect()
            if lp_rect.colliderect(other_rect):
                overlap = lp_rect.clip(other_rect)
                if overlap.width < overlap.height:
                    offset = overlap.width if lp_rect.centerx < other_rect.centerx else -overlap.width
                    local_player.x -= offset
                else:
                    offset = overlap.height if lp_rect.centery < other_rect.centery else -overlap.height
                    local_player.y -= offset
                lp_rect = local_col.get_rect()
        
        # Player vs enemies
        for enemy in self.enemies.values():
            if not enemy or not enemy.active:
                continue
            
            enemy_col = enemy.get_component(CollisionComponent)
            if not enemy_col:
                continue
            
            enemy_rect = enemy_col.get_rect()
            if lp_rect.colliderect(enemy_rect):
                overlap = lp_rect.clip(enemy_rect)
                if overlap.width < overlap.height:
                    offset = overlap.width if lp_rect.centerx < enemy_rect.centerx else -overlap.width
                    local_player.x -= offset
                else:
                    offset = overlap.height if lp_rect.centery < enemy_rect.centery else -overlap.height
                    local_player.y -= offset
                lp_rect = local_col.get_rect()
    
    def update(self, dt):
        """Update game state."""
        from core.game_state import GamePhase
        
        # Only update game objects when playing
        if self.game_state.game_phase == GamePhase.PLAYING:
            self.game_state.update(dt)
            
            if self.game_state.player_object:
                anim_comp = self.game_state.player_object.get_component(AnimationComponent)
                if anim_comp and anim_comp.is_local_player:
                    keys = pygame.key.get_pressed()
                    anim_comp.update_from_keys(dt, keys)
                
                self._resolve_player_collisions()
            
            # Update enemies (only client-side rendering now, server manages state)
            self.update_enemies(dt)
            # Don't check enemy damage on client side anymore - server will handle this
            
            # Periodically clean up old removed projectile IDs to prevent memory leak
            # Keep only the last 100 removed projectiles
            if len(self.removed_projectiles) > 100:
                # Convert to list, keep last 50, convert back to set
                recent_removed = list(self.removed_projectiles)[-50:]
                self.removed_projectiles = set(recent_removed)
    
    def render(self):
        """Render the game."""
        from core.game_state import GamePhase
        
        # Render character select before connecting to server
        if self.game_state.game_phase == GamePhase.CHARACTER_SELECT:
            self.renderer.render_character_select_menu(self.game_state.selected_character_type)
            scaled = pygame.transform.scale(self.display_surface, (self.window_width, self.window_height))
            self.screen.blit(scaled, (0, 0))
            pygame.display.flip()
            return
        
        if not self.game_state.connected:
            self.renderer.draw_disconnect_screen()
            scaled = pygame.transform.scale(self.display_surface, (self.window_width, self.window_height))
            self.screen.blit(scaled, (0, 0))
            pygame.display.flip()
            return
        
        # Render based on game phase
        if self.game_state.game_phase == GamePhase.MENU:
            self._render_menu()
        elif self.game_state.game_phase == GamePhase.DEAD:
            self._render_game()  # Still show game world
            self._render_death_screen()  # Overlay death screen
        elif self.game_state.game_phase == GamePhase.GAME_OVER:
            self._render_game()  # Still show game world
            self._render_game_over_screen()  # Overlay game over screen
        else:  # PLAYING
            self._render_game()
        
        scaled = pygame.transform.scale(self.display_surface, (self.window_width, self.window_height))
        self.screen.blit(scaled, (0, 0))
        pygame.display.flip()
    
    def _render_menu(self):
        """Render the start menu."""
        self.display_surface.fill(BLACK)
        
        # Title
        title_font = pygame.font.SysFont('arial', 72)
        title_text = title_font.render("Multiplayer Survival", True, WHITE)
        title_rect = title_text.get_rect(center=(WIDTH // 2, 100))
        self.display_surface.blit(title_text, title_rect)
        
        # Player count
        player_count = self.network_client.get_player_count()
        count_text = self.renderer.font.render(f"Players Connected: {player_count}", True, WHITE)
        count_rect = count_text.get_rect(center=(WIDTH // 2, 250))
        self.display_surface.blit(count_text, count_rect)
        
        # Host instructions
        if self.game_state.is_host:
            host_text = self.renderer.font.render("You are the HOST", True, (255, 255, 0))
            host_rect = host_text.get_rect(center=(WIDTH // 2, 320))
            self.display_surface.blit(host_text, host_rect)
            
            start_text = self.renderer.font.render("Press SPACE to start the game", True, (0, 255, 0))
            start_rect = start_text.get_rect(center=(WIDTH // 2, 380))
            self.display_surface.blit(start_text, start_rect)
        else:
            wait_text = self.renderer.font.render("Waiting for host to start...", True, (200, 200, 200))
            wait_rect = wait_text.get_rect(center=(WIDTH // 2, 350))
            self.display_surface.blit(wait_text, wait_rect)
    
    def _render_death_screen(self):
        """Render the death overlay."""
        # Semi-transparent overlay
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.set_alpha(180)
        overlay.fill(BLACK)
        self.display_surface.blit(overlay, (0, 0))
        
        # Death message
        death_font = pygame.font.Font(None, 72)
        death_text = death_font.render("YOU DIED", True, (255, 0, 0))
        death_rect = death_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 50))
        self.display_surface.blit(death_text, death_rect)
        
        # Wait message
        wait_text = self.renderer.font.render("Waiting for wave to complete...", True, WHITE)
        wait_rect = wait_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 30))
        self.display_surface.blit(wait_text, wait_rect)
        
        # Show alive players
        alive_count = len(self.game_state.alive_players)
        total_count = self.network_client.get_player_count()
        alive_text = self.renderer.font.render(f"Alive: {alive_count}/{total_count}", True, (0, 255, 0))
        alive_rect = alive_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 70))
        self.display_surface.blit(alive_text, alive_rect)
    
    def _render_game_over_screen(self):
        """Render the game over overlay."""
        # Semi-transparent overlay
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.set_alpha(200)
        overlay.fill(BLACK)
        self.display_surface.blit(overlay, (0, 0))
        
        # Game over message
        gameover_font = pygame.font.Font(None, 72)
        gameover_text = gameover_font.render("GAME OVER", True, (255, 0, 0))
        gameover_rect = gameover_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 50))
        self.display_surface.blit(gameover_text, gameover_rect)
        
        # Reason
        reason = self.game_state.game_over_reason
        reason_str = "All players defeated!" if reason == "all_dead" else "Victory!"
        reason_text = self.renderer.font.render(reason_str, True, WHITE)
        reason_rect = reason_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 30))
        self.display_surface.blit(reason_text, reason_rect)
        
        # Final score
        score_text = self.renderer.font.render(f"Final Kills: {self.kill_count}", True, (255, 255, 0))
        score_rect = score_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 80))
        self.display_surface.blit(score_text, score_rect)
    
    def _render_game(self):
        """Render the main game view."""
        self.display_surface.fill(BLACK)
        
        camera_x = camera_y = 0
        if self.game_state.player_object:
            self.renderer.update_camera(
                self.game_state.player_object.x,
                self.game_state.player_object.y
            )
            camera_x = self.renderer.camera_x
            camera_y = self.renderer.camera_y
        
        self.renderer._draw_world_borders()
        
        from entities.projectile import ProjectileRendererComponent
        from entities.collision_effect import CollisionEffectRenderer
        from systems.render_system import EnemyAnimationComponent
        for obj in self.game_state.game_objects:
            if not obj.active:
                continue
            
            anim_comp = obj.get_component(AnimationComponent)
            if anim_comp:
                anim_comp.render(self.display_surface, camera_x, camera_y)
                continue
            
            proj_renderer = obj.get_component(ProjectileRendererComponent)
            if proj_renderer:
                proj_renderer.render(self.display_surface, camera_x, camera_y)
                continue
            
            effect_renderer = obj.get_component(CollisionEffectRenderer)
            if effect_renderer:
                effect_renderer.render(self.display_surface, camera_x, camera_y)
        
        if DRAW_HITBOXES:
            for obj in self.game_state.game_objects:
                if obj.active:
                    collision_comp = obj.get_component(CollisionComponent)
                    if collision_comp:
                        collision_comp.debug_render(self.display_surface, camera_x, camera_y)
        
        # Render health bars for all players
        for obj in self.game_state.game_objects:
            if obj.active and obj.has_tag('player'):
                health_comp = obj.get_component(HealthComponent)
                if health_comp:
                    health_comp.render_health_bar(self.display_surface, camera_x, camera_y)
        
        # Render health bars for all enemies
        for obj in self.game_state.game_objects:
            if obj.active and obj.has_tag('enemy'):
                health_comp = obj.get_component(HealthComponent)
                if health_comp:
                    health_comp.render_health_bar(self.display_surface, camera_x, camera_y)
        
        player_count = len(self.game_state.get_objects_with_tag('player'))
        self.renderer._draw_connection_status(self.network_client.connected, player_count)
        
        # Draw kill count
        kill_text = self.renderer.font.render(f"Kills: {self.kill_count}", True, WHITE)
        self.display_surface.blit(kill_text, (WIDTH - 120, 10))
        
        # Draw wave number if playing
        from core.game_state import GamePhase
        if self.game_state.game_phase == GamePhase.PLAYING:
            wave_text = self.renderer.font.render(f"Wave: {self.game_state.current_wave}", True, WHITE)
            self.display_surface.blit(wave_text, (WIDTH - 120, 35))    
    def run(self):
        """Main game loop."""
        self.running = True
        server_connected = False
        
        # Wait a bit for player to spawn before spawning enemies
        enemy_spawn_delay = 60  # frames
        frame_counter = 0
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif event.key == pygame.K_F11:
                        pygame.display.toggle_fullscreen()
                    
                    # Handle character selection input
                    from core.game_state import GamePhase
                    if self.game_state.game_phase == GamePhase.CHARACTER_SELECT:
                        if event.key == pygame.K_LEFT:
                            self.game_state.selected_character_type = max(0, self.game_state.selected_character_type - 1)
                        elif event.key == pygame.K_RIGHT:
                            self.game_state.selected_character_type = min(2, self.game_state.selected_character_type + 1)
                        elif event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                            # Only allow confirming default character (index 0)
                            if self.game_state.selected_character_type == 0:
                                print(f"Selected character type: {self.game_state.selected_character_type}")
                                self.game_state.set_phase(GamePhase.MENU)
                            else:
                                print("This character is locked!")
                
                elif event.type == pygame.VIDEORESIZE:
                    self.window_width = event.w
                    self.window_height = event.h
                    self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)
            
            # Connect to server after character selection
            from core.game_state import GamePhase
            if not server_connected and self.game_state.game_phase == GamePhase.MENU:
                if self.connect_to_server():
                    server_connected = True
                else:
                    print("Failed to connect to server!")
                    self.running = False
                    break
            
            # Always render, regardless of connection state
            dt = self.clock.get_time()
            
            if self.game_state.connected:
                # Spawn enemies after delay (only once)
                if frame_counter == enemy_spawn_delay and not self.initial_spawn_done:
                    self.spawn_enemies()
                    self.initial_spawn_done = True
                frame_counter += 1
                
                self.handle_input()
                self.update(dt)
                self.send_position_update()
                self.check_collisions()
            
            self.render()
            
            self.frame_count += 1
            self.clock.tick(FPS)
        
        self.network_client.disconnect()
        pygame.quit()


if __name__ == "__main__":
    client = RefactoredGameClient()
    client.run()
