"""
This module contains a class AsciiColorStrategy, to process video frames and build an ascii output
"""

from enum import Enum
import struct
import time
import sys
import os
import cv2
import tempfile
import threading

import serial 
from . import distance as dis

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

class States(Enum):
    IDLE = 's1.mp4'
    LAUGH = 's2.mp4'
    CURIOUS = 'curious.mp4'
    ANNOYED = 'annoyed.mp4'
    ANGRY = 'angry.mp4'

class AsciiStrategy(re.RenderStrategy):
    """Print each frame in the terminal using ascii characters"""
    ser = serial.Serial('/dev/tty.usbserial-1130', 115200)

    def __init__(self):
        self.current_video_index = 0
        self.transition_frames = 15  # Number of frames for transition
        self.is_transitioning = False
        self.next_frame = None
        
        # Add async distance reading support
        self.latest_distance = 100.0  # Default distance (IDLE state)
        self.distance_lock = threading.Lock()
        self.distance_thread = None
        self.reading_distance = False
        
        # Add smoothing for sensor readings
        self.distance_buffer = []  # Store recent readings
        self.buffer_size = 10  # Number of readings to average
        self.max_valid_distance = 700  # Disregard readings above this
        self.smoothed_distance = 100.0  # The averaged distance
        
    def start_distance_reading(self):
        """Start background thread for continuous distance reading"""
        self.reading_distance = True
        self.distance_thread = threading.Thread(target=self._read_distance_loop, daemon=True)
        self.distance_thread.start()
    
    def stop_distance_reading(self):
        """Stop background distance reading"""
        self.reading_distance = False
        if self.distance_thread:
            self.distance_thread.join(timeout=1.0)
    
    def _read_distance_loop(self):
        """Background loop to continuously read distance from Arduino"""
        while self.reading_distance:
            try:
                bites = AsciiStrategy.ser.read(4)
                distance = struct.unpack('f', bites)[0]
                
                # Filter out invalid readings
                if distance <= self.max_valid_distance and distance > 0:
                    with self.distance_lock:
                        # Add to buffer
                        self.distance_buffer.append(distance)
                        
                        # Keep buffer at fixed size
                        if len(self.distance_buffer) > self.buffer_size:
                            self.distance_buffer.pop(0)
                        
                        # Calculate moving average
                        if len(self.distance_buffer) > 0:
                            self.smoothed_distance = sum(self.distance_buffer) / len(self.distance_buffer)
                            self.latest_distance = self.smoothed_distance
                        
            except Exception as e:
                # Handle serial read errors gracefully
                print(f"Distance read error: {e}")
                time.sleep(0.1)  # Brief pause before retry
    
    def get_latest_distance(self):
        """Get the most recently read distance value (non-blocking)"""
        with self.distance_lock:
            return self.latest_distance

    @staticmethod
    def check_distance():
        bites = AsciiStrategy.ser.read(4)
        return struct.unpack('f',bites)[0]

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
        return ipe.pixel_to_ascii(pixel, colored=False)

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
        # if PLATFORM:
        #     sys.stdout.write("echo -en '\033[2J' \n")
        # else:
        #     sys.stdout.write('\033[2J')
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
        # if PLATFORM:
        #     sys.stdout.write("echo -en '\033[2J' \n")
        # else:
        #     os.system('cls') or None

        # close the frame array
        if output is not None and output_format == 'json':
            file.write(f"]\n")

    def render_playlist(self, video_paths, idle_path, output=None, output_format=None, with_audio=False, transition_type='crossfade', current_state = States.IDLE.value):
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
        
        # Start background distance reading
        self.start_distance_reading()
        
        try:
            while True:
                cap = cv2.VideoCapture(current_state)
                
                if not cap.isOpened():
                    print("Error: Could not open video")
                    continue
            
                # Get terminal dimensions
                if PLATFORM:
                    rows, cols = os.popen('stty size', 'r').read().split()
                else:
                    cols, rows = os.get_terminal_size()
                
                # Get video properties
                fps = cap.get(cv2.CAP_PROP_FPS) or 30
                time_delta = 1./fps
                
                # Render video frame by frame with distance checking
                video_finished = False
                state_changed = False
                
                while cap.isOpened():
                    t0 = time.process_time()
                    
                    # Read and render frame
                    _ret, frame = cap.read()
                    if frame is None:
                        video_finished = True
                        break
                    
                    # Render the frame
                    if PLATFORM:
                        sys.stdout.write('\u001b[0;0H')
                    else:
                        sys.stdout.write("\x1b[0;0H")
                    
                    resized_frame = self.resize_frame(frame, (cols, rows))
                    msg = self.convert_frame_pixels_to_ascii(resized_frame, (cols, rows))
                    sys.stdout.write(msg)
                    
                    # Get latest distance (non-blocking)
                    x = self.get_latest_distance()
                    new_state = current_state
                
                    # Define your distance ranges and corresponding states
                    if int(x) < 20:
                        new_state = States.LAUGH.value
                    elif int(x) < 40:
                        new_state = States.CURIOUS.value
                    elif int(x) < 60:
                        new_state = States.ANNOYED.value
                    elif int(x) < 80:
                        new_state = States.ANGRY.value
                    else:
                        new_state = States.IDLE.value
                    
                    # If state changed, break to transition
                    if current_state != new_state:
                        current_state = new_state
                        state_changed = True
                        break
                    
                    # Maintain frame rate
                    t1 = time.process_time()
                    delta = time_delta - (t1 - t0)
                    if delta > 0:
                        time.sleep(delta)
                
                # Handle transition or loop
                if state_changed:
                    # State changed - transition to new video
                    next_cap = cv2.VideoCapture(current_state)
                    if next_cap.isOpened():
                        # Position current video near end for smooth transition
                        current_frame = cap.get(cv2.CAP_PROP_POS_FRAMES)
                        total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                        
                        # Only do transition if we have enough frames left
                        if total_frames - current_frame > self.transition_frames:
                            cap.set(cv2.CAP_PROP_POS_FRAMES, 
                                   current_frame + max(0, int(total_frames - current_frame - self.transition_frames)))
                        
                        self.wipe_transition(cap, next_cap, (cols, rows), output, direction='top')
                        next_cap.release()
                elif video_finished:
                    # Video finished naturally - loop it
                    next_cap = cv2.VideoCapture(current_state)
                    if next_cap.isOpened():
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 
                               int(cap.get(cv2.CAP_PROP_FRAME_COUNT) - self.transition_frames))
                        self.wipe_transition(cap, next_cap, (cols, rows), output, direction='top')
                        next_cap.release()
                
                cap.release()
        finally:
            # Clean up: stop distance reading thread
            self.stop_distance_reading()
        

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
        
