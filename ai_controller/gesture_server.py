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
    
    def __init__(self, host='localhost', port=5555, client_host='localhost', client_port=6666):
        """
        Initialize gesture server.
        
        Args:
            host: Server bind address
            port: Server listen port
            client_host: Game client address
            client_port: Game client port
        """
        self.host = host
        self.port = port
        self.client_host = client_host
        self.client_port = client_port
        
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
        self.gesture_hold_start_time = None       # When gesture was first detected
        self.gesture_hold_duration = 1.0          # Duration to hold (1 second)
        self.gesture_broadcast = False            # Flag: should broadcast after hold
        
        # Running state
        self.running = True
        self.fps_counter = 0
        self.fps_timer = time.time()
        
    def broadcast_spell(self, spell_name: str, confidence: float) -> bool:
        """
        Send detected spell to game client via UDP.
        
        Args:
            spell_name: Name of detected spell
            confidence: Confidence percentage (0-100)
        
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            payload = {
                'type': 'spell_detected',
                'spell': spell_name,
                'confidence': round(confidence, 2),
                'timestamp': time.time()
            }
            
            message = json.dumps(payload)
            self.socket.sendto(message.encode(), (self.client_host, self.client_port))
            
            print(f"[BROADCAST] {spell_name} ({confidence:.1f}%) -> {self.client_host}:{self.client_port}")
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
    
    def detect_gesture(self, draw_frame=False) -> Tuple[Optional[str], float, Optional[np.ndarray]]:
        """
        Capture and process one frame, detect gesture.
        
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
                
                # Draw landmarks on frame if requested
                if draw_frame:
                    self.recognizer.draw_landmarks(frame, results)
                
                # Extract and normalize hand data
                feature_vector = self.recognizer.process_frame_data(results, hand_count)
                
                if feature_vector is not None:
                    # Predict gesture from feature vector (updated method name)
                    gesture_name, confidence = self.recognizer.predict_gesture(feature_vector)
                    # Debug output (uncomment to see predictions)
                    # print(f"[DETECT] hands={hand_count}, gesture={gesture_name}, conf={confidence:.1f}%")
            
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
    
    def update_gesture_hold(self, spell_name: Optional[str], confidence: float) -> bool:
        """
        Track gesture holding duration for animation chaining.
        Returns True when gesture has been held for required duration.
        
        Args:
            spell_name: Current detected spell (or None if no detection)
            confidence: Detection confidence
        
        Returns:
            True if should broadcast (gesture held for 1s), False otherwise
        """
        current_time = time.time()
        
        # If no spell detected
        if spell_name is None:
            # If we were holding a gesture, reset
            if self.current_gesture_name is not None:
                held_time = current_time - self.gesture_hold_start_time if self.gesture_hold_start_time else 0
                print(f"[HOLD] Gesture released: {self.current_gesture_name} (held {held_time:.2f}s)")
                self.current_gesture_name = None
                self.gesture_hold_start_time = None
                self.gesture_broadcast = False
            return False
        
        # If new gesture detected (different from current hold)
        if spell_name != self.current_gesture_name:
            # If we were holding something else, notify
            if self.current_gesture_name is not None:
                print(f"[HOLD] Gesture changed: {self.current_gesture_name} -> {spell_name}")
            
            # Start holding new gesture
            self.current_gesture_name = spell_name
            self.gesture_hold_start_time = current_time
            self.gesture_broadcast = False
            print(f"[HOLD] Start: {spell_name} ({confidence:.1f}%)")
            return False
        
        # Same gesture still detected - check if held long enough
        if self.current_gesture_name == spell_name and self.gesture_hold_start_time is not None:
            held_time = current_time - self.gesture_hold_start_time
            
            # If held for required duration and not already broadcast
            if held_time >= self.gesture_hold_duration and not self.gesture_broadcast:
                self.gesture_broadcast = True
                return True
            
            # Show progress (every 0.2s)
            if int(held_time * 5) % 1 == 0:  # Every ~0.2s
                progress = min(100, int(held_time / self.gesture_hold_duration * 100))
                print(f"[HOLD] {spell_name}: {held_time:.1f}s / {self.gesture_hold_duration}s [{progress}%]")
        
        return False
    
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
        """Update and display FPS counter."""
        self.fps_counter += 1
        
        if time.time() - self.fps_timer >= 1.0:
            fps = self.fps_counter
            print(f"[FPS] {fps}", end='\r')
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
        try:
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(window_name, 1280, 720)
            print(f"[+] Display window created: {window_name}")
        except Exception as e:
            print(f"[!] Warning: Could not create display window: {e}")
        
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
                    
                    # Update gesture holding system (1s hold = broadcast)
                    should_broadcast = self.update_gesture_hold(spell_name, confidence if spell_name else 0)
                    
                    # If gesture held for 1s, broadcast it
                    if should_broadcast:
                        # Broadcast spell to game client
                        success = self.broadcast_spell(spell_name, confidence)
                        
                        if success:
                            self.stats['spells_detected'] += 1
                            self.stats['last_spell'] = spell_name
                            self.stats['last_confidence'] = confidence
                            
                            print(f"\n[CAST] {spell_name} ({confidence:.1f}%) - Spell triggered!")
                            print(f"   -> Sent to {self.client_host}:{self.client_port}")
                
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
    
    args = parser.parse_args()
    
    # Create and run server
    server = GestureServer(
        host=args.host,
        port=args.port,
        client_host=args.client_host,
        client_port=args.client_port
    )
    
    try:
        server.run()
    except (KeyboardInterrupt, Exception) as e:
        print(f"\n[X] Error: {e}")
        server.shutdown()


if __name__ == "__main__":
    main()
