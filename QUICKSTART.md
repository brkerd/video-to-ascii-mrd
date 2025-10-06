# Video Player Engine - Quick Start Guide

## 🚀 Quick Start

### 1. Basic Setup

```python
from video_to_ascii.render_strategy.ascii_strategy import AsciiStrategy, VideoPlayerEngine

# Create strategy and player
strategy = AsciiStrategy()
player = VideoPlayerEngine(strategy, 'idle.mp4')

# Start playing
player.start(transition_type='wipe', transition_direction='top')
```

### 2. With User Input

```python
import threading

def handle_input(player):
    while player.is_running:
        cmd = input("Command: ")
        if cmd == 'q':
            player.stop()
        else:
            player.add_video(f'video_{cmd}.mp4')

# Start input handler
input_thread = threading.Thread(target=handle_input, args=(player,), daemon=True)
input_thread.start()

# Start player
player.start(transition_type='wipe', transition_direction='top')
```

## 🎬 Transition Options

| Type | Direction | Effect |
|------|-----------|--------|
| `wipe` | `top`, `bottom`, `left`, `right` | Progressive wipe across screen |
| `crossfade` | N/A | Smooth alpha blend |
| `scan` | `top`, `bottom` | Scanning line effect |

## ⚙️ Configuration

```python
strategy = AsciiStrategy()
strategy.transition_frames = 20  # Default: 15

# Faster transition (10 frames)
strategy.transition_frames = 10

# Slower, smoother transition (30 frames)  
strategy.transition_frames = 30
```

## 📝 Complete Example

```python
import threading
from video_to_ascii.render_strategy.ascii_strategy import AsciiStrategy, VideoPlayerEngine

# Video library
videos = {
    '1': 'video1.mp4',
    '2': 'video2.mp4',
    '3': 'video3.mp4'
}

# Input handler
def handle_input(player, videos):
    print("Press 1-3 to play video, 'q' to quit")
    while player.is_running:
        try:
            choice = input().strip()
            if choice == 'q':
                player.stop()
            elif choice in videos:
                player.add_video(videos[choice])
                print(f"✓ Queued video {choice}")
        except KeyboardInterrupt:
            player.stop()

# Setup
strategy = AsciiStrategy()
strategy.transition_frames = 20
player = VideoPlayerEngine(strategy, 'idle.mp4')

# Start
input_thread = threading.Thread(target=handle_input, args=(player, videos), daemon=True)
input_thread.start()

try:
    player.start(transition_type='wipe', transition_direction='top')
except KeyboardInterrupt:
    player.stop()
```

## 🎯 Key Points

- **Idle Loop**: Continuously plays until video is queued
- **Automatic Transitions**: Handles idle→video and video→idle automatically
- **Reverse Direction**: Return transitions use opposite direction (top↔bottom)
- **Thread-Safe**: Queue is thread-safe for concurrent access
- **Blocking Call**: `player.start()` blocks until `player.stop()` is called

## 🔧 Customization

### Custom Transition Direction per Video

```python
# Set direction before starting
player.transition_direction = 'left'
player.start(transition_type='wipe', transition_direction='left')

# Or specify in start()
player.start(transition_type='wipe', transition_direction='right')
```

### Change Transition Type

```python
# Wipe (recommended for visibility)
player.start(transition_type='wipe', transition_direction='top')

# Crossfade (smooth)
player.start(transition_type='crossfade')

# Scan (scanning line effect)
player.start(transition_type='scan', transition_direction='top')
```

## ❓ Common Issues

**Q: Video doesn't play**
- Check file path is correct
- Verify video format (MP4 recommended)
- Ensure OpenCV can read the video

**Q: Transitions are choppy**
- Increase `transition_frames` (try 25-30)
- Ensure videos have similar frame rates
- Check terminal rendering performance

**Q: Input not responding**
- Verify input thread is daemon=True
- Check for blocking operations
- Use try-except around input()

## 📚 More Info

See `PLAYER_ENGINE.md` for detailed documentation.
