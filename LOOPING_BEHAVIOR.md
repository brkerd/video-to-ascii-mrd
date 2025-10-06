# Video Looping Behavior Guide

## 🔄 How Video Looping Works

### Overview
Videos now loop continuously with smooth wipe transitions until you:
1. Queue a different video
2. Manually return to idle with `return_to_idle()`
3. Stop the player

## Visual Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    IDLE STATE                               │
│                                                             │
│  ┌─────────────────────────────────┐                       │
│  │  Playing: idle.mp4 (looping)    │                       │
│  │  Status: Seamless loop, no      │                       │
│  │          transition effect       │                       │
│  └─────────────────────────────────┘                       │
│                      │                                       │
│         User presses '1' to queue video1.mp4               │
│                      │                                       │
└──────────────────────┼─────────────────────────────────────┘
                       │
                       ▼ WIPE TRANSITION (top)
┌──────────────────────────────────────────────────────────────┐
│                 PLAYING STATE                                │
│                                                              │
│  ┌────────────────────────────────────┐                     │
│  │  Playing: video1.mp4               │                     │
│  │  Status: Playing normally           │                     │
│  │  Frame: 1 → 100 → 200 → 299        │                     │
│  └────────────────────────────────────┘                     │
│                      │                                        │
│            Video reaches end (frame 300)                     │
│                      │                                        │
│                      ▼ WIPE TRANSITION (top)                 │
│  ┌────────────────────────────────────┐                     │
│  │  Transition: End → Beginning        │                     │
│  │  From: Frame 300 of video1.mp4     │                     │
│  │  To:   Frame 1 of video1.mp4       │                     │
│  └────────────────────────────────────┘                     │
│                      │                                        │
│                      ▼                                        │
│  ┌────────────────────────────────────┐                     │
│  │  Playing: video1.mp4 (LOOPING)     │                     │
│  │  Status: Playing normally           │                     │
│  │  Frame: 1 → 100 → 200 → 299        │                     │
│  └────────────────────────────────────┘                     │
│                      │                                        │
│            Video reaches end again                           │
│                      │                                        │
│                      ▼ WIPE TRANSITION (top)                 │
│              (Loops back again...)                           │
│                      │                                        │
│         User presses '2' to queue video2.mp4                │
│                      │                                        │
│                      ▼ WIPE TRANSITION (top)                 │
│  ┌────────────────────────────────────┐                     │
│  │  Transition: video1 → video2        │                     │
│  │  From: Current frame of video1.mp4  │                     │
│  │  To:   Frame 1 of video2.mp4       │                     │
│  └────────────────────────────────────┘                     │
│                      │                                        │
│                      ▼                                        │
│  ┌────────────────────────────────────┐                     │
│  │  Playing: video2.mp4 (LOOPING)     │                     │
│  │  Status: Playing normally           │                     │
│  │  Frame: 1 → 150 → 299 → 449        │                     │
│  └────────────────────────────────────┘                     │
│                      │                                        │
│         User presses 'i' to return to idle                  │
│                      │                                        │
└──────────────────────┼─────────────────────────────────────┘
                       │
                       ▼ WIPE TRANSITION (bottom - reverse!)
┌──────────────────────────────────────────────────────────────┐
│                    IDLE STATE                                │
│                                                              │
│  ┌─────────────────────────────────┐                        │
│  │  Playing: idle.mp4 (looping)    │                        │
│  │  Status: Back to idle state      │                        │
│  └─────────────────────────────────┘                        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## Timeline Example

```
Time    State      Video         Action
────────────────────────────────────────────────────────────────
0:00    IDLE       idle.mp4      Player starts
0:05    IDLE       idle.mp4      Idle loops seamlessly
0:10    IDLE       idle.mp4      User presses '1'
        ↓ WIPE TRANSITION (top)
0:11    PLAYING    video1.mp4    Playing video1
0:21    PLAYING    video1.mp4    Video1 reaches end
        ↓ WIPE TRANSITION (top)
0:22    PLAYING    video1.mp4    Video1 loops back to start
0:32    PLAYING    video1.mp4    Video1 reaches end again
        ↓ WIPE TRANSITION (top)
0:33    PLAYING    video1.mp4    Video1 loops again
0:38    PLAYING    video1.mp4    User presses '2'
        ↓ WIPE TRANSITION (top)
0:39    PLAYING    video2.mp4    Now playing video2
0:59    PLAYING    video2.mp4    Video2 reaches end
        ↓ WIPE TRANSITION (top)
1:00    PLAYING    video2.mp4    Video2 loops back
1:15    PLAYING    video2.mp4    User presses 'i'
        ↓ WIPE TRANSITION (bottom - reverse)
1:16    IDLE       idle.mp4      Back to idle
1:20    IDLE       idle.mp4      Idle continues looping
```

## Key Behaviors

### 1. Idle Loop (No Transition)
```
idle.mp4: Frame 1 → 2 → 3 → ... → 100 [END]
                                        ↓ (instant reset, no transition)
idle.mp4: Frame 1 → 2 → 3 → ... → 100 [END]
                                        ↓ (instant reset, no transition)
idle.mp4: Frame 1 → 2 → 3 → ...
```
**Why?** Idle is background state, constant presence, no visual disruption needed.

