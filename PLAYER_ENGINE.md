# Video Player Engine

A dynamic video player engine that loops an idle video and seamlessly transitions to queued videos based on user input.

## Features

- **Idle Loop**: Continuously plays a default idle video
- **Dynamic Queueing**: Add videos to play on-demand
- **Smooth Transitions**: Three transition types supported:
  - `wipe`: Video wipes across the screen (top/bottom/left/right)
  - `crossfade`: Smooth alpha blending between videos
  - `scan`: Scanning line effect with character-by-character replacement
- **Thread-Safe**: Queue management with thread synchronization
- **State Machine**: Clean state management (IDLE → TRANSITIONING → PLAYING → IDLE)

## Architecture

### State Machine

```
┌─────────┐
│  IDLE   │◄──────────────────┐
│ (loop)  │                   │
└────┬────┘                   │
     │ video queued           │ video ends
     │                        │
     ▼                        │
┌──────────────┐              │
│ TRANSITIONING│              │
└──────┬───────┘              │
       │ transition complete  │
       │                      │
       ▼                      │
  ┌─────────┐                 │
  │ PLAYING │─────────────────┘
  └─────────┘
```

### How It Works

1. **Initialization**: Create `VideoPlayerEngine` with an idle video path
2. **Start Loop**: Engine begins playing idle video on repeat
3. **Queue Video**: User input triggers `add_video()` to queue a video
4. **Transition**: Engine detects queue, transitions from idle to queued video
5. **Play**: Queued video plays to completion
6. **Return**: Transitions back to idle video (reverse direction)
7. **Repeat**: Loop continues until `stop()` is called

## Usage

### Basic Example

```python
from video_to_ascii.render_strategy.ascii_strategy import AsciiStrategy, VideoPlayerEngine

# Create strategy
strategy = AsciiStrategy()
strategy.transition_frames = 20  # Adjust transition duration

# Create player engine
player = VideoPlayerEngine(strategy, 'path/to/idle.mp4')

# Add videos to queue
player.add_video('path/to/video1.mp4')

# Start player with wipe transition
player.start(transition_type='wipe', transition_direction='top')
```

### Interactive Example

```python
import threading
from video_to_ascii.render_strategy.ascii_strategy import AsciiStrategy, VideoPlayerEngine

def input_handler(player):
    video_map = {
        '1': 'video1.mp4',
        '2': 'video2.mp4',
        '3': 'video3.mp4'
    }
    
    while player.is_running:
        user_input = input("Enter video number (1-3) or 'q' to quit: ")
        
        if user_input == 'q':
            player.stop()
            break
        elif user_input in video_map:
            player.add_video(video_map[user_input])

# Setup
strategy = AsciiStrategy()
player = VideoPlayerEngine(strategy, 'idle.mp4')

# Start input handler in background
input_thread = threading.Thread(target=input_handler, args=(player,), daemon=True)
input_thread.start()

# Start player
player.start(transition_type='wipe', transition_direction='top')
```

## Configuration

### Transition Types

1. **Wipe Transition** (Recommended)
   ```python
   player.start(transition_type='wipe', transition_direction='top')
   ```
   - Directions: `'top'`, `'bottom'`, `'left'`, `'right'`
   - New video progressively replaces old video
   - Clean, visible effect

2. **Crossfade Transition**
   ```python
   player.start(transition_type='crossfade')
   ```
   - Smooth alpha blending
   - Gradual transition between videos

3. **Scan Transition**
   ```python
   player.start(transition_type='scan', transition_direction='top')
   ```
   - Character-by-character scanning effect
   - Directions: `'top'`, `'bottom'`
   - Visible scanning line

### Transition Duration

Adjust the number of frames for transitions:

```python
strategy = AsciiStrategy()
strategy.transition_frames = 30  # Longer transition (default: 15)
```

- Lower values = faster transitions
- Higher values = slower, smoother transitions
- Recommended range: 15-30 frames

## API Reference

### VideoPlayerEngine

#### `__init__(strategy, idle_video_path)`
Initialize the player engine.

**Parameters:**
- `strategy`: `AsciiStrategy` instance for rendering
- `idle_video_path`: Path to the idle/default video

#### `add_video(video_path)`
Add a video to the playback queue.

**Parameters:**
- `video_path`: Path to video file

#### `start(transition_type='wipe', transition_direction='top')`
Start the player engine (blocking call).

**Parameters:**
- `transition_type`: Transition effect (`'wipe'`, `'crossfade'`, `'scan'`)
- `transition_direction`: Direction for wipe/scan (`'top'`, `'bottom'`, `'left'`, `'right'`)

#### `stop()`
Stop the player engine and clean up.

### PlayerState

State constants:
- `PlayerState.IDLE`: Playing idle video
- `PlayerState.TRANSITIONING`: Performing transition
- `PlayerState.PLAYING`: Playing queued video

## Tips & Best Practices

1. **Video Format**: Use MP4 format for best compatibility
2. **Resolution**: Match idle and queued video resolutions for smoother transitions
3. **Frame Rate**: Consistent FPS across videos recommended
4. **Terminal Size**: Larger terminal = better visual quality
5. **Input Handling**: Use daemon threads for non-blocking input
6. **Error Handling**: Check if videos exist before adding to queue

## Troubleshooting

### Video Won't Play
- Verify video path is correct
- Check video codec compatibility with OpenCV
- Ensure video file is not corrupted

### Transition Looks Choppy
- Increase `transition_frames` for smoother effect
- Ensure videos have similar frame rates
- Check terminal rendering speed

### Input Not Working
- Make sure input thread is set as daemon
- Check for blocking operations
- Use `try-except` for input errors

## Example Application

See `player_example.py` for a complete working example with:
- User input handling
- Multiple video options
- Error handling
- Clean shutdown

Run it with:
```bash
python player_example.py
```

## Future Enhancements

Potential improvements:
- Multiple video queue support
- Playlist randomization
- Volume control integration
- Custom transition effects
- Real-time transition switching
- Network video streaming support
