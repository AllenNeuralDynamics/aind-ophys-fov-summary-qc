""" Functions for combining multiple PNG images into a matrix layout. """

import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import sys
import os


def sort_paths_by_creation_time(paths):
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


def combine_images(image_paths, output_path, num_columns=2, spacing=10, row_labels=None, label_width=200):
    """
    Combine multiple PNG images into a matrix layout with row labels.
    
    Parameters
    ----------
    image_paths : List[str]
        List of paths to PNG images
    output_path : str
        Path where the combined image will be saved
    num_columns : int, optional
        Number of columns in the matrix, by default 2
    spacing : int, optional
        Pixels of spacing between images, by default 10
    row_labels : List[str], optional
        List of labels for each row. If None, no labels are added, by default None
    label_width : int, optional
        Width in pixels reserved for labels, by default 200
    
    Returns
    -------
    None
        Saves the combined image to output_path
    """
    # Open all images and convert to RGBA
    images = [Image.open(path).convert('RGBA') for path in image_paths]
    
    # Calculate number of rows needed
    num_images = len(images)
    num_rows = math.ceil(num_images / num_columns)
    
    # Get dimensions
    widths, heights = zip(*(i.size for i in images))
    max_width = max(widths)
    max_height = max(heights)
    
    # Calculate total dimensions including spacing and labels
    total_width = (max_width * num_columns) + (spacing * (num_columns - 1))
    if row_labels:
        total_width += label_width + spacing  # Add space for labels
    total_height = (max_height * num_rows) + (spacing * (num_rows - 1))
    
    # Create new image with transparent background
    new_image = Image.new('RGBA', (total_width, total_height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(new_image)
    
    # Try to load a system font
    try:
        if sys.platform == 'win32':
            font_path = 'C:/Windows/Fonts/arial.ttf'
        elif sys.platform == 'darwin':  # macOS
            font_path = '/System/Library/Fonts/Helvetica.ttc'
        else:  # Linux
            font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
        
        font = ImageFont.truetype(font_path, size=100)
    except Exception:
        # Fallback to default font
        font = ImageFont.load_default()
    
    # Calculate label position offset
    label_offset = label_width + spacing if row_labels else 0
    
    # Paste images
    for idx, img in enumerate(images):
        # Calculate position
        row = idx // num_columns
        col = idx % num_columns
        
        # Calculate x and y coordinates including spacing and label offset
        x = label_offset + col * (max_width + spacing)
        y = row * (max_height + spacing)
        
        # Center the image if it's smaller than the maximum dimensions
        x_center = x + (max_width - img.size[0]) // 2
        y_center = y + (max_height - img.size[1]) // 2
        
        new_image.paste(img, (x_center, y_center))
        
        # Add row label if it's the first column and we have labels
        if col == 0 and row_labels and row < len(row_labels):
            # Calculate vertical center of the current row
            text_y = y + (max_height // 2)
            
            # Get the size of the text
            text = str(row_labels[row])
            try:
                bbox = draw.textbbox((0, 0), text, font=font)
                text_height = bbox[3] - bbox[1]
            except AttributeError:  # For older Pillow versions
                text_height = font.getsize(text)[1]
            
            # Draw the label vertically centered with the row
            draw.text(
                (spacing, text_y - text_height // 2),
                text,
                fill=(0, 0, 0, 255),  # Black text
                font=font
            )
    
    # Save combined image
    new_image.save(output_path, 'PNG')
    
    # Close all images
    for img in images:
        img.close()