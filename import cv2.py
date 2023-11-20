# Import necessary libraries
import cv2           # OpenCV for image processing
import numpy as np   # NumPy for numerical operations
import time          # Time for sleep and time-related operations
import logging       # Logging for managing logs
from djitellopy import Tello  # Import the Tello library for drone control
import threading     # Threading for parallel processing

# Initialize Tello drone
def init_tello():
    tello = Tello()  # Create a Tello object
    Tello.LOGGER.setLevel(logging.WARNING)  # Set logging level to WARNING
    tello.connect()  # Connect to the Tello drone
    print("Tello battery:", tello.get_battery())  # Get and print the drone's battery level

    # Initialize movement velocities
    tello.for_back_velocity = 0
    tello.left_right_velocity = 0
    tello.up_down_velocity = 0
    tello.yaw_velocity = 0
    tello.speed = 0

    # Turn on video streaming
    tello.streamoff()
    tello.streamon()

    return tello

# Width and height of the camera
w, h = 360, 240

# PID values for smooth moving (Proportional-Integral-Derivative controller)
pid = [0.35, 0.35, 0]
pError = 0
pError_y = 0

# Face limit area (defines the size range of the detected face)
faceLimitArea = [8000, 10000]

# Initialize Tello drone
tello = init_tello()

# Get frame from Tello's stream
def get_frame(tello, w=w, h=h):
    tello_frame = tello.get_frame_read().frame  # Read a frame from the drone's video stream
    return cv2.resize(tello_frame, (w, h))  # Resize the frame to the specified width and height

# Detect frontal faces in the given image
def face_detect(img):
    # Load Haar Cascade classifier for detecting frontal faces
    frontal_face = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)  # Convert the image to grayscale
    img_faces = frontal_face.detectMultiScale(img_gray, 1.2, 8)  # Detect faces in the grayscale image

    # Initialize lists to store detected faces and their areas
    face_list = []
    face_list_area = []

    # Iterate over detected faces and draw rectangles around them
    for (x, y, w, h) in img_faces:
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)  # Draw a rectangle around each detected face

        # Calculate the center coordinates and area of the detected face
        cx = x + w // 2
        cy = y + h // 2

        # Store the detected face's coordinates and area
        face_list.append([cx, cy])
        face_list_area.append(w * h)

    # Check if faces were detected
    if len(face_list_area) != 0:
        i = face_list_area.index(max(face_list_area))  # Find the index of the largest detected face
        return img, [face_list[i], face_list_area[i]]  # Return the image and information about the largest detected face
    else:
        return img, [[0, 0], 0]  # Return the image with no detected faces

# Track a face smoothly using PID control
def face_track(tello, face_info, w, h, pid, pError, pError_y):
    x = face_info[0][0]
    y = face_info[0][1]
    area = face_info[1]
    forw_backw = 0

    error = x - w // 2
    speed = pid[0] * error + pid[1] * (error - pError)
    speed = int(np.clip(speed, -60, 60))  # Clip speed to the range of -60 to 60

    error_y = h // (12 / 5) - y
    speed_y = pid[0] * error_y + pid[1] * (error_y - pError_y)
    speed_y = int(np.clip(speed_y, -60, 60))  # Clip speed_y to the range of -60 to 60

    # Set speeds for moving
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

    # Control the area size and move forward or backward
    if area > faceLimitArea[0] and area < faceLimitArea[1]:
        forw_backw = 0
    elif area > faceLimitArea[1]:
        forw_backw = -10
    elif area < faceLimitArea[0] and area > 100:
        forw_backw = 10

    # Send adjusted forward/backward and yaw (rotation) commands to control the drone
    tello.send_rc_control(0, forw_backw, speed_y, speed)
    return error, error_y

# Function for video streaming and face tracking
def video_stream_and_face_track():
    global takeoff, land, pError, pError_y

    while True:
        # Stream video and get a frame from the drone
        img = get_frame(tello, w, h)

        # Take off Tello when 'T' is pressed
        key = cv2.waitKey(1) & 0xFF
        if key == ord('t') and not takeoff:
            try:
                tello.takeoff()  # Make the drone take off
                tello.move_up(100)  # Move the drone up to 1 meter (100 = 1 meter)
                takeoff = True
                land = True
                time.sleep(2.2)  # Sleep for 2.2 seconds
            except:
                pass
        # Land Tello when 'L' is pressed
        elif key == ord('l') and land:
            try:
                tello.streamoff()  # Turn off video streaming
                tello.land()  # Land the drone
            except:
                pass

        # Press 'Q' to exit the program
        if key == ord('q'):
            break

        # Detect faces in the frame
        img, face_info = face_detect(img)

        # Track the detected face smoothly
        pError, pError_y = face_track(tello, face_info, w, h, pid, pError, pError_y)

        # Display the image frame with additional information (battery level, errors, and area)
        img = cv2.putText(img, str(tello.get_battery()), (0, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 100, 250), 1,
                          cv2.LINE_AA)
        img = cv2.putText(img, str('pError:' + str(pError)), (0, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 100, 0), 1,
                          cv2.LINE_AA)
        img = cv2.putText(img, str('pError_y:' + str(pError_y)), (0, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 100, 0),
                          1, cv2.LINE_AA)
        img = cv2.putText(img, str('Area:' + str(face_info[1])), (0, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                          (255, 100, 0), 1, cv2.LINE_AA)
        cv2.imshow("Image", img)  # Display the image frame

# Create a separate thread for video streaming and face tracking
video_thread = threading.Thread(target=video_stream_and_face_track)
video_thread.start()  # Start the video processing thread

# Wait for the video thread to finish (you can add other functionality here)
video_thread.join()

# Turn off video streaming and close OpenCV windows
tello.streamoff()
cv2.destroyAllWindows()
