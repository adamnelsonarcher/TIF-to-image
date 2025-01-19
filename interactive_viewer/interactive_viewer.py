import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import matplotlib.pyplot as plt
from dem_to_mesh import create_mesh_from_dem
from classify_terrain import classify_and_color_mesh
from terrain_viewer import launch_terrain_viewer
import rasterio


def launch_interactive_viewer(mesh, initial_position=None, initial_target=None, full_dem=None, window_bounds=None, dem_length_km=None):
    # Create a simple minimap if we have the full DEM
    if full_dem is not None and window_bounds is not None:
        plt.figure(figsize=(5, 5))
        plt.imshow(full_dem, cmap='terrain')
        
        # Draw a rectangle around the current view section
        x_min, x_max, y_min, y_max = window_bounds
        plt.plot([x_min, x_max, x_max, x_min, x_min],
                [y_min, y_min, y_max, y_max, y_min],
                'r-', linewidth=2)
        
        plt.title('DEM Overview')
        plt.axis('off')
        plt.show(block=False)
    
    # Launch the 3D viewer
    launch_terrain_viewer(mesh)

def main():
    try:
        # Load DEM data with subsample for testing
        dem_file = 'dem_data.tif'
        manual_length_km = None  # Set this to a number to override the natural scale
        
        print(f"Loading DEM file: {dem_file}")
        with rasterio.open(dem_file) as dem_dataset:
            # Read full DEM for minimap
            full_dem = dem_dataset.read(1)
            
            # Get a 4km x 4km test section from the center
            full_shape = dem_dataset.shape
            center_row = full_shape[0] // 2
            center_col = full_shape[1] // 2
            window_size = int(4000 / dem_dataset.res[0])  # Number of pixels for 4km
            
            window = rasterio.windows.Window(
                center_col - window_size//2,
                center_row - window_size//2,
                window_size,
                window_size
            )
            
            # Store window bounds for minimap
            window_bounds = [
                center_col - window_size//2,
                center_col + window_size//2,
                center_row - window_size//2,
                center_row + window_size//2
            ]
            
            dem_data = dem_dataset.read(1, window=window)
            transform = dem_dataset.window_transform(window)
            
            # If manual length is specified, adjust the transform
            if manual_length_km is not None:
                original_length = full_shape[1] * dem_dataset.res[0]  # Current full DEM length in meters
                scale_factor = (manual_length_km * 1000) / original_length
                
                # Create new transform with adjusted scale
                new_transform = rasterio.Affine(
                    transform[0] * scale_factor,  # Scale X
                    transform[1],                 # Rotation (usually 0)
                    transform[2],                 # X Offset
                    transform[3],                 # Rotation (usually 0)
                    transform[4] * scale_factor,  # Scale Y
                    transform[5]                  # Y Offset
                )
                transform = new_transform
                print(f"\nManually setting full DEM length to {manual_length_km}km")
                print(f"Scale factor applied: {scale_factor}")
            
            print(f"\nTerrain Information:")
            print(f"Full DEM shape: {full_shape}")
            print(f"Full DEM size: {abs(full_shape[1] * dem_dataset.res[0] * scale_factor if manual_length_km else dem_dataset.res[0]):.1f}m x {abs(full_shape[0] * dem_dataset.res[0] * scale_factor if manual_length_km else dem_dataset.res[0]):.1f}m")
            print(f"Test section shape: {dem_data.shape}")
            print(f"Pixel resolution: {abs(transform[0])}m")
            print(f"Test section size: {abs(dem_data.shape[1] * transform[0]):.1f}m x {abs(dem_data.shape[0] * transform[4]):.1f}m")
        
        # Create and process mesh
        print("\nCreating mesh...")
        mesh = create_mesh_from_dem(dem_data, transform)
        mesh = classify_and_color_mesh(mesh)
        
        # Launch viewer with full DEM, window bounds, and DEM length
        launch_interactive_viewer(mesh, 
                                   full_dem=full_dem, 
                                   window_bounds=window_bounds,
                                   dem_length_km=manual_length_km)
        
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == '__main__':
    main() 