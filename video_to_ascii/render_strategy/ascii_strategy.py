"""
This module contains a class AsciiColorStrategy, to process video frames and build an ascii output
"""

import time
import sys
import os
import cv2
import tempfile
import threading
import queue

PLATFORM = 0
if sys.platform != 'win32':
    PLATFORM = 1

from . import render_strategy as re
if PLATFORM:
    from . import image_processor as ipe
else:
    from . import image_processor_win as ipe
from os import get_terminal_size as _term_size
DEFAULT_TERMINAL_SIZE = _term_size().columns, _term_size().lines

class AsciiStrategy(re.RenderStrategy):
    """Print each frame in the terminal using ascii characters"""

    def __init__(self):
        self.current_video_index = 0
        self.transition_frames = 15  # Number of frames for transition
        self.is_transitioning = False
        self.next_frame = None

    def blend_frames(self, frame1, frame2, alpha):
        """
        Blend two frames together using alpha compositing
        
        Args:
            frame1: First frame
            frame2: Second frame
            alpha: Blend factor (0.0 to 1.0), where 0 is fully frame1, 1 is fully frame2
        
        Returns:
            Blended frame
        """
        if frame1.shape != frame2.shape:
            frame2 = cv2.resize(frame2, (frame1.shape[1], frame1.shape[0]))
        
        return cv2.addWeighted(frame1, 1 - alpha, frame2, alpha, 0)

    def crossfade_transition(self, cap1, cap2, dimensions, output=None):
        """
        Perform crossfade transition between two video captures
        
        Args:
            cap1: First video capture (ending)
            cap2: Second video capture (starting)
            dimensions: Terminal dimensions
            output: Output file if exporting
        
        Returns:
            Last frame of transition
        """
        for i in range(self.transition_frames):
            alpha = i / self.transition_frames
            
            ret1, frame1 = cap1.read()
            ret2, frame2 = cap2.read()
            
            if not ret1 or frame1 is None:
                # If first video ended, just show second video
                if ret2 and frame2 is not None:
                    return frame2
                return None
            
            if not ret2 or frame2 is None:
                # If second video not ready, just show first video
                return frame1
            
            # Blend frames
            blended = self.blend_frames(frame1, frame2, alpha)
            
            # Render blended frame
            if output is None:
                cols, rows = dimensions
                if PLATFORM:
                    sys.stdout.write('\u001b[0;0H')
                else:
                    sys.stdout.write("\x1b[0;0H")
                
                resized_frame = self.resize_frame(blended, (cols, rows))
                msg = self.convert_frame_pixels_to_ascii(resized_frame, (cols, rows))
                sys.stdout.write(msg)
                time.sleep(0.033)  # ~30fps
        
        return frame2

    def wipe_transition(self, cap1, cap2, dimensions, output=None, direction='top'):
        """
        Perform wipe transition where new video progressively replaces old video
        
        Args:
            cap1: First video capture (ending)
            cap2: Second video capture (starting)
            dimensions: Terminal dimensions
            output: Output file if exporting
            direction: Wipe direction ('top', 'bottom', 'left', 'right')
        
        Returns:
            Last frame of transition
        """
        cols, rows = dimensions
        
        for i in range(self.transition_frames):
            progress = i / self.transition_frames
            
            ret1, frame1 = cap1.read()
            ret2, frame2 = cap2.read()
            
            if not ret1 or frame1 is None:
                if ret2 and frame2 is not None:
                    return frame2
                return None
            
            if not ret2 or frame2 is None:
                return frame1
            
            # Resize both frames
            resized_frame1 = self.resize_frame(frame1, (cols, rows))
            resized_frame2 = self.resize_frame(frame2, (cols, rows))
            
            h1, w1, _ = resized_frame1.shape
            h2, w2, _ = resized_frame2.shape
            
            # Ensure same dimensions
            if (h1, w1) != (h2, w2):
                resized_frame2 = cv2.resize(resized_frame2, (w1, h1))
            
            # Create composite frame based on direction
            composite = resized_frame1.copy()
            
            if direction == 'top':
                # Wipe from top to bottom
                wipe_line = int(h1 * progress)
                if wipe_line > 0:
                    composite[:wipe_line, :] = resized_frame2[:wipe_line, :]
            elif direction == 'bottom':
                # Wipe from bottom to top
                wipe_line = int(h1 * (1 - progress))
                if wipe_line < h1:
                    composite[wipe_line:, :] = resized_frame2[wipe_line:, :]
            elif direction == 'left':
                # Wipe from left to right
                wipe_col = int(w1 * progress)
                if wipe_col > 0:
                    composite[:, :wipe_col] = resized_frame2[:, :wipe_col]
            elif direction == 'right':
                # Wipe from right to left
                wipe_col = int(w1 * (1 - progress))
                if wipe_col < w1:
                    composite[:, wipe_col:] = resized_frame2[:, wipe_col:]
            
            # Render composite frame
            if output is None:
                if PLATFORM:
                    sys.stdout.write('\u001b[0;0H')
                else:
                    sys.stdout.write("\x1b[0;0H")
                
                msg = self.convert_frame_pixels_to_ascii(composite, (cols, rows))
                sys.stdout.write(msg)
                time.sleep(0.033)  # ~30fps
        
        return resized_frame2

    def scan_transition(self, cap1, cap2, dimensions, output=None, direction='top', scan_speed=2):
        """
        Perform scanning transition with character-by-character replacement effect
        Creates a more visible "scanning line" effect
        
        Args:
            cap1: First video capture (ending)
            cap2: Second video capture (starting)
            dimensions: Terminal dimensions
            output: Output file if exporting
            direction: Scan direction ('top', 'bottom')
            scan_speed: Number of rows to scan per frame (higher = faster)
        
        Returns:
            Last frame of transition
        """
        cols, rows = dimensions
        
        # Get initial frames
        ret1, frame1 = cap1.read()
        ret2, frame2 = cap2.read()
        
        if not ret1 or not ret2 or frame1 is None or frame2 is None:
            return frame2 if ret2 else frame1
        
        # Resize both frames once
        resized_frame1 = self.resize_frame(frame1, (cols, rows))
        resized_frame2 = self.resize_frame(frame2, (cols, rows))
        
        h, w, _ = resized_frame1.shape
        
        # Ensure same dimensions
        if resized_frame2.shape != resized_frame1.shape:
            resized_frame2 = cv2.resize(resized_frame2, (w, h))
        
        # Calculate total scan lines
        total_lines = h
        lines_per_frame = max(1, int(total_lines / self.transition_frames))
        
        current_line = 0
        
        while current_line < total_lines:
            # Read new frames for animation
            ret1, new_frame1 = cap1.read()
            ret2, new_frame2 = cap2.read()
            
            if ret1 and new_frame1 is not None:
                resized_frame1 = self.resize_frame(new_frame1, (cols, rows))
            if ret2 and new_frame2 is not None:
                resized_frame2 = self.resize_frame(new_frame2, (cols, rows))
                if resized_frame2.shape != (h, w, 3):
                    resized_frame2 = cv2.resize(resized_frame2, (w, h))
            
            # Create composite with scan line effect
            composite = resized_frame1.copy()
            
            if direction == 'top':
                # Replace from top
                end_line = min(current_line + scan_speed, total_lines)
                composite[:end_line, :] = resized_frame2[:end_line, :]
                
                # Add visual scan line effect (brighter line)
                if end_line < total_lines:
                    scan_line_thickness = 2
                    for offset in range(scan_line_thickness):
                        line_pos = min(end_line + offset, total_lines - 1)
                        # Brighten the scan line
                        composite[line_pos, :] = cv2.addWeighted(
                            composite[line_pos, :], 0.5,
                            resized_frame2[line_pos, :], 0.5, 50
                        )
            else:  # bottom
                # Replace from bottom
                start_line = max(total_lines - current_line - scan_speed, 0)
                composite[start_line:, :] = resized_frame2[start_line:, :]
                
                # Add visual scan line effect
                if start_line > 0:
                    scan_line_thickness = 2
                    for offset in range(scan_line_thickness):
                        line_pos = max(start_line - offset, 0)
                        composite[line_pos, :] = cv2.addWeighted(
                            composite[line_pos, :], 0.5,
                            resized_frame2[line_pos, :], 0.5, 50
                        )
            
            # Render composite frame
            if output is None:
                if PLATFORM:
                    sys.stdout.write('\u001b[0;0H')
                else:
                    sys.stdout.write("\x1b[0;0H")
                
                msg = self.convert_frame_pixels_to_ascii(composite, (cols, rows))
                sys.stdout.write(msg)
                time.sleep(0.033)  # ~30fps
            
            current_line += lines_per_frame
        
        return resized_frame2

    def slide_transition(self, frame1, frame2, progress, direction='left'):
        """
        Create a sliding transition effect
        
        Args:
            frame1: Outgoing frame
            frame2: Incoming frame
            progress: Transition progress (0.0 to 1.0)
            direction: Slide direction ('left', 'right', 'up', 'down')
        """
        h, w = frame1.shape[:2]
        
        if direction == 'left':
            offset = int(w * progress)
            result = frame1.copy()
            result[:, :w-offset] = frame1[:, offset:]
            result[:, w-offset:] = frame2[:, :offset]
        elif direction == 'right':
            offset = int(w * progress)
            result = frame1.copy()
            result[:, offset:] = frame1[:, :w-offset]
            result[:, :offset] = frame2[:, w-offset:]
        
        return result

    def fade_transition(self, frame, progress, fade_out=True):
        """
        Create a fade to black transition
        
        Args:
            frame: Frame to fade
            progress: Fade progress (0.0 to 1.0)
            fade_out: True for fade out, False for fade in
        """
        alpha = 1 - progress if fade_out else progress
        black_frame = frame * 0  # Create black frame
        return cv2.addWeighted(frame, alpha, black_frame, 1 - alpha, 0)

    def convert_frame_pixels_to_ascii(self, frame, dimensions=DEFAULT_TERMINAL_SIZE, new_line_chars=False):
        """
        Replace all pixels with colored chars and return the resulting string

        This method iterates each pixel of one video frame
        respecting the dimensions of the printing area
        to truncate the width if necessary
        and use the pixel_to_ascii method to convert one pixel
        into a character with the appropriate color.
        Finally joins the set of chars in a string ready to print.

        Args:
            frame: a single video frame
            dimensions: an array with the printing area dimensions
                in pixels [rows, cols]
            new_line_chars: if should append a new line character
                at end of each row

        Returns:
            str: The resulting set of colored chars as a unique string

        """
        cols, _ = dimensions
        h, w, _ = frame.shape

        printing_width = int(min(int(cols), (w*2))/2)
        pad = max(int(cols) - printing_width*2, 0) 
         
        
        msg = ''
        for j in range(h-1):
            for i in range(printing_width):
                pixel = frame[j][i]
                msg += self.apply_pixel_to_ascii_strategy(pixel)
            if new_line_chars:
                msg += "\n"
            else:
                msg += " " * (pad)
        msg += "\r\n"
        return msg

    def apply_pixel_to_ascii_strategy(self, pixel):
        return ipe.pixel_to_ascii(pixel)

    def apply_end_line_modifier(self, msg):
        return msg

    def render(self, cap, output=None, output_format=None, with_audio=False):
        """
        Iterate each video frame to print a set of ascii chars

        This method reads each video frame from a opencv video capture
        resizing the frame and truncate the width if necessary to
        print correctly the final string built with the method
        convert_frame_pixels_to_ascii.
        Finally each final string is printed correctly, if the process
        was done too fast will sleep the necessary time to comply
        with the fps expected (30 fps by default).

        Args:
            cap: An OpenCV video capture
            output: If the render should be exported to a bash file
        """

        v_width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        v_height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        length = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        fps = cap.get(cv2.CAP_PROP_FPS) 
        fps = fps or 30

        if with_audio:
            import pyaudio
            import wave

            temp_dir = tempfile.gettempdir()
            temp_file_path = temp_dir + "/temp-audiofile-for-vta.wav"
            wave_file = wave.open(temp_file_path, 'rb')
            chunk = int(wave_file.getframerate() / fps)
            p = pyaudio.PyAudio()

            stream = p.open(format =
                p.get_format_from_width(wave_file.getsampwidth()),
                channels = wave_file.getnchannels(),
                rate = wave_file.getframerate(),
                output = True)
                       
            data = wave_file.readframes(chunk)
            

        if output is not None:
            file = open(output, 'w+')

            if output_format == 'sh':
                file.write("#!/bin/bash \n")
                file.write("echo -en '\033[2J' \n")
                file.write("echo -en '\u001b[0;0H' \n")

        time_delta = 1./fps
        counter=0
        if PLATFORM:
            sys.stdout.write("echo -en '\033[2J' \n")
        else:
            sys.stdout.write('\033[2J')
        # read each frame
        while cap.isOpened():
            t0 = time.process_time()
            if PLATFORM:
                rows, cols = os.popen('stty size', 'r').read().split()
            else:
                cols, rows = os.get_terminal_size()
            _ret, frame = cap.read()
            if frame is None:
                break
            if with_audio:
                data = wave_file.readframes(chunk)
                stream.write(data)
            # sleep if the process was too fast
            if output is None:
                if PLATFORM:
                    sys.stdout.write('\u001b[0;0H')
                else:
                    sys.stdout.write("\x1b[0;0H")
                # scale each frame according to terminal dimensions
                resized_frame = self.resize_frame(frame, (cols, rows))
                # convert frame pixels to colored string
                msg = self.convert_frame_pixels_to_ascii(resized_frame, (cols, rows)) 
                t1 = time.process_time()
                delta = time_delta - (t1 - t0)
                if delta > 0:
                    time.sleep(delta)
                sys.stdout.write(msg) # Print the final string
            else:
                print(self.build_progress(counter, length))
                if PLATFORM:
                    print("\u001b[2A")
                else:
                    print("\x1b[2A")

                if output_format == 'sh':
                    resized_frame = self.resize_frame(frame)
                    msg = self.convert_frame_pixels_to_ascii(resized_frame, new_line_chars=True)
                    file.write("sleep 0.033 \n")
                    file.write("echo -en '" + msg + "'" + "\n" ) 
                    file.write("echo -en '\u001b[0;0H' \n")
                elif output_format == 'json':
                    # scale each frame according to terminal dimensions
                    resized_frame = self.resize_frame(frame, (cols, rows))
                    msg = self.convert_frame_pixels_to_ascii(resized_frame, (cols, rows), new_line_chars=True)
                    lines = msg.split("\n")
                    # remove last line breaks (\n\r) which generate two extra unwanted array elements
                    lines = lines[0:-2]
                    # opening brackets
                    file.write("[[\n" if counter == 0  else ",[\n")
                    for i in range(len(lines)):
                        file.write(f"\"{lines[i]}\"")
                        # closing brackets
                        file.write("]\n" if i == (len(lines) - 1)  else ",\n")

            counter += 1
        if with_audio:
            stream.close()
            p.terminate()
        if PLATFORM:
            sys.stdout.write("echo -en '\033[2J' \n")
        else:
            os.system('cls') or None

        # close the frame array
        if output is not None and output_format == 'json':
            file.write(f"]\n")

    def render_playlist(self, video_paths, output=None, output_format=None, with_audio=False, transition_type='crossfade'):
        """
        Render multiple videos with smooth transitions
        
        Args:
            video_paths: List of video file paths
            output: Output file if exporting
            output_format: Format of output ('sh' or 'json')
            with_audio: Enable audio playback
            transition_type: Type of transition ('crossfade', 'wipe', 'scan', 'slide', 'fade')
        """
        if PLATFORM:
            sys.stdout.write("echo -en '\033[2J' \n")
        else:
            sys.stdout.write('\033[2J')
        
        for idx, video_path in enumerate(video_paths):
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                print(f"Error: Could not open video {video_path}")
                continue
            
            # Get terminal dimensions
            if PLATFORM:
                rows, cols = os.popen('stty size', 'r').read().split()
            else:
                cols, rows = os.get_terminal_size()
            
            # Render current video
            self.render(cap, output, output_format, with_audio)
            
            # Perform transition to next video if available
            if idx < len(video_paths) - 1:
                next_cap = cv2.VideoCapture(video_paths[idx + 1])
                
                if next_cap.isOpened():
                    # Reopen current video to get last frames
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 
                           cap.get(cv2.CAP_PROP_FRAME_COUNT) - self.transition_frames)
                    
                    if transition_type == 'crossfade':
                        self.crossfade_transition(cap, next_cap, (cols, rows), output)
                    elif transition_type == 'wipe':
                        self.wipe_transition(cap, next_cap, (cols, rows), output, direction='top')
                    elif transition_type == 'scan':
                        self.scan_transition(cap, next_cap, (cols, rows), output, direction='top', scan_speed=3)
                    
                    next_cap.release()
            
            cap.release()
        
        if PLATFORM:
            sys.stdout.write("echo -en '\033[2J' \n")
        else:
            os.system('cls') or None

    def build_progress(self, progress, total):
        """Build a progress bar in the terminal"""
        progress_percent =  int(progress / total * 100) 
        adjusted_size_percent = int((20 / 100) * progress_percent) 
        progress_bar = ('█' * adjusted_size_percent) + ('░' * (20-adjusted_size_percent))
        return  "  " +  "|" +  progress_bar + "| " + str(progress_percent) + "%"

    def resize_frame(self, frame, dimensions=DEFAULT_TERMINAL_SIZE):
        """
        Resize a frame to meet the terminal dimensions

        Calculating the output terminal dimensions (cols, rows),
        we can get a reduction factor to resize the frame
        according to the height of the terminal mainly
        to print each frame at a time, using all the available rows

        Args:
            frame: Frame to resize
            dimensions: If you want to set a printer area size (cols, rows)
        Returns:
            A resized frame
        """
        height, width, _ = frame.shape
        _, rows = dimensions
        reduction_factor = (float(rows)) / height * 100
        reduced_width = int(width * reduction_factor / 100)
        reduced_height = int(height * reduction_factor / 100)
        dimension = (reduced_width, reduced_height)
        resized_frame = cv2.resize(frame, dimension, interpolation=cv2.INTER_LINEAR)
        return resized_frame


