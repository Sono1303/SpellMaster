# SpellMaster - System Architecture

## Overview

When `start_all.py` is executed, it launches 2 independent processes communicating via UDP:

- **Process 1 (AI Controller)**: Webcam capture, MediaPipe hand detection, ML gesture prediction, UDP broadcast
- **Process 2 (Pygame Game)**: Game loop at 60 FPS, spell casting, monster AI, wave system, rendering

## Architecture Diagram

```mermaid
---
id: a1b5ca08-45de-4606-83f7-ee5d6c2b85d5
---
graph LR
    subgraph LAUNCHER["LAUNCHER"]
        direction TB
        L1["start_all.py"]
    end
    
    subgraph AICONT["<b>AI CONTROLLER</b>"]
        direction TB
        subgraph CAP["<b>Capture&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</b>"]
            GS1["Webcam 1280x720"]
            GS2["MediaPipe"]
            GS3["Dual-hand"]
            GS1 --> GS2 --> GS3
        end
        
        subgraph SIG["<b>Processing&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</b>"]
            GS4["Extract 42 pts"]
            GS5["One Euro Filter"]
            GS6["Normalize 84D"]
            GS4 --> GS5 --> GS6
        end
        
        subgraph INF["<b>Inference&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</b>"]
            GS7["SVM RBF"]
            GS8["Confidence ≥85%"]
            GS7 --> GS8
        end
        
        GS3 --> GS4
        GS6 --> GS7
    end
    
    subgraph UDP_SOCK["<b>UDP&nbsp;Socket&nbsp;&nbsp;&nbsp;</b>"]
        direction TB
        U1["spell_id"]
        U2["confidence"]
        U3["timestamp"]
        U1 ~~~ U2 ~~~ U3
    end
    
    subgraph GCC["<b>Gesture&nbsp;Client&nbsp;&nbsp;&nbsp;&nbsp;</b>"]
        direction TB
        GC1["UDP Listener"]
        GC2["Thread-safe"]
        GC3["FIFO Queue"]
        GC1 --> GC2 --> GC3
    end
    
    subgraph PYGAME["<b>PYGAME GAME</b><br/><br/>"]
        direction TB
        
        subgraph MAIN["<b>Main Loop</b>"]
            direction TB
            MP2["handle_events"]
            MP1["process_spells"]
            MP3["update_state"]
            MP4["render_frame"]
            MP2 --> MP3
            MP1 --> MP3 --> MP4
        end
        
        subgraph GAME["<b>Game Logic</b>"]
            direction TB
            M1["entity.py<br/>Player, Monster"]
            M2["spell.py<br/>Effects"]
            M3["spell_bar.py<br/>UI"]
            M1 ~~~ M2 ~~~ M3
        end
        
        subgraph OUT["<b>Visual Output</b>"]
            direction TB
            M5["resource_mgr<br/>Assets"]
            M4["map_engine<br/>Tiles"]
            M7["player_ui<br/>HUD"]
            M5 ~~~ M4 ~~~ M7
        end
        
        subgraph AUD["<b>Audio</b>"]
            direction TB
            M6["sfx_manager<br/>Sound Effects"]
        end
        
        subgraph CFG["<b>Config</b>"]
            direction TB
            C["stat_config<br/>level_config<br/>anim_config<br/>sfx_config<br/>assets_map"]
        end
        
        MAIN -.-> GAME
        MAIN -.-> OUT
        GAME -.-> AUD
        OUT -.-> AUD
        CFG -.-> MAIN
        CFG -.-> GAME
        CFG -.-> OUT
    end
    
    LAUNCHER --> AICONT
    AICONT --> UDP_SOCK
    UDP_SOCK --> GCC
    GCC --> PYGAME
    
    style LAUNCHER fill:#e94560,stroke:#fff,stroke-width:2px,color:#fff
    style AICONT fill:#16213e,stroke:#0f3460,stroke-width:2px,color:#fff
    style CAP fill:#1f4788,stroke:#0f3460,color:#fff
    style SIG fill:#1f4788,stroke:#0f3460,color:#fff
    style INF fill:#1f4788,stroke:#0f3460,color:#fff
    
    style UDP_SOCK fill:#c0504d,stroke:#fff,stroke-width:3px,color:#fff,font-size:16px
    style GCC fill:#d9534f,stroke:#fff,stroke-width:3px,color:#fff,font-size:16px
    
    style PYGAME fill:#1a2d4d,stroke:#533483,stroke-width:2px,color:#fff
    style MAIN fill:#5b7ba1,stroke:#fff,stroke-width:1px,color:#fff
    style GAME fill:#2d65a8,stroke:#fff,stroke-width:1px,color:#fff
    style OUT fill:#2d8f4d,stroke:#fff,stroke-width:1px,color:#fff
    style AUD fill:#f0ad4e,stroke:#fff,stroke-width:1px,color:#000
    style CFG fill:#9b59b6,stroke:#fff,stroke-width:1px,color:#fff
```

## Module Descriptions

### AI Controller Side

| Module | File | Description |
|--------|------|-------------|
| Gesture Server | `gesture_server.py` | Main server loop: webcam capture, hand detection, ML prediction, UDP broadcast |
| Spell Recognizer | `spell_recognizer.py` | MediaPipe hand landmark extraction, normalization, sklearn model inference |
| One Euro Filter | `utils/one_euro_filter.py` | Adaptive low-pass filter to reduce MediaPipe landmark jitter |
| Config | `config.py` | Global constants, paths, colors, thresholds |

### Pygame Game Side

| Module | File | Description |
|--------|------|-------------|
| Gesture Client | `gesture_client.py` | UDP listener thread, receives spell events, queues them for game loop |
| Main Game | `main_pygame.py` | Game loop at 60 FPS: events, state update, rendering, wave system |
| Entity | `entity.py` | Player, Monster, Statue, Portal classes with state machines and collision |
| Spell | `spell.py` | SpellEffect (animation + damage), SpellManager (cast logic, special effects) |
| Spell Bar | `spell_bar.py` | UI bar with 10 spell icons, highlight, kill counter, unlock system |
| Map Engine | `map_engine.py` | Tile-based map rendering from map_data |
| Resource Manager | `resource_manager.py` | Centralized asset loading: images, sounds, sprite sheets |
| SFX Manager | `sfx_manager.py` | Sound effects playback with volume, speed, trim, looping |
| Player UI | `player_ui.py` | HP and Mana container-based HUD with blink animations |

### Config Files

| File | Description |
|------|-------------|
| `stat_config.json` | Player stats, spell damage/effects, monster stats, UI sizing |
| `level_config.json` | Portal positions, wave definitions (monster types + spawn delays) |
| `animations_config.json` | Sprite sheet paths, grid layout, frame counts for all entities |
| `sfx_config.json` | Sound effect paths, volume, speed, trim, loop settings |
| `assets_map.json` | Map tile sprite sheets and decoration asset definitions |
