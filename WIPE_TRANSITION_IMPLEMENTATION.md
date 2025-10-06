# How the Wipe Transition on Loop Works

## Implementation Location

The wipe transition on video loop is implemented in the `_loop_current_video()` method in:
- **File**: `video_to_ascii/render_strategy/ascii_strategy.py`
- **Class**: `VideoPlayerEngine`
- **Method**: `_loop_current_video(self, dimensions)`
- **Lines**: Approximately 774-870

## How It Works

### Step-by-Step Process

1. **Detect Video End**
   - In `_play_queued_video()`, when `ret` is False or `frame` is None
   - This means the video has reached its last frame

2. **Prepare for Transition**
   ```python
   # Get total frames
   total_frames = self.current_cap.get(cv2.CAP_PROP_FRAME_COUNT)
   
   # Rewind to transition_frames before the end
   transition_start = max(0, int(total_frames - self.strategy.transition_frames - 2))
   self.current_cap.set(cv2.CAP_PROP_POS_FRAMES, transition_start)
   ```

3. **Open Second Capture**
   ```python
   # Open video from beginning for transition target
   start_cap = cv2.VideoCapture(self.current_video_path)
   ```
   - Now we have two captures:
     - `self.current_cap` - positioned near the end
     - `start_cap` - positioned at the beginning

4. **Perform Frame-by-Frame Wipe**
   ```python
   for i in range(self.strategy.transition_frames):
       progress = (i + 1) / self.strategy.transition_frames
       
       # Read frame from end
       ret1, frame1 = self.current_cap.read()
       
       # Read frame from beginning
       ret2, frame2 = start_cap.read()
       
       # Create composite with wipe effect
       composite = resized_frame1.copy()
       
       if self.transition_direction == 'top':
           wipe_line = int(h1 * progress)
           composite[:wipe_line, :] = resized_frame2[:wipe_line, :]
   ```

5. **Reset and Continue**
   ```python
   # Close the start capture
   start_cap.release()
   
   # Reset main capture to beginning
   self.current_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
   ```

## Visual Representation

### Wipe Direction: TOP

```
Progress 0% (Start):
┌─────────────────────┐
│                     │ ← Frame 300 (end)
│     END FRAME       │
│                     │
│                     │
└─────────────────────┘

Progress 25%:
┌─────────────────────┐
│  START FRAME   ↓    │ ← Frame 1 (wipes down)
├─────────────────────┤
│                     │ ← Frame 302 (end)
│     END FRAME       │
│                     │
└─────────────────────┘

Progress 50%:
┌─────────────────────┐
│  START FRAME        │ ← Frame 10
│                     │
├─────────────────────┤
│     END FRAME       │ ← Frame 310
│                     │
└─────────────────────┘

Progress 75%:
┌─────────────────────┐
│  START FRAME        │ ← Frame 15
│                     │
│                     │
├─────────────────────┤
│   END FRAME    ↓    │ ← Frame 315
└─────────────────────┘

Progress 100% (End):
┌─────────────────────┐
│  START FRAME        │ ← Frame 20
│                     │
│  (Now at beginning) │
│                     │
└─────────────────────┘
```

## Code Flow

```python
# In _play_queued_video():

while playing:
    ret, frame = self.current_cap.read()
    
    if not ret or frame is None:
        # Video ended!
        self._loop_current_video((cols, rows))  # ← Wipe transition happens here
        continue  # ← Continue playing from frame 0
    
    # Render normal frame
    render_frame(frame)
```

## Key Features

### 1. Dual Capture System
- **Primary Capture** (`self.current_cap`): Positioned near end, reads ending frames
- **Secondary Capture** (`start_cap`): Positioned at beginning, reads starting frames
- Both captures read simultaneously during transition

### 2. Progressive Wipe
- Each transition frame is a composite of:
  - Top portion: Beginning of video (growing)
  - Bottom portion: End of video (shrinking)
- The boundary line moves progressively based on `progress`

