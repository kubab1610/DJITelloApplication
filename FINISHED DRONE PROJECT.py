import threading
from djitellopy import Tello
import cv2
import tkinter as tk
from PIL import Image, ImageTk
import time

WIDTH = 320
HEIGHT = 240
MOVE_DISTANCE = 20
ROTATE_DEGREE = 15
MAX_COMMAND_RETRIES = 5
FACE_THRESHOLD = 50
FACE_SIZE_THRESHOLD = 5000  # Sample threshold for face area to start moving forward
FACE_SIZE_UPPER_THRESHOLD = 15000  # Sample threshold for face area to start moving backward

class TelloApp:
    def __init__(self, window, window_title):
        self.window = window
        self.window.title(window_title)
        self.me = Tello()
        self.video_canvas = None
        self.photo = None
        self.face_cascade = None
        self.battery_percentage = 100
        self.low_battery = False
        self.command_lock = threading.Lock()
        self.setup_ui()
        self.bind_buttons()
        self.initialize_resources()
        self.update_battery()
        self.update_video()
        self.window.protocol("WM_DELETE_WINDOW", self.exit_app)  # Handle window close
        self.window.mainloop()

    def setup_ui(self):
        self.video_canvas = tk.Canvas(self.window, width=WIDTH, height=HEIGHT)
        self.video_canvas.pack(padx=10, pady=10)
        self.draw_buttons()

    def bind_buttons(self):
        buttons_bindings = {
            "start_btn": self.start_drone,
            "land_btn": self.land_drone,
            "exit_btn": self.exit_app,
            "left_btn": self.go_left,
            "right_btn": self.go_right,
            "up_btn": self.go_up,
            "down_btn": self.go_down,
            "yaw_left_btn": self.yaw_left,
            "yaw_right_btn": self.yaw_right,
            "tilt_forward_btn": self.tilt_forward,
            "tilt_backward_btn": self.tilt_backward
        }
        for tag, func in buttons_bindings.items():
            self.video_canvas.tag_bind(tag, "<Button-1>", func)

    def initialize_resources(self):
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.me.connect()
        self.me.streamon()

    def threaded_drone_command(self, func):
        def execute_command():
            retries = 0
            while retries < MAX_COMMAND_RETRIES:
                try:
                    if func() == 'ok':
                        return
                except Exception as e:
                    print(f"Exception while executing command: {e}")
                retries += 1
                time.sleep(0.5)
            print(f"Command failed after {MAX_COMMAND_RETRIES} retries.")

        threading.Thread(target=execute_command).start()  # Execute in a separate thread

    def start_drone(self, event=None):
        self.threaded_drone_command(self.me.takeoff)

    def land_drone(self, event=None):
        self.threaded_drone_command(self.me.land)
        self.low_battery = True

    def exit_app(self, event=None):
        self.threaded_drone_command(self.me.streamoff)
        self.me.land()  # Ensure the drone lands before exiting
        self.window.destroy()  # Close the window

    def go_left(self, event=None):
        if not self.low_battery:
            self.threaded_drone_command(lambda: self.me.move_left(MOVE_DISTANCE))

    def go_right(self, event=None):
        if not self.low_battery:
            self.threaded_drone_command(lambda: self.me.move_right(MOVE_DISTANCE))

    def go_up(self, event=None):
        if not self.low_battery:
            self.threaded_drone_command(lambda: self.me.move_up(MOVE_DISTANCE))

    def go_down(self, event=None):
        if not self.low_battery:
            self.threaded_drone_command(lambda: self.me.move_down(MOVE_DISTANCE))

    def yaw_left(self, event=None):
        if not self.low_battery:
            self.threaded_drone_command(lambda: self.me.rotate_counter_clockwise(ROTATE_DEGREE))

    def yaw_right(self, event=None):
        if not self.low_battery:
            self.threaded_drone_command(lambda: self.me.rotate_clockwise(ROTATE_DEGREE))

    def tilt_forward(self, event=None):
        if not self.low_battery:
            self.threaded_drone_command(lambda: self.me.move_forward(MOVE_DISTANCE))

    def tilt_backward(self, event=None):
        if not self.low_battery:
            self.threaded_drone_command(lambda: self.me.move_backward(MOVE_DISTANCE))

    def update_battery(self):
        self.battery_percentage = int(self.me.get_battery())
        if self.battery_percentage <= 5:
            self.low_battery = True
            self.land_drone(None)
        self.window.after(10000, self.update_battery)
    
    def draw_buttons(self):
        self.video_canvas.create_rectangle(10, 10, 60, 40, fill="green", tags="start_btn")
        self.video_canvas.create_rectangle(10, 50, 60, 80, fill="red", tags="land_btn")
        self.video_canvas.create_rectangle(10, 90, 60, 120, fill="gray", tags="exit_btn")
        self.video_canvas.create_text(35, 25, text="Start", tags="start_text")
        self.video_canvas.create_text(35, 65, text="Land", tags="land_text")
        self.video_canvas.create_text(35, 105, text="Exit", tags="exit_text")

        movement_buttons = [
            (70, 10, 120, 40, "blue", "left_btn", "Left"),
            (130, 10, 180, 40, "blue", "right_btn", "Right"),
            (100, 40, 150, 70, "blue", "up_btn", "Up"),
            (100, 80, 150, 110, "blue", "down_btn", "Down"),
            (190, 10, 240, 40, "purple", "yaw_left_btn", "YawL"),
            (250, 10, 300, 40, "purple", "yaw_right_btn", "YawR"),
            (220, 40, 270, 70, "purple", "tilt_forward_btn", "TiltF"),
            (220, 80, 270, 110, "purple", "tilt_backward_btn", "TiltB"),
        ]

        for x1, y1, x2, y2, color, tag, text in movement_buttons:
            self.video_canvas.create_rectangle(x1, y1, x2, y2, fill=color, tags=tag)
            self.video_canvas.create_text((x1+x2)//2, (y1+y2)//2, text=text)
    def update_video(self):
        if self.low_battery:
            return

        frame_read = self.me.get_frame_read()
        if frame_read is not None and frame_read.frame is not None:
            my_frame = frame_read.frame
            img = cv2.resize(my_frame, (WIDTH, HEIGHT))
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            error_x = 0
            error_y = 0

            faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

            if len(faces) > 0:
                (x, y, w, h) = faces[0]
                cv2.rectangle(img, (x, y), (x + w, y + h), (255, 0, 0), 2)

                center_x = x + w // 2
                center_y = y + h // 2

                error_x = center_x - WIDTH // 2
                error_y = center_y - HEIGHT // 2

                # Yaw control
                if abs(error_x) > FACE_THRESHOLD:
                    if error_x > 0:
                        self.threaded_drone_command(lambda: self.me.rotate_clockwise(ROTATE_DEGREE))
                    else:
                        self.threaded_drone_command(lambda: self.me.rotate_counter_clockwise(ROTATE_DEGREE))

                # Altitude control
                if abs(error_y) > FACE_THRESHOLD:
                    if error_y > 0:
                        self.threaded_drone_command(lambda: self.me.move_down(MOVE_DISTANCE))
                    else:
                        self.threaded_drone_command(lambda: self.me.move_up(MOVE_DISTANCE))

                # Forward/Backward control
                if w * h < FACE_SIZE_THRESHOLD:
                    self.threaded_drone_command(lambda: self.me.move_forward(MOVE_DISTANCE))
                elif w * h > FACE_SIZE_UPPER_THRESHOLD:
                    self.threaded_drone_command(lambda: self.me.move_backward(MOVE_DISTANCE))

            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(img)
            self.photo = ImageTk.PhotoImage(image=image)

            self.video_canvas.delete("all")
            self.video_canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
            self.draw_buttons()

        self.window.after(50, self.update_video)
            
def main():
    root = tk.Tk()
    app = TelloApp(root, "Tello Drone Control")

if __name__ == "__main__":
    main()