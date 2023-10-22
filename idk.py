import threading
from djitellopy import Tello
import cv2
import tkinter as tk
from PIL import Image, ImageTk

width = 320
height = 240
move_distance = 20
rotate_degree = 15

class TelloApp:
    def __init__(self, window, window_title):
        self.window = window
        self.window.title(window_title)

        # Frame for video feed
        self.video_frame = tk.Frame(self.window)
        self.video_frame.grid(row=0, column=1, padx=10, pady=10)

        self.video_canvas = tk.Canvas(self.video_frame, width=width, height=height)
        self.video_canvas.pack()

        # Initialization for drone
        self.me = Tello()
        self.me_connected = self.connect_drone()

        if not self.me_connected:
            self.display_error("Failed to connect to the Tello drone.")
        else:
            self.low_battery = False
            self.update_battery()
            self.update_video()

            self.create_basic_movement_buttons()
            self.create_advanced_movement_buttons()

            # Initialize the object tracker
            self.tracker = None
            self.target_coordinates = None

        self.window.mainloop()

    def connect_drone(self):
        try:
            self.me.connect()
            self.me.streamoff()
            self.me.streamon()
            return True
        except Exception as e:
            self.display_error(f"Failed to connect to the Tello drone: {e}")
            return False

    def create_basic_movement_buttons(self):
        basic_movement_frame = tk.Frame(self.window)
        basic_movement_frame.grid(row=0, column=0, padx=10, pady=10)

        basic_movement_buttons = [
            ("Takeoff", self.start_drone),
            ("Land", self.land_drone),
            ("Exit", self.exit_app),
            ("Up", self.go_up),
            ("Down", self.go_down),
            ("Yaw Left", self.yaw_left),
            ("Yaw Right", self.yaw_right),
            ("Start Tracking", self.start_tracking),
            ("Stop Tracking", self.stop_tracking),
        ]

        for label, command in basic_movement_buttons:
            button = tk.Button(basic_movement_frame, text=label, command=command)
            button.pack(pady=5)

    def create_advanced_movement_buttons(self):
        advanced_movement_frame = tk.Frame(self.window)
        advanced_movement_frame.grid(row=0, column=2, padx=10, pady=10)

        advanced_movement_buttons = [
            ("Left", self.go_left),
            ("Right", self.go_right),
            ("Tilt Forward", self.tilt_forward),
            ("Tilt Backward", self.tilt_backward),
        ]

        for label, command in advanced_movement_buttons:
            button = tk.Button(advanced_movement_frame, text=label, command=command)
            button.pack(pady=5)

    def start_drone(self):
        if not self.me_connected:
            return

        try:
            self.threaded_drone_command(self.me.takeoff)
        except Exception as e:
            self.display_error(f"Takeoff command failed: {e}")

    def land_drone(self):
        if not self.me_connected:
            return

        try:
            self.threaded_drone_command(self.me.land)
            self.low_battery = True
        except Exception as e:
            self.display_error(f"Land command failed: {e}")

    def exit_app(self):
        if not self.me_connected:
            return

        try:
            self.threaded_drone_command(self.me.streamoff)
            self.window.quit()
        except Exception as e:
            self.display_error(f"Streamoff command failed: {e}")

    def go_left(self):
        if not self.me_connected:
            return

        try:
            self.retry_drone_command(lambda: self.me.move_left(move_distance))
        except Exception as e:
            self.display_error(f"Left command failed: {e}")

    def go_right(self):
        if not self.me_connected:
            return

        try:
            self.retry_drone_command(lambda: self.me.move_right(move_distance))
        except Exception as e:
            self.display_error(f"Right command failed: {e}")

    def go_up(self):
        if not self.me_connected:
            return

        try:
            self.retry_drone_command(lambda: self.me.move_up(move_distance))
        except Exception as e:
            self.display_error(f"Up command failed: {e}")

    def go_down(self):
        if not self.me_connected:
            return

        try:
            self.retry_drone_command(lambda: self.me.move_down(move_distance))
        except Exception as e:
            self.display_error(f"Down command failed: {e}")

    def yaw_left(self):
        if not self.me_connected:
            return

        try:
            self.retry_drone_command(lambda: self.me.rotate_counter_clockwise(rotate_degree))
        except Exception as e:
            self.display_error(f"Yaw Left command failed: {e}")

    def yaw_right(self):
        if not self.me_connected:
            return

        try:
            self.retry_drone_command(lambda: self.me.rotate_clockwise(rotate_degree))
        except Exception as e:
            self.display_error(f"Yaw Right command failed: {e}")

    def tilt_forward(self):
        if not self.me_connected:
            return

        try:
            self.retry_drone_command(lambda: self.me.move_forward(move_distance))
        except Exception as e:
            self.display_error(f"Tilt Forward command failed: {e}")

    def tilt_backward(self):
        if not self.me_connected:
            return

        try:
            self.retry_drone_command(lambda: self.me.move_back(move_distance))
        except Exception as e:
            self.display_error(f"Tilt Backward command failed: {e}")

    def threaded_drone_command(self, func):
        threading.Thread(target=func).start()

    def retry_drone_command(self, func, max_retries=5):
        retries = 0
        while retries < max_retries:
            try:
                func()
                break
            except Exception as e:
                retries += 1
                print(f"Command failed (Attempt {retries}/{max_retries}): {e}")
                if retries >= max_retries:
                    self.display_error(f"Max retry limit reached. Command failed: {e}")
                    break

    def update_battery(self):
        if not self.me_connected:
            return

        try:
            self.battery_percentage = self.me.get_battery()

            if int(self.battery_percentage) <= 5:
                self.low_battery = True
                self.land_drone()

            self.window.after(10000, self.update_battery)
        except Exception as e:
            self.display_error(f"Failed to update battery status: {e}")

    def update_video(self):
        if not self.me_connected or self.low_battery:
            return

        try:
            frame_read = self.me.get_frame_read()
            if frame_read is not None and frame_read.frame is not None:
                frame = frame_read.frame
                img = cv2.resize(frame, (width, height))
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                image = Image.fromarray(img)
                self.photo = ImageTk.PhotoImage(image=image)

                if self.tracker is not None:  # Check if the tracker is initialized
                    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    success, box = self.tracker.update(gray_frame)

                    if success:
                        (x, y, w, h) = [int(v) for v in box]
                        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                        self.target_coordinates = (x + w // 2, y + h // 2)

                self.video_canvas.delete("all")
                self.video_canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)

            self.window.after(50, self.update_video)
        except Exception as e:
            self.display_error(f"Failed to update video feed: {e}")

    def display_error(self, error_message):
        print(error_message)

    def start_tracking(self):
        if not self.me_connected:
            return

        frame_read = self.me.get_frame_read()
        frame = frame_read.frame
        roi = cv2.selectROI(frame, False)
        self.tracker = cv2.TrackerCSRT_create()
        self.tracker.init(frame, roi)

        self.target_coordinates = None

    def stop_tracking(self):
        self.tracker = None
        self.target_coordinates = None

root = tk.Tk()
app = TelloApp(root, "Tello Drone Control")
root.mainloop()