"""
AI Module - Gesture Recognition AI Handler
Manages model loading and MediaPipe hand detection initialization
Provides frame processing and spell prediction
"""

import joblib
import mediapipe as mp
import numpy as np
import cv2
import warnings
from pathlib import Path
from config import (
    MODEL_PATH,
    MIN_DETECTION_CONFIDENCE,
    MIN_TRACKING_CONFIDENCE,
    MEDIAPIPE_MODEL_COMPLEXITY,
    CONFIDENCE_THRESHOLD,
)

# Suppress warnings
warnings.filterwarnings('ignore', category=UserWarning, module='sklearn')
warnings.filterwarnings('ignore', category=UserWarning, module='google.protobuf')


class GestureAI:
    """AI handler for gesture recognition using MediaPipe and XGBoost model."""
    
    def __init__(self, model_path=None, debug=False):
        """
        Initialize GestureAI with trained model and MediaPipe Hands.
        
        Args:
            model_path: Path to trained XGBoost model (.pkl file)
                       If None, uses default from config.MODEL_PATH
            debug: Enable debug logging (optional)
        
        Raises:
            FileNotFoundError: If model file not found
        """
        # Debug flag
        self.debug = bool(debug)
        
        # Set model path
        if model_path is None:
            model_path = MODEL_PATH
        else:
            model_path = Path(model_path)
        
        model_path = Path(model_path)
        
        # Load trained model
        self._load_model(model_path)
        
        # Initialize MediaPipe
        self._initialize_mediapipe()
    
    def _load_model(self, model_path):
        """
        Load XGBoost model from file.
        
        Args:
            model_path: Path to .pkl model file
        
        Raises:
            FileNotFoundError: If model file not found
        """
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")
        
        try:
            self.model = joblib.load(str(model_path))
            self.model_classes = self.model.classes_
            print(f"✓ Model loaded: {model_path.name}")
            print(f"  Recognized spells: {list(self.model_classes)}")
        except Exception as e:
            print(f"✗ Failed to load model: {e}")
            raise
    
    def _initialize_mediapipe(self):
        """Initialize MediaPipe Hands for hand detection."""
        # Get MediaPipe solutions
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        
        # Create Hands detector with configuration
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            model_complexity=MEDIAPIPE_MODEL_COMPLEXITY,
            max_num_hands=2,
            min_detection_confidence=MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=MIN_TRACKING_CONFIDENCE
        )
        
        print(f"✓ MediaPipe Hands initialized")
        print(f"  Model complexity: {MEDIAPIPE_MODEL_COMPLEXITY}")
        print(f"  Detection confidence: {MIN_DETECTION_CONFIDENCE}")
        print(f"  Tracking confidence: {MIN_TRACKING_CONFIDENCE}")
    
    def predict(self, frame):
        """
        Process frame and predict spell from hand gestures.
        
        Extracts hand landmarks, uses left wrist as global reference,
        normalizes by palm size, and returns spell prediction.
        
        Args:
            frame: OpenCV frame (BGR format)
        
        Returns:
            Tuple of (spell_name, confidence) or (None, 0) if prediction fails
        """
        # Convert BGR to RGB for MediaPipe
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process frame with MediaPipe
        results = self.hands.process(frame_rgb)
        
        # Store frame dimensions for coordinate denormalization
        frame_h, frame_w = frame.shape[:2]
        
        # Validate hand detection results
        # Both conditions MUST be true:
        # 1. results.multi_hand_landmarks is not None
        # 2. Exactly 2 hands detected (left AND right)
        if results.multi_hand_landmarks is None or len(results.multi_hand_landmarks) != 2:
            # Reset landmark tracking when hands not detected properly
            self.last_landmarks_left = None
            self.last_landmarks_right = None
            self.last_hand_bboxes = None
            return None, 0
        
        # Extract and store landmarks for visualization
        self._store_landmarks(results, frame_w, frame_h)
        self._store_bounding_boxes(results, frame_w, frame_h)
        
        # Extract feature vector from both hands
        feature_vector = self._extract_feature_vector(results)
        
        if feature_vector is None:
            return None, 0
        
        # Predict spell using model
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', category=UserWarning)
                
                # Get prediction and probabilities
                prediction = self.model.predict([feature_vector])[0]
                probabilities = self.model.predict_proba([feature_vector])[0]
                max_confidence = max(probabilities)
            
            # Check confidence threshold
            if max_confidence > CONFIDENCE_THRESHOLD:
                confidence_percentage = max_confidence * 100
                return prediction, confidence_percentage
            else:
                return None, 0
        
        except Exception as e:
            print(f"✗ Prediction error: {e}")
            return None, 0
    
    def _store_landmarks(self, results, frame_w, frame_h):
        """
        Store hand landmarks for visualization.
        
        PRECONDITION: Must be called only when validated that:
        - results.multi_hand_landmarks is not None
        - len(results.multi_hand_landmarks) == 2 (both hands detected)
        
        Args:
            results: MediaPipe detection results
            frame_w: Frame width for denormalization
            frame_h: Frame height for denormalization
        """
        # Safety check: ensure conditions are met
        if results.multi_hand_landmarks is None or len(results.multi_hand_landmarks) != 2:
            self.last_landmarks_left = None
            self.last_landmarks_right = None
            return
        
        self.last_landmarks_left = None
        self.last_landmarks_right = None
        
        for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
            hand_label = handedness.classification[0].label
            landmarks = self._extract_landmarks(hand_landmarks)
            
            # Denormalize to pixel coordinates
            pixel_landmarks = [
                (int(x * frame_w), int(y * frame_h)) for x, y in landmarks
            ]
            
            if hand_label == "Left":
                self.last_landmarks_left = pixel_landmarks
            else:
                self.last_landmarks_right = pixel_landmarks
    
    def _store_bounding_boxes(self, results, frame_w, frame_h):
        """
        Calculate and store bounding boxes for each hand.
        
        PRECONDITION: Must be called only when validated that:
        - results.multi_hand_landmarks is not None
        - len(results.multi_hand_landmarks) == 2 (both hands detected)
        
        Args:
            results: MediaPipe detection results
            frame_w: Frame width for bounds
            frame_h: Frame height for bounds
        """
        # Safety check: ensure conditions are met
        if results.multi_hand_landmarks is None or len(results.multi_hand_landmarks) != 2:
            self.last_hand_bboxes = None
            return
        
        self.last_hand_bboxes = []
        
        for hand_landmarks in results.multi_hand_landmarks:
            landmarks = self._extract_landmarks(hand_landmarks)
            
            # Get min/max coordinates
            xs = [int(x * frame_w) for x, y in landmarks]
            ys = [int(y * frame_h) for x, y in landmarks]
            
            x1 = max(0, min(xs) - 10)
            y1 = max(0, min(ys) - 10)
            x2 = min(frame_w, max(xs) + 10)
            y2 = min(frame_h, max(ys) + 10)
            
            self.last_hand_bboxes.append((x1, y1, x2, y2))
    
    def _extract_feature_vector(self, results):
        """
        Extract 84-dimensional feature vector from hand landmarks.
        
        Uses left wrist (Landmark 0) as global reference for both hands.
        Normalizes coordinates by palm size (distance from wrist to palm center).
        
        Args:
            results: MediaPipe detection results
        
        Returns:
            NumPy array of 84 coordinates (42 landmarks × 2 coords each) or None
        """
        left_coords = []
        right_coords = []
        
        left_wrist_x = None
        left_wrist_y = None
        left_palm_size = None
        has_left_hand = False
        has_right_hand = False
        
        # First pass: Process left hand and establish global reference
        for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
            hand_label = handedness.classification[0].label
            
            if hand_label == "Left":
                has_left_hand = True
                landmarks = self._extract_landmarks(hand_landmarks)
                
                # Left wrist is the origin (Landmark 0)
                left_wrist_x, left_wrist_y = landmarks[0]
                
                # Palm size = distance from wrist (0) to palm center (9)
                palm_x, palm_y = landmarks[9]
                left_palm_size = np.sqrt(
                    (palm_x - left_wrist_x) ** 2 + 
                    (palm_y - left_wrist_y) ** 2
                )
                
                # Prevent division by zero
                if left_palm_size < 0.001:
                    left_palm_size = 0.001
                
                # Extract and normalize left hand coordinates
                for lx, ly in landmarks:
                    rel_x = lx - left_wrist_x
                    rel_y = ly - left_wrist_y
                    norm_x = rel_x / left_palm_size
                    norm_y = rel_y / left_palm_size
                    
                    left_coords.append(norm_x)
                    left_coords.append(norm_y)
        
        # Second pass: Process right hand using left wrist as reference
        for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
            hand_label = handedness.classification[0].label
            
            if hand_label == "Right":
                has_right_hand = True
                landmarks = self._extract_landmarks(hand_landmarks)
                
                # Check if left hand reference is available
                if left_wrist_x is None or left_palm_size is None:
                    return None
                
                # Extract and normalize right hand coordinates using left hand reference
                for lx, ly in landmarks:
                    rel_x = lx - left_wrist_x
                    rel_y = ly - left_wrist_y
                    norm_x = rel_x / left_palm_size
                    norm_y = rel_y / left_palm_size
                    
                    right_coords.append(norm_x)
                    right_coords.append(norm_y)
        
        # Only return feature vector if both hands detected
        if has_left_hand and has_right_hand:
            feature_vector = left_coords + right_coords
            return np.array(feature_vector)
        
        return None
    
    def _extract_landmarks(self, hand_landmarks):
        """
        Extract 21 landmarks from a hand.
        
        Args:
            hand_landmarks: MediaPipe hand landmark object
        
        Returns:
            List of (x, y) tuples for each landmark
        """
        landmarks = []
        for lm in hand_landmarks.landmark:
            landmarks.append((lm.x, lm.y))
        return landmarks
    
    def get_last_landmarks(self):
        """
        Get last detected hand landmarks for visualization.
        
        Returns:
            Tuple of (left_landmarks, right_landmarks) where each is a list of (x, y) pixel coords
            Returns (None, None) if no landmarks detected
        """
        return self.last_landmarks_left, self.last_landmarks_right
    
    def get_last_bounding_boxes(self):
        """
        Get last detected hand bounding boxes.
        
        Returns:
            List of (x1, y1, x2, y2) tuples or None
        """
        return self.last_hand_bboxes
    
    def close(self):
        """Clean up resources."""
        if hasattr(self, 'hands'):
            self.hands.close()
            print("✓ MediaPipe resources released")
