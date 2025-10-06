# Video Player Engine - Visual Flow Diagram

## State Machine Diagram

```
                     ┌──────────────────────────────────────┐
                     │                                      │
                     │         VIDEO PLAYER ENGINE          │
                     │                                      │
                     └──────────────────────────────────────┘
                                      │
                                      ▼
                     ┌──────────────────────────────────────┐
                     │         PlayerState.IDLE             │
                     │                                      │
                     │  ┌────────────────────────────┐     │
                     │  │  Loop idle.mp4             │     │
                     │  │  Check queue every frame    │     │
                     │  │  Display ASCII frames       │     │
                     │  └────────────────────────────┘     │
                     └──────────────────────────────────────┘
                                      │
                        Queue not empty? ───────────┐
                                      │             │
                                      │ Yes         │ No (continue loop)
                                      ▼             │
                     ┌──────────────────────────────▼───────┐
                     │   PlayerState.TRANSITIONING          │
                     │                                      │
                     │  ┌────────────────────────────┐     │
                     │  │  Get video from queue       │     │
                     │  │  Perform wipe transition    │     │
                     │  │  (idle → queued video)      │     │
                     │  └────────────────────────────┘     │
                     └──────────────────────────────────────┘
                                      │
                                      ▼
                     ┌──────────────────────────────────────┐
                     │        PlayerState.PLAYING           │
                     │                                      │
                     │  ┌────────────────────────────┐     │
                     │  │  Play queued video         │     │
                     │  │  Display ASCII frames       │     │
                     │  │  Until video ends           │     │
                     │  └────────────────────────────┘     │
                     └──────────────────────────────────────┘
                                      │
                                      │ Video finished
                                      ▼
                     ┌──────────────────────────────────────┐
                     │   PlayerState.TRANSITIONING          │
                     │                                      │
                     │  ┌────────────────────────────┐     │
                     │  │  Perform wipe transition    │     │
                     │  │  (queued video → idle)      │     │
                     │  │  Reverse direction          │     │
                     │  └────────────────────────────┘     │
                     └──────────────────────────────────────┘
                                      │
                                      │
                                      ▼
                            Back to IDLE state
                          (loop continues...)
```

## Wipe Transition Visualization

### Forward Transition (idle → queued video)

Direction: **TOP**

```
Frame 1/20:    ████████████████████  ← Queued video (wipes down)
               ░░░░░░░░░░░░░░░░░░░░  ← Idle video
               ░░░░░░░░░░░░░░░░░░░░
               ░░░░░░░░░░░░░░░░░░░░
               ░░░░░░░░░░░░░░░░░░░░

Frame 10/20:   ████████████████████
               ████████████████████
               ████████████████████
               ░░░░░░░░░░░░░░░░░░░░  ← Idle video (partially visible)
               ░░░░░░░░░░░░░░░░░░░░

Frame 20/20:   ████████████████████
               ████████████████████
               ████████████████████
               ████████████████████
               ████████████████████  ← Queued video (fully visible)
```

### Return Transition (queued video → idle)

Direction: **BOTTOM** (opposite of forward)

```
Frame 1/20:    ████████████████████  ← Queued video
               ████████████████████
               ████████████████████
               ████████████████████
               ░░░░░░░░░░░░░░░░░░░░  ← Idle video (wipes up)

Frame 10/20:   ████████████████████
               ████████████████████
               ░░░░░░░░░░░░░░░░░░░░  ← Idle video
               ░░░░░░░░░░░░░░░░░░░░
               ░░░░░░░░░░░░░░░░░░░░

Frame 20/20:   ░░░░░░░░░░░░░░░░░░░░
               ░░░░░░░░░░░░░░░░░░░░
               ░░░░░░░░░░░░░░░░░░░░
               ░░░░░░░░░░░░░░░░░░░░
               ░░░░░░░░░░░░░░░░░░░░  ← Idle video (fully visible)
```

## Thread Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       MAIN THREAD                           │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │         VideoPlayerEngine.start()                    │   │
│  │                                                      │   │
│  │  while is_running:                                   │   │
│  │    if state == IDLE:                                 │   │
│  │      _play_idle()                                    │   │
│  │    elif state == PLAYING:                            │   │
│  │      _play_queued_video()                            │   │
│  │                                                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                           ▲                                 │
│                           │                                 │
│                    Reads from queue                         │
│                           │                                 │
└───────────────────────────┼─────────────────────────────────┘
                            │
                    ┌───────┴────────┐
                    │  Thread-Safe   │
                    │  Queue.Queue() │
                    └───────┬────────┘
                            │
                    Writes to queue
                            │
