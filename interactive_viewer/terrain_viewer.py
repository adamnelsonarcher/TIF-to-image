from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from panda3d.core import Point3, Vec3, DirectionalLight, AmbientLight
from panda3d.core import GeomVertexFormat, GeomVertexData, GeomVertexWriter
from panda3d.core import Geom, GeomTriangles, GeomNode, GeomLines
from panda3d.core import RenderModeAttrib, TransparencyAttrib, NodePath
from panda3d.core import CollisionTraverser, CollisionNode, CollisionRay
from panda3d.core import CollisionHandlerQueue, BitMask32
import numpy as np
import math
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import TextNode

class TerrainViewer(ShowBase):
    def __init__(self, mesh):
        ShowBase.__init__(self)
        
        # Set up collision detection
        self.cTrav = CollisionTraverser()
        self.groundRay = CollisionRay()
        self.groundCol = CollisionNode('groundRay')
        self.groundCol.addSolid(self.groundRay)
        self.groundCol.setFromCollideMask(BitMask32.bit(1))
        self.groundCol.setIntoCollideMask(BitMask32.allOff())
        self.groundColNp = self.camera.attachNewNode(self.groundCol)
        self.groundHandler = CollisionHandlerQueue()
        self.cTrav.addCollider(self.groundColNp, self.groundHandler)
        
        # Set up basic scene
        self.setBackgroundColor(0, 0, 0)  # Black background
        
        # Create lighting
        dlight = DirectionalLight('dlight')
        dlight.setColor((0.8, 0.8, 0.8, 1))
        dlnp = self.render.attachNewNode(dlight)
        dlnp.setHpr(45, -45, 0)
        self.render.setLight(dlnp)
        
        # Add ambient light
        alight = AmbientLight('alight')
        alight.setColor((0.2, 0.2, 0.2, 1))
        alnp = self.render.attachNewNode(alight)
        self.render.setLight(alnp)
        
        # Add on-screen coordinate display
        self.coord_display = OnscreenText(
            text="",
            style=1,
            fg=(1, 1, 1, 1),
            pos=(-1.3, 0.95),
            align=TextNode.ALeft,
            scale=.05
        )
        
        # Convert mesh to Panda3D format with coordinate normalization
        self.terrain_node = self.create_terrain_node(mesh)
        self.terrain = self.render.attachNewNode(self.terrain_node)
        self.terrain.setCollideMask(BitMask32.bit(1))
        
        # Find and color the center line red
        center_line = self.terrain.find('**/+GeomNode')
        if not center_line.isEmpty():
            center_line.setColor(1, 0, 0, 1)  # Red color
            center_line.setBin('fixed', 0)     # Render on top
            center_line.setDepthTest(False)    # Don't check depth buffer
            center_line.setDepthWrite(False)   # Don't write to depth buffer
        
        # Make ground plane semi-transparent
        ground_state = self.terrain.getState()
        ground_state = ground_state.addAttrib(TransparencyAttrib.make(TransparencyAttrib.MAlpha))
        self.terrain.setColor(1, 1, 1, 0.5)  # 20% opacity
        self.terrain.setTransparency(TransparencyAttrib.MAlpha)
        
        # Set up first-person camera
        eye_height = 1.7  # More realistic eye height
        self.desired_height = eye_height
        
        # Initialize camera angles
        self.camH = 180  # Start facing -Z (north)
        self.camP = 0    # Level view
        
        # Position camera properly
        self.camera.setPos(0, 0, self.desired_height)  # Camera at eye height
        start_pos = Point3(0, 0, 0)  # Start at origin
        self.camera.setH(self.camH)
        self.camera.setP(self.camP)
        
        # Debug initial position
        print("\n=== Initial Camera Setup ===")
        print(f"Start position: {start_pos}")
        print(f"Initial heading: {self.camH}")
        print(f"Initial pitch: {self.camP}")
        
        # Set up movement controls
        self.keyMap = {
            "forward": False,
            "backward": False,
            "left": False,
            "right": False,
            "up": False,
            "down": False
        }
        
        # Add key bindings
        self.accept("w", self.updateKeyMap, ["forward", True])
        self.accept("w-up", self.updateKeyMap, ["forward", False])
        self.accept("s", self.updateKeyMap, ["backward", True])
        self.accept("s-up", self.updateKeyMap, ["backward", False])
        self.accept("a", self.updateKeyMap, ["left", True])
        self.accept("a-up", self.updateKeyMap, ["left", False])
        self.accept("d", self.updateKeyMap, ["right", True])
        self.accept("d-up", self.updateKeyMap, ["right", False])
        self.accept("space", self.updateKeyMap, ["up", True])
        self.accept("space-up", self.updateKeyMap, ["up", False])
        self.accept("shift", self.updateKeyMap, ["down", True])
        self.accept("shift-up", self.updateKeyMap, ["down", False])
        self.accept("escape", self.quit)
        
        # Add the movement task
        self.taskMgr.add(self.moveTask, "moveTask")
        
        # Mouse look (only when dragging)
        self.disableMouse()
        self.mouseDown = False
        self.accept("mouse1", self.onMouseDown)
        self.accept("mouse1-up", self.onMouseUp)
        self.mouseLookTask = self.taskMgr.add(self.mouseLookTask, "mouseLookTask")
        self.lastMouseX = None
        self.lastMouseY = None
        
    def create_terrain_node(self, mesh):
        vertices = np.asarray(mesh.vertices)
        triangles = np.asarray(mesh.triangles)
        colors = np.asarray(mesh.vertex_colors)
        
        print("\n=== Original Terrain Data ===")
        print(f"Original bounds:")
        print(f"X: {np.min(vertices[:, 0]):.1f} to {np.max(vertices[:, 0]):.1f}")
        print(f"Y: {np.min(vertices[:, 1]):.1f} to {np.max(vertices[:, 1]):.1f}")
        print(f"Z: {np.min(vertices[:, 2]):.1f} to {np.max(vertices[:, 2]):.1f}")
        
        # Normalize coordinates to workable range (-100 to 100)
        max_range = np.max([np.ptp(vertices[:, 0]), np.ptp(vertices[:, 1]), np.ptp(vertices[:, 2])])
        scale = 200.0 / max_range
        
        # Center all axes
        center = np.mean(vertices, axis=0)
        vertices_normalized = vertices.copy()
        vertices_normalized -= center
        vertices_normalized *= scale
        
        # Convert from DEM/mesh coordinates to Panda3D coordinates:
        # DEM/mesh: X=east/west, Y=north/south, Z=up
        # Panda3D:  X=east/west, Y=up/down,    Z=north/south(negative=forward)
        vertices_panda = vertices_normalized.copy()
        # X stays as X (east/west)
        vertices_panda[:, 1] = vertices_normalized[:, 2]  # Y in Panda3D is up (from Z)
        vertices_panda[:, 2] = -vertices_normalized[:, 1]  # Z in Panda3D is forward (from -Y)
        
        print("\n=== Processed Terrain Data ===")
        print(f"Normalized bounds:")
        print(f"X (east/west): {np.min(vertices_panda[:, 0]):.1f} to {np.max(vertices_panda[:, 0]):.1f}")
        print(f"Y (up/down): {np.min(vertices_panda[:, 1]):.1f} to {np.max(vertices_panda[:, 1]):.1f}")
        print(f"Z (north/south): {np.min(vertices_panda[:, 2]):.1f} to {np.max(vertices_panda[:, 2]):.1f}")
        
        # Create vertex data with colors
        format = GeomVertexFormat.getV3n3c4()
        vdata = GeomVertexData('terrain', format, Geom.UHStatic)
        vertex = GeomVertexWriter(vdata, 'vertex')
        color = GeomVertexWriter(vdata, 'color')
        
        # Write vertices and colors
        for v, c in zip(vertices_panda, colors):
            vertex.addData3(v[0], v[1], v[2])
            color.addData4(c[0], c[1], c[2], 1.0)
        
        # Create main node
        node = GeomNode('terrain')
        
        # Create solid mesh
        solid_geom = Geom(vdata)
        prim = GeomTriangles(Geom.UHStatic)
        for face in triangles:
            prim.addVertices(int(face[0]), int(face[1]), int(face[2]))
        solid_geom.addPrimitive(prim)
        node.addGeom(solid_geom)
        
        # Create wireframe
        wire_geom = Geom(vdata)  # Use same vertex data as solid mesh
        lines = GeomLines(Geom.UHStatic)
        for face in triangles:
            lines.addVertices(int(face[0]), int(face[1]))
            lines.addVertices(int(face[1]), int(face[2]))
            lines.addVertices(int(face[2]), int(face[0]))
        wire_geom.addPrimitive(lines)
        
        # Add wireframe to same node with black color
        node.addGeom(wire_geom)
        
        # Add a vertical line at origin (0,0)
        line_vdata = GeomVertexData('center_line', GeomVertexFormat.getV3(), Geom.UHStatic)
        line_vertex = GeomVertexWriter(line_vdata, 'vertex')
        
        # Add vertices for vertical line (from below terrain to above)
        y_min = np.min(vertices_panda[:, 1]) - 10  # Extend below terrain
        y_max = np.max(vertices_panda[:, 1]) + 10  # Extend above terrain
        
        # Create two lines for thickness: one in X=0 plane and one in Z=0 plane
        # Vertical line
        line_vertex.addData3(0, y_min, 0)  # Bottom point
        line_vertex.addData3(0, y_max, 0)  # Top point
        # Cross line at bottom
        line_vertex.addData3(-1, y_min, 0)
        line_vertex.addData3(1, y_min, 0)
        line_vertex.addData3(0, y_min, -1)
        line_vertex.addData3(0, y_min, 1)
        # Cross line at top
        line_vertex.addData3(-1, y_max, 0)
        line_vertex.addData3(1, y_max, 0)
        line_vertex.addData3(0, y_max, -1)
        line_vertex.addData3(0, y_max, 1)
        
        # Create line geometry
        line_geom = Geom(line_vdata)
        lines = GeomLines(Geom.UHStatic)
        
        # Add vertical line
        lines.addVertices(0, 1)
        # Add bottom cross
        lines.addVertices(2, 3)
        lines.addVertices(4, 5)
        # Add top cross
        lines.addVertices(6, 7)
        lines.addVertices(8, 9)
        
        line_geom.addPrimitive(lines)
        
        # Add line to node with red color and make it render on top
        line_state = RenderModeAttrib.make(RenderModeAttrib.MWireframe)  # Changed from MLine to MWireframe
        node.addGeom(line_geom, line_state)
        
        return node
    
    def onMouseDown(self):
        self.mouseDown = True
        
    def onMouseUp(self):
        self.mouseDown = False
    
    def updateKeyMap(self, key, value):
        self.keyMap[key] = value
    
    def moveTask(self, task):
        dt = globalClock.getDt()
        speed = 20.0
        
        # Get the camera's direction vectors in Panda3D coordinates
        heading_rad = math.radians(self.camH)
        # Forward is along Y axis (when heading = 180)
        forward = Vec3(0, 1, 0)  # Base forward vector
        right = Vec3(1, 0, 0)    # Base right vector
        
        # Rotate vectors based on heading
        sin_h = math.sin(heading_rad)
        cos_h = math.cos(heading_rad)
        forward = Vec3(sin_h, cos_h, 0)
        right = Vec3(cos_h, -sin_h, 0)
        
        # Calculate movement direction
        move_vec = Vec3(0, 0, 0)
        if self.keyMap["forward"]:  # W - move forward
            move_vec += forward
        if self.keyMap["backward"]:  # S - move backward
            move_vec -= forward
        if self.keyMap["left"]:  # A - move left
            move_vec -= right
        if self.keyMap["right"]:  # D - move right
            move_vec += right
        
        # Normalize and apply movement
        if move_vec.length() > 0:
            move_vec.normalize()
            move_vec *= dt * speed
            new_pos = self.camera.getPos() + move_vec
            self.camera.setPos(new_pos)
        
        # Update coordinate display
        pos = self.camera.getPos()
        heading = self.camera.getH()
        pitch = self.camera.getP()
        self.coord_display.setText(
            f"Position: ({pos.x:.1f}, {pos.y:.1f}, {pos.z:.1f})\n"
            f"Heading: {heading:.1f}°\n"
            f"Pitch: {pitch:.1f}°"
        )
        
        # Ground collision check
        self.groundRay.setOrigin(pos + Vec3(0, 1000, 0))
        self.groundRay.setDirection(Vec3(0, -1, 0))
        
        self.cTrav.traverse(self.render)
        entries = []
        for i in range(self.groundHandler.getNumEntries()):
            entry = self.groundHandler.getEntry(i)
            entries.append(entry)
        
        if entries:
            entries.sort(key=lambda x: x.getSurfacePoint(self.render).getY())
            ground_height = entries[-1].getSurfacePoint(self.render).getY()
            current_pos = self.camera.getPos()
            # Set position maintaining X and Z but updating Y to stay above ground
            self.camera.setPos(current_pos.getX(), 
                                    ground_height + self.desired_height,
                                    current_pos.getZ())
            
            # Debug every second
            if task.frame % 60 == 0:
                print(f"\nPosition Update:")
                print(f"Camera pos: {self.camera.getPos()}")
                print(f"Ground height: {ground_height:.1f}")
                print(f"Height above ground: {self.camera.getY() - ground_height:.1f}")
        
        return Task.cont
    
    def mouseLookTask(self, task):
        if self.mouseWatcherNode.hasMouse():
            mouseX = self.mouseWatcherNode.getMouseX()
            mouseY = self.mouseWatcherNode.getMouseY()
            
            if self.mouseDown:
                if self.lastMouseX is not None and self.lastMouseY is not None:
                    deltaX = mouseX - self.lastMouseX
                    deltaY = mouseY - self.lastMouseY
                    
                    # Update both heading and pitch
                    self.camH -= deltaX * 50
                    self.camH %= 360  # Keep between 0 and 360
                    
                    # Update pitch with limits
                    self.camP += deltaY * 50
                    self.camP = max(-89, min(89, self.camP))  # Limit vertical look
                    
                    # Apply rotations to camera only
                    self.camera.setH(self.camH)
                    self.camera.setP(self.camP)
            
            self.lastMouseX = mouseX
            self.lastMouseY = mouseY
        
        return Task.cont
    
    def quit(self):
        self.userExit()

def launch_terrain_viewer(mesh):
    app = TerrainViewer(mesh)
    app.run() 