#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SpellMaster - Unified Gesture Recognition Launcher
Single entry point that launches:
  1. Gesture Recognition Server (UDP broadcaster)
  2. Hand Detection Display (with webcam and hand landmarks)
  3. Pygame Game (connected to gesture recognition)

Usage:
    python start_all.py              # Start all components
    python start_all.py --help       # Show help
    python start_all.py --game-only  # Start only game
    python start_all.py --server-only # Start only server
"""

import os
import sys
import subprocess
import threading
import time
import argparse
import cv2
from pathlib import Path

# Add paths for imports
PROJECT_ROOT = Path(__file__).parent
AI_CONTROLLER_DIR = PROJECT_ROOT / "ai_controller"
PYGAME_DIR = PROJECT_ROOT / "pygame" / "scripts"

sys.path.insert(0, str(AI_CONTROLLER_DIR))
sys.path.insert(0, str(PYGAME_DIR))

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(title="SPELLMASTER - GESTURE RECOGNITION"):
    """Print startup header"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{title.center(80)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}\n")

def print_success(msg: str):
    """Print success message"""
    print(f"{Colors.GREEN}[+]{Colors.RESET} {msg}")

def print_error(msg: str):
    """Print error message"""
    print(f"{Colors.RED}[X]{Colors.RESET} {msg}")

def print_info(msg: str):
    """Print info message"""
    print(f"{Colors.BLUE}[*]{Colors.RESET} {msg}")

def verify_files():
    """Verify all required files exist"""
    print_info("Checking required files...")
    
    required_files = {
        'Gesture Server': AI_CONTROLLER_DIR / 'gesture_server.py',
        'Spell Recognizer': AI_CONTROLLER_DIR / 'spell_recognizer.py',
        'Pygame Game': PYGAME_DIR / 'main_pygame.py',
        'ML Model': AI_CONTROLLER_DIR / 'data' / 'models' / 'best_spell_model.pkl'
    }
    
    all_ok = True
    for name, path in required_files.items():
        if path.exists():
            print_success(f"  {name:.<50} FOUND")
        else:
            print_error(f"  {name:.<50} NOT FOUND")
            all_ok = False
    
    return all_ok

def start_gesture_server() -> subprocess.Popen:
    """Start gesture recognition server in background"""
    print_info("Starting Gesture Recognition Server...")
    
    try:
        process = subprocess.Popen(
            [sys.executable, 'gesture_server.py'],
            cwd=str(AI_CONTROLLER_DIR)
            # stdout/stderr inherit from parent (visible in console)
        )
        
        time.sleep(2)
        
        if process.poll() is None:
            print_success(f"Gesture Server started (PID: {process.pid})")
            return process
        else:
            print_error("Gesture Server failed to start")
            return None
    
    except Exception as e:
        print_error(f"Error starting Gesture Server: {e}")
        return None

def start_pygame_game() -> subprocess.Popen:
    """Start pygame game in background"""
    print_info("Starting Pygame Game...")
    
    try:
        process = subprocess.Popen(
            [sys.executable, 'main_pygame.py'],
            cwd=str(PYGAME_DIR)
            # stdout/stderr inherit from parent (visible in console)
        )
        
        time.sleep(2)
        
        if process.poll() is None:
            print_success(f"Pygame Game started (PID: {process.pid})")
            return process
        else:
            print_error("Pygame Game failed to start")
            return None
    
    except Exception as e:
        print_error(f"Error starting Pygame Game: {e}")
        return None

def start_hand_recognition_display():
    """Display hand recognition in OpenCV window with error handling"""
    print_info("Starting Hand Recognition Display...")
    
    def recognition_loop():
        try:
            from spell_recognizer import SpellRecognizer
            
            # Initialize with graceful camera failure handling
            try:
                recognizer = SpellRecognizer(skip_camera=False)
                if not recognizer.camera_available or recognizer.cap is None:
                    print_error("Camera not available - skipping hand recognition display")
                    return
            except Exception as e:
                print_error(f"Failed to initialize recognizer: {e}")
                print_info("Continuing without hand recognition display...")
                return
            
            print_success("Hand Recognition window active (Press 'Q' to quit)")
            
            while True:
                try:
                    if recognizer.cap is None:
                        break
                    
                    ret, frame = recognizer.cap.read()
                    if not ret:
                        break
                    
                    # Flip for mirror effect
                    frame = cv2.flip(frame, 1)
                    
                    # Process hand detection
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    results = recognizer.hands.process(frame_rgb)
                    
                    # Draw hand landmarks
                    if results.multi_hand_landmarks:
                        recognizer.draw_landmarks(frame, results)
                    
                    # Display frame
                    cv2.imshow("Hand Recognition - Ignite: Spell Master", frame)
                    
                    # Check if window closed or Q pressed
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q') or key == ord('Q'):
                        break
                    
                    if cv2.getWindowProperty("Hand Recognition - Ignite: Spell Master", cv2.WND_PROP_VISIBLE) < 1:
                        break
                
                except Exception as e:
                    print_error(f"Error in recognition loop: {e}")
                    break
            
            # Cleanup
            try:
                if recognizer.cap is not None:
                    recognizer.cap.release()
                cv2.destroyAllWindows()
                recognizer.hands.close()
                print_info("Hand Recognition Display closed")
            except:
                pass
        
        except Exception as e:
            print_error(f"Fatal error in hand recognition: {type(e).__name__}: {e}")
    
    thread = threading.Thread(target=recognition_loop, daemon=True)
    thread.start()
    return thread

