import pyvista as pv
import numpy as np
import rasterio
from dem_to_mesh import create_mesh_from_dem
from classify_terrain import classify_and_color_mesh

def launch_interactive_viewer(mesh, initial_position=None, initial_target=None, full_dem=None, window_bounds=None, dem_length_km=None):
    print("\n=== Launching Interactive Viewer ===")
    
    # Create a second window for the minimap using matplotlib
    if full_dem is not None and window_bounds is not None:
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle, Circle
        
        plt.figure(figsize=(8, 8))
        plt.imshow(full_dem, cmap='gray')
        
        # Draw rectangle around current view window
        x_min, x_max, y_min, y_max = window_bounds
        window_size = x_max - x_min  # Calculate window size from bounds
        rect = Rectangle((x_min, y_min), 
                        window_size, 
                        window_size,
                        fill=False, 
                        color='red', 
                        linewidth=2,
                        label='Current View (4km x 4km)')
        plt.gca().add_patch(rect)
        
        # Add observer position (center of view window)
        observer_x = (x_min + x_max) / 2
        observer_y = (y_min + y_max) / 2
        observer = Circle((observer_x, observer_y), 
                         radius=window_size/50,  # Adjust size for visibility
                         color='blue',
                         fill=True,
                         label='Observer Position')
        plt.gca().add_patch(observer)
        
        # Add 1km marker points
        marker_size = window_size/50
        km_markers = []
        for dx, dy in [(window_size/4, 0), (-window_size/4, 0), (0, window_size/4), (0, -window_size/4)]:
            marker = Circle((observer_x + dx, observer_y + dy),
                          radius=marker_size,
                          color='red',
                          fill=True)
            plt.gca().add_patch(marker)
            km_markers.append(marker)
        
        plt.title('DEM Overview\nRed box shows current view (4km x 4km)\nBlue dot is observer position\nRed dots mark 1km distances', 
                 pad=20)
        
        # Add scale bar at bottom
        if dem_length_km is not None:
            plt.text(full_dem.shape[1]/2, full_dem.shape[0] * 1.1,
                    f'Total DEM width: {dem_length_km:.1f}km',
                    ha='center', va='bottom', color='black')
        
        plt.legend()
        plt.axis('off')  # Turn off all axes and grid
        plt.show(block=False)
    
    # Convert Open3D mesh to PyVista
    vertices = np.asarray(mesh.vertices)
    triangles = np.asarray(mesh.triangles)
    colors = np.asarray(mesh.vertex_colors)
    
    # Center the vertices around origin and invert Z axis
    center_offset = np.mean(vertices, axis=0)
    vertices = vertices - center_offset
    vertices[:, 2] = -vertices[:, 2]  # Invert Z coordinates of the mesh
    
    print("\nMesh Statistics:")
    print(f"Original center: {center_offset}")
    print(f"Number of vertices: {len(vertices)}")
    print(f"Number of triangles: {len(triangles)}")
    print(f"Vertex range X: {vertices[:, 0].min():.2f} to {vertices[:, 0].max():.2f}")
    print(f"Vertex range Y: {vertices[:, 1].min():.2f} to {vertices[:, 1].max():.2f}")
    print(f"Vertex range Z: {vertices[:, 2].min():.2f} to {vertices[:, 2].max():.2f}")
    print(f"Has colors: {colors is not None}")
    if colors is not None:
        print(f"Color range: {colors.min():.2f} to {colors.max():.2f}")
    
    # Create PyVista mesh with inverted vertices
    faces = np.column_stack((np.full(len(triangles), 3), triangles))
    pv_mesh = pv.PolyData(vertices, faces)
    
    # Create plotter with specific parameters
    plotter = pv.Plotter()
    plotter.set_background('black')
    
    # Add mesh with simpler parameters first
    plotter.add_mesh(pv_mesh, 
                    color='gray',
                    show_edges=True,
                    lighting=True,
                    opacity=1.0)
    
    # Function to get height at any (x,y) coordinate by casting a ray down
    def get_ground_height(x, y):
        start_point = np.array([x, y, 2000])  # Start high above terrain
        end_point = np.array([x, y, -2000])   # End below terrain
        intersection = pv_mesh.ray_trace(start_point, end_point)
        
        if len(intersection) > 0:
            # intersection[0] is the points array, and we want the first point's Z coordinate
            height = intersection[0][0][2]  # Get Z coordinate from the first intersection point
            print(f"Finding height at ({x}, {y}): intersection at z = {height}")
            return height
        else:
            print(f"Warning: No intersection found at ({x}, {y})")
            return 0
    
    # Place observer at center
    center_height = get_ground_height(0, 0)
    eye_height = 1.7  # meters
    observer_position = (0, -100, center_height + eye_height)
    
    # Add 100m reference markers
    for x, y in [(100, 0), (-100, 0), (0, 100), (0, -100)]:
        height = get_ground_height(x, y)
        # Create a small sphere at the intersection point
        sphere = pv.Sphere(radius=1, center=np.array([x, y, height]))  # Use numpy array for center
        plotter.add_mesh(sphere, color='green')
        # Then add the marker line
        marker = pv.Line((x, y, height), (x, y, height + 1))
        plotter.add_mesh(marker, color='blue', line_width=2)
        print(f"100m marker at ({x}, {y}): ground height = {height}")
    
    # Add 1km reference markers
    for x, y in [(1000, 0), (-1000, 0), (0, 1000), (0, -1000)]:
        height = get_ground_height(x, y)
        # Create a small sphere at the intersection point
        sphere = pv.Sphere(radius=10, center=(x, y, height))
        plotter.add_mesh(sphere, color='green')
        # Then add the marker line
        marker = pv.Line((x, y, height), (x, y, height + 100))
        plotter.add_mesh(marker, color='red', line_width=2)
        print(f"1km marker at ({x}, {y}): ground height = {height}")
    
    # Add a reference plane at observer height that covers the entire terrain
    x_range = vertices[:, 0].max() - vertices[:, 0].min()
    y_range = vertices[:, 1].max() - vertices[:, 1].min()
    plane = pv.Plane(center=(0, 0, center_height + eye_height), 
                    direction=(0, 0, 1),  # Normal pointing up
                    i_size=x_range,  # Match terrain width
                    j_size=y_range)  # Match terrain length
    plotter.add_mesh(plane, color='yellow', opacity=0.3)
    
    # Set up camera
    camera = plotter.camera
    camera.position = observer_position
    camera.focal_point = (0, 0, center_height + eye_height)
    camera.up = (0, 0, 1)  # Z is up
    
    # Use trackball style for first-person view
    plotter.enable_trackball_style()  # Changed from terrain_style to trackball_style
    
    def on_key_press():
        plotter.close()
    
    plotter.add_key_event('q', on_key_press)
    
    print("\nControls:")
    print("Left mouse: Look around")
    print("Right mouse: Pan")
    print("Mouse wheel: Move forward/backward")
    print("Press 'Q' to exit")
    
    plotter.show()

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