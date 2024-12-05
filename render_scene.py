# render_scene.py

import numpy as np
import pyrender
import trimesh

def render_scene(mesh, rover_position, camera_target, image_width=1024, image_height=768):
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
        
        # Create scene with ambient light
        scene = pyrender.Scene(bg_color=[0, 0, 0], ambient_light=[0.2, 0.2, 0.2])
        scene.add(mesh)
        
        # Calculate camera parameters
        camera = pyrender.PerspectiveCamera(
            yfov=np.pi/3.0,  # Wider FOV (60 degrees)
            aspectRatio=float(image_width)/float(image_height),
            znear=1.0,  # Adjusted for real-world scale
            zfar=10000.0  # Increased for real-world distances
        )
        
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
        
        # Add multiple lights for better illumination
        # Main directional light (sun)
        direct_l = pyrender.DirectionalLight(color=[1.0, 1.0, 1.0], intensity=10.0)
        scene.add(direct_l, pose=pose)
        
        # Additional directional light from above
        light_pose = np.eye(4)
        light_pose[:3, 3] = rover_position + np.array([0, 0, 1000])  # Light from above
        scene.add(direct_l, pose=light_pose)
        
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
