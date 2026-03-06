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
        """Main loop for real-time spell recognition."""
        print("\n" + "="*60)
        print("=== Real-time Spell Recognizer with VFX ===".center(60))
        print("="*60)
        print(f"Confidence threshold: {self.confidence_threshold * 100:.0f}%")
        print(f"VFX Trigger threshold: 80%")
        print(f"Trigger cooldown: {self.trigger_cooldown_frames} frames")
        print(f"Recognized spells: {list(self.vfx_manager.effects.keys())}")
        print("\n📋 Controls:")
        print("  Q: Quit")
        print("  D: Toggle Debug Mode (keyboard spell casting)")
        print("  V: Toggle verbose mode (show all predictions)")
        print("\n🔧 Debug Mode (Press D):")
        print("  1: Cast Fireball (Tiger)")
        print("  2: Cast Ice (Dragon)")
        print("  3: Cast Lightning (Ox)")
        print("="*60 + "\n")
        
        verbose_mode = False
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("Failed to capture frame")
                break
            
            # Increment frame counter
            self.frame_count += 1
            
            # Mirror the frame
            frame = cv2.flip(frame, 1)
            h, w, c = frame.shape
            
            # Convert to RGB for MediaPipe
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(frame_rgb)
            
            # Draw landmarks
            self.draw_landmarks(frame, results)
            
            hand_count = len(results.multi_hand_landmarks) if results.multi_hand_landmarks else 0
            bbox = None
            spell_name = None
            confidence = 0
            show_warning = False
            
            # Track single hand warning
            if hand_count == 1:
                self.single_hand_warning_frames = self.single_hand_warning_duration
                show_warning = True
            elif self.single_hand_warning_frames > 0:
                self.single_hand_warning_frames -= 1
                show_warning = True
            
            if hand_count == 2:
                # Only process when exactly 2 hands are detected
                feature_vector = self.process_frame_data(results, hand_count)
                
                if feature_vector is not None:
                    spell_name, confidence = self.predict_spell(feature_vector)
                    
                    # Log prediction for diagnostics
                    if verbose_mode:
                        print(f"[Frame {self.frame_count}] Predicted: {spell_name if spell_name else 'NO_MATCH'} ({confidence:.1f}%)")
                    
                    # Update last prediction
                    if spell_name is not None:
                        self.last_prediction = spell_name
                        self.last_confidence = confidence
                        self.prediction_hold_frames = 0
                        
                        # Start countdown if confidence is high enough AND not already in countdown
                        if confidence > 80 and not self.countdown_active:
                            bbox = self.get_hand_bounding_box(results, frame.shape)
                            if bbox is not None:
                                bbox_center = ((bbox[0] + bbox[2]) // 2, (bbox[1] + bbox[3]) // 2)
                                self.countdown_active = True
                                self.countdown_frames = 0
                                self.pending_spell_name = spell_name
                                self.pending_spell_center = bbox_center
                                print(f"⏱️ CASTING: {spell_name}... (Confidence: {confidence:.0f}%)")
                    else:
                        # Continue holding last prediction for a few frames
                        if self.last_prediction is not None:
                            self.prediction_hold_frames += 1
                            if self.prediction_hold_frames < self.prediction_hold_count:
                                spell_name = self.last_prediction
                                confidence = self.last_confidence
                            else:
                                self.last_prediction = None
                                self.last_confidence = 0
                    
                    # Get bounding box
                    bbox = self.get_hand_bounding_box(results, frame.shape)
            
            else:
                # Not processing - either 0 or 1 hand detected
                self.last_prediction = None
                self.last_confidence = 0
            
            # Update countdown timer and trigger spell when countdown completes
            if self.countdown_active:
                self.countdown_frames += 1
                if self.countdown_frames >= self.countdown_total:
                    # Countdown complete - trigger the spell
                    print(f"[DEBUG] Countdown completed! pending_spell_name={self.pending_spell_name}, pending_spell_center={self.pending_spell_center}")
                    self.trigger_vfx_for_spell(self.pending_spell_name, self.pending_spell_center)
                    self.countdown_active = False
                    self.countdown_frames = 0
                    self.pending_spell_name = None
                    self.pending_spell_center = None
            
            # Draw bounding box and prediction
            self.draw_bounding_box(frame, bbox, spell_name, confidence)
            
            # Update and draw VFX effects
            # Always render VFX (use debug center if no bbox or in debug mode)
            if bbox is not None:
                bbox_center = ((bbox[0] + bbox[2]) // 2, (bbox[1] + bbox[3]) // 2)
                self.vfx_manager.update_and_draw(frame, bbox_center)
            elif self.debug_mode:
                # In debug mode, render at screen center even without hands
                self.vfx_manager.update_and_draw(frame, self.debug_spell_center)
            else:
                # Normal mode without hands: still update effects (they'll fade out)
                self.vfx_manager.update_and_draw(frame, (w // 2, h // 2))
            
            # Draw UI with warning
            self.draw_ui(frame, hand_count, show_warning)
            
            # Display frame
            cv2.imshow("Real-time Spell Recognizer", frame)
            
            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            
            # Check debug mode controls first
            if self.handle_debug_input(key):
                continue
            
            # Regular input handling
            if key == ord('q') or key == ord('Q'):
                print("Exiting...")
                break
        
        # Cleanup
        self.cap.release()
        cv2.destroyAllWindows()
        self.hands.close()


if __name__ == "__main__":
    recognizer = SpellRecognizer()
    recognizer.run()
