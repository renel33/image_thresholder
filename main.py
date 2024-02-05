import tkinter as tk
from tkinter import ttk
import os
import rasterio
from rasterio.windows import Window
import numpy as np
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
from skimage import exposure
from skimage.filters import threshold_local
from sklearn.preprocessing import MinMaxScaler

# Global variables
image_directory = "/mnt/sdc/landsat_senegal_data/early_training_images_sar_v3"
out_directory = "/mnt/sdc/landsat_senegal_data/late_training_images_vegetation_cover_thresh"
os.makedirs(out_directory, exist_ok=True)
overwrite = False
threshold_value = 0.2
image_filename = None
current_image = None
current_color_image = None
current_ndvi_image = None
thresh_image = None
current_index = 0
image_list = []
import numexpr

def pan_sharpen_brovey(band_1, band_2, band_3, pan_band):
    
    # Calculate total
    exp = 'band_1 + band_2 + band_3'
    total = numexpr.evaluate(exp)
    # Perform Brovey Transform in form of: band/total*panchromatic
    exp = 'a/b*c'
    band_1_sharpen = numexpr.evaluate(exp, local_dict={'a': band_1,
                                                       'b': total,
                                                       'c': pan_band})
    band_2_sharpen = numexpr.evaluate(exp, local_dict={'a': band_2,
                                                       'b': total,
                                                       'c': pan_band})
    band_3_sharpen = numexpr.evaluate(exp, local_dict={'a': band_3,
                                                       'b': total,
                                                       'c': pan_band})

    return band_1_sharpen, band_2_sharpen, band_3_sharpen


def load_image():
    global current_image, current_color_image, current_ndvi_image, image_list, current_index, image_filename
    if current_index < len(image_list):
        image_path = os.path.join(image_directory, image_list[current_index])
            
        #image = np.transpose(rasterio.open(image_path).read((2,3,4,7), window=Window(0, 0, 128, 128)),(1,2,0))
        src = rasterio.open(image_path)
        out_meta = src.meta.copy()
        
        # Read the window from the raster
        window_data = src.read()
        
        #ndvi_image = exposure.equalize_hist(window_data[10])
        ndvi_image = window_data[10]
        ndvi_image = MinMaxScaler().fit_transform(ndvi_image.reshape(-1, 1)).reshape(ndvi_image.shape)
        cm = plt.get_cmap('RdYlGn')
        cm2 = plt.get_cmap('RdYlGn_r')
        
        n, r, g = pan_sharpen_brovey(window_data[3], window_data[2], window_data[1], window_data[6])
        
        image = np.stack([n, r, g])
        
        image = np.transpose(image, (1,2,0)).astype(np.float32)
        ndvi_hist = (cm(ndvi_image)[:, :, :3] *  255.0).astype(np.uint8)
        #image = exposure.equalize_hist(image).astype(np.float32)
        image *= 255.0 / image.max()
        image = image.astype(np.uint8)
        
        ndvi_thresh = window_data[10].astype(np.float32)
        
        
        ndvi_thresh *= 255.0 / ndvi_thresh.max()
        
        current_image = Image.fromarray(ndvi_thresh)
        current_ndvi_image = Image.fromarray(ndvi_hist).resize((1000,1000))
        current_color_image = Image.fromarray(image).resize((1000, 1000))
        
        image_filename = image_list[current_index]
        update_display()

def update_display():
    global current_image, current_color_image, current_ndvi_image, image_filename, thresh_image
    if current_image:
        # Create a copy of the current image for thresholding
        img_copy = current_image.copy()

        img, thresh_image = apply_threshold(img_copy)
        img = img.resize((1000,1000))
        img_tk = ImageTk.PhotoImage(img)
        
        # Display the unthresholded image as the background
        background_label.config(image=ImageTk.PhotoImage(current_ndvi_image))
        
        # Update the label with the thresholded image
        label.config(image=img_tk)
        label.image = img_tk

        if current_color_image:
            color_img_tk = ImageTk.PhotoImage(current_color_image)
            canvas.create_image(0, 0, anchor="nw", image=color_img_tk)
            canvas.image = color_img_tk
        
        if current_ndvi_image:
            ndvi_img_tk = ImageTk.PhotoImage(current_ndvi_image)
            canvas1.create_image(0, 0, anchor="nw", image=ndvi_img_tk)
            canvas1.image = ndvi_img_tk

        threshold_label.config(text=f"Threshold: {threshold_value:.2f}")
        
        imagefile_label.config(text=f"{image_filename}")

