import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import matplotlib.pyplot as plt
from dem_to_mesh import create_mesh_from_dem
from classify_terrain import classify_and_color_mesh
from dem_terrain import create_terrain_from_dem
from simple_camera_viewer import SimpleCameraViewer
from panda3d.core import BitMask32, Point3
import rasterio

def launch_interactive_viewer(mesh, full_dem=None, window_bounds=None):
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
    
    # Create the terrain node from the mesh
    terrain_node, terrain_info = create_terrain_from_dem(mesh)
    
    # Create and launch the viewer with no default terrain
    app = SimpleCameraViewer(create_default_terrain=False)
    
    # Add our DEM terrain
    app.terrain = app.render.attachNewNode(terrain_node)
    app.terrain.setCollideMask(BitMask32.bit(1))
    app.terrain.setColor(0.4, 0.4, 0.4, 1)  # Gray color
    
    # Add wireframe overlay for better visibility
    wireframe = app.terrain.copyTo(app.render)
    wireframe.setRenderModeWireframe()
    wireframe.setColor(0.2, 0.8, 0.2, 0.3)  # Green, semi-transparent
    wireframe.setTransparency(True)
    wireframe.setZ(0.01)
    
    # Create reference lines AFTER terrain is attached
    app.create_reference_lines()
    
    # Set initial camera position at a good starting point
    app.set_initial_position(0, 0)
    
    # Run the viewer
    app.run()

def main():
    try:
        # Load DEM data with subsample for testing
        dem_file = 'dem_data.tif'
        
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
            
            print(f"\nTerrain Information:")
            print(f"Test section shape: {dem_data.shape}")
            print(f"Pixel resolution: {abs(transform[0])}m")
            print(f"Test section size: {abs(dem_data.shape[1] * transform[0]):.1f}m x {abs(dem_data.shape[0] * transform[4]):.1f}m")
        
        # Create and process mesh
        print("\nCreating mesh...")
        mesh = create_mesh_from_dem(dem_data, transform)
        mesh = classify_and_color_mesh(mesh)
        
        # Launch viewer
        launch_interactive_viewer(mesh, full_dem=full_dem, window_bounds=window_bounds)
        
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == '__main__':
    main() 