from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy import platform
from kivy.properties import ListProperty, ObjectProperty
from kivy.clock import Clock
from kivy.factory import Factory

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.app import MDApp
from kivymd.uix.button import MDFlatButton
from kivymd.uix.list import OneLineIconListItem
from kivymd.uix.list import MDList
from kivymd.uix.list import TwoLineAvatarIconListItem
from kivymd.uix.dialog import MDDialog

import datetime
import time
import requests
import numpy as np
import threading
import pyaudio
import wave
import os

from audio import Audio

au = Audio()


class ListItemWithIcon(TwoLineAvatarIconListItem):
    '''Custom list item'''

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._txt_left_pad = "10dp"
        self.playback_thread = None
        self.playback_paused = False
        self.playback_completed = False

    def on_kv_post(self, base_widget):
        super().on_kv_post(base_widget)
        self.ids._left_container.padding = [
            self._txt_left_pad, "0dp", "0dp", "0dp"]

    def play_rec(self):
        if self.ids.status.icon == 'play':
            self.ids.status.icon = 'pause'
            MDApp.get_running_app().root.ids.first.sett.disabled = True
            MDApp.get_running_app().root.ids.first.rec.disabled = True
            # Start a new thread for audio playback if not already playing
            if not self.playback_thread or not self.playback_thread.is_alive():
                self.playback_thread = threading.Thread(target=self.play_audio)
                self.playback_thread.start()
            else:
                # Resume playback if paused
                self.playback_paused = False
        else:
            self.ids.status.icon = 'play'
            # Pause playback
            self.playback_paused = True

    def play_audio(self):

        directory_path = os.path.abspath("./recordings")
        filename = "Recording A.wav"
        file_path = os.path.join(directory_path, filename)
        # Open the wave file for playback
        wf = wave.open(file_path, 'rb')

        # Initialize PyAudio for playback
        audio = pyaudio.PyAudio()

        # Open an audio stream for playback
        stream = audio.open(
            format=audio.get_format_from_width(wf.getsampwidth()),
            channels=wf.getnchannels(),
            rate=wf.getframerate(),
            output=True
        )

        # Read the audio data from the saved file
        data = wf.readframes(1024)

        # Play the audio frames
        while data:
            if not self.playback_paused:
                stream.write(data)
                data = wf.readframes(1024)
            else:
                # Sleep for a short duration to reduce CPU usage
                time.sleep(0.1)

            # Check if playback reaches the end of the audio file
            if data == b'' and not self.playback_paused:
                self.playback_completed = True
                MDApp.get_running_app().root.ids.first.rec.disabled = False
                MDApp.get_running_app().root.ids.first.sett.disabled = False
                break

        # Stop and close the playback stream
        stream.stop_stream()
        stream.close()
        audio.terminate()

        # Update the play button icon at the end of the recording
        self.ids.status.icon = 'play'

    def on_enter(self):
        super().on_enter()

        # Reset playback state when entering the screen
        self.playback_paused = False
        self.playback_completed = False