def save_image():
    global current_index, current_image, image_list, thresh_image
    if current_image:
        image_path = os.path.join(image_directory, image_list[current_index])
        save_path = os.path.join(out_directory, image_list[current_index])
        
        src = rasterio.open(image_path)
        
        if src.width != 128 or src.height != 128:
            out_meta = src.meta.copy()
            # Calculate the center of the raster
            center_x, center_y = src.width // 2, src.height // 2

            # Define the window
            left = center_x - 128 // 2
            top = center_y - 128 // 2
            window = rasterio.windows.Window(left, top, *(128, 128))

            # Read the window from the raster
            orig = src.read(window=window)
            
            #print(thresh_image.shape)
            out_thresh_image = thresh_image.copy()
            #print(out_thresh_image.shape)
            out_thresh_image = np.expand_dims(out_thresh_image, 0)
            
            combined = np.concatenate([orig, out_thresh_image], axis=0)
            
            out_meta.update({"driver": "GTiff",
                                "height": 128,
                                "width": 128,
                                "transform": rasterio.windows.transform(window, src.transform),
                                "count": 3,})
            
        else:
            out_meta = src.meta.copy()
            orig = src.read()
            
            #print(thresh_image.shape)
            out_thresh_image = thresh_image.copy()
            #print(out_thresh_image.shape)
            out_thresh_image = np.expand_dims(out_thresh_image, 0)
            orig = orig[[0,1,2,3,4,5,6,7,8,9],:,:]
            combined = np.concatenate([orig, out_thresh_image], axis=0)
            
            out_meta.update({"driver": "GTiff",
                                "height": 128,
                                "width": 128,
                                "count": 11,})
            
            
        
        with rasterio.open(save_path, "w", **out_meta) as out:
            out.write(combined)
        current_index += 1
        load_image()

def apply_threshold(img):
    img_array = np.array(img)
    img_array = img_array > float(threshold_value)
    img_array[img_array>0] = 255
    return Image.fromarray(img_array), img_array

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
label.grid(row=0, column=0)

background_label = ttk.Label(frame)
background_label.grid(row=0, column=0)

canvas = tk.Canvas(frame, width=1000, height=1000)  # Adjust width and height as needed
canvas.grid(row=0, column=1)

canvas1 = tk.Canvas(frame, width=1000, height=1000)  # Adjust width and height as needed
canvas1.grid(row=0, column=2)

load_button = ttk.Button(frame, text="Load Image", command=load_image)
load_button.grid(row=1, column=0, padx=5, pady=5)

save_button = ttk.Button(frame, text="Save Image", command=save_image)
save_button.grid(row=1, column=1, padx=5, pady=5)

threshold_slider = ttk.Scale(frame, from_=0, to=255, orient="horizontal", command=threshold_changed, length=1000)
threshold_slider.grid(row=2, column=0, columnspan=2, padx=5, pady=5)
threshold_slider.set(threshold_value)

prev_button = ttk.Button(frame, text="Previous", command=previous_image)
prev_button.grid(row=3, column=0, padx=5, pady=5)

next_button = ttk.Button(frame, text="Next", command=next_image)
next_button.grid(row=3, column=1, padx=5, pady=5)

threshold_label = ttk.Label(frame, text=f"Threshold: {threshold_value:.2f}")
threshold_label.grid(row=4, column=0, columnspan=2)

imagefile_label = ttk.Label(frame, text=f"{image_filename}")
imagefile_label.grid(row=5, column=0, columnspan=2)

image_list = [filename for filename in os.listdir(image_directory) if filename.endswith(('.tif'))]

if not overwrite:
    out_list = [filename for filename in os.listdir(out_directory) if filename.endswith(('.tif'))]
    image_list = [filename for filename in image_list if filename not in out_list]

if len(image_list) > 0:
    load_image()

root.mainloop()
