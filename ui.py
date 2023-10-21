>>> from djitellopy import Tello
... import cv2
... import tkinter as tk
... from PIL import Image, ImageTk
... 
... # Image parameters
... width = 320
... height = 240
... 
... class TelloApp:
...     def __init__(self, window, window_title):
...         self.window = window
...         self.window.title(window_title)
...         
...         # Canvas for video frame
...         self.video_canvas = tk.Canvas(self.window, width=width, height=height)
...         self.video_canvas.pack(padx=10, pady=10)
...         
...         # Bind the buttons to mouse click events
...         self.video_canvas.tag_bind("start_btn", "<Button-1>", self.start_drone)
...         self.video_canvas.tag_bind("land_btn", "<Button-1>", self.land_drone)
...         self.video_canvas.tag_bind("exit_btn", "<Button-1>", self.exit_app)
...         
...         # Tello setup
...         self.me = Tello()
...         self.me.connect()
...         self.battery_percentage = self.me.get_battery()
... 
...         self.me.streamoff()
...         self.me.streamon()
... 
...         self.update_video()  # Start video stream update loop
... 
...         self.window.mainloop()
... 
...     def draw_buttons(self):
...         # Buttons drawn on canvas
        self.video_canvas.create_rectangle(10, 10, 60, 40, fill="green", tags="start_btn")
        self.video_canvas.create_rectangle(10, 50, 60, 80, fill="red", tags="land_btn")
        self.video_canvas.create_rectangle(10, 90, 60, 120, fill="gray", tags="exit_btn")
        self.video_canvas.create_text(35, 25, text="Start", tags="start_text")
        self.video_canvas.create_text(35, 65, text="Land", tags="land_text")
        self.video_canvas.create_text(35, 105, text="Exit", tags="exit_text")
        
        # Display battery percentage at top middle
        self.video_canvas.create_text(width//2, 10, anchor=tk.N, text=f"Battery: {self.battery_percentage}%", fill="white", tags="battery_text")

    def update_video(self):
        frame_read = self.me.get_frame_read()
        if frame_read is not None and frame_read.frame is not None:
            my_frame = frame_read.frame
            img = cv2.resize(my_frame, (width, height))
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(img)
            self.photo = ImageTk.PhotoImage(image=image)
            
            # Clear the canvas and update the image
            self.video_canvas.delete("all")
            self.video_canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
            self.draw_buttons()
            
        self.window.after(10, self.update_video)  # Adjusted the update time to 10ms for better performance

    def start_drone(self, event):
        self.me.takeoff()

    def land_drone(self, event):
        self.me.land()
        
    def exit_app(self, event):
        self.me.streamoff()
        self.window.quit()

root = tk.Tk()
app = TelloApp(root, "Tello Drone Control")
