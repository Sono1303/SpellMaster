#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gesture Recognition Client - UDP Network Communication
Runs in the Pygame game to receive detected spells from gesture server

This client:
1. Listens for spell detection messages from gesture_server
2. Runs in a background thread to avoid blocking game loop
3. Queues detected spells for the game to process
4. Handles network errors gracefully

Usage:
    In main_pygame.py:
        client = GestureClient(host='localhost', port=6666)
        client.start()
        
        # In game loop:
        spell = client.get_next_spell()
        if spell:
            game.cast_spell(spell['spell'], spell['confidence'])
"""

import socket
import json
import threading
import queue
import time
from typing import Optional, Dict, Any
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class GestureClient:
    """
    UDP Client for receiving gesture recognition events
    
    Attributes:
        host: Client bind address
        port: Client listen port
        spell_queue: Thread-safe queue for detected spells
        server_host: Address of gesture server
    """
    
    def __init__(self, host='localhost', port=6666, timeout=5.0):
        """
        Initialize gesture client.
        
        Args:
            host: Client bind address
            port: Client listen port (should match server's client_port)
            timeout: Socket timeout in seconds
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        
        # Initialize UDP socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.settimeout(self.timeout)
        
        # Bind to listening port
        try:
            self.socket.bind((self.host, self.port))
            logger.info(f"Client listening on {self.host}:{self.port}")
        except OSError as e:
            logger.error(f"Error binding to {self.host}:{self.port}: {e}")
            raise
        
        # Thread-safe queue for spell events
        self.spell_queue = queue.Queue(maxsize=100)
        
        # Thread management
        self.listener_thread = None
        self.running = False
        
        # Statistics
        self.stats = {
            'spells_received': 0,
            'spells_queued': 0,
            'spells_processed': 0,
            'connection_errors': 0,
            'last_spell': None,
            'last_confidence': 0,
            'server_status': 'disconnected',
            'server_host': None,
            'start_time': time.time()
        }
    
    def start(self):
        """Start listening for spell events in background thread."""
        if self.running:
            logger.warning("Client already running")
            return
        
        self.running = True
        self.listener_thread = threading.Thread(
            target=self._listener_loop,
            daemon=True,
            name='GestureListener'
        )
        self.listener_thread.start()
        logger.info("[+] Gesture client started")
    
    def stop(self):
        """Stop listening and cleanup."""
        if not self.running:
            return
        
        logger.info("Stopping gesture client...")
        self.running = False
        
        if self.listener_thread:
            self.listener_thread.join(timeout=2.0)
        
        try:
            self.socket.close()
        except Exception as e:
            logger.error(f"Error closing socket: {e}")
        
        logger.info("[+] Gesture client stopped")
    
    def _listener_loop(self):
        """
        Background thread loop - continuously listen for spell messages.
        This runs in a separate thread to avoid blocking the game.
        """
        logger.info("[Thread] Gesture listener started")
        
        while self.running:
            try:
                # Check if socket is still valid before receiving
                if not self.running or self.socket is None:
                    break
                
                # Receive message from gesture server
                message, addr = self.socket.recvfrom(4096)
                
                # Check if should stop (might have been set during recvfrom)
                if not self.running:
                    break
                
                self.stats['server_host'] = addr[0]
                
                # Parse JSON payload
                data = json.loads(message.decode('utf-8'))
                
                # Handle different message types
                if data.get('type') == 'spell_detected':
                    self._handle_spell_detected(data, addr)
                
                elif data.get('type') == 'server_status':
                    self._handle_server_status(data, addr)
            
            except socket.timeout:
                # Timeout is normal when no data is being received
                continue
            
            except (OSError, socket.error) as e:
                # Socket closed or other socket error (WinError 10038)
                if self.running:
                    logger.error(f"Socket error (still running): {e}")
                    self.stats['connection_errors'] += 1
                    time.sleep(0.1)
                else:
                    # Socket closed intentionally
                    break
            
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON received: {e}")
                self.stats['connection_errors'] += 1
            
            except Exception as e:
                logger.error(f"Error in listener loop: {e}")
                self.stats['connection_errors'] += 1
                # Brief pause to avoid rapid error loops
                time.sleep(0.1)
        
        logger.info("[Thread] Gesture listener stopped")
    
    def _handle_spell_detected(self, data: Dict[str, Any], addr: tuple):
        """Handle spell detection message from server."""
        spell_name = data.get('spell')
        confidence = data.get('confidence', 0)
        state = data.get('state', 'cast')  # ✅ NEW: spell state (focus, holding, cast)
        
        # Only log cast events (focus/holding logged by game loop)
        if state == 'cast':
            print(f"[RECV] {spell_name} ({confidence:.1f}%) cast")
        
        self.stats['spells_received'] += 1
        self.stats['last_spell'] = spell_name
        self.stats['last_confidence'] = confidence
        
        # Queue spell for game processing (always queue, game decides what to do based on state)
        try:
            self.spell_queue.put_nowait({
                'spell': spell_name,
                'confidence': confidence,
                'state': state,  # ✅ NEW: Include state for game to handle
                'timestamp': data.get('timestamp', time.time())
            })
            self.stats['spells_queued'] += 1
        
        except queue.Full:
            print(f"[X] Spell queue full - dropping: {spell_name}")
    
    def _handle_server_status(self, data: Dict[str, Any], addr: tuple):
        """Handle server status message."""
        status = data.get('status')
        
        if status == 'ready':
            spells = data.get('data', {}).get('spells', [])
            logger.info(f"[+] Server ready at {addr[0]} - Spells: {', '.join(spells)}")
            self.stats['server_status'] = 'ready'
        
        elif status == 'disconnected':
            logger.warning(f"[!] Server disconnected from {addr[0]}")
            self.stats['server_status'] = 'disconnected'
        
        else:
            logger.info(f"[?] Server status: {status} from {addr[0]}")
    
    def get_next_spell(self) -> Optional[Dict[str, Any]]:
        """
        Get next spell from queue (non-blocking).
        
        Returns:
            Dict with 'spell', 'confidence', 'timestamp' or None if queue empty
        """
        try:
            spell = self.spell_queue.get_nowait()
            self.stats['spells_processed'] += 1
            return spell
        
        except queue.Empty:
            return None
    
    def get_all_spells(self) -> list:
        """
        Get all queued spells at once (useful for batch processing).
        
        Returns:
            List of spell dicts, empty list if no spells queued
        """
        spells = []
        
        while True:
            try:
                spell = self.spell_queue.get_nowait()
                spells.append(spell)
                self.stats['spells_processed'] += 1
            except queue.Empty:
                break
        
        return spells
    
    def is_connected(self) -> bool:
        """Check if server is connected."""
        return self.stats['server_status'] == 'ready'
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        return self.stats.copy()
    
    def print_stats(self):
        """Print client statistics to console."""
        elapsed = time.time() - self.stats['start_time']
        uptime_str = f"{int(elapsed // 3600)}h {int((elapsed % 3600) // 60)}m {int(elapsed % 60)}s"
        
        print("\n" + "="*70)
        print("GESTURE CLIENT STATISTICS".center(70))
        print("="*70)
        print(f"Uptime: {uptime_str}")
        print(f"Connection status: {self.stats['server_status']}")
        print(f"Server: {self.stats['server_host'] or 'Unknown'}")
        print(f"Client: {self.host}:{self.port}")
        print(f"Spells received: {self.stats['spells_received']}")
        print(f"Spells queued: {self.stats['spells_queued']}")
        print(f"Spells processed: {self.stats['spells_processed']}")
        print(f"Connection errors: {self.stats['connection_errors']}")
        print(f"Last spell: {self.stats['last_spell']} ({self.stats['last_confidence']:.1f}%)")
        print("="*70 + "\n")


class GestureControllerDemo:
    """
    Minimal demo showing how to use GestureClient in game loop.
    """
    
    @staticmethod
    def demo():
        """Run demo of gesture client."""
        print("\n" + "="*70)
        print("GESTURE CLIENT DEMO".center(70))
        print("="*70)
        print("This demo shows how to use GestureClient in a game loop")
        print("\nMake sure gesture_server.py is running in another terminal:")
        print("  python gesture_server.py\n")
        print("Listening for spells for 30 seconds...\n")
        
        client = GestureClient(host='localhost', port=6666)
        client.start()
        
        try:
            start_time = time.time()
            spell_count = 0
            
            while time.time() - start_time < 30:
                # Get next spell from queue (non-blocking)
                spell = client.get_next_spell()
                
                if spell:
                    spell_count += 1
                    print(f"[{spell_count}] Caught spell: {spell['spell']} "
                          f"(confidence: {spell['confidence']:.1f}%)")
                else:
                    # Simulate game loop
                    time.sleep(0.01)
            
            print(f"\nDemo complete! Received {spell_count} spells")
        
        except KeyboardInterrupt:
            print("\n[!] Demo interrupted")
        
        finally:
            client.print_stats()
            client.stop()


if __name__ == "__main__":
    # Run demo
    GestureControllerDemo.demo()