### 2. Video Loop (With Wipe Transition)
```
video1.mp4: Frame 1 → 2 → ... → 99 → 100 [END]
                                            ↓
                                     [WIPE TRANSITION]
                                     Frame 100 (end)
                                            ↓ wipes to ↓
                                     Frame 1 (beginning)
                                            ↓
video1.mp4: Frame 1 → 2 → ... → 99 → 100 [END]
                                            ↓
                                     [WIPE TRANSITION]
                                          (loops...)
```
**Why?** Creates engaging visual effect, signals loop is happening, maintains user attention.

### 3. Video to Video Transition
```
video1.mp4: Frame 1 → 2 → 3 → ... → 50 [User presses '2']
                                        ↓
                                 [WIPE TRANSITION]
                                 video1 Frame 50
                                        ↓ wipes to ↓
                                 video2 Frame 1
                                        ↓
video2.mp4: Frame 1 → 2 → 3 → ... → 100 [END]
                                        ↓
                                 [WIPE TRANSITION]
                                 video2 Frame 100
                                        ↓ wipes to ↓
                                 video2 Frame 1
                                        ↓
                                    (loops...)
```

### 4. Return to Idle (Reverse Direction)
```
video2.mp4: Frame 1 → 2 → ... → 75 [User presses 'i']
                                    ↓
                             [WIPE TRANSITION - BOTTOM]
                             video2 Frame 75
                                    ↓ wipes from bottom ↓
                             idle Frame 1
                                    ↓
idle.mp4:   Frame 1 → 2 → 3 → ... (seamless loops...)
```
**Why reverse?** Visual symmetry - went in from top, come out from bottom.

## User Control Summary

| Input | Current State | Result | Transition |
|-------|--------------|--------|------------|
| '1' | IDLE | Play video1 (loops) | Top wipe |
| '2' | Playing video1 | Switch to video2 (loops) | Top wipe |
| '3' | Playing video2 | Switch to video3 (loops) | Top wipe |
| 'i' | Playing any video | Return to idle | Bottom wipe (reverse) |
| 'q' | Any | Stop player | None |

## Code Examples

### Queuing Multiple Videos
```python
# Start in idle
player.start()

# User interactions:
player.add_video('video1.mp4')  # Wipe: idle → video1, then video1 loops
player.add_video('video2.mp4')  # Wipe: video1 → video2, then video2 loops
player.add_video('video3.mp4')  # Wipe: video2 → video3, then video3 loops
player.return_to_idle()         # Wipe: video3 → idle (reverse direction)
```

### Checking Current Behavior
```python
# In _play_queued_video():

while playing:
    # Check for new video
    if not self.video_queue.empty():
        new_video = self.video_queue.get()
        
        if new_video is None:
            # Return to idle
            self._transition_back_to_idle()
            return
        else:
            # Switch to new video
            self._transition_to_next_video(new_video)
            continue
    
    # Read frame
    ret, frame = self.current_cap.read()
    
    if not ret:
        # Video ended - loop it!
        self._loop_current_video()
        continue
    
    # Render frame...
```

## Transition Details

### Loop Transition Implementation
```python
def _loop_current_video(self, dimensions):
    # Reopen video from start
    new_cap = cv2.VideoCapture(self.current_video_path)
    
    # Current cap is at end, new cap is at start
    # Perform wipe transition
    self.strategy.wipe_transition(
        self.current_cap,  # End of video
        new_cap,           # Beginning of video
        dimensions,
        direction='top'    # Same as forward direction
    )
    
    # Replace old with new
    self.current_cap.release()
    self.current_cap = new_cap
```

## Visual Wipe Effect

```
Loop Transition (video end → video beginning):

Frame 1/20:  ████████████████  ← Beginning (wipes down)
             ░░░░░░░░░░░░░░░░  ← End
             ░░░░░░░░░░░░░░░░

Frame 10/20: ████████████████
             ████████████████
             ░░░░░░░░░░░░░░░░  ← End (partially visible)

Frame 20/20: ████████████████
             ████████████████
             ████████████████  ← Beginning (fully visible)
             
Now video plays from beginning again...
```

## Configuration

### Adjust Loop Transition Speed
```python
strategy = AsciiStrategy()

# Fast loop transition (10 frames)
strategy.transition_frames = 10

# Smooth loop transition (30 frames) 
strategy.transition_frames = 30

# Default (20 frames)
strategy.transition_frames = 20
```

### Change Transition Direction
```python
# Wipe from top (default)
player.start(transition_type='wipe', transition_direction='top')

# Wipe from bottom
player.start(transition_type='wipe', transition_direction='bottom')

# Wipe from left
player.start(transition_type='wipe', transition_direction='left')

# Wipe from right
player.start(transition_type='wipe', transition_direction='right')
```

## Best Practices

1. **Video Length**: 10-30 seconds works well for looping
2. **Transition Frames**: 15-25 frames for smooth loop transitions
3. **Consistent FPS**: Use videos with same frame rate
4. **Loop-Friendly Content**: Content that flows well from end to beginning
5. **User Control**: Always provide option to return to idle or change videos

## Troubleshooting

**Q: Loop transition looks choppy**
- Increase `transition_frames` (try 25-30)
- Ensure video has consistent frame rate
- Check terminal rendering performance

**Q: Video doesn't loop, goes to idle**
- Verify you're using updated code
- Check that `_loop_current_video()` is called on video end
- Ensure `current_video_path` is being set correctly

**Q: Can't return to idle**
- Use `player.return_to_idle()` method
- Or press 'i' if using test.py input handler
- Check that queue is handling `None` correctly

---

**Enjoy your looping video player!** 🎥🔄
