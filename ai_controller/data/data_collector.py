import cv2
import mediapipe as mp
import pandas as pd
import numpy as np
import os
from pathlib import Path
import csv
import time

class GestureDataCollector:
    def __init__(self):
        # MediaPipe initialization
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            model_complexity=1,  # Higher accuracy for interlaced fingers
            max_num_hands=2,
            min_detection_confidence=0.5,  # Lower for better detection of overlapping hands
            min_tracking_confidence=0.4    # Lower for better tracking of close/overlapping hands
        )
        
        # Data collection state
        self.current_label = None
        self.recording = False
        self.frame_count = 0
        self.collected_data = []
        self.data_dir = Path(__file__).parent  # data/ directory
        self.csv_file = None
        self.csv_writer = None
        
        # Directory paths
        self.csv_output_dir = self.data_dir / "csv"
        self.images_output_dir = self.data_dir / "images"
        
        # Ensure directories exist
        self.csv_output_dir.mkdir(exist_ok=True)
        self.images_output_dir.mkdir(exist_ok=True)
        
        # Timer for auto-recording
        self.last_activity_time = time.time()
        self.auto_record_timeout = 10  # 10 seconds
        self.pause_countdown = False  # Pause/resume countdown
        
        # Landmark smoothing (to reduce jitter)
        self.smoothing_factor = 0.6  # Range: 0-1 (lower = more smooth, higher = more responsive)
        self.previous_landmarks = {}  # Store previous frame landmarks
        self.previous_hand_count = 0  # Track previous hand count for stability
        self.skipped_frames = 0  # Count skipped frames
        
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
    
    def process_frame_data(self, results, label):
        """
        Process frame data with GLOBAL Coordinate Reference.
        Uses LEFT hand wrist (Landmark 0) as origin (0,0) for ALL 42 landmarks of both hands.
        
        Returns a list with 85 columns: [Label, x1_L, y1_L, ..., x21_L, y21_L, x1_R, y1_R, ..., x21_R, y21_R]
        
        IMPORTANT: Only accepts frames when BOTH hands are detected.
        This preserves hand-to-hand spatial relationships (gesture shape/volume).
        """
        row = [label]
        
        # Check hand count stability
        current_hand_count = len(results.multi_hand_landmarks) if results.multi_hand_landmarks else 0
        
        # REQUIREMENT: Only accept frames with EXACTLY 2 hands detected
        if current_hand_count != 2:
            self.skipped_frames += 1
            return None  # Signal to skip this frame
        
        # Check if hand count is stable (not jumping)
        if not self.is_hand_count_stable(current_hand_count):
            self.skipped_frames += 1
            return None  # Signal to skip this frame
        
        # Initialize all 42 coordinates with 0
        left_coords = [0] * 42
        right_coords = [0] * 42
        
        # Store left hand wrist for global reference
        left_wrist_x = None
        left_wrist_y = None
        left_palm_size = None
        
        if results.multi_hand_landmarks and results.multi_handedness:
            # First pass: identify and process left hand to establish global reference
            for hand_idx, (hand_landmarks, handedness) in enumerate(
                zip(results.multi_hand_landmarks, results.multi_handedness)
            ):
                hand_label = handedness.classification[0].label
                
                if hand_label == "Left":
                    # Extract landmarks for left hand
                    landmarks = self.extract_hand_landmarks(hand_landmarks)
                    landmarks = self.apply_strong_smoothing(landmarks, hand_idx)
                    
                    # Establish global reference: left wrist is origin (0,0)
                    left_wrist_x, left_wrist_y = landmarks[0]
                    
                    # Get palm size (distance between wrist and middle finger MCP) for normalization
                    palm_x, palm_y = landmarks[9]
                    left_palm_size = np.sqrt((palm_x - left_wrist_x) ** 2 + (palm_y - left_wrist_y) ** 2)
                    
                    # Prevent division by zero
                    if left_palm_size < 0.001:
                        left_palm_size = 0.001
                    
                    # Process LEFT hand coordinates relative to LEFT wrist
                    processed_coords = []
                    for i, (lx, ly) in enumerate(landmarks):
                        # Relative to left wrist (global origin)
                        rel_x = lx - left_wrist_x
                        rel_y = ly - left_wrist_y
                        
                        # Normalize by left palm size
                        norm_x = rel_x / left_palm_size
                        norm_y = rel_y / left_palm_size
                        
                        processed_coords.append(norm_x)
                        processed_coords.append(norm_y)
                    
                    left_coords = processed_coords
            
            # Second pass: process right hand using the same global reference
            for hand_idx, (hand_landmarks, handedness) in enumerate(
                zip(results.multi_hand_landmarks, results.multi_handedness)
            ):
                hand_label = handedness.classification[0].label
                
                if hand_label == "Right":
                    # Extract landmarks for right hand
                    landmarks = self.extract_hand_landmarks(hand_landmarks)
                    landmarks = self.apply_strong_smoothing(landmarks, hand_idx)
                    
                    # Process RIGHT hand coordinates relative to LEFT wrist (global origin)
                    processed_coords = []
                    for i, (lx, ly) in enumerate(landmarks):
                        # Relative to left wrist (global origin, NOT to right wrist)
                        rel_x = lx - left_wrist_x
                        rel_y = ly - left_wrist_y
                        
                        # Normalize by left palm size
                        norm_x = rel_x / left_palm_size
                        norm_y = rel_y / left_palm_size
                        
                        processed_coords.append(norm_x)
                        processed_coords.append(norm_y)
                    
                    right_coords = processed_coords
        
        # Combine all coordinates
        row.extend(left_coords)
        row.extend(right_coords)
        
        self.previous_hand_count = current_hand_count
        return row
    
    def start_recording(self):
        """Start recording mode."""
        if self.current_label is None:
            print("Error: No label set. Press 'N' to set a label first.")
            return
        
        self.recording = True
        self.frame_count = 0
        self.collected_data = []
        
        # Create CSV file
        filename = self.get_next_filename(self.current_label)
        self.csv_file = self.csv_output_dir / filename
        
        # Create corresponding image folder
        self.image_label_dir = self.images_output_dir / filename.replace('.csv', '')
        self.image_label_dir.mkdir(exist_ok=True)
        
        print(f"Recording started. File: {filename}")
        print(f"Images folder: {self.image_label_dir.name}")
    
    def stop_recording(self):
        """Stop recording and save data to CSV."""
        if self.csv_file is None:
            return
        
        # Create column names: [Label, x1_L, y1_L, ..., x21_L, y21_L, x1_R, y1_R, ..., x21_R, y21_R]
        columns = ["Label"]
        
        # Left hand
        for i in range(1, 22):
            columns.append(f"x{i}_L")
            columns.append(f"y{i}_L")
        
        # Right hand
        for i in range(1, 22):
            columns.append(f"x{i}_R")
            columns.append(f"y{i}_R")
        
        # Save to CSV
        df = pd.DataFrame(self.collected_data, columns=columns)
        df.to_csv(self.csv_file, index=False)
        
        print(f"Recording stopped. Saved {len(self.collected_data)} frames to {self.csv_file.name}")
        print(f"(Skipped {self.skipped_frames} unstable frames due to hand detection jitter)")
        
        self.recording = False
        self.frame_count = 0
        self.skipped_frames = 0
        self.collected_data = []
        self.csv_file = None
    
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
    
    def draw_ui(self, frame):
        """Draw UI text on the frame."""
        h, w, _ = frame.shape
        
        # Current label
        label_text = f"Label: {self.current_label if self.current_label else 'NONE'}"
        cv2.putText(frame, label_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        # Status
        if self.recording:
            status_text = f"RECORDING ({self.frame_count}/200)"
            color = (0, 0, 255)  # Red
        else:
            # Show countdown to auto-record
            elapsed = time.time() - self.last_activity_time
            countdown = max(0, self.auto_record_timeout - elapsed)
            
            if self.pause_countdown:
                status_text = f"PAUSED (countdown frozen)"
                color = (0, 165, 255)  # Orange
            else:
                status_text = f"READY (auto-record in {countdown:.1f}s)"
                color = (0, 255, 0)  # Green
        
        cv2.putText(frame, status_text, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        
        # File count for current label
        if self.current_label:
            file_count = self.count_files_for_label(self.current_label)
            count_text = f"Files: {file_count}"
            cv2.putText(frame, count_text, (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        # Smoothing info
        smooth_text = f"Smoothing: {self.smoothing_factor:.1f}"
        cv2.putText(frame, smooth_text, (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 0), 1)
        
        # Stability info when recording
        if self.recording and self.skipped_frames > 0:
            stability_text = f"Skipped: {self.skipped_frames}"
            cv2.putText(frame, stability_text, (10, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 1)
        
        # Instructions
        instructions = [
            "S: Start Recording",
            "N: New Label",
            "+/-: Adjust Smoothing",
            "P: Pause Countdown",
            "Q: Quit"
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
    
    def run(self):
        """Main loop for the data collector."""
        print("\n=== Gesture Data Collector ===")
        self.set_new_label()
        self.last_activity_time = time.time()  # Start timer
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("Failed to capture frame")
                break
            
            # Mirror the frame
            frame = cv2.flip(frame, 1)
            h, w, c = frame.shape
            
            # Convert to RGB for MediaPipe
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(frame_rgb)
            
            # Draw landmarks
            self.draw_landmarks(frame, results)
            
            # Process frame if recording
            if self.recording and results.multi_hand_landmarks:
                row_data = self.process_frame_data(results, self.current_label)
                
                # Skip frame if detection was unstable (hand count jumping)
                if row_data is None:
                    continue
                
                self.collected_data.append(row_data)
                self.frame_count += 1
                
                # Save frame with markers
                self.save_frame_with_markers(frame)
                
                # Stop recording after 200 frames
                if self.frame_count >= 200:
                    self.stop_recording()
                    self.last_activity_time = time.time()  # Reset timer after recording
            
            # Auto-record if 10 seconds have passed without activity
            if not self.recording:
                elapsed = time.time() - self.last_activity_time
                if not self.pause_countdown and elapsed >= self.auto_record_timeout:
                    self.start_recording()
                    self.last_activity_time = time.time()
            
            # Draw UI
            self.draw_ui(frame)
            
            # Display frame
            cv2.imshow("Gesture Data Collector", frame)
            
            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q') or key == ord('Q'):
                print("Exiting...")
                if self.recording:
                    self.stop_recording()
                break
            elif key == ord('s') or key == ord('S'):
                if not self.recording:
                    self.start_recording()
                self.last_activity_time = time.time()  # Reset timer
            elif key == ord('n') or key == ord('N'):
                if self.recording:
                    self.stop_recording()
                self.set_new_label()
                self.last_activity_time = time.time()  # Reset timer
            elif key == ord('+') or key == ord('='):
                # Increase smoothing
                self.smoothing_factor = min(1.0, self.smoothing_factor + 0.05)
                print(f"Smoothing increased to: {self.smoothing_factor:.2f}")
            elif key == ord('-') or key == ord('_'):
                # Decrease smoothing
                self.smoothing_factor = max(0.0, self.smoothing_factor - 0.05)
                print(f"Smoothing decreased to: {self.smoothing_factor:.2f}")
            elif key == ord('p') or key == ord('P'):
                # Pause/resume countdown
                self.pause_countdown = not self.pause_countdown
                if self.pause_countdown:
                    print("Countdown PAUSED - adjust and press P to resume")
                else:
                    print("Countdown RESUMED - timer reset")
                    self.last_activity_time = time.time()
        
        # Cleanup
        self.cap.release()
        cv2.destroyAllWindows()
        self.hands.close()


if __name__ == "__main__":
    collector = GestureDataCollector()
    collector.run()
