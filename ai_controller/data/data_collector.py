import cv2
import mediapipe as mp
import pandas as pd
import numpy as np
import os
from pathlib import Path
import csv
import time

class GestureDataCollector:
    """
    Two-hand gesture data collector with normalization support.
    
    ╔════════════════════════════════════════════════════════════════════╗
    ║                     NORMALIZATION PIPELINE                         ║
    ╚════════════════════════════════════════════════════════════════════╝
    
    NORMALIZED PATH:
      Raw Landmarks → Smoothing → Translation (to left wrist origin)
                                → Scaling (by palm size) → CSV
    
    RAW PATH (Compare mode):
      Raw Landmarks → Smoothing → CSV (no transformation)
    
    ╔════════════════════════════════════════════════════════════════════╗
    ║                    NORMALIZATION METHODS                           ║
    ╚════════════════════════════════════════════════════════════════════╝
    
    1. GLOBAL REFERENCE POINT
       • Origin: Left hand wrist (Landmark 0)
       • Both hands transformed to same origin
       • Preserves hand-to-hand spatial relationships
       → Function: _process_landmarks_with_smoothing() [Lines 166-208]
    
    2. TRANSLATION
       • Shift all landmarks so left wrist = (0, 0)
       • Formula: rel_x = landmark_x - left_wrist_x
       •          rel_y = landmark_y - left_wrist_y
       → Function: _create_coordinate_row() [Lines 211-230], normalize=True
    
    3. SCALING BY PALM SIZE
       • Palm size = distance from wrist to middle finger MCP (Landmark 9)
       • Formula: palm_size = √((mcp_x - wrist_x)² + (mcp_y - wrist_y)²)
       • Normalization: norm_x = rel_x / palm_size, norm_y = rel_y / palm_size
       • Makes gesture size-invariant
       → Function: _create_coordinate_row() [Lines 211-230], normalize=True
    
    4. SMOOTHING (Exponential Moving Average)
       • Reduces sensor jitter and detection noise
       • Formula: smoothed = 0.3 × current + 0.7 × previous
       • Applied per-hand independently
       → Function: apply_strong_smoothing() [Lines 99-122]
    
    5. STABILITY VALIDATION
       • Requires exactly 2 hands (skip if 0, 1, or 3+)
       • Validates hand count stability (no flickering)
       • Ensures left hand present for reference
       • Division-by-zero protection (palm_size ≥ 0.001)
       → Functions: is_hand_count_stable() [Lines 79-92]
                    _process_landmarks_with_smoothing() [Lines 166-191]
    
    ╔════════════════════════════════════════════════════════════════════╗
    ║                      OUTPUT COMPARISON                             ║
    ╚════════════════════════════════════════════════════════════════════╝
    
    RAW DATA:
      Input:  MediaPipe landmarks (0.0-1.0 normalized to image)
      Output: [Label, x1_L, y1_L, ..., x21_L, y21_L, x1_R, y1_R, ..., x21_R, y21_R]
              (Smoothed only, no coordinate transformation)
    
    NORMALIZED DATA:
      Input:  MediaPipe landmarks (0.0-1.0 normalized to image)
      Output: [Label, x1_L, y1_L, ..., x21_L, y21_L, x1_R, y1_R, ..., x21_R, y21_R]
              (Translated to left_wrist origin + scaled by palm_size)
    
    COMPARE MODE OUTPUT STRUCTURE:
      data/compare/normalize_data/
      └── {gesture_label}/
          ├── normalized_{n}.csv     (Normalized coordinates)
          ├── raw_{n}.csv            (Raw smoothed coordinates)
          └── images_{n}/
              └── frame_001.jpg      (First frame with landmarks drawn)
    """
    
    def __init__(self, mode="normal"):
        """
        Initialize GestureDataCollector.
        
        Args:
            mode: "normal" = standard collection, "compare" = show normalized vs raw side-by-side
        """
        # MediaPipe initialization
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            model_complexity=1,
            max_num_hands=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.4
        )
        
        # Collection mode
        self.mode = mode  # "normal" or "compare"
        
        # Data collection state
        self.current_label = None
        self.recording = False
        self.frame_count = 0
        self.collected_data = []  # Normalized data
        self.collected_data_raw = []  # Raw data (for compare mode)
        self.data_dir = Path(__file__).parent
        self.csv_file = None
        self.csv_file_raw = None
        self.space_pressed_once = False
        
        # Directory paths
        self.csv_output_dir = self.data_dir / "csv"
        self.images_output_dir = self.data_dir / "images"
        if mode == "compare":
            self.compare_output_dir = self.data_dir / "compare" / "normalize_data"
            self.compare_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Ensure directories exist
        self.csv_output_dir.mkdir(exist_ok=True)
        self.images_output_dir.mkdir(exist_ok=True)
        
        # Timer for auto-recording
        self.last_activity_time = time.time()
        self.auto_record_timeout = 10
        self.pause_countdown = False
        
        # Landmark smoothing
        self.smoothing_factor = 0.6
        self.previous_landmarks = {}
        self.previous_hand_count = 0
        self.skipped_frames = 0
        
        # Camera initialization
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
    def get_next_filename(self, label):
        """Generate the next filename for the given label (auto-increment)."""
        existing_files = list(self.csv_output_dir.glob(f"{label}_*.csv"))
        if not existing_files:
            return f"{label}_1.csv"
        
        # Extract numbers from filenames and find max
        numbers = []
        for f in existing_files:
            try:
                num = int(f.stem.split('_')[-1])
                numbers.append(num)
            except ValueError:
                pass
        
        next_num = max(numbers) + 1 if numbers else 1
        return f"{label}_{next_num}.csv"
    
    def count_files_for_label(self, label):
        """Count how many CSV files exist for this label."""
        return len(list(self.csv_output_dir.glob(f"{label}_*.csv")))
    
    def extract_hand_landmarks(self, hand_landmarks):
        """Extract 21 landmarks from a hand, return as list of (x, y) tuples."""
        landmarks = []
        for lm in hand_landmarks.landmark:
            landmarks.append((lm.x, lm.y))
        return landmarks
    
    def is_hand_count_stable(self, current_hand_count, threshold=2):
        """
        Check if hand count is stable. 
        Skip frame if hand count changes drastically (indicates detection instability).
        
        Args:
            current_hand_count: Number of hands detected in current frame
            threshold: Number of consecutive frames with different count before accepting change
        
        Returns:
            True if hand count is stable or acceptable, False if unstable
        """
        # If this is first detection, accept it
        if self.previous_hand_count == 0:
            return True
        
        # If hand count stays same, it's stable
        if current_hand_count == self.previous_hand_count:
            self.previous_hand_count = current_hand_count
            return True
        
        # If hand count changes, it might be unstable - return False to skip this frame
        # This prevents jitter when hands appear/disappear due to detection noise
        return False
    
    def apply_strong_smoothing(self, landmarks_list, hand_id):
        """Apply even stronger smoothing using exponential moving average.
        
        Args:
            landmarks_list: List of (x, y) tuples
            hand_id: Unique identifier for hand (0 or 1)
        
        Returns:
            Smoothed landmarks list
        """
        landmarks_dict = {}
        for i, (x, y) in enumerate(landmarks_list):
            landmarks_dict[f"x{i}"] = x
            landmarks_dict[f"y{i}"] = y
        
        if hand_id not in self.previous_landmarks:
            self.previous_landmarks[hand_id] = landmarks_dict
            return landmarks_list
        
        prev = self.previous_landmarks[hand_id]
        smoothed_dict = {}
        
        # Apply stronger smoothing for overlapping hands (reduce jitter)
        # Lower factor = more stable, higher = more responsive
        alpha = self.smoothing_factor * 0.5  # Make it even smoother for overlapping cases
        
        for i, (x, y) in enumerate(landmarks_list):
            smoothed_x = alpha * x + (1 - alpha) * prev.get(f"x{i}", x)
            smoothed_y = alpha * y + (1 - alpha) * prev.get(f"y{i}", y)
            
            smoothed_dict[f"x{i}"] = smoothed_x
            smoothed_dict[f"y{i}"] = smoothed_y
        
        self.previous_landmarks[hand_id] = smoothed_dict
        
        # Convert back to list of tuples
        smoothed_list = [(smoothed_dict[f"x{i}"], smoothed_dict[f"y{i}"]) for i in range(len(landmarks_list))]
        return smoothed_list
    
    def _process_landmarks_with_smoothing(self, results, hand_id):
        """
        Common landmark extraction and smoothing for both raw and normalized modes.
        
        Returns:
            (left_landmarks, right_landmarks, left_wrist, left_palm_size) or None if unstable
        """
        # Check hand count
        current_hand_count = len(results.multi_hand_landmarks) if results.multi_hand_landmarks else 0
        if current_hand_count != 2 or not self.is_hand_count_stable(current_hand_count):
            self.skipped_frames += 1
            return None
        
        left_landmarks = None
        right_landmarks = None
        left_wrist = None
        left_palm_size = None
        
        # Extract left hand
        if results.multi_hand_landmarks and results.multi_handedness:
            for hand_idx, (hand_landmarks, handedness) in enumerate(
                zip(results.multi_hand_landmarks, results.multi_handedness)
            ):
                hand_label = handedness.classification[0].label
                if hand_label == "Left":
                    landmarks = self.extract_hand_landmarks(hand_landmarks)
                    landmarks = self.apply_strong_smoothing(landmarks, hand_idx)
                    left_landmarks = landmarks
                    left_wrist = landmarks[0]
                    left_palm_size = np.sqrt((landmarks[9][0] - left_wrist[0])**2 + 
                                             (landmarks[9][1] - left_wrist[1])**2)
                    if left_palm_size < 0.001:
                        left_palm_size = 0.001
                    break
            
            # Extract right hand
            if left_wrist is not None and left_palm_size is not None:
                for hand_idx, (hand_landmarks, handedness) in enumerate(
                    zip(results.multi_hand_landmarks, results.multi_handedness)
                ):
                    hand_label = handedness.classification[0].label
                    if hand_label == "Right":
                        landmarks = self.extract_hand_landmarks(hand_landmarks)
                        landmarks = self.apply_strong_smoothing(landmarks, hand_idx)
                        right_landmarks = landmarks
                        break
            else:
                self.skipped_frames += 1
                return None
        
        self.previous_hand_count = current_hand_count
        return (left_landmarks, right_landmarks, left_wrist, left_palm_size)
    
    def _create_coordinate_row(self, landmarks, offset_x, offset_y, palm_size, normalize=True):
        """
        Create coordinate row for left or right hand.
        
        Args:
            landmarks: List of (x, y) tuples
            offset_x, offset_y: Global origin coordinates
            palm_size: Hand scale for normalization
            normalize: If True, apply translation and scaling
        
        Returns:
            List of 42 floats (21 landmarks × 2 coordinates)
        """
        coords = []
        for lx, ly in landmarks:
            if normalize:
                rel_x = lx - offset_x
                rel_y = ly - offset_y
                norm_x = rel_x / palm_size
                norm_y = rel_y / palm_size
            else:
                norm_x = lx
                norm_y = ly
            coords.extend([norm_x, norm_y])
        return coords
    
    def process_frame_data_normalized(self, results, label):
        """
        Process frame with GLOBAL coordinate reference (normalized).
        
        Normalization:
        1. Translate: All points relative to left wrist (0,0)
        2. Scale: Divide by left palm size (distance wrist→middle MCP)
        3. Smoothing: Exponential moving average (alpha=0.3)
        4. Validation: Require exactly 2 hands + stable detection
        
        Returns: Row with 85 columns [Label, ...left_coords, ...right_coords] or None if unstable
        """
        landmark_data = self._process_landmarks_with_smoothing(results, None)
        if landmark_data is None:
            return None
        
        left_landmarks, right_landmarks, left_wrist, left_palm_size = landmark_data
        
        row = [label]
        row.extend(self._create_coordinate_row(left_landmarks, left_wrist[0], left_wrist[1], 
                                               left_palm_size, normalize=True))
        row.extend(self._create_coordinate_row(right_landmarks, left_wrist[0], left_wrist[1], 
                                               left_palm_size, normalize=True))
        return row
    
    def process_frame_data_raw(self, results, label):
        """
        Process frame with RAW coordinates (no normalization, only smoothing).
        
        Returns: Row with 85 columns [Label, ...left_coords_raw, ...right_coords_raw] or None if unstable
        """
        landmark_data = self._process_landmarks_with_smoothing(results, None)
        if landmark_data is None:
            return None
        
        left_landmarks, right_landmarks, _, _ = landmark_data
        
        row = [label]
        row.extend(self._create_coordinate_row(left_landmarks, 0, 0, 1.0, normalize=False))
        row.extend(self._create_coordinate_row(right_landmarks, 0, 0, 1.0, normalize=False))
        return row
    
    def process_frame_data(self, results, label):
        """Legacy method - redirects to normalized version."""
        return self.process_frame_data_normalized(results, label)
    
    def start_recording(self):
        """Start recording mode."""
        if self.current_label is None:
            print("Error: No label set. Press 'N' to set a label first.")
            return
        
        if self.recording:
            return
        
        self.recording = True
        self.frame_count = 0
        self.collected_data = []
        self.collected_data_raw = []
        self.skipped_frames = 0
        
        # Create CSV files
        if self.mode == "compare":
            # Save to compare folder
            label_folder = self.compare_output_dir / self.current_label
            label_folder.mkdir(parents=True, exist_ok=True)
            
            next_num = len(list(label_folder.glob("normalized_*.csv"))) + 1
            self.csv_file = label_folder / f"normalized_{next_num}.csv"
            self.csv_file_raw = label_folder / f"raw_{next_num}.csv"
            
            # Image folder
            self.image_label_dir = label_folder / f"images_{next_num}"
            self.image_label_dir.mkdir(exist_ok=True)
            
            print(f"[COMPARE MODE] Recording {self.current_label} #{next_num}")
            print(f"  Normalized CSV: {self.csv_file.name}")
            print(f"  Raw CSV: {self.csv_file_raw.name}")
        else:
            # Normal mode
            filename = self.get_next_filename(self.current_label)
            self.csv_file = self.csv_output_dir / filename
            
            self.image_label_dir = self.images_output_dir / filename.replace('.csv', '')
            self.image_label_dir.mkdir(exist_ok=True)
            
            print(f"Recording started. File: {filename}")
    
    def stop_recording(self):
        """Stop recording and save data to CSV."""
        if not self.recording or self.csv_file is None:
            return
        
        # Column names
        columns = ["Label"]
        for i in range(1, 22):
            columns.append(f"x{i}_L")
            columns.append(f"y{i}_L")
        for i in range(1, 22):
            columns.append(f"x{i}_R")
            columns.append(f"y{i}_R")
        
        # Save normalized data
        df = pd.DataFrame(self.collected_data, columns=columns)
        df.to_csv(self.csv_file, index=False)
        print(f"✓ Saved {len(self.collected_data)} frames → {self.csv_file.name}")
        
        # Save raw data (if compare mode)
        if self.mode == "compare" and self.csv_file_raw is not None:
            df_raw = pd.DataFrame(self.collected_data_raw, columns=columns)
            df_raw.to_csv(self.csv_file_raw, index=False)
            print(f"✓ Saved {len(self.collected_data_raw)} frames → {self.csv_file_raw.name}")
        
        if self.skipped_frames > 0:
            print(f"  (Skipped {self.skipped_frames} unstable frames)")
        
        self.recording = False
        self.frame_count = 0
        self.skipped_frames = 0
        self.collected_data = []
        self.collected_data_raw = []
        self.csv_file = None
        self.csv_file_raw = None
    
    def set_new_label(self):
        """Prompt user to enter a new label."""
        label = input("Enter gesture label (e.g., 'Tiger'): ").strip()
        if label:
            self.current_label = label
            print(f"Label set to: {self.current_label}")
        else:
            print("Invalid label. Try again.")
    
    def draw_wrist_connection(self, frame, results):
        """Draw a line connecting both wrists to visualize hand-to-hand distance."""
        if results.multi_hand_landmarks and results.multi_handedness and len(results.multi_hand_landmarks) == 2:
            # Get wrist positions (landmark 0)
            wrists = []
            for hand_landmarks in results.multi_hand_landmarks:
                wrist = hand_landmarks.landmark[0]
                h, w, _ = frame.shape
                x = int(wrist.x * w)
                y = int(wrist.y * h)
                wrists.append((x, y))
            
            # Draw line between wrists
            if len(wrists) == 2:
                cv2.line(frame, wrists[0], wrists[1], (0, 165, 255), 3)  # Orange line
                
                # Draw circles at wrists
                cv2.circle(frame, wrists[0], 8, (0, 255, 0), -1)  # Green for left
                cv2.circle(frame, wrists[1], 8, (255, 0, 0), -1)  # Blue for right
                
                # Calculate and display distance
                dist = np.sqrt((wrists[0][0] - wrists[1][0])**2 + (wrists[0][1] - wrists[1][1])**2)
                mid_x = (wrists[0][0] + wrists[1][0]) // 2
                mid_y = (wrists[0][1] + wrists[1][1]) // 2
                cv2.putText(frame, f"Distance: {dist:.0f}px", (mid_x - 50, mid_y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
    
    def draw_landmarks(self, frame, results):
        """Draw hand landmarks and connections on the frame."""
        # Draw wrist connection line
        self.draw_wrist_connection(frame, results)
        
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Draw all landmarks and connections
                self.mp_drawing.draw_landmarks(
                    frame,
                    hand_landmarks,
                    self.mp_hands.HAND_CONNECTIONS,
                    self.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                    self.mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=2)
                )
    
    def save_frame_with_markers(self, frame):
        """Save only the first frame of the gesture with drawn markers to image folder."""
        if not self.recording or not hasattr(self, 'image_label_dir'):
            return
        
        # Only save the first frame
        if self.frame_count == 1:
            image_filename = f"frame_001.jpg"
            image_path = self.image_label_dir / image_filename
            
            # Save image
            cv2.imwrite(str(image_path), frame)
            print(f"Saved first frame to {image_filename}")
    
    def draw_ui(self, frame, is_raw=False):
        """Draw UI text on the frame."""
        h, w, _ = frame.shape
        
        mode_label = "[RAW]" if is_raw else "[NORMALIZED]"
        label_text = f"{mode_label} {self.current_label if self.current_label else 'NONE'}"
        cv2.putText(frame, label_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        # Status
        if self.recording:
            status_text = f"RECORDING ({self.frame_count}/200)"
            color = (0, 0, 255)
        else:
            elapsed = time.time() - self.last_activity_time
            countdown = max(0, self.auto_record_timeout - elapsed)
            status_text = f"READY (auto-record in {countdown:.1f}s)"
            color = (0, 255, 0)
        
        cv2.putText(frame, status_text, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        
        # Instructions (right side)
        instructions = [
            "S: Start Recording",
            "N: New Label",
            "P: Pause & Reset",
            "Q: Quit"
        ]
        
        for i, instruction in enumerate(instructions):
            cv2.putText(
                frame,
                instruction,
                (w - 250, 30 + i * 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (200, 200, 200),
                1
            )

    
    def run(self):
        """Main loop for the data collector."""
        print(f"\n=== Gesture Data Collector [{self.mode.upper()} MODE] ===")
        self.set_new_label()
        self.last_activity_time = time.time()
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("Failed to capture frame")
                break
            
            frame = cv2.flip(frame, 1)
            h, w, c = frame.shape
            
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(frame_rgb)
            
            # Main processing
            if self.recording and results.multi_hand_landmarks:
                # Process normalized data
                row_norm = self.process_frame_data_normalized(results, self.current_label)
                if row_norm is not None:
                    self.collected_data.append(row_norm)
                    self.frame_count += 1
                    
                    # In compare mode, also process raw data
                    if self.mode == "compare":
                        row_raw = self.process_frame_data_raw(results, self.current_label)
                        if row_raw is not None:
                            self.collected_data_raw.append(row_raw)
                            
                            # Save frames side-by-side
                            if self.frame_count == 1:
                                self.save_compare_frames(frame, results)
                    
                    # Stop recording after 200 frames
                    if self.frame_count >= 200:
                        self.stop_recording()
                        self.last_activity_time = time.time()
            
            # Auto-record if timeout
            if not self.recording:
                elapsed = time.time() - self.last_activity_time
                if not self.pause_countdown and elapsed >= self.auto_record_timeout:
                    self.start_recording()
                    self.last_activity_time = time.time()
            
            # Prepare display
            display_frame = frame.copy()
            self.draw_landmarks(display_frame, results)
            if self.mode == "compare":
                self.draw_ui(display_frame, is_raw=False)
                cv2.putText(display_frame, "[Preview - Normalized will be recorded]", 
                           (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
            else:
                self.draw_ui(display_frame, is_raw=False)
            
            cv2.imshow("Gesture Data Collector", display_frame)
            
            # Handle keyboard
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q') or key == ord('Q'):
                print("Exiting...")
                if self.recording:
                    self.stop_recording()
                break
            elif key == ord('s') or key == ord('S'):
                if not self.recording:
                    self.start_recording()
                self.last_activity_time = time.time()
            elif key == ord('n') or key == ord('N'):
                if self.recording:
                    self.stop_recording()
                self.set_new_label()
                self.last_activity_time = time.time()
                self.space_pressed_once = False
            elif key == ord('+') or key == ord('='):
                self.smoothing_factor = min(1.0, self.smoothing_factor + 0.05)
                print(f"Smoothing increased to: {self.smoothing_factor:.2f}")
            elif key == ord('-') or key == ord('_'):
                self.smoothing_factor = max(0.0, self.smoothing_factor - 0.05)
                print(f"Smoothing decreased to: {self.smoothing_factor:.2f}")
            elif key == ord('p') or key == ord('P'):
                if self.recording:
                    self.stop_recording()
                self.pause_countdown = not self.pause_countdown
                self.space_pressed_once = False
        
        # Cleanup
        self.cap.release()
        cv2.destroyAllWindows()
        self.hands.close()
    
    def save_compare_frames(self, frame, results):
        """Save frame images for both normalized and raw modes."""
        if not self.recording or not hasattr(self, 'image_label_dir'):
            return
        
        if self.frame_count == 1:
            image_filename = "frame_001.jpg"
            image_path = self.image_label_dir / image_filename
            cv2.imwrite(str(image_path), frame)
            print(f"✓ Frame saved: {image_filename}")


if __name__ == "__main__":
    import sys
    
    print("\n╔════════════════════════════════════════════════════════════════╗")
    print("║         Gesture Data Collector - Normalization Modes          ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    print("\n[NORMAL MODE (default)]")
    print("  - Collects normalized data only")
    print("  - Output: data/csv/{label}_{num}.csv")
    print("  - Usage: python data_collector.py")
    
    print("\n[COMPARE MODE]")
    print("  - Collects both normalized and raw data side-by-side")
    print("  - Output: data/compare/normalize_data/{label}/{normalized,raw}_{num}.csv")
    print("  - Usage: python data_collector.py --compare")
    
    print("\n" + "="*70)
    print("NORMALIZATION TECHNIQUES USED:")
    print("="*70)
    print("""
    1. GLOBAL COORDINATE REFERENCE
       - Origin: Left hand wrist (Landmark 0) = (0, 0)
       - All 42 landmarks (both hands) use same origin
       - Preserves hand-to-hand spatial relationships (gesture volume/shape)
       
    2. TRANSLATION
       - Formula: rel_x = landmark_x - left_wrist_x
       - Formula: rel_y = landmark_y - left_wrist_y
       - Relative position instead of absolute screen coordinates
       
    3. SCALE NORMALIZATION
       - Palm size reference: distance from wrist to middle finger MCP (Landmark 9)
       - Formula: palm_size = √((palm_x - wrist_x)² + (palm_y - wrist_y)²)
       - Normalized coords: norm_x = rel_x / palm_size
       - Normalized coords: norm_y = rel_y / palm_size
       - Makes gesture size-invariant (large/small hand same data)
       
    4. SMOOTHING (Exponential Moving Average)
       - Reduces sensor jitter and detection noise
       - Formula: smoothed = α × current + (1-α) × previous
       - Alpha value: 0.3 (70% weight to previous frame for stability)
       - Applied per-hand independently
       
    5. STABILITY VALIDATION
       - Requires exactly 2 hands detected (not 0, 1, or 3+)
       - Skips frames where hand count changes (prevents detection flicker)
       - Validates left hand present before using as reference
       - Division-by-zero protection (palm_size minimum = 0.001)
    
    SUMMARY:
    ✓ Raw data: 42 normalized image coordinates (0.0-1.0 range) + smoothing
    ✓ Normalized: Translation (origin at left wrist) + scaling (by palm size)
    ✓ Result: Pose-relative, scale-invariant gesture representation
    """)
    print("="*70)
    
    # Choose mode
    mode = "compare" if "--compare" in sys.argv else "normal"
    collector = GestureDataCollector(mode=mode)
    print(f"\n[{mode.upper()} MODE ACTIVATED]\n")
    collector.run()
