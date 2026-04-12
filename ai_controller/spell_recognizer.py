#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gesture Recognition Module - Simplified for Pure Hand Gesture Recognition
Detects hand gestures using MediaPipe and classifies them using a trained ML model
"""

import cv2
import mediapipe as mp
import joblib
import numpy as np
from pathlib import Path
import time
import warnings
import sys
import argparse

# Suppress warnings
warnings.filterwarnings('ignore', category=UserWarning, module='sklearn')
warnings.filterwarnings('ignore', category=UserWarning, module='google.protobuf')


class SpellRecognizer:
    """Simple gesture recognizer using MediaPipe hands and ML model"""
    
    def __init__(self, model_path=None, skip_camera=False):
        """Initialize the gesture recognizer with trained model.
        
        Args:
            model_path: Path to ML model
            skip_camera: If True, don't initialize camera (testing mode)
        """
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
            print(f"[+] Model loaded successfully from {model_path}")
            self.model_classes_ = self.model.classes_
            print(f"[+] Recognized gestures: {list(self.model_classes_)}")
        except FileNotFoundError:
            print(f"[!] Error: Model file not found at {model_path}")
            raise
        
        # Configuration
        self.confidence_threshold = 0.90  # 90% confidence threshold
        
        self.previous_hand_count = 0
        self.skipped_frames = 0
        
        # Camera initialization
        self.cap = None
        self.camera_available = False
        
        if not skip_camera:
            try:
                self.cap = cv2.VideoCapture(0)
                if self.cap.isOpened():
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                    self.camera_available = True
                    print("[+] Camera initialized successfully")
                else:
                    print("[!] Warning: Camera not available (will run in testing mode)")
                    self.cap = None
            except Exception as e:
                print(f"[!] Warning: Camera initialization failed: {e}")
                self.cap = None
        
        # Tracking
        self.frame_count = 0
        self.last_prediction = None
        self.last_confidence = 0
    
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
    
    def process_frame_data(self, results, hand_count):
        """
        Process frame data and return feature vector for prediction.
        
        IMPORTANT: Only processes when exactly 2 hands are detected.
        Returns feature vector if valid, None otherwise
        """
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
                
                # Check if left hand was found before processing right hand
                if left_wrist_x is None or left_palm_size is None:
                    self.skipped_frames += 1
                    return None
                
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
    
    def predict_gesture(self, feature_vector):
        """
        Predict gesture from feature vector.
        
        Returns: (gesture_name, confidence_percentage) or (None, 0) if below threshold
        """
        if feature_vector is None:
            return None, 0
        
        try:
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
            print(f"[!] Error during prediction: {e}")
            return None, 0
    
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
    
    def draw_info(self, frame, hand_count, gesture_name, confidence, fps):
        """Draw gesture recognition information on frame."""
        h, w, _ = frame.shape
        
        # Hand count
        hand_color = (0, 255, 0) if hand_count == 2 else (0, 165, 255)
        cv2.putText(frame, f"Hands: {hand_count}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, hand_color, 2)
        
        # Gesture prediction
        if gesture_name:
            pred_text = f"Recognized: {gesture_name} ({confidence:.1f}%)"
            pred_color = (0, 255, 0) if confidence >= 75 else (0, 165, 255)
        else:
            pred_text = "Recognized: NONE"
            pred_color = (100, 100, 100)
        
        cv2.putText(frame, pred_text, (10, 70), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, pred_color, 2)
        
        # FPS
        cv2.putText(frame, f"FPS: {fps:.1f}", (10, 110), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
        
        # Instructions
        cv2.putText(frame, "Q: Quit", (w - 150, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        cv2.putText(frame, "Confidence threshold: 75%", (w - 250, 70), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
    
    def run(self):
        """Main loop for real-time gesture recognition."""
        try:
            print("\n" + "="*60)
            print("Gesture Recognition Display".center(60))
            print("="*60)
            print(f"Confidence threshold: {self.confidence_threshold * 100:.0f}%")
            print(f"Recognized gestures: {list(self.model_classes_)}")
            print("\nControls:")
            print("  Q: Quit")
            print("="*60 + "\n")
            
            # Check if camera is available
            if not self.camera_available or self.cap is None:
                print("[!] Camera not available!")
                print("[*] Options:")
                print("    1. Check if camera is connected")
                print("    2. Check if another application is using the camera")
                print("    3. Use --no-camera flag for testing mode")
                return
            
            # Create window
            print("[*] Creating OpenCV window...")
            cv2.namedWindow("Hand Recognition - Ignite: Spell Master", cv2.WINDOW_NORMAL)
            print("[+] Window created successfully")
            
            start_time = time.time()
            frame_count = 0
            
            print("[*] Starting main recognition loop...")
            print("[+] Hand Recognition window active (Press 'Q' to quit)\n")
            
            while True:
                try:
                    # Capture frame
                    ret, frame = self.cap.read()
                    if not ret:
                        print("[!] Failed to capture frame")
                        break
                    
                    frame_count += 1
                    self.frame_count += 1
                    
                    # Mirror the frame
                    frame = cv2.flip(frame, 1)
                    h, w, c = frame.shape
                    
                    # Calculate FPS
                    elapsed_time = time.time() - start_time
                    fps = frame_count / elapsed_time if elapsed_time > 0 else 0
                    
                    # Convert to RGB for MediaPipe
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    results = self.hands.process(frame_rgb)
                    
                    # Extract data
                    hand_count = len(results.multi_hand_landmarks) if results.multi_hand_landmarks else 0
                    gesture_name = None
                    confidence = 0
                    
                    # Process hand data and predict gesture
                    if hand_count == 2:
                        feature_vector = self.process_frame_data(results, hand_count)
                        
                        if feature_vector is not None:
                            gesture_name, confidence = self.predict_gesture(feature_vector)
                            
                            if gesture_name:
                                self.last_prediction = gesture_name
                                self.last_confidence = confidence
                    
                    # Draw landmarks
                    self.draw_landmarks(frame, results)
                    
                    # Draw info
                    self.draw_info(frame, hand_count, gesture_name, confidence, fps)
                    
                    # Display frame
                    cv2.imshow("Hand Recognition - Ignite: Spell Master", frame)
                    
                    # Check if window is closed
                    if cv2.getWindowProperty("Hand Recognition - Ignite: Spell Master", cv2.WND_PROP_VISIBLE) < 1:
                        print("[*] Hand Recognition Display closed")
                        break
                    
                    # Handle keyboard input
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q') or key == ord('Q'):
                        print("[*] User pressed Q to quit")
                        break
                
                except Exception as e:
                    print(f"[!] Error in main loop: {type(e).__name__}: {e}")
                    import traceback
                    traceback.print_exc()
                    break
            
            print("[*] Exiting main loop")
        
        except Exception as e:
            print(f"[!] Fatal error in run(): {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            # Cleanup
            print("[*] Cleaning up resources...")
            try:
                if self.cap is not None:
                    self.cap.release()
                    print("[+] Camera released")
            except:
                pass
            
            try:
                cv2.destroyAllWindows()
                print("[+] OpenCV windows closed")
            except:
                pass
            
            try:
                self.hands.close()
                print("[+] MediaPipe hands closed")
            except:
                pass
            
            print("[*] Recognition complete")


if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Ignite: Spell Master - Gesture Recognition System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python spell_recognizer.py              # Normal mode (requires camera)
  python spell_recognizer.py --no-camera  # Testing mode (no camera needed)
  python spell_recognizer.py --help       # Show this help message
        """
    )
    
    parser.add_argument(
        '--no-camera',
        action='store_true',
        help='Run in testing mode without camera'
    )
    
    parser.add_argument(
        '--model',
        type=str,
        default=None,
        help='Path to ML model file'
    )
    
    args = parser.parse_args()
    
    try:
        print("\n" + "="*70)
        print("Ignite: Spell Master - Gesture Recognition System".center(70))
        print("="*70)
        
        print("\n[*] Initializing gesture recognizer...")
        recognizer = SpellRecognizer(model_path=args.model, skip_camera=args.no_camera)
        print("[+] Recognizer initialized successfully\n")
        
        recognizer.run()
    
    except Exception as e:
        print(f"\n[!] Fatal error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        print("\nPlease check:")
        print("  1. Camera is connected and not in use by another application")
        print("  2. Model file exists: e:\\SpellMaster\\ai_controller\\data\\models\\best_spell_model.pkl")
        print("  3. MediaPipe and OpenCV are correctly installed")
        print("\nTip: Use --no-camera flag for testing without camera:")
        print("  python spell_recognizer.py --no-camera")
        input("\nPress Enter to exit...")


