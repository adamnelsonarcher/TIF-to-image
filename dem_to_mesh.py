# dem_to_mesh.py

import numpy as np
import open3d as o3d
import rasterio

def create_mesh_from_dem(dem_data, transform, downsample_factor=2):
    print("\n=== DEM to Mesh Conversion ===")
    print(f"Input DEM shape: {dem_data.shape}")
    print(f"Downsample factor: {downsample_factor}")
    
    # Downsample the DEM data
    rows, cols = dem_data.shape
    downsampled_rows = rows // downsample_factor
    downsampled_cols = cols // downsample_factor
    
    # Create a downsampled grid
    row_indices = np.linspace(0, rows-1, downsampled_rows, dtype=int)
    col_indices = np.linspace(0, cols-1, downsampled_cols, dtype=int)
    dem_data = dem_data[row_indices][:, col_indices]
    
    rows, cols = dem_data.shape
    print(f"Downsampled DEM shape: {dem_data.shape}")
    
    # Create coordinate grids
    print("Creating coordinate grids...")
    x_coords, y_coords = np.meshgrid(np.arange(cols), np.arange(rows))
    x_coords, y_coords = rasterio.transform.xy(transform, x_coords * downsample_factor, 
                                             y_coords * downsample_factor)
    x_coords = np.array(x_coords)
    y_coords = np.array(y_coords)
    
    print("Normalizing coordinates...")
    # Scale coordinates to reasonable size
    x = x_coords.flatten()
    y = y_coords.flatten()
    z = dem_data.flatten()
    
    print(f"Coordinate ranges before normalization:")
    print(f"X: {np.min(x):.2f} to {np.max(x):.2f}")
    print(f"Y: {np.min(y):.2f} to {np.max(y):.2f}")
    print(f"Z: {np.min(z):.2f} to {np.max(z):.2f}")
    
    # Normalize coordinates to prevent numerical issues
    x = (x - np.min(x)) / (np.max(x) - np.min(x)) * 1000
    y = (y - np.min(y)) / (np.max(y) - np.min(y)) * 1000
    z = (z - np.min(z)) / (np.max(z) - np.min(z)) * 100
    
    print(f"Coordinate ranges after normalization:")
    print(f"X: {np.min(x):.2f} to {np.max(x):.2f}")
    print(f"Y: {np.min(y):.2f} to {np.max(y):.2f}")
    print(f"Z: {np.min(z):.2f} to {np.max(z):.2f}")
    
    print("Creating vertices...")
    vertices = np.column_stack((x, y, z))
    print(f"Number of vertices: {len(vertices)}")
    
    print("Creating faces...")
    faces = []
    for i in range(rows - 1):
        for j in range(cols - 1):
            idx = i * cols + j
            idx_right = idx + 1
            idx_down = idx + cols
            idx_down_right = idx + cols + 1
            
            faces.append([idx, idx_down, idx_down_right])
            faces.append([idx, idx_down_right, idx_right])
    
    faces = np.array(faces)
    print(f"Number of faces: {len(faces)}")
    
    print("Building mesh...")
    try:
        mesh = o3d.geometry.TriangleMesh()
        print("Created empty mesh")
        
        mesh.vertices = o3d.utility.Vector3dVector(vertices)
        print("Added vertices to mesh")
        
        # Verify triangle indices are valid
        max_vertex_idx = len(vertices) - 1
        valid_faces = []
        for face in faces:
            if all(idx <= max_vertex_idx for idx in face):
                valid_faces.append(face)
            else:
                print(f"Skipping invalid face with indices: {face}")
        
        valid_faces = np.array(valid_faces)
        print(f"Valid faces: {len(valid_faces)} out of {len(faces)}")
        print(f"Face array shape: {valid_faces.shape}")
        print(f"Face array dtype: {valid_faces.dtype}")
        
        # Convert to int32 (Open3D expects 32-bit integers)
        print("Converting faces to int32...")
        valid_faces = valid_faces.astype(np.int32)
        print(f"New dtype: {valid_faces.dtype}")
        
        # Verify data is contiguous
        if not valid_faces.flags['C_CONTIGUOUS']:
            print("Making array contiguous...")
            valid_faces = np.ascontiguousarray(valid_faces)
        
        print("Converting faces to Vector3iVector...")
        try:
            faces_vector = o3d.utility.Vector3iVector(valid_faces)
            print("Successfully converted faces")
        except Exception as e:
            print(f"Vector3iVector conversion failed: {str(e)}")
            print(f"Array info:")
            print(f"Shape: {valid_faces.shape}")
            print(f"Min: {valid_faces.min()}")
            print(f"Max: {valid_faces.max()}")
            raise
        
        print("Assigning faces to mesh...")
        mesh.triangles = faces_vector
        print("Added faces to mesh")
        
        # Verify mesh integrity
        if not mesh.has_triangles():
            raise ValueError("Failed to add triangles to mesh")
            
        print("Computing normals...")
        mesh.compute_vertex_normals()
        print("Computed normals")
        
        # Remove degenerate triangles
        mesh.remove_degenerate_triangles()
        print("Removed degenerate triangles")
        
        # Remove duplicated vertices
        mesh.remove_duplicated_vertices()
        print("Removed duplicated vertices")
        
        # Remove unreferenced vertices
        mesh.remove_unreferenced_vertices()
        print("Removed unreferenced vertices")
        
        # Final validation
        print("\nFinal mesh statistics:")
        print(f"Vertices: {len(mesh.vertices)}")
        print(f"Triangles: {len(mesh.triangles)}")
        print(f"Has vertex normals: {mesh.has_vertex_normals()}")
        
    except Exception as e:
        print(f"Error during mesh creation: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
    
    print("Mesh creation completed successfully")
    return mesh
