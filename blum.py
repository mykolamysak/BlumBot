import pygetwindow as gw
import pyautogui
from PIL import ImageGrab
import cv2
import numpy as np
from pynput import mouse, keyboard
import time
import threading
from pynput.mouse import Button, Controller as MouseController
from concurrent.futures import ThreadPoolExecutor

pause_clicking = True  # The algorithm will be paused at startup
last_click_time = time.time()  # Time of the last click
exit_program = threading.Event()  # Event to signal exit

def get_telegram_window_bbox():
    windows = gw.getWindowsWithTitle('Telegram')
    if windows:
        window = windows[0]
        return (window.left, window.top, window.right, window.bottom)
    return None

def find_color_on_screen(target_color, bbox, tolerance=8, resize_factor=0.40):
    # Capture and resize the screenshot within the bounding box
    screenshot = ImageGrab.grab(bbox=bbox)
    screenshot = screenshot.resize(
        (int(screenshot.width * resize_factor), int(screenshot.height * resize_factor)),
        ImageGrab.Image.BILINEAR
    )

    # Convert the screenshot to a NumPy array
    screenshot = np.array(screenshot)

    # Convert the screenshot to HSV color space
    hsv_screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGB2HSV)

    # Convert the target color to HSV
    target_color_hsv = cv2.cvtColor(np.uint8([[target_color]]), cv2.COLOR_BGR2HSV)[0][0]

    # Define the color range for the mask in HSV
    lower_bound = np.array([max(0, target_color_hsv[0] - tolerance), max(0, target_color_hsv[1] - tolerance), max(0, target_color_hsv[2] - tolerance)])
    upper_bound = np.array([min(255, target_color_hsv[0] + tolerance), min(255, target_color_hsv[1] + tolerance), min(255, target_color_hsv[2] + tolerance)])

    # Create the mask
    mask = cv2.inRange(hsv_screenshot, lower_bound, upper_bound)

    # Find contours in the mask
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # If contours are found, return the center of the largest contour
    if contours:
        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)
        center_x, center_y = x + w // 2, y + h // 2

        # Adjust the center coordinates to match the original screenshot size
        center_x = int(center_x / resize_factor)
        center_y = int(center_y / resize_factor)

        return bbox[0] + center_x, bbox[1] + center_y

    return None

def on_click(x, y, button, pressed):
    global pause_clicking
    if button == mouse.Button.right and pressed:
        pause_clicking = not pause_clicking
        print(f"[⌛] Clicking {'paused' if pause_clicking else 'resumed'}")
        return True

def on_press(key):
    if key == keyboard.Key.space:
        print("[🦋] Spacebar pressed. Exiting...")
        exit_program.set()
        return False  # Stop listener

mouse_controller = MouseController()

def click_on_color(target_color, bbox):
    global pause_clicking, last_click_time, exit_program
    with ThreadPoolExecutor(max_workers=4) as executor:
        while not exit_program.is_set():
            if not pause_clicking:
                future = executor.submit(find_color_on_screen, target_color, bbox)
                position = future.result()

                if position:
                    current_time = time.time()
                    print(f"[⌚] Time since last click: {current_time - last_click_time} seconds")
                    last_click_time = current_time
                    mouse_controller.position = position
                    mouse_controller.press(Button.left)  # Press mouse button
                    mouse_controller.release(Button.left)  # Release mouse button

def main(target_color):
    global pause_clicking
    print(f"[🍀] Searching for color BGR: {target_color}")
    bbox = get_telegram_window_bbox()
    if bbox is None:
        print("[🍂] Telegram window not found.")
        return
    print(f"[🌐] Telegram window coordinates: {bbox}")

    # Активуємо вікно Telegram
    telegram_window = gw.getWindowsWithTitle('Telegram')[0]
    telegram_window.activate()

    mouse_listener = mouse.Listener(on_click=on_click)
    mouse_listener.start()

    keyboard_listener = keyboard.Listener(on_press=on_press)
    keyboard_listener.start()

    click_thread = threading.Thread(target=click_on_color, args=(target_color, bbox))
    click_thread.start()

    keyboard_listener.join()
    exit_program.set()  # Ensure click thread will exit
    click_thread.join()
    mouse_listener.stop()
    print("\n[🗿] Program exited.")

if __name__ == "__main__":
    target_color = (1, 218, 69)  # Set the color directly in BGR format
    main(target_color)