class PlayerState:
    """States for the video player engine"""
    IDLE = "idle"
    TRANSITIONING = "transitioning"
    PLAYING = "playing"


class VideoPlayerEngine:
    """Video player engine with idle loop and dynamic video queueing"""
    
    def __init__(self, strategy, idle_video_path):
        """
        Initialize the video player engine
        
        Args:
            strategy: AsciiStrategy instance for rendering
            idle_video_path: Path to the idle/default video to loop
        """
        self.strategy = strategy
        self.idle_video_path = idle_video_path
        self.video_queue = queue.Queue()
        self.state = PlayerState.IDLE
        self.current_cap = None
        self.current_video_path = None
        self.is_running = False
        self.lock = threading.Lock()
        
    def add_video(self, video_path):
        """
        Add a video to the playback queue
        
        Args:
            video_path: Path to the video file to queue
        """
        self.video_queue.put(video_path)
        
    def return_to_idle(self):
        """Manually return to idle state from playing video"""
        with self.lock:
            if self.state == PlayerState.PLAYING:
                # None signals return to idle
                self.video_queue.put(None)
        
    def start(self, transition_type='wipe', transition_direction='top'):
        """
        Start the video player engine
        
        Args:
            transition_type: Type of transition ('crossfade', 'wipe', 'scan')
            transition_direction: Direction for wipe/scan transitions
        """
        self.is_running = True
        self.transition_type = transition_type
        self.transition_direction = transition_direction
        
        if PLATFORM:
            sys.stdout.write("echo -en '\033[2J' \n")
        else:
            sys.stdout.write('\033[2J')
        
        while self.is_running:
            with self.lock:
                if self.state == PlayerState.IDLE:
                    self._play_idle()
                elif self.state == PlayerState.PLAYING:
                    self._play_queued_video()
    
    def _play_idle(self):
        """Play idle video in loop, checking for queued videos"""
        cap = cv2.VideoCapture(self.idle_video_path)
        
        if not cap.isOpened():
            print(f"Error: Could not open idle video {self.idle_video_path}")
            return
        
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        time_delta = 1.0 / fps
        
        if PLATFORM:
            rows, cols = os.popen('stty size', 'r').read().split()
            rows, cols = int(rows), int(cols)
        else:
            cols, rows = os.get_terminal_size()
        
        while self.is_running and self.state == PlayerState.IDLE:
            # Check if video should be queued
            if not self.video_queue.empty():
                self.state = PlayerState.TRANSITIONING
                video_path = self.video_queue.get()
                self._transition_to_video(cap, video_path, (cols, rows))
                cap.release()
                return
            
            t0 = time.process_time()
            ret, frame = cap.read()
            
            # Loop idle video
            if not ret or frame is None:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            
            # Render frame
            if PLATFORM:
                sys.stdout.write('\u001b[0;0H')
            else:
                sys.stdout.write("\x1b[0;0H")
            
            resized_frame = self.strategy.resize_frame(frame, (cols, rows))
            msg = self.strategy.convert_frame_pixels_to_ascii(resized_frame, (cols, rows))
            sys.stdout.write(msg)
            sys.stdout.flush()
            
            t1 = time.process_time()
            delta = time_delta - (t1 - t0)
            if delta > 0:
                time.sleep(delta)
        
        cap.release()
    
    def _transition_to_video(self, from_cap, to_video_path, dimensions):
        """
        Transition from current video to queued video
        
        Args:
            from_cap: Current video capture
            to_video_path: Path to the next video
            dimensions: Terminal dimensions (cols, rows)
        """
        to_cap = cv2.VideoCapture(to_video_path)
        
        if not to_cap.isOpened():
            print(f"Error: Could not open video {to_video_path}")
            self.state = PlayerState.IDLE
            return
        
        # Perform transition
        if self.transition_type == 'crossfade':
            self.strategy.crossfade_transition(from_cap, to_cap, dimensions)
        elif self.transition_type == 'wipe':
            self.strategy.wipe_transition(from_cap, to_cap, dimensions, direction=self.transition_direction)
        elif self.transition_type == 'scan':
            self.strategy.scan_transition(from_cap, to_cap, dimensions, direction=self.transition_direction, scan_speed=3)
        
        # Start playing the queued video
        self.state = PlayerState.PLAYING
        self.current_cap = to_cap
        self.current_video_path = to_video_path
    
    def _play_queued_video(self):
        """Play the queued video in a loop until another video is queued or stopped"""
        if self.current_cap is None:
            self.state = PlayerState.IDLE
            return
        
        fps = self.current_cap.get(cv2.CAP_PROP_FPS) or 30
        time_delta = 1.0 / fps
        
        if PLATFORM:
            rows, cols = os.popen('stty size', 'r').read().split()
            rows, cols = int(rows), int(cols)
        else:
            cols, rows = os.get_terminal_size()
        
        while self.is_running and self.state == PlayerState.PLAYING:
            # Check if a new video is queued or return to idle requested
            if not self.video_queue.empty():
                video_path = self.video_queue.get()
                
                # None signals return to idle
                if video_path is None:
                    self._transition_back_to_idle((cols, rows))
                    return
                
                self._transition_to_next_video(video_path, (cols, rows))
                continue
            
            t0 = time.process_time()
            ret, frame = self.current_cap.read()
            
            # Video finished, loop back to start with wipe transition
            if not ret or frame is None:
                self._loop_current_video((cols, rows))
                continue
            
            # Render frame
            if PLATFORM:
                sys.stdout.write('\u001b[0;0H')
            else:
                sys.stdout.write("\x1b[0;0H")
            
            resized_frame = self.strategy.resize_frame(frame, (cols, rows))
            msg = self.strategy.convert_frame_pixels_to_ascii(resized_frame, (cols, rows))
            sys.stdout.write(msg)
            sys.stdout.flush()
            
            t1 = time.process_time()
            delta = time_delta - (t1 - t0)
            if delta > 0:
                time.sleep(delta)
    
    def _loop_current_video(self, dimensions):
        """
        Loop the current video back to start with wipe transition
        
        Args:
            dimensions: Terminal dimensions (cols, rows)
        """
        if self.current_cap is None or self.current_video_path is None:
            return
        
        cols, rows = dimensions
        
        # Get total frames and position near the end for transition
        total_frames = self.current_cap.get(cv2.CAP_PROP_FRAME_COUNT)
        fps = self.current_cap.get(cv2.CAP_PROP_FPS) or 30
        frame_delay = 1.0 / fps
        
        # Position at transition_frames before the end
        transition_start = max(0, int(total_frames - self.strategy.transition_frames - 2))
        self.current_cap.set(cv2.CAP_PROP_POS_FRAMES, transition_start)
        
        # Open a second capture from the beginning
        start_cap = cv2.VideoCapture(self.current_video_path)
        
        if not start_cap.isOpened():
            # If can't reopen, just reset to beginning
            self.current_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            return
        
        # Manually perform wipe transition
        for i in range(self.strategy.transition_frames):
            progress = (i + 1) / self.strategy.transition_frames
            
            # Read from end of video
            ret1, frame1 = self.current_cap.read()
            # Read from beginning of video
            ret2, frame2 = start_cap.read()
            
            # If we run out of frames at the end, get the last frame
            if not ret1 or frame1 is None:
                self.current_cap.set(cv2.CAP_PROP_POS_FRAMES, int(total_frames - 1))
                ret1, frame1 = self.current_cap.read()
                if not ret1 or frame1 is None:
                    break
            
            if not ret2 or frame2 is None:
                break
            
            # Resize both frames
            resized_frame1 = self.strategy.resize_frame(frame1, (cols, rows))
            resized_frame2 = self.strategy.resize_frame(frame2, (cols, rows))
            
            h1, w1, _ = resized_frame1.shape
            h2, w2, _ = resized_frame2.shape
            
            # Ensure same dimensions
            if (h1, w1) != (h2, w2):
                resized_frame2 = cv2.resize(resized_frame2, (w1, h1))
                h2, w2 = h1, w1
            
            # Create composite frame with wipe effect
            composite = resized_frame1.copy()
            
            if self.transition_direction == 'top':
                wipe_line = int(h1 * progress)
                if wipe_line > 0 and wipe_line <= h1:
                    composite[:wipe_line, :] = resized_frame2[:wipe_line, :]
            elif self.transition_direction == 'bottom':
                wipe_line = int(h1 * (1 - progress))
                if wipe_line >= 0 and wipe_line < h1:
                    composite[wipe_line:, :] = resized_frame2[wipe_line:, :]
            elif self.transition_direction == 'left':
                wipe_col = int(w1 * progress)
                if wipe_col > 0 and wipe_col <= w1:
                    composite[:, :wipe_col] = resized_frame2[:, :wipe_col]
            elif self.transition_direction == 'right':
                wipe_col = int(w1 * (1 - progress))
                if wipe_col >= 0 and wipe_col < w1:
                    composite[:, wipe_col:] = resized_frame2[:, wipe_col:]
            
            # Render composite frame
            if PLATFORM:
                sys.stdout.write('\u001b[0;0H')
            else:
                sys.stdout.write("\x1b[0;0H")
            
            msg = self.strategy.convert_frame_pixels_to_ascii(composite, (cols, rows))
            sys.stdout.write(msg)
            sys.stdout.flush()
            
            time.sleep(frame_delay)
        
        # Close the start capture and reset main capture to beginning
        start_cap.release()
        self.current_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    
    def _transition_to_next_video(self, to_video_path, dimensions):
        """
        Transition from current playing video to a new queued video
        
        Args:
            to_video_path: Path to the next video
            dimensions: Terminal dimensions (cols, rows)
        """
        to_cap = cv2.VideoCapture(to_video_path)
        
        if not to_cap.isOpened():
            print(f"Error: Could not open video {to_video_path}")
            return
        
        # Perform transition from current video to new video
        if self.transition_type == 'crossfade':
            self.strategy.crossfade_transition(self.current_cap, to_cap, dimensions)
        elif self.transition_type == 'wipe':
            self.strategy.wipe_transition(self.current_cap, to_cap, dimensions, direction=self.transition_direction)
        elif self.transition_type == 'scan':
            self.strategy.scan_transition(self.current_cap, to_cap, dimensions, direction=self.transition_direction, scan_speed=3)
        
        # Release old capture and switch to new one
        self.current_cap.release()
        self.current_cap = to_cap
        self.current_video_path = to_video_path
        
        # Stay in PLAYING state to continue with new video
    
    def _transition_back_to_idle(self, dimensions):
        """
        Transition from queued video back to idle
        
        Args:
            dimensions: Terminal dimensions (cols, rows)
        """
        idle_cap = cv2.VideoCapture(self.idle_video_path)
        
        if not idle_cap.isOpened():
            print(f"Error: Could not open idle video {self.idle_video_path}")
            self.current_cap.release()
            self.current_cap = None
            self.current_video_path = None
            self.state = PlayerState.IDLE
            return
        
        # Use opposite direction for return transition
        return_direction = 'bottom' if self.transition_direction == 'top' else 'top'
        
        # Perform transition
        if self.transition_type == 'crossfade':
            self.strategy.crossfade_transition(self.current_cap, idle_cap, dimensions)
        elif self.transition_type == 'wipe':
            self.strategy.wipe_transition(self.current_cap, idle_cap, dimensions, direction=return_direction)
        elif self.transition_type == 'scan':
            self.strategy.scan_transition(self.current_cap, idle_cap, dimensions, direction=return_direction, scan_speed=3)
        
        self.current_cap.release()
        self.current_cap = None
        self.current_video_path = None
        idle_cap.release()
        self.state = PlayerState.IDLE
    
    def stop(self):
        """Stop the video player engine"""
        self.is_running = False
        if self.current_cap:
            self.current_cap.release()
        
        if PLATFORM:
            sys.stdout.write("echo -en '\033[2J' \n")
        else:
            os.system('cls') or None
        
