# Import necessary libraries
import cv2  # For computer vision tasks
import time  # For time-related operations
import threading  # For multi-threading support
import tkinter as tk  # For creating a graphical user interface
from PIL import Image, ImageTk  # For handling images
from djitellopy import Tello  # For controlling the Tello drone

# Constants for various settings
MOVE_DISTANCE = 20  # Distance for drone movement
ROTATE_DEGREE = 15  # Degree for drone rotation
MAX_COMMAND_RETRIES = 5  # Maximum number of retries for sending drone commands
FACE_SIZE_THRESHOLD = 5000  # Threshold for face size detection
FACE_SIZE_UPPER_THRESHOLD = 15000  # Upper threshold for face size detection
SMOOTHING_FACTOR = 0.2  # Smoothing factor for drone movements

# Initialize the Tello drone
def init_tello():
    tello = Tello()
    tello.connect()  # Connect to the drone
    tello.streamon()  # Start receiving the video stream from the drone
    return tello

# PID values for smooth drone movement
pid = [0.35, 0.35, 0]

# Initialize the Tello drone
tello = init_tello()

# Set the width and height for video display
w, h = 360, 240

# Global variables for tracking and error handling
pError = 0
pError_y = 0
tracking_enabled = False  # Flag to enable/disable face tracking

# Function to capture a frame from the Tello's video stream
def get_frame():
    tello_frame = tello.get_frame_read().frame
    return cv2.resize(tello_frame, (w, h))

# Function to detect frontal faces in an image
def face_detect(img):
    # Load the pre-trained face detection model
    frontal_face = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img_faces = frontal_face.detectMultiScale(img_gray, 1.2, 8)

    face_list = []
    face_list_area = []

    # Loop through the detected faces and draw rectangles around them
    for (x, y, w, h) in img_faces:
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)

        # Calculate the center coordinates of the detected face
        cx = x + w // 2
        cy = y + h // 2

        face_list.append([cx, cy])
        face_list_area.append(w * h)

    # If faces are detected, return the image with the largest detected face
    if len(face_list_area) != 0:
        i = face_list_area.index(max(face_list_area))
        return img, [face_list[i], face_list_area[i]]
    else:
        return img, [[0, 0], 0]

# Function to track a face using PID control
def face_track(face_info):
    global pError, pError_y, tracking_enabled

    if tracking_enabled and face_info[1] > 0:  # Check if tracking is enabled and a face is detected
        x = face_info[0][0]
        y = face_info[0][1]
        area = face_info[1]
        forw_backw = 0

        # Calculate the error in the x-axis for face tracking
        error = x - w // 2
        speed = pid[0] * error + pid[1] * (error - pError)
        speed = int(max(-100, min(speed, 100)))  # Limit the speed range

        # Calculate the error in the y-axis for face tracking
        error_y = h // 2 - y
        speed_y = pid[0] * error_y + pid[1] * (error_y - pError_y)
        speed_y = int(max(-100, min(speed_y, 100)))  # Limit the speed range

        # Adjust drone's yaw and up/down velocity based on face position and size
        if x != 0:
            tello.yaw_velocity = speed
        else:
            speed = 0
            tello.yaw_velocity = speed
            error = 0

        if y != 0:
            tello.up_down_velocity = speed_y
        else:
            speed_y = 0
            tello.up_down_velocity = speed_y
            error_y = 0

        # Adjust forward/backward movement based on face size
        if area > FACE_SIZE_THRESHOLD and area < FACE_SIZE_UPPER_THRESHOLD:
            forw_backw = 0
        elif area > FACE_SIZE_UPPER_THRESHOLD:
            forw_backw = -20  # Increase backward speed
        elif area < FACE_SIZE_THRESHOLD and area > 100:
            forw_backw = 20  # Increase forward speed

        # Send control commands to the drone
        tello.send_rc_control(0, forw_backw, speed_y, speed)
        pError, pError_y = error, error_y
    else:
        # No face detected or tracking is disabled, stop the drone
        tello.send_rc_control(0, 0, 0, 0)

# Function to toggle the tracking system on/off
def toggle_tracking():
    global tracking_enabled
    tracking_enabled = not tracking_enabled

