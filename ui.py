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

        self.video_canvas = tk.Canvas(self.window, width=width, height=height)
        self.video_canvas.pack(padx=10, pady=10)

        self.bind_buttons()

        self.me = Tello()
        self.me.connect()
        self.me.streamoff()
        self.me.streamon()

        self.low_battery = False
        self.update_battery()
        self.update_video()
        self.draw_buttons()

        self.window.mainloop()

    def bind_buttons(self):
        self.video_canvas.tag_bind("start_btn", "<Button-1>", self.start_drone)
        self.video_canvas.tag_bind("land_btn", "<Button-1>", self.land_drone)
        self.video_canvas.tag_bind("exit_btn", "<Button-1>", self.exit_app)
        self.video_canvas.tag_bind("left_btn", "<Button-1>", self.go_left)
        self.video_canvas.tag_bind("right_btn", "<Button-1>", self.go_right)
        self.video_canvas.tag_bind("up_btn", "<Button-1>", self.go_up)
        self.video_canvas.tag_bind("down_btn", "<Button-1>", self.go_down)
        self.video_canvas.tag_bind("yaw_left_btn", "<Button-1>", self.yaw_left)
        self.video_canvas.tag_bind("yaw_right_btn", "<Button-1>", self.yaw_right)
        self.video_canvas.tag_bind("tilt_forward_btn", "<Button-1>", self.tilt_forward)
        self.video_canvas.tag_bind("tilt_backward_btn", "<Button-1>", self.tilt_backward)

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

    def threaded_drone_command(self, func):
        threading.Thread(target=func).start()

    def start_drone(self, event=None):
        self.threaded_drone_command(self.me.takeoff)

    def land_drone(self, event=None):
        self.threaded_drone_command(self.me.land)
        self.low_battery = True

    def exit_app(self, event=None):
        self.threaded_drone_command(self.me.streamoff)
        self.window.quit()

    def go_left(self, event=None):
        if not self.low_battery:
            self.threaded_drone_command(lambda: self.me.move_left(move_distance))

    def go_right(self, event=None):
        if not self.low_battery:
            self.threaded_drone_command(lambda: self.me.move_right(move_distance))

    def go_up(self, event=None):
        if not self.low_battery:
            self.threaded_drone_command(lambda: self.me.move_up(move_distance))

    def go_down(self, event=None):
        if not self.low_battery:
            self.threaded_drone_command(lambda: self.me.move_down(move_distance))

    def yaw_left(self, event=None):
        if not self.low_battery:
            self.threaded_drone_command(lambda: self.me.rotate_counter_clockwise(rotate_degree))

    def yaw_right(self, event=None):
        if not self.low_battery:
            self.threaded_drone_command(lambda: self.me.rotate_clockwise(rotate_degree))

    def tilt_forward(self, event=None):
        if not self.low_battery:
            self.threaded_drone_command(lambda: self.me.move_forward(move_distance))

    def tilt_backward(self, event=None):
        if not self.low_battery:
            self.threaded_drone_command(lambda: self.me.move_backward(move_distance))

    def update_battery(self):
        self.battery_percentage = self.me.get_battery()

        if int(self.battery_percentage) <= 5:
            self.low_battery = True
            self.land_drone(None)

        self.window.after(10000, self.update_battery)

    def update_video(self):
        if self.low_battery:
            return

        frame_read = self.me.get_frame_read()
        if frame_read is not None and frame_read.frame is not None:
            my_frame = frame_read.frame
            img = cv2.resize(my_frame, (width, height))
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(img)
            self.photo = ImageTk.PhotoImage(image=image)
            
            self.video_canvas.delete("all")
            self.video_canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
            self.draw_buttons()

        self.window.after(50, self.update_video)

root = tk.Tk()
app = TelloApp(root, "Tello Drone Control")
