import numpy as np
import matplotlib.pyplot as plt
import os
from view_config import FOV_ANGLE, VIEW_DISTANCE_RATIO

def draw_agent_on_dem(dem_data, transform, observer_position, look_target, filename, dem_length_km):
    print(f"\nDrawing agent on DEM for {filename}")
    try:
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Plot the DEM with proper normalization
        dem_normalized = (dem_data - dem_data.min()) / (dem_data.max() - dem_data.min())
        extent = [
            transform[2], 
            transform[2] + transform[0] * dem_data.shape[1],
            transform[5] + transform[4] * dem_data.shape[0], 
            transform[5]
        ]
        ax.imshow(dem_normalized, cmap='gray', extent=extent)
        
        # Convert normalized coordinates back to real-world coordinates
        real_observer_x = transform[2] + (observer_position[0] / 1000.0) * transform[0] * dem_data.shape[1]
        real_observer_y = transform[5] + (1 - observer_position[1] / 1000.0) * transform[4] * dem_data.shape[0]
        
        real_target_x = transform[2] + (look_target[0] / 1000.0) * transform[0] * dem_data.shape[1]
        real_target_y = transform[5] + (1 - look_target[1] / 1000.0) * transform[4] * dem_data.shape[0]
        
        # Debug prints
        print(f"DEM length: {dem_length_km} km")
        print(f"Normalized observer position: ({observer_position[0]:.2f}, {observer_position[1]:.2f})")
        print(f"Real-world observer position: ({real_observer_x:.2f}, {real_observer_y:.2f})")
        
        # Plot the agent's position
        ax.scatter(real_observer_x, real_observer_y, 
                  color='red', s=100, marker='o', label='Agent')
        
        # Calculate and plot FOV
        direction = np.array([real_target_x - real_observer_x, 
                            real_target_y - real_observer_y])
        direction_norm = np.linalg.norm(direction)
        
        if direction_norm > 0:
            direction = direction / direction_norm
            fov_distance = dem_length_km * 1000 * VIEW_DISTANCE_RATIO
            
            # Calculate FOV lines using shared angle
            base_angle = np.arctan2(direction[1], direction[0])
            left_angle = base_angle + FOV_ANGLE/2  # Half the total FOV angle
            right_angle = base_angle - FOV_ANGLE/2
            
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
        ax.set_title(f'Agent Position and Field of View (DEM width: {dem_length_km} km)')
        
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