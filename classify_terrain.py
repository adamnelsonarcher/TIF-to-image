# classify_terrain.py

import numpy as np
import open3d as o3d

def classify_and_color_mesh(mesh):
    print("\n=== Terrain Classification ===")
    vertices = np.asarray(mesh.vertices)
    print(f"Number of vertices to classify: {len(vertices)}")

    # Simple classification based on elevation
    z_coords = vertices[:, 2]
    min_z = z_coords.min()
    max_z = z_coords.max()
    elevation_range = max_z - min_z
    
    print(f"Elevation range: {min_z:.2f} to {max_z:.2f}")

    # Define thresholds
    ground_threshold = min_z + 0.3 * elevation_range
    hill_threshold = min_z + 0.6 * elevation_range
    
    print(f"Classification thresholds:")
    print(f"Ground: < {ground_threshold:.2f}")
    print(f"Hills: {ground_threshold:.2f} to {hill_threshold:.2f}")
    print(f"Rocks: > {hill_threshold:.2f}")

    labels = np.zeros(len(z_coords), dtype=int)
    labels[z_coords < ground_threshold] = 1  # Ground
    labels[(z_coords >= ground_threshold) & (z_coords < hill_threshold)] = 2  # Hills
    labels[z_coords >= hill_threshold] = 3  # Rocks
    
    print("\nTerrain distribution:")
    print(f"Ground pixels: {np.sum(labels == 1)}")
    print(f"Hill pixels: {np.sum(labels == 2)}")
    print(f"Rock pixels: {np.sum(labels == 3)}")

    # Assign colors based on labels
    colors = np.zeros((len(z_coords), 3))
    colors[labels == 1] = [0.95, 0.95, 0.95]  # Ground - Almost white
    colors[labels == 2] = [0.75, 0.75, 0.75]  # Hills - Light gray
    colors[labels == 3] = [0.55, 0.55, 0.55]  # Rocks - Medium gray
    
    print("Assigning colors to mesh...")
    mesh.vertex_colors = o3d.utility.Vector3dVector(colors)
    print("Terrain classification completed successfully")
    return mesh
