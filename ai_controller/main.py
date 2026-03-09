"""
Main Entry Point - Ignite: Spell Master

Initializes the application with dual-window display (Gameplay + Debug Console).
Manages camera input, window management, and main game loop orchestration.
"""

import cv2
import sys
from pathlib import Path

# Import all core modules
from config import (
    WINDOW_GAMEPLAY,
    WINDOW_DEBUG,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    TARGET_FPS,
    SHOW_FPS,
    COLOR_BLACK,
)

from ui_system import UIRenderer
from spell_logic import SpellManager, SpellState, SpellEvent
from ai_module import GestureAI


class DisplayManager:
    """
    Manages dual-window display system (Gameplay + Debug Console).
    
    Handles window creation, positioning, and event management.
    """
    
    def __init__(self, width=WINDOW_WIDTH, height=WINDOW_HEIGHT):
        """
        Initialize display manager with dual windows.
        
        Args:
            width: Window width in pixels
            height: Window height in pixels
        """
        self.width = width
        self.height = height
        self.gameplay_window = WINDOW_GAMEPLAY
        self.debug_window = WINDOW_DEBUG
        
        self.windows_open = False
        
        # Initialize windows
        self._create_windows()
    
    def _create_windows(self):
        """Create both gameplay and debug windows."""
        try:
            # Create named windows
            cv2.namedWindow(self.gameplay_window, cv2.WINDOW_NORMAL)
            cv2.namedWindow(self.debug_window, cv2.WINDOW_NORMAL)
            
            # Set window sizes
            cv2.resizeWindow(self.gameplay_window, self.width, self.height)
            cv2.resizeWindow(self.debug_window, self.width, self.height)
            
            # Reposition windows side by side
            cv2.moveWindow(self.gameplay_window, 0, 0)  # Top-left
            cv2.moveWindow(self.debug_window, self.width + 20, 0)  # Top-right (offset by width + gap)
            
            self.windows_open = True
            print(f"✓ Display windows created:")
            print(f"  [{self.gameplay_window}] at (0, 0) - {self.width}x{self.height}")
            print(f"  [{self.debug_window}] at ({self.width+20}, 0) - {self.width}x{self.height}")
            
        except Exception as e:
            print(f"✗ Failed to create display windows: {e}")
            self.windows_open = False
    
    def display_gameplay(self, frame):
        """
        Display frame on gameplay window.
        
        Args:
            frame: OpenCV frame (BGR)
        """
        if self.windows_open and frame is not None:
            cv2.imshow(self.gameplay_window, frame)
    
    def display_debug(self, frame):
        """
        Display frame on debug window.
        
        Args:
            frame: OpenCV frame (BGR)
        """
        if self.windows_open and frame is not None:
            cv2.imshow(self.debug_window, frame)
    
    def close(self):
        """Close all windows."""
        cv2.destroyAllWindows()
        self.windows_open = False
        print("✓ Display windows closed")
    
    @staticmethod
    def handle_keyboard():
        """
        Handle keyboard input.
        
        Returns:
            Key code pressed (-1 if no key), with special handling:
            - 'q' or ESC (27): Quit
            - 'd': Toggle debug mode
            - ' ': Pause/Resume
        """
        return cv2.waitKey(1) & 0xFF


class CameraManager:
    """
    Manages camera input and frame capture.
    
    Handles initialization, frame reading, and resource cleanup.
    """
    
    def __init__(self, camera_id=0, width=WINDOW_WIDTH, height=WINDOW_HEIGHT):
        """
        Initialize camera manager.
        
        Args:
            camera_id: Camera device ID (0 = default webcam)
            width: Capture width resolution
            height: Capture height resolution
        """
        self.camera_id = camera_id
        self.target_width = width
        self.target_height = height
        self.capture = None
        self.frame_count = 0
        
        self._initialize_camera()
    
    def _initialize_camera(self):
        """Initialize camera capture."""
        try:
            self.capture = cv2.VideoCapture(self.camera_id)
            
            if not self.capture.isOpened():
                raise RuntimeError(f"Failed to open camera {self.camera_id}")
            
            # Set camera properties
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.target_width)
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.target_height)
            self.capture.set(cv2.CAP_PROP_FPS, TARGET_FPS)
            
            # Get actual properties
            actual_width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = self.capture.get(cv2.CAP_PROP_FPS)
            
            print(f"✓ Camera {self.camera_id} initialized:")
            print(f"  Resolution: {actual_width}x{actual_height}")
            print(f"  FPS: {actual_fps:.1f}")
            
        except Exception as e:
            print(f"✗ Camera initialization failed: {e}")
            self.capture = None
    
    def read_frame(self):
        """
        Capture and return next frame.
        
        Returns:
            Tuple (success: bool, frame: np.array) or (False, None) if failed
        """
        if self.capture is None:
            return False, None
        
        success, frame = self.capture.read()
        
        if success:
            self.frame_count += 1
            # Flip frame horizontally for mirror effect
            frame = cv2.flip(frame, 1)
        
        return success, frame
    
    def close(self):
        """Close camera and release resources."""
        if self.capture is not None:
            self.capture.release()
            print(f"✓ Camera closed ({self.frame_count} frames captured)")
    
    def is_open(self):
        """Check if camera is open and ready."""
        return self.capture is not None and self.capture.isOpened()


