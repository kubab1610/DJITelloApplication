import cv2
from djitellopy import Tello
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.graphics.texture import Texture
from kivy.graphics import Rectangle
from kivy.clock import Clock
from PIL import Image

width = 320
height = 240
move_distance = 20
rotate_degree = 15

class TelloApp(BoxLayout):
    def __init__(self, **kwargs):
        super(TelloApp, self).__init__(**kwargs)

        self.orientation = 'vertical'

        self.video_canvas = Widget(size=(width, height))
        self.add_widget(self.video_canvas)

        self.low_battery = False

        self.me = Tello()
        self.me.connect()
        self.me.streamoff()
        self.me.streamon()

        self.update_battery()
        self.draw_buttons()

    def draw_buttons(self):
        button_layout = BoxLayout(orientation='horizontal')

        start_button = Button(text="Start", on_press=self.start_drone)
        land_button = Button(text="Land", on_press=self.land_drone)
        exit_button = Button(text="Exit", on_press=self.exit_app)

        button_layout.add_widget(start_button)
        button_layout.add_widget(land_button)
        button_layout.add_widget(exit_button)

        self.add_widget(button_layout)

    def start_drone(self, event):
        self.threaded_drone_command(self.me.takeoff)

    def land_drone(self, event):
        self.threaded_drone_command(self.me.land)
        self.low_battery = True

    def exit_app(self, event):
        self.threaded_drone_command(self.me.streamoff)
        App.get_running_app().stop()

    def go_left(self, event):
        if not self.low_battery:
            self.threaded_drone_command(lambda: self.me.move_left(move_distance))

    def go_right(self, event):
        if not self.low_battery:
            self.threaded_drone_command(lambda: self.me.move_right(move_distance))

    def go_up(self, event):
        if not self.low_battery:
            self.threaded_drone_command(lambda: self.me.move_up(move_distance))

    def go_down(self, event):
        if not self.low_battery:
            self.threaded_drone_command(lambda: self.me.move_down(move_distance))

    def yaw_left(self, event):
        if not self.low_battery:
            self.threaded_drone_command(lambda: self.me.rotate_counter_clockwise(rotate_degree))

    def yaw_right(self, event):
        if not self.low_battery:
            self.threaded_drone_command(lambda: self.me.rotate_clockwise(rotate_degree))

    def tilt_forward(self, event):
        if not self.low_battery:
            self.threaded_drone_command(lambda: self.me.move_forward(move_distance))

    def tilt_backward(self, event):
        if not self.low_battery:
            self.threaded_drone_command(lambda: self.me.move_backward(move_distance))

    def threaded_drone_command(self, func):
        import threading
        threading.Thread(target=func).start()

    def update_battery(self):
        battery_label = Label(text="Battery: 100%")

        if int(self.me.get_battery()) <= 5:
            self.low_battery = True
            self.land_drone(None)
            battery_label.text = "Battery: Low"

        self.add_widget(battery_label)

    def update_video(self, dt):
        if self.low_battery:
            return

        frame_read = self.me.get_frame_read()
        if frame_read is not None and frame_read.frame is not None:
            my_frame = frame_read.frame
            img = cv2.resize(my_frame, (width, height))
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(img)
            texture = Texture.create(size=(width, height), colorfmt='rgb')

            texture.blit_buffer(image.tobytes(), colorfmt='rgb', bufferfmt='ubyte')
            if not hasattr(self, 'video_texture'):
                with self.video_canvas.canvas:
                    self.video_texture = Rectangle(pos=self.video_canvas.pos, size=self.video_canvas.size, texture=texture)
            else:
                self.video_texture.texture = texture

class TelloControlApp(App):
    def build(self):
        app = TelloApp()
        Clock.schedule_interval(app.update_video, 1/30)
        return app

if __name__ == '__main__':
    TelloControlApp().run()