def main():
    """Main launcher"""
    parser = argparse.ArgumentParser(
        description='SpellMaster - Unified Gesture Recognition',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
  python start_all.py              # Start server + game (NO separate hand display)
                                    # Hand display runs inside gesture server
  
  python start_all.py --server-only # Start only gesture server
  
  python start_all.py --game-only # Start only game
  
  python start_all.py --hand-display # Start server + game + separate hand display
                                    # (NOT recommended - camera conflict!)

NOTE: By default, hand landmarks are displayed inside the gesture server window.
      Only use --hand-display if you want a separate hand recognition window.
        """
    )
    
    parser.add_argument('--server-only', action='store_true', help='Start only server')
    parser.add_argument('--game-only', action='store_true', help='Start only game')
    parser.add_argument('--hand-display', action='store_true', help='Start separate hand display (experimental)')
    
    args = parser.parse_args()
    
    print_header()
    
    if not verify_files():
        print_error("Required files not found!")
        sys.exit(1)
    
    server_process = None
    game_process = None
    hand_thread = None
    
    try:
        # Start Gesture Server
        if not args.game_only:
            print_info("\n" + "="*80)
            print_info("STEP 1: GESTURE RECOGNITION SERVER")
            print_info("="*80)
            server_process = start_gesture_server()
            if not server_process:
                sys.exit(1)
        
        # Start Pygame Game
        if not args.server_only:
            print_info("\n" + "="*80)
            print_info("STEP 2: PYGAME GAME")
            print_info("="*80)
            game_process = start_pygame_game()
            if not game_process:
                sys.exit(1)
        
        # Start Hand Recognition Display (OPTIONAL - separate from server)
        # By default, gesture_server displays hand recognition internally
        # Only start separate hand display if explicitly requested
        if args.hand_display and not args.server_only:
            print_info("\n" + "="*80)
            print_info("STEP 3: SEPARATE HAND RECOGNITION DISPLAY (EXPERIMENTAL)")
            print_info("="*80)
            print_info("Note: This may cause camera conflicts with gesture server!")
            hand_thread = start_hand_recognition_display()
        
        # Print summary
        print("\n" + "="*80)
        print(f"{Colors.GREEN}{Colors.BOLD}SPELLMASTER STARTED{Colors.RESET}")
        print("="*80)
        print(f"\n{Colors.GREEN}Active Components:{Colors.RESET}")
        
        if server_process:
            status = "[+] Running" if server_process.poll() is None else "[X] Failed"
            print(f"  * Gesture Recognition Server{Colors.RESET:.<35} {status}")
        
        if game_process:
            status = "[+] Running" if game_process.poll() is None else "[X] Failed"
            print(f"  * Pygame Game{Colors.RESET:.<45} {status}")
        
        if hand_thread and hand_thread.is_alive():
            print(f"  * Hand Recognition Display{Colors.RESET:.<32} [+] Running")
        
        print("\n" + "="*80)
        print(f"{Colors.CYAN}How to use:{Colors.RESET}")
        print("  1. Make hand gestures in front of webcam")
        print("  2. See hand landmarks in Hand Recognition window")
        print("  3. Detected spells are cast in the game")
        print("\nWindows:")
        print("  * Hand Recognition - Shows webcam with hand landmarks")
        print("  * Pygame Game - Game window for spell casting")
        print("\n" + "="*80)
        print_info("Press Ctrl+C to stop all components...")
        print("="*80 + "\n")
        
        # Monitor processes
        while True:
            time.sleep(1)
            
            # If game closes, shutdown everything
            if game_process and game_process.poll() is not None:
                print_error("Pygame Game closed. Shutting down all components...")
                
                # Stop gesture server if running
                if server_process and server_process.poll() is None:
                    try:
                        print_info("Stopping Gesture Server...")
                        server_process.terminate()
                        server_process.wait(timeout=2)
                        print_success("Gesture Server stopped")
                    except:
                        try:
                            server_process.kill()
                        except:
                            pass
                break
            
            if server_process and server_process.poll() is not None:
                print_error("Gesture Server process exited")
                break
    
    except KeyboardInterrupt:
        print("\n\n" + "="*80)
        print_info("Shutting down...")
        print("="*80 + "\n")
        
        if server_process:
            try:
                print_info(f"Stopping Gesture Server...")
                server_process.terminate()
                server_process.wait(timeout=2)
                print_success("Gesture Server stopped")
            except:
                server_process.kill()
        
        if game_process:
            try:
                print_info(f"Stopping Pygame Game...")
                game_process.terminate()
                game_process.wait(timeout=2)
                print_success("Pygame Game stopped")
            except:
                game_process.kill()
        
        print("\n" + "="*80)
        print_success("All components stopped")
        print("="*80 + "\n")
    
    except Exception as e:
        print_error(f"Error: {e}")
        
        if server_process:
            try:
                server_process.kill()
            except:
                pass
        
        if game_process:
            try:
                game_process.kill()
            except:
                pass
        
        sys.exit(1)

if __name__ == "__main__":
    main()