class FirstWindow(Screen):

    files = ListProperty([])

    Builder.load_file('firstwindow.kv')

    def __init__(self, **kw):
        super().__init__(**kw)

        Clock.schedule_once(self.begin)

    def begin(self, *args):
        if au.FI() is True:
            self.get_audio_files()
        else:
            self.error_dialog(
                message="Sorry, the application failed to establish a connection. Please try again.")

    def get_audio_files(self):
        if au.CS() is True:
            # Get the directory path where WAV files are located
            directory_path = os.path.abspath("./recordings")

            os.makedirs(directory_path, exist_ok=True)
            # Iterate through files in the directory
            for file_name in os.listdir(directory_path):
                # Check if the file has a .wav extension
                if file_name.endswith('.wav'):
                    # Add the file name to the files list
                    self.files.append(file_name)

            # Populate the file list view with the WAV files
            for file_name in self.files:
                list_item = ListItemWithIcon(text=file_name)
                self.ids.container.add_widget(list_item)

            self.files = []
        else:
            self.error_dialog(
                message="Sorry, the application failed to establish a connection. Please try again.")

    def delete_audio_files(self):
        # Get the directory path where WAV files are located
        directory_path = os.path.abspath("./recordings")

        # Iterate through files in the directory
        for file_name in os.listdir(directory_path):
            # Check if the file has a .wav extension
            if file_name.endswith('.wav'):
                # Construct the absolute file path
                file_path = os.path.join(directory_path, file_name)

                # Delete the file
                os.remove(file_path)

        self.ids.container.clear_widgets()

        self.files = []

    def error_dialog(self, message):

        close_button = MDFlatButton(
            text='CLOSE',
            text_color=[0, 0, 0, 1],
            on_release=self.close_dialog,
        )
        self.dialog = MDDialog(
            title='[color=#FF0000]Ooops![/color]',
            text=message,
            buttons=[close_button],
            auto_dismiss=False
        )
        self.dialog.open()

    # Close Dialog
    def close_dialog(self, obj):
        MDApp.get_running_app().stop()

    def toggle_recording(self):
        if self.ids.rec.icon == 'record-circle-outline':
            self.ids.rec.icon = 'stop'
            self.ids.sett.disabled = True
            threading.Thread(target=self.start_recording).start()
        else:
            self.ids.sett.disabled = False
            self.ids.rec.icon = 'record-circle-outline'

    def play_audio(self):

        directory_path = os.path.abspath("./recordings")
        filename = "Recording A.wav"
        file_path = os.path.join(directory_path, filename)
        chunk = 1024
        wf = wave.open(file_path, 'rb')
        audio = pyaudio.PyAudio()

        stream = audio.open(
            format=audio.get_format_from_width(wf.getsampwidth()),
            channels=wf.getnchannels(),
            rate=wf.getframerate(),
            output=True
        )

        data = wf.readframes(chunk)

        while data:
            stream.write(data)
            data = wf.readframes(chunk)
            self.ids.sett.disabled = True
            self.ids.rec.disabled = True
        stream.stop_stream()
        stream.close()
        audio.terminate()

        self.ids.sett.disabled = False
        self.ids.rec.disabled = False
    # -------------------------- START  RECORDING ------------------------------

    def start_recording(self):
        self.delete_audio_files()

        audio = pyaudio.PyAudio()

        stream = audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=44100,
            input=True,
            frames_per_buffer=1024
        )

        frames = []

        # Silence Threshold
        energy_threshold = MDApp.get_running_app(
        ).root.ids.second.ids.silence_treshold.value * 100

        # Silence Duration
        max_silence_duration = MDApp.get_running_app(
        ).root.ids.second.ids.silence_duration.value

        # Length of Record (Max 20s)
        recording_length = MDApp.get_running_app(
        ).root.ids.second.ids.recording_length.value

        silence_frames = 0
        silence_start_time = None

        start_time = time.time()

        while self.ids.rec.icon == 'stop':
            data = stream.read(1024)
            frames.append(data)

            # Convert the data to numpy array
            audio_data = np.frombuffer(data, dtype=np.int16)

            # Calculate energy of the current frame (squared amplitude)
            energy = np.sum(audio_data.astype(np.int32) ** 2) / len(audio_data)

            # Check if the energy is below the threshold
            if energy < energy_threshold*1000:
                # If silence has just started, set the silence start time
                if silence_start_time is None:
                    silence_start_time = time.time()

                # Increment the silence frames counter
                silence_frames += 1

            else:
                # Reset the silence start time and frames counter
                silence_start_time = None
                silence_frames = 0

            # Check if the silence duration exceeds the maximum silence duration
            if silence_frames * 1024 >= max_silence_duration * 44100:
                self.ids.rec.icon = 'record-circle-outline'
                self.ids.sett.disabled = False
                break

            # Check if the desired duration (20 seconds) has elapsed
            elapsed_time = time.time() - start_time
            if elapsed_time >= recording_length:
                self.ids.rec.icon = 'record-circle-outline'
                self.ids.sett.disabled = False
                break

        stream.stop_stream()
        stream.close()
        audio.terminate()

        directory = "./recordings"

        os.makedirs(directory, exist_ok=True)

        filename = os.path.join(directory, "Recording A.wav")
        # Save audio frames to a WAV file

        wf = wave.open(filename, 'wb')
        wf.setnchannels(1)
        wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
        wf.setframerate(44100)
        wf.writeframes(b''.join(frames))
        wf.close()

        self.ids.container.clear_widgets()

        self.begin()

        self.play_audio()

    def settings(self):

        self.manager.current = "second"
        self.manager.transition.direction = "left"


class SecondWindow(Screen):

    def __init__(self, **kw):
        super().__init__(**kw)

    Builder.load_file('secondwindow.kv')

    def back(self):
        self.manager.transition.direction = 'right'
        self.manager.current = "first"

    def verify(self):

        self.ids.silence_duration.value = int(self.ids.silence_duration.value)
        self.ids.silence_treshold.value = int(self.ids.silence_treshold.value)
        self.ids.recording_length.value = int(self.ids.recording_length.value)

        self.back()


class WindowManager(ScreenManager):
    pass


class rawApp(MDApp):

    def build(self):

        return WindowManager()


if __name__ == '__main__':
    rawApp().run()
