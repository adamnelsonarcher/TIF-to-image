import pyvista as pv
import numpy as np
import rasterio
from dem_to_mesh import create_mesh_from_dem
from classify_terrain import classify_and_color_mesh

def launch_interactive_viewer(mesh, initial_position=None, initial_target=None, full_dem=None, window_bounds=None):
    print("\n=== Launching Interactive Viewer ===")
    
    # Convert Open3D mesh to PyVista
    vertices = np.asarray(mesh.vertices)
    triangles = np.asarray(mesh.triangles)
    colors = np.asarray(mesh.vertex_colors)
    
    # Center the vertices around origin and flip Z axis
    center_offset = np.mean(vertices, axis=0)
    vertices = vertices - center_offset
    vertices[:, 2] = -vertices[:, 2]  # Flip Z coordinates
    
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
    
    # Create PyVista mesh with centered vertices
    faces = np.column_stack((np.full(len(triangles), 3), triangles))
    pv_mesh = pv.PolyData(vertices, faces)
    
    # Create plotter with specific parameters and subplot
    plotter = pv.Plotter()
    plotter.set_background('black')
    
    # Main view (larger)
    plotter.add_mesh(pv_mesh, 
                    color='gray',
                    show_edges=True,
                    lighting=True,
                    opacity=1.0)
    
    # Find ground height at center before adding markers
    center_point = np.array([0, 0, 0])
    closest_point_id = pv_mesh.find_closest_point(center_point)
    ground_height = vertices[closest_point_id][2]
    print(f"\nGround height at center: {ground_height}")
    
    # Add reference markers to main view
    z_min = vertices[:, 2].min() - 100
    z_max = vertices[:, 2].max() + 100
    
    center_line = pv.Line((0, 0, z_min), (0, 0, z_max))
    plotter.add_mesh(center_line, color='blue', line_width=2)
    
    for x, y in [(1000, 0), (-1000, 0), (0, 1000), (0, -1000)]:
        marker = pv.Line((x, y, z_min), (x, y, z_max))
        plotter.add_mesh(marker, color='red', line_width=2)
    
    # Set up main camera
    camera = plotter.camera
    camera.position = (0, -100, ground_height + 2)
    camera.focal_point = (0, 0, ground_height + 2)
    camera.up = (0, 0, 1)
    
    # Enable terrain interaction style
    plotter.enable_terrain_style()
    
    def on_key_press():
        plotter.close()
    
    plotter.add_key_event('q', on_key_press)
    
    print("\nControls:")
    print("Left mouse: Look around")
    print("Right mouse: Pan")
    print("Mouse wheel: Zoom")
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
        
        # Launch viewer with full DEM and window bounds
        launch_interactive_viewer(mesh, full_dem=full_dem, window_bounds=window_bounds)
        
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == '__main__':
    main() 