class Application:
    """
    Main application class - Orchestrates all systems.
    
    Manages initialization, state management, and cleanup.
    """
    
    def __init__(self, debug=False):
        """
        Initialize application and all subsystems.
        
        Args:
            debug: Enable debug mode
        """
        self.debug = debug
        self.running = False
        
        # Subsystems (initialized by setup())
        self.display_manager = None
        self.camera_manager = None
        self.ui_renderer = None
        self.spell_manager = None
        self.ai_engine = None
        
        print("\n" + "="*70)
        print("IGNITE: SPELL MASTER - Initialization")
        print("="*70 + "\n")
    
    def setup(self):
        """
        Initialize all application subsystems.
        
        This is the setup phase - call once before main loop.
        """
        print("[SETUP] Initializing subsystems...")
        
        # 1. Initialize display manager (windows)
        print("\n[SETUP] Creating display windows...")
        self.display_manager = DisplayManager(WINDOW_WIDTH, WINDOW_HEIGHT)
        
        if not self.display_manager.windows_open:
            print("✗ Failed to create display windows")
            return False
        
        # 2. Initialize camera
        print("\n[SETUP] Initializing camera...")
        self.camera_manager = CameraManager(camera_id=0, width=WINDOW_WIDTH, height=WINDOW_HEIGHT)
        
        if not self.camera_manager.is_open():
            print("✗ Failed to initialize camera")
            return False
        
        # 3. Initialize UI renderer
        print("\n[SETUP] Initializing UI renderer...")
        self.ui_renderer = UIRenderer(WINDOW_WIDTH, WINDOW_HEIGHT)
        print(f"✓ UIRenderer ready ({WINDOW_WIDTH}x{WINDOW_HEIGHT})")
        
        # 4. Initialize spell manager
        print("\n[SETUP] Initializing spell manager...")
        self.spell_manager = SpellManager(fps=TARGET_FPS, debug=self.debug)
        print(f"✓ SpellManager ready (FPS: {TARGET_FPS})")
        
        # 5. Initialize AI engine
        print("\n[SETUP] Initializing AI gesture recognition...")
        self.ai_engine = GestureAI(model_path=None, debug=self.debug)
        print(f"✓ GestureAI ready (Model: XGBoost, MediaPipe Hands)")
        
        print("\n" + "="*70)
        print("SETUP COMPLETE - All systems initialized")
        print("="*70 + "\n")
        
        return True
    
    def cleanup(self):
        """Clean up all resources."""
        print("\n[CLEANUP] Shutting down...")
        
        if self.camera_manager:
            self.camera_manager.close()
        
        if self.ai_engine:
            self.ai_engine.close()
        
        if self.display_manager:
            self.display_manager.close()
        
        print("[CLEANUP] Complete\n")
    
    def get_camera_frame(self):
        """
        Capture frame from camera.
        
        Returns:
            Frame or None if capture failed
        """
        if self.camera_manager is None:
            return None
        
        success, frame = self.camera_manager.read_frame()
        return frame if success else None
    
    def is_ready(self):
        """Check if application is fully initialized and ready."""
        return (
            self.display_manager and self.display_manager.windows_open and
            self.camera_manager and self.camera_manager.is_open() and
            self.ui_renderer is not None and
            self.spell_manager is not None and
            self.ai_engine is not None
        )


