import rasterio
import numpy as np
import matplotlib.pyplot as plt
from rasterio.plot import show

def get_valid_file_path(prompt):
    while True:
        file_path = input(prompt)
        if file_path.endswith(".tif"):
            return file_path
        else:
            print("Invalid file format. Please enter a .tif file.")

def read_raster(file_path):
    with rasterio.open(file_path) as src:
        data = src.read(1)
        profile = src.profile
    return data, profile

def resample_raster(data, reference_shape):
    return np.resize(data, reference_shape)

def calculate_difference(image1, image2):
    return np.abs(image1 - image2)

def enhance_contrast(diff_image, threshold_factor=0.75):
    diff_image = (diff_image - np.min(diff_image)) / (np.max(diff_image) - np.min(diff_image)) * 255
    diff_image = diff_image.astype(np.uint8)

    diff_image = np.log1p(diff_image)
    diff_image = (diff_image / np.max(diff_image)) * 255
    diff_image = diff_image.astype(np.uint8)

    threshold = threshold_factor * np.max(diff_image)  # Set a dynamic threshold
    return np.where(diff_image > threshold, 255, 0).astype(np.uint8)

def save_raster(output_path, data, profile):
    profile.update(dtype=rasterio.uint8, count=1)
    with rasterio.open(output_path, 'w', **profile) as dst:
        dst.write(data, 1)

def main():
    image1_path = get_valid_file_path("Enter path to the first .tif image: ")
    image2_path = get_valid_file_path("Enter path to the second .tif image: ")
    output_path = get_valid_file_path("Enter path for the output .tif file: ")

    image1, profile1 = read_raster(image1_path)
    image2, profile2 = read_raster(image2_path)

    if image1.shape != image2.shape:
        print("Resampling second image to match the first...")
        image2 = resample_raster(image2, image1.shape)
    
    diff_image = calculate_difference(image1, image2)
    change_map = enhance_contrast(diff_image)
    save_raster(output_path, change_map, profile1)

    print(f"Change map saved to {output_path}")
    
    plt.figure(figsize=(10, 5))

    plt.subplot(1, 3, 1)
    plt.title("Image 1")
    plt.imshow(image1)
    plt.axis("off")

    plt.subplot(1, 3, 2)
    plt.title("Image 2")
    plt.imshow(image2)
    plt.axis("off")

    plt.subplot(1, 3, 3)
    plt.title("Change Map")
    plt.imshow(change_map)
    plt.axis("off")

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()
