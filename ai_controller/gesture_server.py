#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gesture Recognition Server - UDP Network Communication
Runs independently and sends detected spells to game client via UDP

This server:
1. Continuously processes webcam frames
2. Recognizes gestures using the trained ML model
3. Sends detected spells to the game via UDP socket
4. Can run on same machine or network

Usage:
    python gesture_server.py --host localhost --port 5555
    python gesture_server.py --host 192.168.1.100 --port 5555  (network)
"""

import socket
import json
import time
import argparse
import sys
import cv2
import numpy as np
from pathlib import Path
from typing import Tuple, Optional
import threading

# Import SpellRecognizer
sys.path.insert(0, str(Path(__file__).parent))
from spell_recognizer import SpellRecognizer


class GestureServer:
    """
    UDP Server for gesture recognition and spell broadcasting
    
    Attributes:
        host: Server host IP
        port: Server listening port
        client_host: Game client IP
        client_port: Game client port
        recognizer: SpellRecognizer instance
    """
    
    def __init__(self, host='localhost', port=5555, client_host='localhost', client_port=6666,
                 no_display=False):
        """
        Initialize gesture server.
        
        Args:
            host: Server bind address
            port: Server listen port
            client_host: Game client address
            client_port: Game client port
            no_display: If True, don't show webcam window
        """
        self.host = host
        self.port = port
        self.client_host = client_host
        self.client_port = client_port
        self.no_display = no_display
        
        # Initialize UDP socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Bind to listening port
        try:
            self.socket.bind((self.host, self.port))
            print(f"[+] Server listening on {self.host}:{self.port}")
        except OSError as e:
            print(f"[X] Error binding to {self.host}:{self.port}: {e}")
            raise
        
        # Initialize spell recognizer with camera
        print("\n[*] Initializing gesture recognizer...")
        try:
            self.recognizer = SpellRecognizer(skip_camera=False)
            if not self.recognizer.camera_available or self.recognizer.cap is None:
                print(f"[X] Camera not available!")
                raise RuntimeError("Camera initialization failed")
            print("[+] Recognizer initialized")
            print(f"[+] Camera available and ready\n")
        except Exception as e:
            print(f"[X] Failed to initialize recognizer: {e}")
            print("[X] Please check:")
            print("    1. Camera is connected and not in use")
            print("    2. All dependencies are installed")
            raise
        
        # Statistics
        self.stats = {
            'frames_processed': 0,
            'spells_detected': 0,
            'last_spell': None,
            'last_confidence': 0,
            'server_start_time': time.time(),
            'detection_rate': 0.0
        }
        
        # Spell cooldown to prevent spam
        self.last_spell_name = None
        self.last_spell_time = 0
        self.spell_cooldown = 0.5  # Minimum 0.5s between same spell
        
        # Gesture holding system (charge/animation chaining)
        self.current_gesture_name = None          # Currently held gesture
        self.current_gesture_confidence = 0.0     # Confidence of current held gesture
        self.gesture_hold_start_time = None       # When gesture was first detected
        self.gesture_hold_duration = 1.0          # Duration to hold (1 second)
        self.gesture_broadcast = False            # Flag: should broadcast after hold
        self.gesture_to_broadcast = None          # Gesture name to broadcast on release
        self.gesture_to_broadcast_confidence = 0.0  # Confidence to broadcast on release

        # Gesture change tolerance — ignore brief mispredictions during hold
        self.gesture_change_tolerance = 0.2       # Seconds a different gesture must persist before switching
        self.gesture_change_candidate = None      # Candidate gesture for takeover
        self.gesture_change_start_time = None     # When candidate was first seen
        
        # Running state
        self.running = True
        self.fps_counter = 0
        self.fps_timer = time.time()
        
    def broadcast_spell(self, spell_name: str, confidence: float, state: str = "cast") -> bool:
        """
        Send detected spell to game client via UDP.
        
        Args:
            spell_name: Name of detected spell
            confidence: Confidence percentage (0-100)
            state: Spell state - "focus" (just detected), "holding" (being held), "cast" (released)
        
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            payload = {
                'type': 'spell_detected',
                'spell': spell_name,
                'confidence': round(confidence, 2),
                'state': state,  # NEW: spell state for focus/holding/cast
                'timestamp': time.time()
            }
            
            message = json.dumps(payload)
            self.socket.sendto(message.encode(), (self.client_host, self.client_port))
            
            if state == "focus":
                print(f"[FOCUS] {spell_name} ({confidence:.1f}%)")
            elif state == "cast":
                print(f"[CAST] {spell_name} ({confidence:.1f}%)")
            # holding state: no log (too frequent)
            
            return True
        
        except Exception as e:
            print(f"[X] Error broadcasting spell: {e}")
            return False
    
    def broadcast_status(self, status: str, data: dict = None) -> bool:
        """
        Send server status to game client.
        
        Args:
            status: Status type ('ready', 'error', 'disconnected', etc.)
            data: Additional status data
        """
        try:
            payload = {
                'type': 'server_status',
                'status': status,
                'timestamp': time.time()
            }
            
            if data:
                payload['data'] = data
            
            message = json.dumps(payload)
            self.socket.sendto(message.encode(), (self.client_host, self.client_port))
            
            return True
        
        except Exception as e:
            print(f"[X] Error broadcasting status: {e}")
            return False
    
    def get_hand_bounding_box(self, hand_landmarks) -> Tuple[float, float, float, float]:
        """
        Get normalized bounding box of hand from landmarks.
        
        Args:
            hand_landmarks: MediaPipe hand landmarks
            
        Returns:
            (min_x, min_y, max_x, max_y) - normalized coordinates (0-1)
        """
        xs = [lm.x for lm in hand_landmarks.landmark]
        ys = [lm.y for lm in hand_landmarks.landmark]
        return min(xs), min(ys), max(xs), max(ys)
    
    def hands_are_close(self, hand_landmarks_list) -> bool:
        """
        Check if 2 hands are very close to each other (bounding boxes actually touch/overlap).
        Gesture is only detected when hands are together.
        
        Args:
            hand_landmarks_list: List of hand landmarks
            
        Returns:
            True if hands are very close (almost overlapping), False otherwise
        """
        if len(hand_landmarks_list) < 2:
            return False  # Not enough hands
        
        # Get bounding boxes for each hand
        box1 = self.get_hand_bounding_box(hand_landmarks_list[0])
        box2 = self.get_hand_bounding_box(hand_landmarks_list[1])
        
        x1_min, y1_min, x1_max, y1_max = box1
        x2_min, y2_min, x2_max, y2_max = box2
        
        # Calculate center and size of each bounding box
        center1_x = (x1_min + x1_max) / 2
        center1_y = (y1_min + y1_max) / 2
        size1_x = x1_max - x1_min
        size1_y = y1_max - y1_min
        
        center2_x = (x2_min + x2_max) / 2
        center2_y = (y2_min + y2_max) / 2
        size2_x = x2_max - x2_min
        size2_y = y2_max - y2_min
        
        # Calculate average box size
        avg_size_x = (size1_x + size2_x) / 2
        avg_size_y = (size1_y + size2_y) / 2
        
        # Distance between centers
        distance_x = abs(center1_x - center2_x)
        distance_y = abs(center1_y - center2_y)
        
        # Hands are close if distance between centers < average box size * 1.3
        # This means the boxes are touching or nearly touching (allows edge-near detection)
        hands_touch = (distance_x < avg_size_x * 1.3) and (distance_y < avg_size_y * 1.3)
        
        return hands_touch
    
    def draw_hand_bounding_boxes(self, frame, hand_landmarks_list, frame_width: int, frame_height: int, hands_close: bool = False) -> None:
        """
        Draw bounding boxes for detected hands on the frame.
        When hands are close together, draws 1 merged bounding box.
        Otherwise draws separate boxes for each hand.
        
        Args:
            frame: OpenCV frame to draw on
            hand_landmarks_list: List of hand landmarks
            frame_width: Frame width in pixels
            frame_height: Frame height in pixels
            hands_close: If True, hands are close - merge into 1 box
        """
        if not hand_landmarks_list:
            return
        
        if hands_close and len(hand_landmarks_list) >= 2:
            # NEW: Merge 2 hands into 1 bounding box
            all_xs = []
            all_ys = []
            for hand_landmarks in hand_landmarks_list:
                xs = [lm.x for lm in hand_landmarks.landmark]
                ys = [lm.y for lm in hand_landmarks.landmark]
                all_xs.extend(xs)
                all_ys.extend(ys)
            
            min_x, max_x = min(all_xs), max(all_xs)
            min_y, max_y = min(all_ys), max(all_ys)
            
            # Convert to pixel coords
            x_min = int(min_x * frame_width)
            y_min = int(min_y * frame_height)
            x_max = int(max_x * frame_width)
            y_max = int(max_y * frame_height)
            
            # Draw merged bounding box (cyan color)
            cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (255, 255, 0), 3)  # Cyan, thick
            cv2.putText(frame, "DUAL-HAND GESTURE", (x_min, y_min - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        else:
            # Draw separate boxes for each hand
            colors = [(0, 255, 0), (255, 0, 0)]  # Green for hand 1, Red for hand 2
            
            for idx, hand_landmarks in enumerate(hand_landmarks_list):
                # Get bounding box
                min_x, min_y, max_x, max_y = self.get_hand_bounding_box(hand_landmarks)
                
                # Convert normalized coords to pixel coords
                x_min = int(min_x * frame_width)
                y_min = int(min_y * frame_height)
                x_max = int(max_x * frame_width)
                y_max = int(max_y * frame_height)
                
                # Draw rectangle
                color = colors[idx % len(colors)]
                thickness = 2
                cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), color, thickness)
                
                # Draw label
                hand_label = f"Hand {idx + 1}"
                cv2.putText(frame, hand_label, (x_min, y_min - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    
    def detect_gesture(self, draw_frame=False) -> Tuple[Optional[str], float, Optional[np.ndarray]]:
        """
        Capture and process one frame, detect gesture.
        Only recognizes gesture when BOTH hands are detected and close together.
        
        Args:
            draw_frame: If True, return annotated frame with landmarks
        
        Returns:
            (spell_name, confidence, frame) or (None, 0, None) if no valid detection
        """
        try:
            # Check camera availability
            if self.recognizer.cap is None or not self.recognizer.camera_available:
                return None, 0, None
            
            ret, frame = self.recognizer.cap.read()
            if not ret:
                # Camera read failed - create placeholder frame to keep window responsive
                if draw_frame:
                    placeholder = np.zeros((720, 1280, 3), dtype=np.uint8)
                    cv2.putText(placeholder, "ERROR: No frame captured", (50, 100),
                               cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
                    cv2.putText(placeholder, "Check camera connection", (50, 150),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
                    return None, 0, placeholder
                return None, 0, None
            
            # Flip frame for mirror effect
            frame = cv2.flip(frame, 1)
            h, w, c = frame.shape
            
            # Convert to RGB for MediaPipe
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.recognizer.hands.process(frame_rgb)
            
            gesture_name = None
            confidence = 0
            hand_count = 0
            
            # Process hand landmarks if detected
            if results.multi_hand_landmarks:
                hand_count = len(results.multi_hand_landmarks)
                hands_close = hand_count >= 2 and self.hands_are_close(results.multi_hand_landmarks)
                
                # Draw landmarks on frame if requested
                if draw_frame:
                    self.recognizer.draw_landmarks(frame, results)
                    # Draw bounding boxes with merge when hands are close
                    self.draw_hand_bounding_boxes(frame, results.multi_hand_landmarks, w, h, hands_close=hands_close)
                
                # Only detect gesture when BOTH hands are present and close together
                if hands_close:
                    # Extract and normalize hand data
                    feature_vector = self.recognizer.process_frame_data(results, hand_count)
                    
                    if feature_vector is not None:
                        # Predict gesture from feature vector
                        gesture_name, confidence = self.recognizer.predict_gesture(feature_vector)
                elif hand_count < 2 and draw_frame:
                    # Show info: waiting for 2 hands
                    cv2.putText(frame, f"Hands detected: {hand_count}/2", (50, 50),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
                    cv2.putText(frame, "Bring 2 hands together to detect spell", (50, 100),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 255), 1)
            
            # Draw info on frame if requested
            if draw_frame:
                self.recognizer.draw_info(frame, hand_count, gesture_name, confidence, self.fps_counter)
            
            return gesture_name, confidence, frame if draw_frame else None
        
        except Exception as e:
            print(f"[X] Error in detect_gesture: {e}")
            # Return placeholder on error to keep window responsive
            if draw_frame:
                placeholder = np.zeros((720, 1280, 3), dtype=np.uint8)
                cv2.putText(placeholder, f"ERROR: {str(e)[:40]}", (50, 100),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                return None, 0, placeholder
            return None, 0, None
    
    def apply_spell_cooldown(self, spell_name: str, confidence: float) -> bool:
        """
        Apply cooldown to prevent rapid re-triggering of same spell.
        
        Args:
            spell_name: Detected spell
            confidence: Detection confidence
        
        Returns:
            True if spell should be broadcasted, False if on cooldown
        """
        try:
            current_time = time.time()
            
            # Different spells always broadcast
            if spell_name != self.last_spell_name:
                self.last_spell_name = spell_name
                self.last_spell_time = current_time
                return True
            
            # Same spell: check cooldown
            if current_time - self.last_spell_time >= self.spell_cooldown:
                self.last_spell_time = current_time
                return True
            
            return False
        
        except Exception as e:
            print(f"[X] Error in cooldown check: {e}")
            return False
    
    def update_gesture_hold(self, spell_name: Optional[str], confidence: float) -> dict:
        """
        Track gesture holding duration for real-time focus/holding/cast states.
        
        Args:
            spell_name: Current detected spell (or None if no detection)
            confidence: Detection confidence
        
        Returns:
            dict with keys:
              - 'state': "focus" (new), "holding" (active), "cast" (released), or None
              - 'spell': spell name or None
              - 'confidence': confidence float
              - 'should_broadcast': bool
        """
        current_time = time.time()
        
        # === GESTURE DETECTED ===
        if spell_name is not None:
            if spell_name == self.current_gesture_name:
                # SAME GESTURE BEING HELD — reset tolerance candidate, update confidence
                self.gesture_change_candidate = None
                self.gesture_change_start_time = None
                if not self.gesture_broadcast and self.gesture_hold_start_time is not None:
                    self.current_gesture_confidence = max(self.current_gesture_confidence, confidence)
                return {
                    'state': 'holding',
                    'spell': self.current_gesture_name,
                    'confidence': self.current_gesture_confidence,
                    'should_broadcast': True
                }

            # DIFFERENT GESTURE DETECTED
            if self.current_gesture_name is None:
                # No gesture was held: accept immediately as new focus
                self.current_gesture_name = spell_name
                self.current_gesture_confidence = confidence
                self.gesture_hold_start_time = current_time
                self.gesture_broadcast = False
                self.gesture_to_broadcast = None
                self.gesture_change_candidate = None
                self.gesture_change_start_time = None
                return {
                    'state': 'focus',
                    'spell': spell_name,
                    'confidence': confidence,
                    'should_broadcast': True
                }

            # A gesture is currently held but a different one appeared — use tolerance window
            if self.gesture_change_candidate != spell_name:
                # New candidate, start timing
                self.gesture_change_candidate = spell_name
                self.gesture_change_start_time = current_time
            elif current_time - self.gesture_change_start_time >= self.gesture_change_tolerance:
                # Candidate persisted long enough → accept as new focus, reset hold
                self.current_gesture_name = spell_name
                self.current_gesture_confidence = confidence
                self.gesture_hold_start_time = current_time
                self.gesture_broadcast = False
                self.gesture_to_broadcast = None
                self.gesture_change_candidate = None
                self.gesture_change_start_time = None
                return {
                    'state': 'focus',
                    'spell': spell_name,
                    'confidence': confidence,
                    'should_broadcast': True
                }

            # Still within tolerance window → treat as still holding current gesture
            if not self.gesture_broadcast and self.gesture_hold_start_time is not None:
                self.current_gesture_confidence = max(self.current_gesture_confidence, confidence)
            return {
                'state': 'holding',
                'spell': self.current_gesture_name,
                'confidence': self.current_gesture_confidence,
                'should_broadcast': True
            }
        
        # === GESTURE RELEASED (spell_name is None) ===
        if self.current_gesture_name is not None:
            held_time = current_time - self.gesture_hold_start_time if self.gesture_hold_start_time else 0
            gesture_being_released = self.current_gesture_name
            confidence_being_released = self.current_gesture_confidence
            
            # Check if held long enough BEFORE resetting
            should_broadcast = held_time >= self.gesture_hold_duration
            
            # Reset state immediately
            self.current_gesture_name = None
            self.current_gesture_confidence = 0.0
            self.gesture_hold_start_time = None
            self.gesture_broadcast = False
            self.gesture_change_candidate = None
            self.gesture_change_start_time = None
            
            if should_broadcast:
                print(f"[RELEASE] {gesture_being_released} after {held_time:.1f}s -> cast")
                return {
                    'state': 'cast',
                    'spell': gesture_being_released,
                    'confidence': confidence_being_released,
                    'should_broadcast': True
                }
            else:
                print(f"[CANCEL] {gesture_being_released} released too early ({held_time:.1f}s)")
                return {
                    'state': 'cancel',
                    'spell': gesture_being_released,
                    'confidence': 0,
                    'should_broadcast': True
                }
        
        return {
            'state': None,
            'spell': None,
            'confidence': 0,
            'should_broadcast': False
        }
    
    def print_statistics(self):
        """Print server statistics to console."""
        elapsed = time.time() - self.stats['server_start_time']
        uptime_str = f"{int(elapsed // 3600)}h {int((elapsed % 3600) // 60)}m {int(elapsed % 60)}s"
        
        detection_rate = (
            self.stats['spells_detected'] / self.stats['frames_processed'] * 100
            if self.stats['frames_processed'] > 0 else 0
        )
        
        print("\n" + "="*70)
        print("GESTURE SERVER STATISTICS".center(70))
        print("="*70)
        print(f"Uptime: {uptime_str}")
        print(f"Frames processed: {self.stats['frames_processed']:,}")
        print(f"Spells detected: {self.stats['spells_detected']}")
        print(f"Detection rate: {detection_rate:.1f}%")
        print(f"Last detected: {self.stats['last_spell'] or 'None'} "
              f"({self.stats['last_confidence']:.1f}%)")
        print(f"Server: {self.host}:{self.port}")
        print(f"Broadcasting to: {self.client_host}:{self.client_port}")
        print("="*70 + "\n")
    
    def print_fps(self):
        """Update FPS counter (stored for display, not printed)."""
        self.fps_counter += 1
        
        if time.time() - self.fps_timer >= 1.0:
            self.fps_counter = 0
            self.fps_timer = time.time()
    
    def run(self):
        """Main server loop - continuously process frames and broadcast spells."""
        print("\n" + "="*70)
        print("GESTURE RECOGNITION SERVER - UDP BROADCAST MODE".center(70))
        print("="*70)
        print(f"Listening on: {self.host}:{self.port}")
        print(f"Broadcasting to: {self.client_host}:{self.client_port}")
        print("\nRecognized spells:")
        for i, spell in enumerate(self.recognizer.model_classes_, 1):
            print(f"  {i:2}. {spell}")
        print("\nControls:")
        print("  - Close the gesture window to quit")
        print("  - Make hand gestures to cast spells")
        print("\n[*] Server started. Processing frames...")
        print("="*70 + "\n")
        
        # Create display window
        window_name = "Gesture Server - Hand Recognition"
        if not self.no_display:
            try:
                cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
                cv2.resizeWindow(window_name, 1280, 720)
                print(f"[+] Display window created: {window_name}")
            except Exception as e:
                print(f"[!] Warning: Could not create display window: {e}")
        else:
            print("[*] Display window disabled (--no-display)")
        
        # Send ready status to client
        self.broadcast_status('ready', {
            'spells': list(self.recognizer.model_classes_),
            'confidence_threshold': self.recognizer.confidence_threshold
        })
        
        window_alive = True
        
        try:
            while self.running and window_alive:
                try:
                    # Detect gesture from camera WITH display frame
                    spell_name, confidence, frame = self.detect_gesture(draw_frame=True)
                    
                    self.stats['frames_processed'] += 1
                    self.print_fps()
                    
                    # Display frame if available (should always be available now with placeholder)
                    if frame is not None:
                        if not self.no_display:
                            try:
                                # Display the frame
                                cv2.imshow(window_name, frame)
                                
                                # Check for key press (non-blocking, 1ms timeout)
                                key = cv2.waitKey(1) & 0xFF
                                
                                # Handle quit commands
                                if key == ord('q') or key == ord('Q') or key == 27:  # 27 = ESC
                                    print("\n[*] Quit command received. Shutting down...")
                                    break
                                
                                # Check if window was closed by user
                                try:
                                    if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                                        print("\n[*] Display window closed. Shutting down...")
                                        window_alive = False
                                        break
                                except (cv2.error, Exception):
                                    # Window doesn't exist anymore
                                    pass
                            
                            except Exception as e:
                                print(f"[!] Error displaying frame: {type(e).__name__}: {e}")
                                # Continue even if display fails
                                time.sleep(0.001)
                    
                    # Update gesture holding system - returns {state, spell, confidence, should_broadcast}
                    gesture_update = self.update_gesture_hold(spell_name, confidence if spell_name else 0)
                    
                    # Broadcast based on state: "focus" (instant), "holding" (continuous), "cast" (release)
                    if gesture_update['should_broadcast']:
                        state = gesture_update['state']
                        spell_to_send = gesture_update['spell']
                        confidence_to_send = gesture_update['confidence']
                        
                        # Broadcast spell to game client with state
                        success = self.broadcast_spell(spell_to_send, confidence_to_send, state=state)
                        
                        if success:
                            # Only count final casts for statistics
                            if state == 'cast':
                                self.stats['spells_detected'] += 1
                                self.stats['last_spell'] = spell_to_send
                                self.stats['last_confidence'] = confidence_to_send
                
                except Exception as e:
                    print(f"[X] Error in main loop iteration: {type(e).__name__}: {e}")
                    # Continue running even if one frame fails
                    time.sleep(0.001)
                    continue
        
        except KeyboardInterrupt:
            print("\n\n[!] Interrupt received. Shutting down...")
        
        finally:
            self.shutdown()

    
    def shutdown(self):
        """Cleanup and shutdown server."""
        print("\n[*] Shutting down gesture server...")
        
        self.running = False
        
        # Close OpenCV window FIRST (before releasing camera)
        try:
            cv2.destroyAllWindows()
            print("[+] OpenCV windows closed")
        except Exception as e:
            print(f"[!] Error closing windows: {e}")
        
        # Send disconnect status
        try:
            self.broadcast_status('disconnected')
        except:
            pass
        
        # Cleanup recognizer - DO THIS AFTER window is closed
        try:
            if self.recognizer and self.recognizer.cap is not None:
                self.recognizer.cap.release()
                print("[+] Camera released")
        except Exception as e:
            print(f"[!] Error releasing camera: {e}")
        
        try:
            if self.recognizer and self.recognizer.hands:
                self.recognizer.hands.close()
                print("[+] MediaPipe closed")
        except Exception as e:
            print(f"[!] Error closing MediaPipe: {e}")
        
        # Close socket
        try:
            self.socket.close()
            print("[+] Socket closed")
        except Exception as e:
            print(f"[!] Error closing socket: {e}")
        
        # Print final statistics
        try:
            self.print_statistics()
        except:
            pass
        
        print("[+] Server shutdown complete")
        sys.exit(0)


def main():
    """Parse arguments and start gesture server."""
    parser = argparse.ArgumentParser(
        description='Gesture Recognition UDP Server for SpellMaster Game'
    )
    
    parser.add_argument(
        '--host',
        default='localhost',
        help='Server bind address (default: localhost)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=5555,
        help='Server listen port (default: 5555)'
    )
    
    parser.add_argument(
        '--client-host',
        default='localhost',
        help='Game client address (default: localhost)'
    )
    
    parser.add_argument(
        '--client-port',
        type=int,
        default=6666,
        help='Game client port (default: 6666)'
    )
    
    parser.add_argument(
        '--no-display',
        action='store_true',
        help='Disable webcam display window (headless mode)'
    )
    
    args = parser.parse_args()
    
    if args.no_display:
        print("[*] Running in headless mode (no display window)")
    
    # Create and run server
    server = GestureServer(
        host=args.host,
        port=args.port,
        client_host=args.client_host,
        client_port=args.client_port,
        no_display=args.no_display
    )
    
    try:
        server.run()
    except (KeyboardInterrupt, Exception) as e:
        print(f"\n[X] Error: {e}")
        server.shutdown()


if __name__ == "__main__":
    main()