def main():
    """
    Main application entry point.
    
    Initializes the application and sets up for game loop execution.
    """
    # Initialize application
    app = Application(debug=False)
    
    # Setup all subsystems
    if not app.setup():
        print("✗ Setup failed - exiting")
        app.cleanup()
        return 1
    
    # Verify all systems ready
    if not app.is_ready():
        print("✗ Not all systems initialized - exiting")
        app.cleanup()
        return 1
    
    print("\n✓ Application ready to start - press 'q' to quit")
    print("  Press 'd' to toggle debug mode")
    print("  Press 'space' to pause/resume\n")
    
    # Main game loop
    print("\n[LOOP] Starting main game loop...")
    print("       Press 'q' to quit, 'd' to toggle debug\n")
    
    app.running = True
    frame_count = 0
    
    while app.running:
        # 1. Capture frame from camera
        frame = app.get_camera_frame()
        if frame is None:
            print("✗ Failed to capture frame - exiting")
            break
        
        frame_count += 1
        
        # 2. Update spell manager (handles state machine timing)
        app.spell_manager.update()
        
        # 3. AI Prediction - Get spell prediction and hand coordinates
        spell_name, confidence = app.ai_engine.predict(frame)
        
        # 4. Hand detection status
        # Only True if both hands detected AND spell recognized
        hands_detected = spell_name is not None
        
        # 5. Update hand tracking in spell manager (with validation)
        # Pass spell_name to validate 2-hand requirement
        # If spell_name is None → reset CHANTING/ACTIVATED to IDLE
        app.spell_manager.set_hand_held(hands_detected, spell_name)
        
        # 6. Handle spell state transitions
        if hands_detected and app.spell_manager.is_idle():
            # Hand detected in IDLE state → start chanting
            app.spell_manager.start_chanting()
            if app.debug:
                print(f"[Frame {frame_count}] Gesture detected - starting chant")
        
        elif not hands_detected and app.spell_manager.is_chanting():
            # Hand lost during chanting → cancel chanting
            app.spell_manager.cancel_chanting()
            if app.debug:
                print(f"[Frame {frame_count}] Gesture lost - cancelled chanting")
        
        # 7. Check for automatic spell execution event (hand released during ACTIVATED)
        if app.spell_manager.has_event(SpellEvent.EXECUTE_SPELL):
            if spell_name and app.spell_manager.execute_spell(spell_name, confidence):
                print(f"[Frame {frame_count}] ⚡ SPELL EXECUTED: {spell_name} ({confidence*100:.1f}%)")
                print(f"                   MP: {app.spell_manager.current_mp}/{app.spell_manager.max_mp}")
            else:
                if app.spell_manager.current_mp < app.spell_manager.mp_cost_per_spell:
                    print(f"[Frame {frame_count}] ✗ Insufficient mana (need {app.spell_manager.mp_cost_per_spell}, "
                          f"have {app.spell_manager.current_mp})")
        
        # 8. Check for cooldown completion
        if app.spell_manager.has_event(SpellEvent.COOLDOWN_END):
            print(f"[Frame {frame_count}] ✓ Cooldown complete - ready to cast")
        
        # Debug logging every 30 frames
        if app.debug and frame_count % 30 == 0:
            stats = app.spell_manager.get_debug_info()
            print(f"[Frame {frame_count}] {stats}")
        
        # =====================================================================
        # UI RENDERING PHASE
        # =====================================================================
        
        # Create game frame (for gameplay UI)
        game_frame = frame.copy()
        
        # Create debug frame (for debugging visualization)
        debug_frame = frame.copy()
        
        # --- Draw Gameplay UI ---
        # Draw status bars (HP/MP)
        game_frame = app.ui_renderer.draw_status_bars(
            game_frame,
            hp_ratio=app.spell_manager.get_hp_ratio(),
            mp_ratio=app.spell_manager.get_mp_ratio(),
            x=20, y=20, bar_width=200
        )
        
        # Draw current spell name if chanting or activated
        if spell_name and app.spell_manager.is_chanting():
            game_frame = app.ui_renderer.draw_gesture_hint(
                game_frame,
                f"Chanting: {spell_name}",
                position="top-center"
            )
        elif spell_name and app.spell_manager.is_activated():
            game_frame = app.ui_renderer.draw_gesture_hint(
                game_frame,
                f"READY: {spell_name}",
                position="top-center"
            )
        elif app.spell_manager.is_executing():
            game_frame = app.ui_renderer.draw_gesture_hint(
                game_frame,
                f"⚡ {app.spell_manager.current_spell_name}",
                position="top-center"
            )
        
        # Draw chant progress bar if chanting
        if app.spell_manager.is_chanting():
            chant_progress = app.spell_manager.get_chant_progress()
            progress_color = (0, 165, 255)  # Orange
            bar_y = WINDOW_HEIGHT - 40
            bar_width = int(WINDOW_WIDTH * chant_progress)
            cv2.rectangle(game_frame, (0, bar_y), (bar_width, WINDOW_HEIGHT),
                         progress_color, -1)
            cv2.rectangle(game_frame, (0, bar_y), (WINDOW_WIDTH, WINDOW_HEIGHT),
                         (255, 255, 255), 2)
        
        # Draw cooldown bar if in cooldown
        if app.spell_manager.is_in_cooldown():
            cooldown_progress = app.spell_manager.get_cooldown_progress()
            cooldown_color = (200, 100, 0)  # Dark blue
            bar_y = WINDOW_HEIGHT - 40
            bar_width = int(WINDOW_WIDTH * cooldown_progress)
            cv2.rectangle(game_frame, (0, bar_y), (bar_width, WINDOW_HEIGHT),
                         cooldown_color, -1)
            cv2.rectangle(game_frame, (0, bar_y), (WINDOW_WIDTH, WINDOW_HEIGHT),
                         (255, 255, 255), 2)
        
        # --- Draw Debug UI ---
        # Get hand landmarks and bounding boxes
        landmarks_left, landmarks_right = app.ai_engine.get_last_landmarks()
        hand_bboxes = app.ai_engine.get_last_bounding_boxes()
        
        # Draw bounding boxes on debug frame
        if hand_bboxes:
            debug_frame = app.ui_renderer.draw_bounding_box(
                debug_frame,
                bboxes=hand_bboxes,
                merge_hands=True,
                color=(0, 255, 0),  # Green
                thickness=2
            )
        
        # Draw left hand landmarks and connections
        if landmarks_left:
            debug_frame = app.ui_renderer.draw_landmarks(
                debug_frame,
                landmarks=landmarks_left,
                color=(0, 255, 0),  # Green for left hand
                radius=3,
                thickness=1
            )
            
            # Draw hand skeleton (connections)
            hand_connections = [
                (0, 1), (1, 2), (2, 3), (3, 4),  # Thumb
                (0, 5), (5, 6), (6, 7), (7, 8),  # Index
                (0, 9), (9, 10), (10, 11), (11, 12),  # Middle
                (0, 13), (13, 14), (14, 15), (15, 16),  # Ring
                (0, 17), (17, 18), (18, 19), (19, 20),  # Pinky
                (5, 9), (9, 13), (13, 17)  # Palm connections
            ]
            debug_frame = app.ui_renderer.draw_connections(
                debug_frame,
                landmarks=landmarks_left,
                connections=hand_connections,
                color=(0, 255, 0),  # Green
                thickness=1
            )
        
        # Draw right hand landmarks and connections
        if landmarks_right:
            debug_frame = app.ui_renderer.draw_landmarks(
                debug_frame,
                landmarks=landmarks_right,
                color=(255, 0, 0),  # Blue for right hand
                radius=3,
                thickness=1
            )
            
            # Draw hand skeleton
            debug_frame = app.ui_renderer.draw_connections(
                debug_frame,
                landmarks=landmarks_right,
                connections=hand_connections,
                color=(255, 0, 0),  # Blue
                thickness=1
            )
        
        # Draw debug info on debug frame
        debug_info = {
            'State': app.spell_manager.current_state.name,
            'Spell': spell_name or "None",
            f'Conf': f"{confidence*100:.0f}%" if spell_name else "0%",
            'HP': f"{int(app.spell_manager.current_hp)}/{int(app.spell_manager.max_hp)}",
            'MP': f"{int(app.spell_manager.current_mp)}/{int(app.spell_manager.max_mp)}",
            'Frame': frame_count,
        }
        debug_frame = app.ui_renderer.draw_debug_info(
            debug_frame,
            debug_info,
            position="bottom-left",
            bg_alpha=0.7
        )
        
        # Display both frames
        app.display_manager.display_gameplay(game_frame)
        app.display_manager.display_debug(debug_frame)
        
        # 9. Handle keyboard input
        key = DisplayManager.handle_keyboard()
        
        if key == ord('q') or key == 27:  # 'q' or ESC
            print("✓ Quit signal received")
            app.running = False
        
        elif key == ord('d'):  # 'd' for debug toggle
            app.debug = not app.debug
            print(f"[Debug mode: {'ON' if app.debug else 'OFF'}]")
        
        elif key == ord(' '):  # Space for pause
            print("[PAUSED] Press 'p' to resume, 'q' to quit")
            while True:
                key_pause = DisplayManager.handle_keyboard()
                if key_pause == ord('p'):
                    print("[RESUMED]")
                    break
                elif key_pause == ord('q'):
                    app.running = False
                    break
                cv2.waitKey(10)
    
    # Cleanup and exit
    app.cleanup()
    print("\n✓ Application terminated successfully")
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n✗ Interrupted by user (Ctrl+C)")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