# Create a tkinter window for controls and video display
class TelloApp:
    def __init__(self, window, window_title):
        self.window = window
        self.window.title(window_title)
        self.me = Tello()
        self.video_canvas = None
        self.photo = None
        self.face_cascade = None
        self.command_lock = threading.Lock()
        self.setup_ui()
        self.bind_buttons()
        self.initialize_resources()
        self.update_battery()
        self.update_video()
        self.window.protocol("WM_DELETE_WINDOW", self.exit_app)

    # Function to set up the user interface
    def setup_ui(self):
        self.video_canvas = tk.Canvas(self.window, width=w, height=h)
        self.video_canvas.pack()

        self.draw_buttons()

    # Function to bind button clicks to drone control functions
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
            "tilt_backward_btn": self.tilt_backward,
            "toggle_tracking_btn": lambda event=None: toggle_tracking(),  # Use lambda to wrap the function
        }

        for tag, func in buttons_bindings.items():
            self.video_canvas.tag_bind(tag, "<Button-1>", func)

    # Function to initialize resources and connect to the Tello drone
    def initialize_resources(self):
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.me.connect()  # Connect to the drone
        self.me.streamon()  # Start receiving the video stream from the drone

    # Function to execute drone commands in a separate thread
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

        threading.Thread(target=execute_command).start()

    # Drone control functions
    def start_drone(self, event=None):
        self.threaded_drone_command(self.me.takeoff)  # Send the command to start the drone

    def land_drone(self, event=None):
        self.threaded_drone_command(self.me.land)  # Send the command to land the drone

    def exit_app(self, event=None):
        self.threaded_drone_command(self.me.streamoff)  # Stop receiving the video stream
        self.me.land()  # Land the drone
        self.window.destroy()  # Close the tkinter window

    def go_left(self, event=None):
        self.threaded_drone_command(lambda: self.me.move_left(MOVE_DISTANCE))  # Send the command to move the drone left

    def go_right(self, event=None):
        self.threaded_drone_command(lambda: self.me.move_right(MOVE_DISTANCE))  # Send the command to move the drone right

    def go_up(self, event=None):
        self.threaded_drone_command(lambda: self.me.move_up(MOVE_DISTANCE))  # Send the command to move the drone up

    def go_down(self, event=None):
        self.threaded_drone_command(lambda: self.me.move_down(MOVE_DISTANCE))  # Send the command to move the drone down

    def yaw_left(self, event=None):
        self.threaded_drone_command(lambda: self.me.rotate_counter_clockwise(ROTATE_DEGREE))  # Send the command to rotate the drone left

    def yaw_right(self, event=None):
        self.threaded_drone_command(lambda: self.me.rotate_clockwise(ROTATE_DEGREE))  # Send the command to rotate the drone right

    def tilt_forward(self, event=None):
        self.threaded_drone_command(lambda: self.me.move_forward(MOVE_DISTANCE))  # Send the command to tilt the drone forward

    def tilt_backward(self, event=None):
        self.threaded_drone_command(lambda: self.me.move_back(MOVE_DISTANCE))  # Send the command to tilt the drone backward

    # Function to draw buttons on the tkinter canvas
    def draw_buttons(self):
        # Define button coordinates and dimensions for general controls (left)
        general_controls = [
            ("start_btn", "Start Drone", 10, 10),
            ("land_btn", "Land Drone", 10, 40),
            ("left_btn", "Left", 150, 70),
            ("right_btn", "Right", 270, 70),
            ("up_btn", "Up", 210, 10),
            ("down_btn", "Down", 210, 70),
            ("yaw_left_btn", "Yaw Left", 150, 10),
            ("yaw_right_btn", "Yaw Right", 270, 10),
            ("tilt_forward_btn", "Tilt Forward", 90, 10),
            ("tilt_backward_btn", "Tilt Backward", 90, 70),
        ]

        # Create and display buttons on the canvas
        for tag, text, x, y in general_controls:
            self.video_canvas.create_rectangle(x, y, x + 100, y + 20, fill="gray")
            self.video_canvas.create_text(x + 50, y + 10, text=text, tag=tag, fill="white")

        # Define button coordinates and dimensions for additional controls (right)
        additional_controls = [
            ("toggle_tracking_btn", "Toggle Tracking", 325, 40),  # Moved tracking toggle to the middle
            ("exit_btn", "Exit", 10, 100),  # Combined exit button
        ]

        # Create and display additional buttons on the canvas
        for tag, text, x, y in additional_controls:
            self.video_canvas.create_rectangle(x, y, x + 100, y + 20, fill="gray")
            self.video_canvas.create_text(x + 50, y + 10, text=text, tag=tag, fill="white")

    # Function to update the displayed battery percentage
    def update_battery(self):
        battery_percentage = int(self.me.get_battery())  # Get the drone's battery percentage
        battery_text = f"Battery: {battery_percentage}%"  # Format the battery text
        self.video_canvas.delete("battery")  # Clear the previous battery text
        self.video_canvas.create_text(10, h - 10, text=battery_text, anchor=tk.W, tag="battery", fill="white")  # Display the updated battery text

        # If the battery is critically low, automatically land the drone
        if battery_percentage <= 5:
            self.land_drone(None)
        self.window.after(10000, self.update_battery)  # Schedule the next battery update after 10 seconds

    # Function to update the displayed video stream
    def update_video(self):
        frame_read = self.me.get_frame_read()
        if frame_read is not None and frame_read.frame is not None:
            my_frame = frame_read.frame
            img = cv2.resize(my_frame, (w, h))
            img, face_info = face_detect(img)  # Detect faces in the image
            face_track(face_info)  # Track faces using PID control

            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(img)
            self.photo = ImageTk.PhotoImage(image=image)

            self.video_canvas.delete("all")  # Clear the previous video frame
            self.video_canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)  # Display the updated video frame
            self.draw_buttons()  # Redraw the buttons on top of the video frame

        self.window.after(50, self.update_video)  # Schedule the next video update after 50 milliseconds

# Function for smooth speed control
def smooth_speed(current_speed, smoothing_factor=SMOOTHING_FACTOR):
    global smoothed_speed
    if 'smoothed_speed' not in globals():
        smoothed_speed = current_speed
    smoothed_speed = (1 - smoothing_factor) * smoothed_speed + smoothing_factor * current_speed
    return int(smoothed_speed)

# Main function to create and run the application
def main():
    root = tk.Tk()
    app = TelloApp(root, "Tello Drone Control")
    root.mainloop()

if __name__ == "__main__":
    main()