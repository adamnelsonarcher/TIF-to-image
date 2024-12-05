# Common configuration for rendering views and drawing agent positions
import numpy as np

# Field of view settings
FOV_ANGLE = np.pi / 3.0  # 60 degrees
VIEW_DISTANCE_RATIO = 0.6  # How far to look/draw as a ratio of DEM width

# Camera settings
ZNEAR = 0.1  # Near clipping plane in km
VIEW_DISTANCE_RATIO = 0.2  # Percentage of DEM width to show in view

# Visualization settings
LIGHT_INTENSITY = 5.0 