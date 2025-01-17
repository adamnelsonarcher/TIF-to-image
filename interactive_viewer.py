import open3d as o3d
import numpy as np
import rasterio
from dem_to_mesh import create_mesh_from_dem
from classify_terrain import classify_and_color_mesh

def launch_interactive_viewer(mesh, initial_position=None, initial_target=None):
    print("\n=== Launching Interactive Viewer ===")
    
    # Debug mesh info
    print("\nMesh Information:")
    print(f"Has vertices: {mesh.has_vertices()}")
    print(f"Number of vertices: {len(mesh.vertices)}")
    print(f"Has triangles: {mesh.has_triangles()}")
    print(f"Number of triangles: {len(mesh.triangles)}")
    print(f"Has colors: {mesh.has_vertex_colors()}")
    
    # Center the mesh around origin for better numerical stability
    print("\nCentering mesh around origin...")
    vertices = np.asarray(mesh.vertices)
    center_offset = np.mean(vertices, axis=0)
    vertices = vertices - center_offset
    mesh.vertices = o3d.utility.Vector3dVector(vertices)
    print(f"Original center: {center_offset}")
    print(f"New coordinate ranges:")
    print(f"X: {vertices[:, 0].min():.2f} to {vertices[:, 0].max():.2f}")
    print(f"Y: {vertices[:, 1].min():.2f} to {vertices[:, 1].max():.2f}")
    print(f"Z: {vertices[:, 2].min():.2f} to {vertices[:, 2].max():.2f}")
    
    # Create visualizer
    print("\nCreating visualizer...")
    vis = o3d.visualization.Visualizer()
    vis.create_window(window_name="Terrain Viewer", width=1024, height=768)
    print("Window created")
    
    # Add mesh to visualizer
    print("\nAdding mesh to visualizer...")
    success = vis.add_geometry(mesh)
    print(f"Add geometry success: {success}")
    
    # Create vertical reference lines
    z_range = vertices[:, 2].max() - vertices[:, 2].min()
    line_height = z_range * 2  # Make lines twice the terrain height for visibility
    z_min = vertices[:, 2].min() - z_range/2
    z_max = vertices[:, 2].max() + z_range/2
    
    # Create center vertical line (rover position)
    center_line = o3d.geometry.LineSet()
    center_line.points = o3d.utility.Vector3dVector([[0, 0, z_min], [0, 0, z_max]])
    center_line.lines = o3d.utility.Vector2iVector([[0, 1]])
    center_line.colors = o3d.utility.Vector3dVector([[1, 0, 0]])  # Red
    vis.add_geometry(center_line)
    print("Added center reference line")
    
    # Create 1km marker lines
    for x, y in [(1000, 0), (-1000, 0), (0, 1000), (0, -1000)]:  # 1km in each direction
        marker_line = o3d.geometry.LineSet()
        marker_line.points = o3d.utility.Vector3dVector([[x, y, z_min], [x, y, z_max]])
        marker_line.lines = o3d.utility.Vector2iVector([[0, 1]])
        marker_line.colors = o3d.utility.Vector3dVector([[1, 0, 0]])  # Red
        vis.add_geometry(marker_line)
        print(f"Added 1km marker line at ({x}, {y})")
    
    # Add reference markers (100m intervals)
    markers = []
    for dist in [100, 200, 300]:
        # Create a small sphere at each distance
        sphere = o3d.geometry.TriangleMesh.create_sphere(radius=2)  # 2m radius for visibility
        sphere.paint_uniform_color([1, 0, 0])  # Red color
        sphere.translate(np.array([dist, 0, 0]))  # Place along X-axis
        markers.append(sphere)
        vis.add_geometry(sphere)
        print(f"Added {dist}m distance marker")
    
    # Get view control
    print("\nGetting view control...")
    view_control = vis.get_view_control()
    
    # Get mesh bounds for better camera positioning
    print("\nCalculating mesh bounds...")
    bbox = mesh.get_axis_aligned_bounding_box()
    center = bbox.get_center()
    bbox_size = bbox.get_max_bound() - bbox.get_min_bound()
    print(f"Bounding box center: {center}")
    print(f"Bounding box size: {bbox_size} meters")
    
    # Find ground height at center position
    print("\nFinding ground height at center position...")
    center_x_idx = len(vertices) // 2
    ground_height = vertices[center_x_idx, 2]  # Z coordinate at center
    print(f"Ground height at center: {ground_height}")
    
    # Set initial position exactly 2m above ground at center
    initial_position = np.array([0, 0, ground_height + 2])  # 2m above ground
    initial_target = initial_position + np.array([100, 0, 0])  # Look 100m along X-axis
    print(f"Initial camera position: {initial_position}")
    print(f"Initial camera target: {initial_target}")
    print(f"Camera height above ground: 2m")
    
    # Set initial camera position
    print("\nSetting up camera parameters...")
    cam = view_control.convert_to_pinhole_camera_parameters()
    
    # Calculate look direction
    look_dir = initial_target - initial_position
    up_vector = np.array([0, 0, 1])
    
    print("\nCalculating view matrix...")
    # Create view matrix
    z_axis = -look_dir / np.linalg.norm(look_dir)
    x_axis = np.cross(up_vector, z_axis)
    x_axis = x_axis / np.linalg.norm(x_axis)
    y_axis = np.cross(z_axis, x_axis)
    
    # Create a new extrinsic matrix
    extrinsic = np.eye(4)
    extrinsic[:3, 0] = x_axis
    extrinsic[:3, 1] = y_axis
    extrinsic[:3, 2] = z_axis
    extrinsic[:3, 3] = initial_position
    
    # Create new camera parameters
    new_cam = o3d.camera.PinholeCameraParameters()
    new_cam.intrinsic = cam.intrinsic
    new_cam.extrinsic = extrinsic
    
    # Update the camera parameters
    view_control.convert_from_pinhole_camera_parameters(new_cam)
    
    # Lock camera translation and only allow rotation
    view_control.change_field_of_view(60)  # Set 60-degree FOV
    view_control.set_zoom(0.7)  # Adjust zoom level
    view_control.set_lookat(initial_position)  # Lock position
    view_control.camera_local_rotate(0, 0)  # Reset rotation
    
    # Set rendering options
    opt = vis.get_render_option()
    opt.background_color = np.asarray([0, 0, 0])
    opt.point_size = 1.0
    opt.show_coordinate_frame = True
    opt.mesh_show_back_face = True
    
    print("\nReference Points:")
    print("Red vertical line at center marks rover position")
    print("Red vertical lines at 1km mark cardinal directions")
    print("Red spheres mark 100m, 200m, and 300m distances along X-axis")
    print("Coordinate frame: Each grid unit = 1 meter")
    print("\nControls:")
    print("Left mouse: Look around (rotate view)")
    print("Mouse wheel: Adjust field of view")
    print("Press 'Q' to exit")
    
    vis.run()
    vis.destroy_window()

def main():
    try:
        # Load DEM data with subsample for testing
        dem_file = 'dem_data.tif'
        print(f"Loading DEM file: {dem_file}")
        with rasterio.open(dem_file) as dem_dataset:
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
            
            dem_data = dem_dataset.read(1, window=window)
            transform = dem_dataset.window_transform(window)
            
            print(f"Full DEM shape: {full_shape}")
            print(f"Test section shape: {dem_data.shape}")
            print(f"Pixel resolution: {dem_dataset.res[0]}m")
            print(f"Test section size: {dem_data.shape[0] * dem_dataset.res[0]}m x {dem_data.shape[1] * dem_dataset.res[0]}m")
        
        # Create and process mesh
        print("\nCreating mesh...")
        mesh = create_mesh_from_dem(dem_data, transform)
        mesh = classify_and_color_mesh(mesh)
        
        # Launch viewer
        launch_interactive_viewer(mesh)
        
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == '__main__':
    main() 