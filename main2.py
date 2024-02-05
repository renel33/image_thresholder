import tkinter as tk
from tkinter import ttk
import os
import rasterio
import numpy as np
from PIL import Image, ImageTk
import matplotlib.pyplot as plt


# Global variables
image_directory = "/mnt/sdd/vegetation_mask/"
threshold_value = 0.2
current_image = None
colour_image = None
current_index = 0
image_list = []

def load_image():
    global current_image, image_list, current_index, colour_image
    if current_index < len(image_list):
        image_path = os.path.join(image_directory, image_list[current_index])
        image = rasterio.open(image_path).read(7)
        image = image.astype(np.float32)
        image *= 255.0/image.max()
        
        cm = plt.get_cmap('RdYlGn')
        colour_image = (cm(image)[:, :, :3] * 255).astype(np.uint8)
        
        current_image = Image.fromarray(image)
        colour_image = Image.fromarray(colour_image)
        update_display()

def update_display():
    global current_image, colour_image
    if current_image:
        # Create a copy of the current image for thresholding
        # Get the color map by name:
        img_copy = current_image.copy()
        
        img = apply_threshold(img_copy)
        img_tk = ImageTk.PhotoImage(img)
        
        # Display the unthresholded image as the background
        background_label.config(image=ImageTk.PhotoImage(colour_image))
        
        # Update the label with the thresholded image
        label.config(image=img_tk)
        label.image = img_tk
        
        # Update the threshold label
        threshold_label.config(text=f"Threshold: {threshold_value:.2f}")

def save_image():
    global current_index, current_image, image_list
    if current_image:
        save_path = os.path.join(image_directory, "thresholded_" + image_list[current_index])
        current_image.save(save_path)
        current_index += 1
        load_image()

def apply_threshold(img):
    img_array = np.array(img)
    img_array[img_array > float(threshold_value)] = 255
    return Image.fromarray(img_array)

def threshold_changed(value):
    global threshold_value
    threshold_value = float(value)
    update_display()

def next_image():
    global current_index
    current_index += 1
    load_image()

def previous_image():
    global current_index
    current_index -= 1
    load_image()

root = tk.Tk()
root.title("Image Thresholding Application")

frame = ttk.Frame(root)
frame.grid(row=0, column=0, padx=10, pady=10)

label = ttk.Label(frame)
label.grid(row=0, column=0, columnspan=2)

background_label = ttk.Label(frame)
background_label.grid(row=0, column=0, columnspan=2)

load_button = ttk.Button(frame, text="Load Image", command=load_image)
load_button.grid(row=1, column=0, padx=5, pady=5)

save_button = ttk.Button(frame, text="Save Image", command=save_image)
save_button.grid(row=1, column=1, padx=5, pady=5)

threshold_slider = ttk.Scale(frame, from_=0, to=255, orient="horizontal", command=threshold_changed, length=1000)
threshold_slider.grid(row=2, column=0, columnspan=4, padx=5, pady=5)
threshold_slider.set(threshold_value)

prev_button = ttk.Button(frame, text="Previous", command=previous_image)
prev_button.grid(row=3, column=0, padx=5, pady=5)

next_button = ttk.Button(frame, text="Next", command=next_image)
next_button.grid(row=3, column=1, padx=5, pady=5)

threshold_label = ttk.Label(frame, text=f"Threshold: {threshold_value:.2f}")
threshold_label.grid(row=4, column=0, columnspan=2)

image_list = [filename for filename in os.listdir(image_directory) if filename.endswith(('.tif'))]

if len(image_list) > 0:
    load_image()

root.mainloop()