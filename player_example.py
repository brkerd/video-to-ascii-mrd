"""
Example usage of the VideoPlayerEngine with idle loop and dynamic video queueing.

This script demonstrates how to:
1. Create a video player that loops an idle video
2. Queue videos dynamically based on user input
3. Transition smoothly between idle and queued videos using wipe transitions
"""

import threading
from video_to_ascii.render_strategy.ascii_strategy import AsciiStrategy, VideoPlayerEngine


def input_handler(player_engine, video_map):
    """
    Background thread to handle user input and queue videos
    
    Args:
        player_engine: VideoPlayerEngine instance
        video_map: Dictionary mapping user input to video paths
    """
    print("\n" + "="*50)
    print("Video Player Controls:")
    print("="*50)
    for key, path in video_map.items():
        if key != 'q':
            print(f"Press '{key}' to play: {path}")
    print("Press 'q' to quit")
    print("="*50 + "\n")
    
    while player_engine.is_running:
        try:
            user_input = input().strip().lower()
            
            if user_input == 'q':
                print("Stopping player...")
                player_engine.stop()
                break
            elif user_input in video_map and user_input != 'q':
                player_engine.add_video(video_map[user_input])
                print(f"✓ Added video '{user_input}' to queue")
            elif user_input:
                print(f"✗ Invalid input '{user_input}'. Try again.")
        except EOFError:
            break
        except KeyboardInterrupt:
            player_engine.stop()
            break


def main():
    """Main function to run the video player"""
    
    # Define your video paths here
    video_map = {
        '1': 'path/to/video1.mp4',
        '2': 'path/to/video2.mp4',
        '3': 'path/to/video3.mp4',
        'q': 'quit'
    }
    
    idle_video_path = 'path/to/idle.mp4'
    
    # Create strategy and configure transitions
    strategy = AsciiStrategy()
    strategy.transition_frames = 20  # Number of frames for transition effect
    
    # Create player engine
    player = VideoPlayerEngine(strategy, idle_video_path)
    
    # Start input handler in background thread
    input_thread = threading.Thread(
        target=input_handler, 
        args=(player, video_map), 
        daemon=True
    )
    input_thread.start()
    
    try:
        # Start the player (blocking call)
        # Using 'wipe' transition with 'top' direction
        player.start(transition_type='wipe', transition_direction='top')
    except KeyboardInterrupt:
        print("\nShutting down player...")
        player.stop()
    
    print("Player stopped. Goodbye!")


if __name__ == '__main__':
    main()
