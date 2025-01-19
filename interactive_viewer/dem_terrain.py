from panda3d.core import GeomVertexFormat, GeomVertexData, GeomVertexWriter
from panda3d.core import Geom, GeomTriangles, GeomNode
import numpy as np

def create_terrain_from_dem(mesh):
    """
    Convert a DEM mesh into a Panda3D terrain node.
    
    Args:
        mesh: The DEM mesh object with vertices, normals, colors, and triangles
        
    Returns:
        tuple: (GeomNode, dict) - The Panda3D node and terrain info dictionary
    """
    # Create vertex data format (position, normal, color)
    format = GeomVertexFormat.getV3n3c4()
    vdata = GeomVertexData('terrain', format, Geom.UHStatic)
    
    # Create writers for vertex attributes
    vertex = GeomVertexWriter(vdata, 'vertex')
    normal = GeomVertexWriter(vdata, 'normal')
    color = GeomVertexWriter(vdata, 'color')
    
    # Convert mesh data to numpy arrays
    vertices = np.asarray(mesh.vertices)
    normals = np.asarray(mesh.vertex_normals)
    colors = np.asarray(mesh.vertex_colors)
    
    # Calculate center and normalize coordinates
    center = np.mean(vertices, axis=0)
    normalized_vertices = vertices - center
    
    # Store terrain information
    terrain_info = {
        'center': center,
        'original_bounds': {
            'min': np.min(vertices, axis=0),
            'max': np.max(vertices, axis=0)
        },
        'normalized_bounds': {
            'min': np.min(normalized_vertices, axis=0),
            'max': np.max(normalized_vertices, axis=0)
        }
    }
    
    # Print debug info
    print("\nTerrain Statistics:")
    print(f"Original bounds: {terrain_info['original_bounds']['min']} to {terrain_info['original_bounds']['max']}")
    print(f"Normalized bounds: {terrain_info['normalized_bounds']['min']} to {terrain_info['normalized_bounds']['max']}")
    print(f"Center point: {center}")
    
    # Add vertices to the geometry
    for v, n, c in zip(normalized_vertices, normals, colors):
        vertex.addData3(v[0], v[1], v[2])
        normal.addData3(n[0], n[1], n[2])
        color.addData4(c[0], c[1], c[2], 1.0)
    
    # Create triangles
    tris = GeomTriangles(Geom.UHStatic)
    triangles = np.asarray(mesh.triangles)
    for face in triangles:
        tris.addVertices(int(face[0]), int(face[1]), int(face[2]))
    
    # Create the geometry
    geom = Geom(vdata)
    geom.addPrimitive(tris)
    
    # Create and return the node
    node = GeomNode('terrain')
    node.addGeom(geom)
    
    return node, terrain_info 