import cv2
import mediapipe as mp
import joblib
import numpy as np
from pathlib import Path
import time
import warnings
from vfx_library import VFXManager, draw_vfx

# Suppress sklearn and protobuf warnings
warnings.filterwarnings('ignore', category=UserWarning, module='sklearn')
warnings.filterwarnings('ignore', category=UserWarning, module='google.protobuf')

# Spell State Machine states
class SpellState:
    IDLE = "IDLE"           # No active spell detection
    CHANTING = "CHANTING"   # Confidence > 0.8, charging timer
    ACTIVATED = "ACTIVATED" # Timer reached threshold, ready to cast
    EXECUTING = "EXECUTING" # Spell is executing

class SpellRecognizer:
    def __init__(self, model_path=None):
        """Initialize the spell recognizer with trained model."""
        
        # MediaPipe initialization
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            model_complexity=1,  # Higher accuracy for interlaced fingers
            max_num_hands=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.4
        )
        
        # Load trained model
        if model_path is None:
            # Default path relative to this script
            model_path = Path(__file__).parent / "data" / "models" / "best_spell_model.pkl"
        else:
            model_path = Path(model_path)
        
        try:
            self.model = joblib.load(model_path)
            print(f"Model loaded successfully from {model_path}")
            self.model_classes = self.model.classes_
            print(f"Recognized spells: {list(self.model_classes)}")
        except FileNotFoundError:
            print(f"Error: Model file not found at {model_path}")
            print("Please ensure best_spell_model.pkl exists in the data directory")
            raise
        
        # Configuration
        self.confidence_threshold = 0.75  # 75% confidence threshold
        self.bbox_color = (0, 255, 0)  # Green
        self.bbox_thickness = 2
        
        # Smoothing for stable predictions
        self.smoothing_factor = 0.6
        self.previous_landmarks = {}
        self.previous_hand_count = 0
        self.skipped_frames = 0
        
        # Prediction smoothing (show last valid prediction for N frames)
        self.last_prediction = None
        self.last_confidence = 0
        self.prediction_hold_frames = 0
        self.prediction_hold_count = 5  # Hold prediction for 5 frames
        
        # Single hand warning tracker
        self.single_hand_warning_frames = 0
        self.single_hand_warning_duration = 60  # Show warning for ~2 seconds (at 30fps)
        
        # VFX Manager initialization
        self.vfx_manager = VFXManager()
        from vfx_library import extract_sprites, SpriteEffect

        # Optional: Load sprite sheets if available
        sprites_dir = Path(__file__).parent / "assets" / "sprites"

        try:
            # Load sprite sheets
            tiger_sprites = extract_sprites(
                str(sprites_dir / "fireball.png"),
                rows=4,
                cols=4
            )
            if tiger_sprites:
                self.vfx_manager.effects['Tiger'] = SpriteEffect(
                    tiger_sprites,
                    duration=60,
                    frame_skip=2,
                    scale=1.5
                )

            # Repeat for Dragon and Ox...
            dragon_sprites = extract_sprites(
                str(sprites_dir / "ice.png"),
                rows=4,
                cols=4
            )
            if dragon_sprites:
                self.vfx_manager.effects['Dragon'] = SpriteEffect(
                    dragon_sprites,
                    duration=60,
                    frame_skip=2,
                    scale=1.5
                )

            ox_sprites = extract_sprites(
                str(sprites_dir / "lightning.png"),
                rows=4,
                cols=4
            )
            if ox_sprites:
                self.vfx_manager.effects['Ox'] = SpriteEffect(
                    ox_sprites,
                    duration=60,
                    frame_skip=2,
                    scale=1.5
                )

        except Exception as e:
            print(f"Warning: Could not load sprite sheets: {e}")
            print("Using procedural effects instead")

        
        # Spell State Machine
        self.current_state = SpellState.IDLE
        self.chant_timer = 0
        self.chant_threshold = 30  # Frames needed to reach ACTIVATED state (~1 second at 30fps)
        self.last_hand_detected_time = 0  # Track when hand was last detected
        
        # Game State (HP/MP)
        self.hp = 100
        self.mp = 100
        self.max_hp = 100
        self.max_mp = 100
        self.mp_cost_per_spell = 25  # MP consumed when spell is cast
        
        # Gesture icons configuration
        self.gesture_icons = ['🔥 Fireball', '❄️ Ice', '⚡Lightning']
        
        # Spell trigger tracking (prevent rapid re-triggering)
        self.last_triggered_spell = None
        self.spell_trigger_cooldown = 0
        self.last_trigger_time = 0  # Track when spell was last triggered
        self.trigger_cooldown_frames = 150  # Prevent re-triggering for 150 frames (~5 sec at 30fps)
        
        # Countdown timer for spell casting
        self.countdown_active = False
        self.countdown_frames = 0
        self.countdown_total = 30  # 30 frames = ~1 second at 30fps
        self.pending_spell_name = None
        self.pending_spell_center = None
        
        # Debug mode for keyboard spell casting
        self.debug_mode = False
        self.debug_spell_center = (640, 360)  # Center of screen for debug effects
        
        # Diagnostic tracking
        self.frame_count = 0
        self.prediction_log = []  # Track last 10 predictions
        
        # Camera initialization
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    def extract_hand_landmarks(self, hand_landmarks):
        """Extract 21 landmarks from a hand, return as list of (x, y) tuples."""
        landmarks = []
        for lm in hand_landmarks.landmark:
            landmarks.append((lm.x, lm.y))
        return landmarks
    
    def is_hand_count_stable(self, current_hand_count, threshold=2):
        """Check if hand count is stable."""
        if self.previous_hand_count == 0:
            return True
        
        if current_hand_count == self.previous_hand_count:
            self.previous_hand_count = current_hand_count
            return True
        
        return False
    
    def apply_strong_smoothing(self, landmarks_list, hand_id):
        """Apply smoothing using exponential moving average."""
        landmarks_dict = {}
        for i, (x, y) in enumerate(landmarks_list):
            landmarks_dict[f"x{i}"] = x
            landmarks_dict[f"y{i}"] = y
        
        if hand_id not in self.previous_landmarks:
            self.previous_landmarks[hand_id] = landmarks_dict
            return landmarks_list
        
        prev = self.previous_landmarks[hand_id]
        smoothed_dict = {}
        
        alpha = self.smoothing_factor * 0.5
        
        for i, (x, y) in enumerate(landmarks_list):
            smoothed_x = alpha * x + (1 - alpha) * prev.get(f"x{i}", x)
            smoothed_y = alpha * y + (1 - alpha) * prev.get(f"y{i}", y)
            
            smoothed_dict[f"x{i}"] = smoothed_x
            smoothed_dict[f"y{i}"] = smoothed_y
        
        self.previous_landmarks[hand_id] = smoothed_dict
        
        smoothed_list = [(smoothed_dict[f"x{i}"], smoothed_dict[f"y{i}"]) for i in range(len(landmarks_list))]
        return smoothed_list
    
    def process_frame_data(self, results, hand_count):
        """
        Process frame data with GLOBAL Coordinate Reference.
        Returns feature vector for prediction, or None if unstable or not exactly 2 hands.
        
        IMPORTANT: Only processes when exactly 2 hands are detected.
        Single hand gestures are not supported.
        """
        # Check hand count stability
        current_hand_count = hand_count
        
        # Only process if exactly 2 hands are detected
        if current_hand_count != 2:
            self.skipped_frames += 1
            return None
        
        # Check if hand count is stable
        if not self.is_hand_count_stable(current_hand_count):
            self.skipped_frames += 1
            self.previous_hand_count = current_hand_count
            return None
        
        # Two hands case: LEFT wrist is global origin for both
        left_coords = []
        right_coords = []
        
        left_wrist_x = None
        left_wrist_y = None
        left_palm_size = None
        has_left_hand = False
        has_right_hand = False
        
        # First pass: identify and process left hand
        for hand_idx, (hand_landmarks, handedness) in enumerate(
            zip(results.multi_hand_landmarks, results.multi_handedness)
        ):
            hand_label = handedness.classification[0].label
            
            if hand_label == "Left":
                has_left_hand = True
                landmarks = self.extract_hand_landmarks(hand_landmarks)
                landmarks = self.apply_strong_smoothing(landmarks, hand_idx)
                
                left_wrist_x, left_wrist_y = landmarks[0]
                
                palm_x, palm_y = landmarks[9]
                left_palm_size = np.sqrt((palm_x - left_wrist_x) ** 2 + (palm_y - left_wrist_y) ** 2)
                
                if left_palm_size < 0.001:
                    left_palm_size = 0.001
                
                for i, (lx, ly) in enumerate(landmarks):
                    rel_x = lx - left_wrist_x
                    rel_y = ly - left_wrist_y
                    
                    norm_x = rel_x / left_palm_size
                    norm_y = rel_y / left_palm_size
                    
                    left_coords.append(norm_x)
                    left_coords.append(norm_y)
        
        # Second pass: process right hand using same global reference
        for hand_idx, (hand_landmarks, handedness) in enumerate(
            zip(results.multi_hand_landmarks, results.multi_handedness)
        ):
            hand_label = handedness.classification[0].label
            
            if hand_label == "Right":
                has_right_hand = True
                landmarks = self.extract_hand_landmarks(hand_landmarks)
                landmarks = self.apply_strong_smoothing(landmarks, hand_idx)
                
                # Check if left hand was found before processing right hand
                if left_wrist_x is None or left_palm_size is None:
                    self.skipped_frames += 1
                    return None  # Left hand reference not available, skip frame
                
                for i, (lx, ly) in enumerate(landmarks):
                    rel_x = lx - left_wrist_x
                    rel_y = ly - left_wrist_y
                    
                    norm_x = rel_x / left_palm_size
                    norm_y = rel_y / left_palm_size
                    
                    right_coords.append(norm_x)
                    right_coords.append(norm_y)
        
        # Only return feature vector if both hands were detected
        if has_left_hand and has_right_hand:
            feature_vector = []
            feature_vector.extend(left_coords)
            feature_vector.extend(right_coords)
            self.previous_hand_count = current_hand_count
            return np.array(feature_vector)
        else:
            self.skipped_frames += 1
            return None
    
    def get_hand_bounding_box(self, results, frame_shape):
        """
        Calculate bounding box coordinates for detected hands.
        
        For 1 hand: Returns bounding box for that hand
        For 2 hands: Returns single unified bounding box encompassing both hands
        
        Returns: (min_x, min_y, max_x, max_y) in pixel coordinates
        """
        h, w, _ = frame_shape
        hand_count = len(results.multi_hand_landmarks) if results.multi_hand_landmarks else 0
        
        if hand_count == 0:
            return None
        
        all_x = []
        all_y = []
        
        # Collect all landmark coordinates
        for hand_landmarks in results.multi_hand_landmarks:
            for landmark in hand_landmarks.landmark:
                pixel_x = int(landmark.x * w)
                pixel_y = int(landmark.y * h)
                all_x.append(pixel_x)
                all_y.append(pixel_y)
        
        min_x = max(0, min(all_x) - 20)  # Add padding
        max_x = min(w, max(all_x) + 20)
        min_y = max(0, min(all_y) - 20)
        max_y = min(h, max(all_y) + 20)
        
        return (min_x, min_y, max_x, max_y)
    
    def draw_status_bars(self, frame, hp, mp):
        """
        Draw HP and MP bars on top-left corner of frame.
        
        Args:
            frame: The image frame to draw on
            hp: Current HP value
            mp: Current MP value
        """
        h, w, _ = frame.shape
        
        # Bar configuration
        bar_width = 200
        bar_height = 20
        padding = 15
        x_offset = padding
        y_offset = padding
        
        # HP Bar (Red)
        hp_percentage = hp / self.max_hp
        cv2.rectangle(frame, (x_offset, y_offset), (x_offset + bar_width, y_offset + bar_height), (50, 50, 50), -1)
        cv2.rectangle(frame, (x_offset, y_offset), 
                     (x_offset + int(bar_width * hp_percentage), y_offset + bar_height), 
                     (0, 0, 255), -1)
        cv2.rectangle(frame, (x_offset, y_offset), (x_offset + bar_width, y_offset + bar_height), (200, 200, 200), 2)
        
        # HP Text
        hp_text = f"HP: {int(hp)}/{int(self.max_hp)}"
        cv2.putText(frame, hp_text, (x_offset + 10, y_offset + 15), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        
        # MP Bar (Blue) - positioned below HP bar
        mp_y_offset = y_offset + bar_height + 10
        mp_percentage = mp / self.max_mp
        cv2.rectangle(frame, (x_offset, mp_y_offset), (x_offset + bar_width, mp_y_offset + bar_height), (50, 50, 50), -1)
        cv2.rectangle(frame, (x_offset, mp_y_offset), 
                     (x_offset + int(bar_width * mp_percentage), mp_y_offset + bar_height), 
                     (255, 0, 0), -1)
        cv2.rectangle(frame, (x_offset, mp_y_offset), (x_offset + bar_width, mp_y_offset + bar_height), (200, 200, 200), 2)
        
        # MP Text
        mp_text = f"MP: {int(mp)}/{int(self.max_mp)}"
        cv2.putText(frame, mp_text, (x_offset + 10, mp_y_offset + 15), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    
    def draw_gesture_icons(self, frame):
        """
        Draw gesture/spell icon hints at the bottom of the frame.
        
        Args:
            frame: The image frame to draw on
        """
        h, w, _ = frame.shape
        
        # Configuration
        icon_y_offset = h - 60
        icon_spacing = w // (len(self.gesture_icons) + 1)
        icon_size = 40
        
        # Draw icons with labels
        for idx, gesture in enumerate(self.gesture_icons):
            x_pos = icon_spacing * (idx + 1)
            
            # Draw gesture box
            cv2.rectangle(frame, (x_pos - icon_size // 2, icon_y_offset - icon_size // 2),
                        (x_pos + icon_size // 2, icon_y_offset + icon_size // 2),
                        (0, 200, 200), 2)
            
            # Draw gesture number
            number_text = f"{idx + 1}"
            cv2.putText(frame, number_text, (x_pos - 8, icon_y_offset + 8),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 200), 2)
            
            # Draw gesture label
            cv2.putText(frame, gesture, (x_pos - 30, icon_y_offset + 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 200), 1)
    
    def draw_progress_circle(self, frame, center, radius, progress, thickness=3):
        """
        Draw a progress circle around hand position.
        
        Args:
            frame: The image frame to draw on
            center: Circle center position (x, y)
            radius: Circle radius
            progress: Progress percentage (0.0 - 1.0)
            thickness: Line thickness
        """
        # Calculate the arc angle
        angle = int(360 * progress)
        
        # Draw background circle
        cv2.circle(frame, center, radius, (50, 50, 100), thickness)
        
        # Draw progress arc (cyan color)
        cv2.ellipse(frame, center, (radius, radius), 0, 0, angle, (0, 255, 255), thickness)
        
        # Draw progress percentage text
        progress_text = f"{int(progress * 100)}%"
        text_size = cv2.getTextSize(progress_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
        cv2.putText(frame, progress_text, 
                   (center[0] - text_size[0] // 2, center[1] + 8),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    
    def draw_landmarks(self, frame, results):
        """Draw hand landmarks and connections on the frame."""
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                self.mp_drawing.draw_landmarks(
                    frame,
                    hand_landmarks,
                    self.mp_hands.HAND_CONNECTIONS,
                    self.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                    self.mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=2)
                )
    
    def draw_bounding_box(self, frame, bbox, spell_name, confidence):
        """Draw bounding box and prediction text on frame."""
        if bbox is None:
            return
        
        min_x, min_y, max_x, max_y = bbox
        
        # Draw bounding box rectangle
        cv2.rectangle(frame, (min_x, min_y), (max_x, max_y), self.bbox_color, self.bbox_thickness)
        
        # Draw prediction text above bounding box
        if spell_name and confidence > 0:
            text = f"{spell_name} - {confidence:.0f}%"
            text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
            
            # Background rectangle for text
            text_x = min_x
            text_y = max(10, min_y - 10)
            
            cv2.rectangle(
                frame,
                (text_x - 5, text_y - text_size[1] - 5),
                (text_x + text_size[0] + 5, text_y + 5),
                self.bbox_color,
                -1
            )
            
            # Draw text
            cv2.putText(
                frame,
                text,
                (text_x, text_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 0),
                2
            )
    
    def trigger_vfx_for_spell(self, spell_name, center_coord):
        """
        Trigger VFX effect when spell is recognized.
        
        Args:
            spell_name: Name of recognized spell
            center_coord: Center position (x, y) of bounding box
        """
        # Map spell names to VFX types (using Fire, Air, Water, Earth system)
        spell_to_vfx = {
            # Direct spell names
            'Fire': 'Fire',
            'Water': 'Water',
            'Air': 'Air',
            'Earth': 'Fire',  # Fallback to Fire if Earth is detected
            # Aliases
            'Tiger': 'Fire',
            'Fireball': 'Fire',
            'Dragon': 'Water',
            'Ice': 'Water',
            'Ox': 'Air',
            'Lightning': 'Air',
        }
        
        print(f"[DEBUG] trigger_vfx_for_spell called: spell_name={spell_name}, center={center_coord}")
        
        if spell_name in spell_to_vfx:
            vfx_type = spell_to_vfx[spell_name]
            cooldown_remaining = self.frame_count - self.last_trigger_time
            print(f"[DEBUG] Cooldown check: frame_count={self.frame_count}, last_trigger_time={self.last_trigger_time}, remaining={cooldown_remaining}, threshold={self.trigger_cooldown_frames}")
            
            # Check cooldown to prevent rapid re-triggering
            if cooldown_remaining > self.trigger_cooldown_frames:
                self.vfx_manager.trigger_spell(vfx_type)
                self.last_triggered_spell = spell_name
                self.last_trigger_time = self.frame_count
                remaining_cooldown = self.trigger_cooldown_frames / 30.0  # Convert frames to seconds
                print(f"✨ SPELL CAST: {spell_name} → VFX: {vfx_type} (Confidence: {self.last_confidence:.0f}%) | Cooldown: {remaining_cooldown:.1f}s")
                return True
            else:
                print(f"[DEBUG] Still in cooldown period: {cooldown_remaining}/{self.trigger_cooldown_frames} frames")
                return False
        else:
            print(f"[DEBUG] Spell '{spell_name}' not found in mapping. Available: {list(spell_to_vfx.keys())}")
            return False
    
    def handle_debug_input(self, key):
        """
        Handle debug keyboard input for spell casting.
        
        Keys:
            D: Toggle debug mode
            1: Cast Tiger/Fireball
            2: Cast Dragon/Ice
            3: Cast Ox/Lightning
            M: Move debug center to mouse position (if supported)
        """
        if key == ord('d') or key == ord('D'):
            self.debug_mode = not self.debug_mode
            status = "ON" if self.debug_mode else "OFF"
            print(f"\n🔧 Debug Mode: {status}")
            if self.debug_mode:
                print("   Press 1: Cast Fireball (Tiger)")
                print("   Press 2: Cast Ice (Dragon)")
                print("   Press 3: Cast Lightning (Ox)")
                print("   Press D: Toggle debug mode off")
            return True
        
        if self.debug_mode:
            if key == ord('1'):
                self.trigger_vfx_for_spell('Tiger', self.debug_spell_center)
                return True
            elif key == ord('2'):
                self.trigger_vfx_for_spell('Dragon', self.debug_spell_center)
                return True
            elif key == ord('3'):
                self.trigger_vfx_for_spell('Ox', self.debug_spell_center)
                return True
        
        return False
    
    def draw_ui(self, frame, hand_count, show_warning=False):
        """Draw UI information on frame."""
        h, w, _ = frame.shape
        
        # Hand count
        hand_text = f"Hands detected: {hand_count}"
        hand_color = (0, 255, 0) if hand_count == 2 else (0, 165, 255)  # Green if 2 hands, Orange otherwise
        cv2.putText(frame, hand_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, hand_color, 2)
        
        # Debug mode indicator
        if self.debug_mode:
            debug_text = "DEBUG MODE: ON"
            cv2.putText(frame, debug_text, (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 165, 255), 2)
            
            # Draw debug center point
            cv2.circle(frame, self.debug_spell_center, 10, (0, 165, 255), 2)
            cv2.circle(frame, self.debug_spell_center, 3, (0, 165, 255), -1)
            
            # Draw debug help
            debug_help = [
                "1: Fireball (Tiger)",
                "2: Ice (Dragon)",
                "3: Lightning (Ox)",
                "D: Turn off debug"
            ]
            
            for i, help_text in enumerate(debug_help):
                cv2.putText(frame, help_text, (10, 120 + i * 35), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 1)
        
        # Countdown timer display
        if self.countdown_active:
            countdown_remaining = self.countdown_total - self.countdown_frames
            countdown_percent = int((self.countdown_frames / self.countdown_total) * 100)
            countdown_text = f"⏱️ CASTING {self.pending_spell_name}... {countdown_percent}%"
            
            # Draw countdown background
            text_size = cv2.getTextSize(countdown_text, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 3)[0]
            cv2.rectangle(
                frame,
                (w // 2 - text_size[0] // 2 - 10, h // 2 - 50),
                (w // 2 + text_size[0] // 2 + 10, h // 2 - 10),
                (100, 50, 200),  # Purple background
                -1
            )
            
            # Draw countdown text
            cv2.putText(
                frame,
                countdown_text,
                (w // 2 - text_size[0] // 2, h // 2 - 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.2,
                (0, 255, 255),  # Yellow text
                3
            )
        
        # Single hand warning
        if show_warning and hand_count == 1:
            warning_text = "⚠ SINGLE HAND DETECTED - Use BOTH hands for spells"
            warning_color = (0, 0, 255)  # Red
            text_size = cv2.getTextSize(warning_text, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)[0]
            
            # Draw warning background
            cv2.rectangle(
                frame,
                (10, 60),
                (20 + text_size[0], 90 + text_size[1]),
                warning_color,
                -1
            )
            
            # Draw warning text
            cv2.putText(
                frame,
                warning_text,
                (15, 85),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (255, 255, 255),
                2
            )
        
        # Instructions
        instructions = [
            "Q: Quit",
            "D: Debug Mode",
            "Confidence: 75%"
        ]
        
        for i, instruction in enumerate(instructions):
            cv2.putText(
                frame,
                instruction,
                (w - 300, 30 + i * 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (200, 200, 200),
                1
            )
    
    def draw_debug_info(self, frame, spell_name, confidence, fps, hand_count):
        """
        Draw technical debug information on frame.
        
        Args:
            frame: The image frame to draw on
            spell_name: Detected spell name
            confidence: Confidence percentage
            fps: Current frames per second
            hand_count: Number of hands detected
        """
        h, w, _ = frame.shape
        info_y = 20
        line_spacing = 30
        
        # Create colored background for info box
        cv2.rectangle(frame, (10, 5), (400, 200), (0, 0, 0), -1)
        cv2.rectangle(frame, (10, 5), (400, 200), (200, 200, 200), 2)
        
        # Draw technical info
        debug_info = [
            f"State: {self.current_state}",
            f"Detected: {spell_name if spell_name else 'NONE'}",
            f"Confidence: {confidence:.1f}%",
            f"Chant Timer: {self.chant_timer}/{self.chant_threshold}",
            f"Hands: {hand_count}",
            f"FPS: {fps:.1f}",
            f"HP: {int(self.hp)}/{int(self.max_hp)}",
            f"MP: {int(self.mp)}/{int(self.max_mp)}",
        ]
        
        for idx, info in enumerate(debug_info):
            y_pos = info_y + idx * line_spacing
            cv2.putText(frame, info, (20, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
    
    def predict_spell(self, feature_vector):
        """
        Predict spell from feature vector.
        
        Returns: (spell_name, confidence_percentage) or (None, 0) if below threshold
        """
        if feature_vector is None:
            return None, 0
        
        try:
            # Suppress sklearn feature name warning
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', category=UserWarning)
                # Get prediction
                prediction = self.model.predict([feature_vector])[0]
                
                # Get confidence probabilities
                probabilities = self.model.predict_proba([feature_vector])[0]
                max_confidence = max(probabilities)
            
            # Apply confidence threshold
            if max_confidence > self.confidence_threshold:
                confidence_percentage = max_confidence * 100
                return prediction, confidence_percentage
            else:
                return None, 0
        
        except Exception as e:
            print(f"Error during prediction: {e}")
            return None, 0
    
    def run(self):
        """Main loop for real-time spell recognition with dual windows."""
        print("\n" + "="*70)
        print("=== Ignite: Spell Master - Dual Window Display System ===".center(70))
        print("="*70)
        print(f"Confidence threshold: {self.confidence_threshold * 100:.0f}%")
        print(f"Chanting threshold: {self.chant_threshold} frames")
        print(f"Recognized spells: {list(self.vfx_manager.effects.keys())}")
        print("\n📋 Controls:")
        print("  Q: Quit")
        print("  D: Toggle Debug Mode (keyboard spell casting)")
        print("  V: Toggle verbose mode (show all predictions)")
        print("\n🎮 Game Windows:")
        print("  Window 1: Ignite: Spell Master - Gameplay")
        print("  Window 2: Debug Console - AI Recognition")
        print("="*70 + "\n")
        
        # Create both windows
        cv2.namedWindow("Ignite: Spell Master - Gameplay", cv2.WINDOW_NORMAL)
        cv2.namedWindow("Debug Console - AI Recognition", cv2.WINDOW_NORMAL)
        
        verbose_mode = False
        start_time = time.time()
        frame_count = 0
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("Failed to capture frame")
                break
            
            frame_count += 1
            self.frame_count += 1
            
            # Mirror the frame
            frame = cv2.flip(frame, 1)
            h, w, c = frame.shape
            
            # Create copies for game and debug displays
            game_frame = frame.copy()
            debug_frame = frame.copy()
            
            # Calculate FPS
            elapsed_time = time.time() - start_time
            fps = frame_count / elapsed_time if elapsed_time > 0 else 0
            
            # Convert to RGB for MediaPipe
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(frame_rgb)
            
            # Extract data
            hand_count = len(results.multi_hand_landmarks) if results.multi_hand_landmarks else 0
            bbox = None
            spell_name = None
            confidence = 0
            show_warning = False
            
            # --- SPELL STATE MACHINE LOGIC ---
            
            # Track single hand warning
            if hand_count == 1:
                self.single_hand_warning_frames = self.single_hand_warning_duration
                show_warning = True
            elif self.single_hand_warning_frames > 0:
                self.single_hand_warning_frames -= 1
                show_warning = True
            
            if hand_count == 2:
                # Process hand detection
                feature_vector = self.process_frame_data(results, hand_count)
                
                if feature_vector is not None:
                    spell_name, confidence = self.predict_spell(feature_vector)
                    
                    if verbose_mode and spell_name:
                        print(f"[Frame {self.frame_count}] Predicted: {spell_name} ({confidence:.1f}%)")
                    
                    # Get bounding box for visual feedback
                    bbox = self.get_hand_bounding_box(results, frame.shape)
                    bbox_center = None
                    if bbox:
                        bbox_center = ((bbox[0] + bbox[2]) // 2, (bbox[1] + bbox[3]) // 2)
                    
                    # --- STATE TRANSITIONS ---
                    if self.current_state == SpellState.IDLE:
                        # IDLE -> CHANTING: When confidence > 0.8
                        if confidence > 80:
                            self.current_state = SpellState.CHANTING
                            self.chant_timer = 0
                            self.pending_spell_name = spell_name
                            self.pending_spell_center = bbox_center
                            print(f"⚡ CHANTING STARTED: {spell_name} (Confidence: {confidence:.0f}%)")
                        else:
                            self.chant_timer = 0
                    
                    elif self.current_state == SpellState.CHANTING:
                        # Increment chant timer
                        self.chant_timer += 1
                        
                        # Check if still same gesture
                        if confidence > 80:
                            # CHANTING -> ACTIVATED: When timer reaches threshold
                            if self.chant_timer >= self.chant_threshold:
                                self.current_state = SpellState.ACTIVATED
                                self.pending_spell_name = spell_name
                                self.pending_spell_center = bbox_center
                                print(f"🔥 SPELL ACTIVATED: {spell_name}!")
                        else:
                            # Confidence dropped, return to IDLE
                            self.current_state = SpellState.IDLE
                            self.chant_timer = 0
                    
                    elif self.current_state == SpellState.ACTIVATED:
                        # Stay in ACTIVATED state while gesture is detected
                        # This allows smooth execution
                        self.pending_spell_center = bbox_center
                    
                    # Update last detection time
                    self.last_hand_detected_time = self.frame_count
                
                else:
                    # No valid feature vector
                    if self.current_state == SpellState.CHANTING:
                        self.current_state = SpellState.IDLE
                        self.chant_timer = 0
            
            else:
                # Hand count is not 2 (could be 0, 1, or >2)
                # Check if we should execute spell (hand lost while in ACTIVATED state)
                if self.current_state == SpellState.ACTIVATED and hand_count < 2:
                    # ACTIVATED -> EXECUTING: Hand lost during activation
                    if self.mp >= self.mp_cost_per_spell:
                        print(f"✨ SPELL EXECUTED: {self.pending_spell_name}!")
                        if self.pending_spell_center:
                            self.trigger_vfx_for_spell(self.pending_spell_name, self.pending_spell_center)
                        self.mp -= self.mp_cost_per_spell
                        self.current_state = SpellState.IDLE
                        self.chant_timer = 0
                    else:
                        print(f"❌ NOT ENOUGH MP! Required: {self.mp_cost_per_spell}, Current: {int(self.mp)}")
                        self.current_state = SpellState.IDLE
                        self.chant_timer = 0
                
                elif self.current_state == SpellState.CHANTING:
                    # Hands lost while chanting
                    self.current_state = SpellState.IDLE
                    self.chant_timer = 0
            
            # --- GAME FRAME RENDERING (Gameplay View) ---
            
            # Draw landmarks only on debug frame
            self.draw_landmarks(debug_frame, results)
            
            # Draw bounding box on both frames
            if bbox:
                min_x, min_y, max_x, max_y = bbox
                
                # Color based on state
                if self.current_state == SpellState.IDLE:
                    bbox_color = (0, 255, 0)  # Green
                elif self.current_state == SpellState.CHANTING:
                    bbox_color = (0, 165, 255)  # Orange
                elif self.current_state == SpellState.ACTIVATED:
                    bbox_color = (0, 255, 255)  # Yellow
                else:
                    bbox_color = (0, 255, 0)  # Green
                
                # Draw bounding box on game frame
                cv2.rectangle(game_frame, (min_x, min_y), (max_x, max_y), bbox_color, 3)
                
                # Draw bounding box on debug frame
                cv2.rectangle(debug_frame, (min_x, min_y), (max_x, max_y), bbox_color, 2)
                
                # Draw progress circle in CHANTING state
                if self.current_state == SpellState.CHANTING:
                    center = ((min_x + max_x) // 2, (min_y + max_y) // 2)
                    radius = max((max_x - min_x), (max_y - min_y)) // 2 + 20
                    progress = self.chant_timer / self.chant_threshold
                    self.draw_progress_circle(game_frame, center, radius, progress, thickness=3)
            
            # Draw VFX effects
            if bbox:
                bbox_center = ((bbox[0] + bbox[2]) // 2, (bbox[1] + bbox[3]) // 2)
                self.vfx_manager.update_and_draw(game_frame, bbox_center)
            elif self.debug_mode:
                self.vfx_manager.update_and_draw(game_frame, self.debug_spell_center)
            else:
                self.vfx_manager.update_and_draw(game_frame, (w // 2, h // 2))
            
            # Draw UI on game frame
            self.draw_status_bars(game_frame, self.hp, self.mp)
            self.draw_gesture_icons(game_frame)
            
            # Draw warnings and debug info on game frame
            self.draw_ui(game_frame, hand_count, show_warning)
            
            # --- DEBUG FRAME RENDERING (Debug Console View) ---
            
            # Draw debug information
            self.draw_debug_info(debug_frame, spell_name if spell_name else "NONE", confidence, fps, hand_count)
            
            # Draw MP cost warning if applicable
            if self.mp < self.mp_cost_per_spell:
                warning_text = f"⚠ LOW MP: Need {self.mp_cost_per_spell} to cast"
                text_size = cv2.getTextSize(warning_text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
                cv2.rectangle(debug_frame, (w - 350, h - 60), (w - 10, h - 10), (0, 0, 255), -1)
                cv2.putText(debug_frame, warning_text, (w - 340, h - 20), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            
            # --- DISPLAY BOTH FRAMES ---
            cv2.imshow("Ignite: Spell Master - Gameplay", game_frame)
            cv2.imshow("Debug Console - AI Recognition", debug_frame)
            
            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            
            # Check if windows are closed
            if cv2.getWindowProperty("Ignite: Spell Master - Gameplay", cv2.WND_PROP_VISIBLE) < 1:
                print("Gameplay window closed. Exiting...")
                break
            if cv2.getWindowProperty("Debug Console - AI Recognition", cv2.WND_PROP_VISIBLE) < 1:
                print("Debug window closed. Exiting...")
                break
            
            # Check debug mode controls first
            if self.handle_debug_input(key):
                continue
            
            # Regular input handling
            if key == ord('q') or key == ord('Q'):
                print("Exiting...")
                break
            elif key == ord('v') or key == ord('V'):
                verbose_mode = not verbose_mode
                status = "ON" if verbose_mode else "OFF"
                print(f"Verbose mode: {status}")
        
        # Cleanup
        self.cap.release()
        cv2.destroyAllWindows()
        self.hands.close()


if __name__ == "__main__":
    recognizer = SpellRecognizer()
    recognizer.run()
