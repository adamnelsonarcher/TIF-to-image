# render_scene.py

import numpy as np
import pyrender
import trimesh

def render_scene(mesh, rover_position, camera_target, dem_length_km, image_width=1024, image_height=768):
    print("\n=== Setting up Pyrender Scene ===")
    
    try:
        # Convert Open3D mesh to trimesh
        vertices = np.asarray(mesh.vertices)
        faces = np.asarray(mesh.triangles)
        colors = np.asarray(mesh.vertex_colors)
        
        # Create trimesh mesh
        tri_mesh = trimesh.Trimesh(vertices=vertices, 
                                 faces=faces, 
                                 vertex_colors=colors)
        
        # Create pyrender mesh
        mesh = pyrender.Mesh.from_trimesh(tri_mesh)
        
        # Create scene
        scene = pyrender.Scene(bg_color=[0, 0, 0])
        scene.add(mesh)
        
        # Calculate camera parameters
        yfov = np.pi / 3.0  # Field of view
        aspect_ratio = float(image_width) / float(image_height)
        znear = 0.1  # Near clipping plane
        zfar = dem_length_km * 1000  # Far clipping plane based on DEM size
        
        camera = pyrender.PerspectiveCamera(yfov=yfov, aspectRatio=aspect_ratio, znear=znear, zfar=zfar)
        
        # Set up camera pose
        look_dir = camera_target - rover_position
        up_vector = np.array([0, 0, 1])
        
        z_axis = -look_dir / np.linalg.norm(look_dir)
        x_axis = np.cross(up_vector, z_axis)
        x_axis = x_axis / np.linalg.norm(x_axis)
        y_axis = np.cross(z_axis, x_axis)
        
        pose = np.eye(4)
        pose[:3, 0] = x_axis
        pose[:3, 1] = y_axis
        pose[:3, 2] = z_axis
        pose[:3, 3] = rover_position
        
        scene.add(camera, pose=pose)
        
        # Add stronger directional light
        light = pyrender.DirectionalLight(
            color=[1.0, 1.0, 1.0],
            intensity=5.0  # Increased intensity for brighter illumination
        )
        scene.add(light, pose=pose)
        
        # Create renderer
        r = pyrender.OffscreenRenderer(image_width, image_height)
        
        # Render scene
        color, depth = r.render(scene)
        
        r.delete()
        
        return color

    except Exception as e:
        print(f"Error during rendering: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
