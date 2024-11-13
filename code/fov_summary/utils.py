""" Functions for combining multiple PNG images into a matrix layout. """

from PIL import Image
import math
from pathlib import Path


def sort_paths_by_creation_time(paths) -> list[Path]:
    """
    Sort a list of Path objects by their creation time.

    Parameters
    ----------
    paths : List[Path]
        List of pathlib.Path objects to sort

    Returns
    -------
    List[Path]
        Sorted list of Path objects, oldest first
    """

    def get_creation_time(path):
        try:
            stats = path.stat()
            # Try to get birth time (not available on all Unix systems)
            try:
                return stats.st_birthtime
            except AttributeError:
                # Fall back to modification time if birth time is not available
                return stats.st_mtime
        except OSError as e:
            print(f"Error accessing {path}: {e}")
            # Return a very old timestamp to sort problematic files to the start
            return 0

    return sorted(paths, key=get_creation_time)


def combine_images(image_paths, output_path, num_columns=2, spacing=10):
    """Combine multiple PNG images into a matrix layout.
    Parameters
    ----------
    image_paths : list
        List of paths to PNG images.
    output_path : str
        Path where the combined image will be saved.
    num_columns : int, optional
        Number of columns in the matrix (default is 2).
    spacing : int, optional
        Pixels of spacing between images (default is 10).
    Returns
    -------
    None
        Saves the combined image to output_path.
    """  # Open all images and convert to RGBA
    images = [Image.open(path).convert("RGBA") for path in image_paths]

    # Calculate number of rows needed
    num_images = len(images)
    num_rows = math.ceil(num_images / num_columns)

    # Get dimensions
    widths, heights = zip(*(i.size for i in images))
    max_width = max(widths)
    max_height = max(heights)

    # Calculate total dimensions including spacing
    total_width = (max_width * num_columns) + (spacing * (num_columns - 1))
    total_height = (max_height * num_rows) + (spacing * (num_rows - 1))

    # Create new image with white background
    new_image = Image.new("RGBA", (total_width, total_height), (255, 255, 255, 0))

    # Paste images
    for idx, img in enumerate(images):
        # Calculate position
        row = idx // num_columns
        col = idx % num_columns

        # Calculate x and y coordinates including spacing
        x = col * (max_width + spacing)
        y = row * (max_height + spacing)

        # Center the image if it's smaller than the maximum dimensions
        x_center = x + (max_width - img.size[0]) // 2
        y_center = y + (max_height - img.size[1]) // 2

        new_image.paste(img, (x_center, y_center))

    # Save combined image
    new_image.save(output_path, "PNG")

    # Close all images
    for img in images:
        img.close()


def calculate_optimal_columns(image_paths, target_aspect_ratio=16 / 9):
    """
    Calculate the optimal number of columns for a given set of images and target aspect ratio.

    Parameters
    ----------
    image_paths : list
        List of paths to PNG images
    target_aspect_ratio : float

    Returns
    -------
    int
        Recommended number of columns
    """
    # Open first image to get typical dimensions
    sample_img = Image.open(image_paths[0])
    img_width, img_height = sample_img.size
    sample_img.close()

    num_images = len(image_paths)
    best_columns = 1
    best_ratio_diff = float("inf")

    # Try different numbers of columns
    for cols in range(1, num_images + 1):
        rows = math.ceil(num_images / cols)
        width = cols * img_width
        height = rows * img_height
        ratio = width / height
        ratio_diff = abs(ratio - target_aspect_ratio)

        if ratio_diff < best_ratio_diff:
            best_ratio_diff = ratio_diff
            best_columns = cols

    return best_columns