┌───────────────────────────┼─────────────────────────────────┐
│                 INPUT HANDLER THREAD                         │
│                      (daemon=True)                           │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │       input_handler(player, videos)                  │   │
│  │                                                      │   │
│  │  while player.is_running:                            │   │
│  │    user_input = input()                              │   │
│  │    if user_input == 'q':                             │   │
│  │      player.stop()                                   │   │
│  │    elif user_input in videos:                        │   │
│  │      player.add_video(videos[user_input])            │   │
│  │                                                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

```
User Input
    │
    ▼
input_handler()
    │
    │ user presses '1'
    ▼
player.add_video('video1.mp4')
    │
    │ adds to queue
    ▼
video_queue.put('video1.mp4')
    │
    │ thread-safe
    ▼
Main Loop (_play_idle)
    │
    │ checks queue
    ▼
video_queue.empty() == False
    │
    │ state → TRANSITIONING
    ▼
_transition_to_video()
    │
    │ wipe transition
    ▼
state → PLAYING
    │
    ▼
_play_queued_video()
    │
    │ plays until end
    ▼
Video finished
    │
    ▼
_transition_back_to_idle()
    │
    │ reverse wipe
    ▼
state → IDLE
    │
    ▼
Back to idle loop
```

## Example Timeline

```
Time →
0s ────────────────────────────────────────────────────
      [IDLE: idle.mp4 looping]

5s ────────────────────────────────────────────────────
      User presses '1'
      ↓
      Queue: ['video1.mp4']

6s ────────────────────────────────────────────────────
      [TRANSITIONING: wipe from top]
      idle.mp4 → video1.mp4

7s ────────────────────────────────────────────────────
      [PLAYING: video1.mp4]

17s ───────────────────────────────────────────────────
      video1.mp4 ends
      ↓
      [TRANSITIONING: wipe from bottom]
      video1.mp4 → idle.mp4

18s ───────────────────────────────────────────────────
      [IDLE: idle.mp4 looping]

20s ───────────────────────────────────────────────────
      User presses '2'
      ↓
      Queue: ['video2.mp4']
      (cycle repeats...)
```

## Component Interaction

```
┌─────────────────┐
│  AsciiStrategy  │
│                 │
│  - resize_frame │◄────────────┐
│  - convert_...  │             │
│  - wipe_trans.. │             │
└─────────────────┘             │
                                │ uses
                                │
┌──────────────────────────────┴─────────────────┐
│           VideoPlayerEngine                    │
│                                                │
│  Properties:                                   │
│    - strategy: AsciiStrategy                   │
│    - idle_video_path: str                      │
│    - video_queue: Queue                        │
│    - state: PlayerState                        │
│    - is_running: bool                          │
│                                                │
│  Methods:                                      │
│    - add_video(path)                           │
│    - start(type, direction)                    │
│    - _play_idle()                              │
│    - _transition_to_video()                    │
│    - _play_queued_video()                      │
│    - _transition_back_to_idle()                │
│    - stop()                                    │
└────────────────────────────────────────────────┘
        ▲                           ▲
        │                           │
        │ controls                  │ adds videos
        │                           │
┌───────┴──────┐          ┌─────────┴────────┐
│  Main Thread │          │  Input Thread    │
│  (blocking)  │          │  (daemon)        │
└──────────────┘          └──────────────────┘
```

## Key Features Illustrated

### 1. Non-Blocking Input
```
Main Thread               Input Thread
    │                         │
    ├─ Render frame          │
    ├─ Render frame          ├─ Wait for input
    ├─ Render frame          │
    ├─ Render frame          ├─ Get '1'
    ├─ Check queue ◄─────────┼─ Add video
    ├─ Found video!          │
    ├─ Transition            ├─ Wait for input
    ├─ Play video            │
    └─ ...                   └─ ...
```

### 2. Thread-Safe Queue
```
Input Thread              Queue              Main Thread
    │                      │                     │
    ├─ add_video() ───────►│                     │
    │                      ├─ Lock               │
    │                      ├─ Put video          │
    │                      ├─ Unlock             │
    │                      │                     │
    │                      │◄──────── Check empty
    │                      ├─ Lock               │
    │                      ├─ Get video          │
    │                      ├─ Unlock             │
    │                      │────────────────────►│
```

---

**Legend:**
- `█` = New video content
- `░` = Old video content
- `↓` = Wipe direction
- `◄` = Data flow
- `▼` = Process flow
