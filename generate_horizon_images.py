# generate_horizon_images.py

import numpy as np
import rasterio
from dem_to_mesh import create_mesh_from_dem
from classify_terrain import classify_and_color_mesh
from render_scene import render_scene
import open3d as o3d
import matplotlib.pyplot as plt
import os

def generate_horizon_views(mesh, dem_data, transform, num_views=8):
    print("\n=== Generating Horizon Views ===")
    
    # Get mesh bounds
    bbox = mesh.get_axis_aligned_bounding_box()
    center = bbox.get_center()
    bbox_size = bbox.get_max_bound() - bbox.get_min_bound()
    
    # Calculate observer parameters based on real-world meters
    observer_radius = 10.0  # 5 meter radius for observer to rotate and move
    look_distance = 80.0  # Look 80m into the distance
    
    print(f"Observer setup:")
    print(f"Observer radius: {observer_radius:.2f}")
    print(f"Look distance: {look_distance:.2f}")
    
    images = []
    positions = []  # Store observer positions
    targets = []    # Store look targets
    
    for i in range(num_views):
        angle = (2 * np.pi * i) / num_views

        x_offset = -3500
        y_offset = 1000
        
        x_pos = center[0] + x_offset + observer_radius * np.cos(angle)
        y_pos = center[1] + y_offset + observer_radius * np.sin(angle)

        # Now determine ground elevation at (x_pos, y_pos)
        col, row = rasterio.transform.rowcol(transform, x_pos, y_pos)
        ground_elevation = dem_data[row, col]

        observer_position = np.array([x_pos, y_pos, ground_elevation + 20])

        
        # Look target
        look_target = np.array([
            center[0]+ x_offset + look_distance * np.cos(angle),
            center[1] + y_offset + look_distance * np.sin(angle),
            ground_elevation - 2.0 # Adjust look height to be consistent
        ])
        
        print(f"\nProcessing view {i+1}/{num_views}")
        print(f"Observer position: {observer_position}")
        print(f"Looking towards: {look_target}")
        
        try:
            image = render_scene(mesh, observer_position, look_target)
            print(f"Successfully rendered view {i+1}")
            images.append(image)
            positions.append(observer_position)
            targets.append(look_target)
        except Exception as e:
            print(f"Failed to render view {i+1}: {str(e)}")
            raise
    
    return images, positions, targets

def save_image(image, filename):
    print(f"\nSaving image to {filename}")
    try:
        import imageio
        
        # Construct full path
        filepath = os.path.join('horizon_views', filename)
        imageio.imwrite(filepath, image)
        print(f"Saved {filepath}")
        return True
    except Exception as e:
        print(f"Error saving image: {str(e)}")
        return False

def draw_agent_on_dem(dem_data, transform, observer_position, look_target, filename):
    print(f"\nDrawing agent on DEM for {filename}")
    try:
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Plot the DEM without normalization
        extent = [
            transform[2], 
            transform[2] + transform[0] * dem_data.shape[1],
            transform[5] + transform[4] * dem_data.shape[0], 
            transform[5]
        ]
        ax.imshow(dem_data, cmap='gray', extent=extent)
        
        # Convert normalized coordinates back to real-world coordinates
        real_observer_x = observer_position[0]
        real_observer_y = observer_position[1]
        
        real_target_x = look_target[0]
        real_target_y = look_target[1]
        
        # Debug prints
        print(f"Coordinate observer position: ({real_observer_x:.2f}, {real_observer_y:.2f})")
        
        # Plot the agent's position
        ax.scatter(real_observer_x, real_observer_y, 
                  color='red', s=100, marker='o', label='Agent')
        
        # Calculate and plot FOV
        direction = np.array([real_target_x - real_observer_x, 
                            real_target_y - real_observer_y])
        direction_norm = np.linalg.norm(direction)
        
        if direction_norm > 0:
            direction = direction / direction_norm
            fov_distance = (extent[1] - extent[0]) * 0.2  # 20% of DEM width
            fov_angle = np.pi / 6  # 30 degrees
            
            # Calculate FOV lines
            base_angle = np.arctan2(direction[1], direction[0])
            left_angle = base_angle + fov_angle
            right_angle = base_angle - fov_angle
            
            # Plot FOV lines
            for angle in [left_angle, right_angle]:
                end_point = np.array([
                    real_observer_x + fov_distance * np.cos(angle),
                    real_observer_y + fov_distance * np.sin(angle)
                ])
                ax.plot([real_observer_x, end_point[0]],
                       [real_observer_y, end_point[1]],
                       'r--', linewidth=2)
            
            # Plot center line of view
            center_end = np.array([
                real_observer_x + fov_distance * direction[0],
                real_observer_y + fov_distance * direction[1]
            ])
            ax.plot([real_observer_x, center_end[0]],
                   [real_observer_y, center_end[1]],
                   'r-', linewidth=1)
        
        # Add legend and title
        ax.legend()
        ax.set_title('Agent Position and Field of View')
        
        # Ensure proper axis limits
        ax.set_xlim(extent[0], extent[1])
        ax.set_ylim(extent[2], extent[3])
        
        # Save the image
        filepath = os.path.join('views_with_agents', filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close(fig)
        print(f"Saved {filepath}")
        
    except Exception as e:
        print(f"Error drawing agent on DEM: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    try:
        # Create output directories
        output_dir = 'horizon_views'
        views_with_agents_dir = 'views_with_agents'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        if not os.path.exists(views_with_agents_dir):
            os.makedirs(views_with_agents_dir)
        
        # Load DEM data
        dem_file = 'dem_data.tif'
        print(f"Attempting to load DEM file: {dem_file}")
        with rasterio.open(dem_file) as dem_dataset:
            dem_data = dem_dataset.read(1)
            transform = dem_dataset.transform
            print(f"DEM data shape: {dem_data.shape}")
            print(f"DEM elevation range: {dem_data.min():.2f} to {dem_data.max():.2f}")

        # Create and process mesh
        print("\nCreating mesh...")
        mesh = create_mesh_from_dem(dem_data, transform)
        
        if mesh.is_empty():
            raise ValueError("Created mesh is empty")
            
        print("\nClassifying mesh...")
        mesh = classify_and_color_mesh(mesh)
        
        if not mesh.has_vertex_colors():
            raise ValueError("Mesh classification did not add colors")
            
        # Generate views
        print("\nGenerating views...")
        images, positions, targets = generate_horizon_views(mesh, dem_data, transform)
        
        if not images:
            raise ValueError("No images were generated")
            
        # Save images and create agent views
        print("\nSaving images...")
        for i, (image, pos, target) in enumerate(zip(images, positions, targets)):
            # Save horizon view
            output_file = f'horizon_view_{i+1}.png'
            save_image(image, output_file)
            
            # Create agent view
            agent_file = f'agent_view_{i+1}.png'
            draw_agent_on_dem(dem_data, transform, pos, target, agent_file)

    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == '__main__':
    main()