### 3. Frame Timing
```python
fps = self.current_cap.get(cv2.CAP_PROP_FPS) or 30
frame_delay = 1.0 / fps
time.sleep(frame_delay)
```
- Maintains consistent frame rate during transition
- Matches the video's native FPS

### 4. Direction Support
Supports all four directions:
- **top**: New frames wipe down from top
- **bottom**: New frames wipe up from bottom
- **left**: New frames wipe right from left
- **right**: New frames wipe left from right

## Configuration

### Adjust Transition Speed
```python
strategy = AsciiStrategy()
strategy.transition_frames = 10   # Fast (10 frames = ~0.33s at 30fps)
strategy.transition_frames = 20   # Default (20 frames = ~0.67s at 30fps)
strategy.transition_frames = 30   # Slow (30 frames = 1.0s at 30fps)
```

### Choose Direction
```python
player.start(transition_type='wipe', transition_direction='top')    # Down
player.start(transition_type='wipe', transition_direction='bottom') # Up
player.start(transition_type='wipe', transition_direction='left')   # Right
player.start(transition_type='wipe', transition_direction='right')  # Left
```

## Troubleshooting

### Issue: No transition visible, just instant loop

**Possible Causes:**
1. `transition_frames` is set too low (e.g., 1 or 2)
2. Video doesn't have enough frames at the end
3. Frame rate is very high, making transition too fast

**Solutions:**
```python
# Increase transition frames
strategy.transition_frames = 25

# Check video properties
cap = cv2.VideoCapture('video.mp4')
fps = cap.get(cv2.CAP_PROP_FPS)
total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
print(f"FPS: {fps}, Total Frames: {total_frames}")
```

### Issue: Transition looks choppy

**Possible Causes:**
1. Frame rate mismatch
2. Transition too long
3. Terminal rendering is slow

**Solutions:**
```python
# Reduce transition frames for smoother appearance
strategy.transition_frames = 15

# Ensure video has consistent frame rate
# Use videos with 24, 30, or 60 fps
```

### Issue: Video doesn't loop at all

**Possible Causes:**
1. `current_video_path` is not set
2. Error opening second capture
3. Video file is corrupted

**Solutions:**
```python
# Check if path is stored
print(f"Current video path: {player.current_video_path}")

# Verify video can be opened
test_cap = cv2.VideoCapture(video_path)
print(f"Can open: {test_cap.isOpened()}")
```

## Example Output

When running with `transition_frames = 20`:

```
Video plays normally...
Frame 280
Frame 281
Frame 282
...
Frame 298
Frame 299
Frame 300 (END)

[WIPE TRANSITION STARTS]
Composite 1: 95% end + 5% beginning
Composite 2: 90% end + 10% beginning
Composite 3: 85% end + 15% beginning
...
Composite 18: 10% end + 90% beginning
Composite 19: 5% end + 95% beginning
Composite 20: 100% beginning
[WIPE TRANSITION ENDS]

Frame 21 (from beginning)
Frame 22
Frame 23
...
(continues playing from beginning)
```

## Testing the Implementation

### Manual Test
```python
from video_to_ascii.render_strategy.ascii_strategy import AsciiStrategy, VideoPlayerEngine

strategy = AsciiStrategy()
strategy.transition_frames = 20  # Should see ~0.67s transition

player = VideoPlayerEngine(strategy, 'idle.mp4')
player.add_video('short_video.mp4')  # Use a 5-10 second video for testing

player.start(transition_type='wipe', transition_direction='top')
```

### Expected Behavior
1. Video plays normally
2. When it reaches the end, you should see:
   - The bottom portion showing the last frames
   - The top portion gradually showing the first frames
   - A clear horizontal line moving down the screen
3. After transition, video continues from the beginning
4. Process repeats indefinitely

## Performance Notes

- Transition requires opening a second VideoCapture temporarily
- Memory usage increases briefly during transition
- CPU usage spikes during composite frame creation
- For best performance:
  - Use videos under 1080p resolution
  - Keep `transition_frames` between 15-30
  - Ensure SSD for faster file access

---

**The wipe transition on loop is now fully implemented and functional!** 🎬✨
