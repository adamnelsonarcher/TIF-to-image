from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from panda3d.core import Point3, Vec3, DirectionalLight, AmbientLight
from panda3d.core import GeomVertexFormat, GeomVertexData, GeomVertexWriter
from panda3d.core import Geom, GeomLines, GeomNode, GeomTriangles
from panda3d.core import TextNode, CollisionTraverser, CollisionNode
from panda3d.core import CollisionRay, CollisionHandlerQueue, BitMask32
from panda3d.core import RenderModeAttrib
from direct.gui.OnscreenText import OnscreenText
import math
import numpy as np
from simple_camera_viewer import SimpleCameraViewer

class TerrainViewer(SimpleCameraViewer):
    def __init__(self, mesh):
        # Override create_terrain before parent initialization
        self.mesh = mesh  # Store mesh for later use
        SimpleCameraViewer.__init__(self)
        
        # Set initial camera position
        self.camera.setPos(0, 0, 1.7)  # Start at origin with eye height
        self.camera.setHpr(0, 0, 0)    # Looking forward
        
    def create_terrain(self):
        # Override parent's terrain creation with our mesh
        terrain_node = self.create_terrain_node(self.mesh)
        self.terrain = self.render.attachNewNode(terrain_node)
        self.terrain.setCollideMask(BitMask32.bit(1))
        
        # Create wireframe overlay
        wireframe = self.terrain.copyTo(self.render)
        wireframe.setRenderModeWireframe()
        wireframe.setColor(1, 1, 1, 0.3)  # White, semi-transparent
        wireframe.setTransparency(True)
        wireframe.setZ(0.01)  # Slight offset to prevent z-fighting
        
    def create_terrain_node(self, mesh):
        # Create vertex data
        format = GeomVertexFormat.getV3n3c4()
        vdata = GeomVertexData('terrain', format, Geom.UHStatic)
        vertex = GeomVertexWriter(vdata, 'vertex')
        normal = GeomVertexWriter(vdata, 'normal')
        color = GeomVertexWriter(vdata, 'color')
        
        # Convert vertices to numpy array and normalize coordinates
        vertices = np.asarray(mesh.vertices)
        normals = np.asarray(mesh.vertex_normals)
        colors = np.asarray(mesh.vertex_colors)
        
        # Calculate center and normalize
        center = np.mean(vertices, axis=0)
        vertices = vertices - center  # Center around origin
        
        # Debug info
        print("\nTerrain Statistics:")
        print(f"Original bounds: {np.min(vertices, axis=0)} to {np.max(vertices, axis=0)}")
        print(f"Center point: {center}")
        
        # Add vertices
        for v, n, c in zip(vertices, normals, colors):
            vertex.addData3(v[0], v[1], v[2])
            normal.addData3(n[0], n[1], n[2])
            color.addData4(c[0], c[1], c[2], 1.0)
        
        # Create triangles
        tris = GeomTriangles(Geom.UHStatic)
        triangles = np.asarray(mesh.triangles)
        for face in triangles:
            tris.addVertices(int(face[0]), int(face[1]), int(face[2]))
        
        # Create geometry
        geom = Geom(vdata)
        geom.addPrimitive(tris)
        
        # Create node
        node = GeomNode('terrain')
        node.addGeom(geom)
        
        return node

def launch_terrain_viewer(mesh):
    app = TerrainViewer(mesh)
    app.run()