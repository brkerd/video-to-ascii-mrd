"""
This module contains a class AsciiColorStrategy, to process video frames and build an ascii output
"""

import time
import sys
import os
import cv2
import tempfile 

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
            transition_type: Type of transition ('crossfade', 'slide', 'fade')
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
        
