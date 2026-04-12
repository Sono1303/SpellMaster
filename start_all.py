#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SpellMaster - Unified Launcher

Usage:
    python start_all.py              # Start game + server + camera display
    python start_all.py --no-camera  # Start game + server, no hand-sign window
    python start_all.py --help       # Show help
"""

import os
import sys
import subprocess
import time
import argparse
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

def start_gesture_server(no_display=False) -> subprocess.Popen:
    """Start gesture recognition server in background"""
    print_info("Starting Gesture Recognition Server...")
    
    cmd = [sys.executable, 'gesture_server.py']
    if no_display:
        cmd.append('--no-display')
    
    try:
        process = subprocess.Popen(
            cmd,
            cwd=str(AI_CONTROLLER_DIR)
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

def main():
    """Main launcher"""
    parser = argparse.ArgumentParser(
        description='SpellMaster - Unified Gesture Recognition Launcher',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
MODES:
  (default)        Start game + server + webcam hand-sign window
  --no-camera      Start game + server only, no hand-sign window
        """
    )
    
    parser.add_argument('--no-camera', action='store_true',
                        help='Disable the webcam hand-sign display window')
    
    args = parser.parse_args()
    
    print_header()
    
    if not verify_files():
        print_error("Required files not found!")
        sys.exit(1)
    
    server_process = None
    game_process = None
    
    try:
        # Step 1: Gesture Server
        print_info("\n" + "="*80)
        print_info("STEP 1: GESTURE RECOGNITION SERVER")
        print_info("="*80)
        server_process = start_gesture_server(
            no_display=args.no_camera
        )
        if not server_process:
            sys.exit(1)
        
        # Step 2: Pygame Game
        print_info("\n" + "="*80)
        print_info("STEP 2: PYGAME GAME")
        print_info("="*80)
        game_process = start_pygame_game()
        if not game_process:
            sys.exit(1)
        
        print("\n" + "="*80)
        print(f"{Colors.GREEN}{Colors.BOLD}SPELLMASTER STARTED{Colors.RESET}")
        print("="*80)
        print(f"\n{Colors.GREEN}Active Components:{Colors.RESET}")
        
        if server_process:
            status = "[+] Running" if server_process.poll() is None else "[X] Failed"
            cam_note = " (no display)" if args.no_camera else ""
            print(f"  * Gesture Server{cam_note:.<45} {status}")
        
        if game_process:
            status = "[+] Running" if game_process.poll() is None else "[X] Failed"
            print(f"  * Pygame Game{Colors.RESET:.<45} {status}")
        
        print("\n" + "="*80)
        print(f"{Colors.CYAN}How to use:{Colors.RESET}")
        print("  1. Make hand gestures in front of webcam")
        if not args.no_camera:
            print("  2. Watch hand landmarks in the Gesture Server window")
        print("  3. Detected spells are cast in the game")
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
