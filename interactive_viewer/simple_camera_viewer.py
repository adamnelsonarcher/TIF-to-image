from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from panda3d.core import Point3, Vec3, DirectionalLight, AmbientLight
from panda3d.core import GeomVertexFormat, GeomVertexData, GeomVertexWriter
from panda3d.core import Geom, GeomLines, GeomNode, GeomTriangles
from panda3d.core import TextNode, CollisionTraverser, CollisionNode
from panda3d.core import CollisionRay, CollisionHandlerQueue, BitMask32
from direct.gui.OnscreenText import OnscreenText
import math
import random

class SimpleCameraViewer(ShowBase):
    def __init__(self):
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
        
        # Add coordinate display
        self.coord_display = OnscreenText(
            text="",
            style=1,
            fg=(1, 1, 1, 1),
            pos=(-1.3, 0.95),
            align=TextNode.ALeft,
            scale=.05
        )
        
        # Create bumpy terrain
        self.create_terrain()
        
        # Create reference lines
        self.create_reference_lines()
        
        # Set up camera
        self.camera_setup()
        
        # Set up controls
        self.setup_controls()
        
    def create_terrain(self):
        # Create vertex data
        format = GeomVertexFormat.getV3n3()
        vdata = GeomVertexData('terrain', format, Geom.UHStatic)
        vertex = GeomVertexWriter(vdata, 'vertex')
        normal = GeomVertexWriter(vdata, 'normal')
        
        # Create a grid of vertices with random heights
        size = 200  # Size of terrain
        segments = 40  # Number of segments
        step = size / segments
        
        # Create vertices
        for y in range(-segments//2, segments//2 + 1):
            for x in range(-segments//2, segments//2 + 1):
                # Add some random height variation
                height = random.uniform(0, 3) * math.sin(x/5) * math.cos(y/5)
                vertex.addData3(x * step, y * step, height)
                normal.addData3(0, 0, 1)  # Simple normal pointing up
        
        # Create triangles
        tris = GeomTriangles(Geom.UHStatic)
        for y in range(-segments//2, segments//2):
            for x in range(-segments//2, segments//2):
                # Calculate vertex indices
                v0 = (y + segments//2) * (segments + 1) + (x + segments//2)
                v1 = v0 + 1
                v2 = v0 + (segments + 1)
                v3 = v1 + (segments + 1)
                
                # Add triangles
                tris.addVertices(v0, v1, v2)
                tris.addVertices(v1, v3, v2)
        
        # Create and attach solid geometry
        geom = Geom(vdata)
        geom.addPrimitive(tris)
        node = GeomNode('terrain')
        node.addGeom(geom)
        terrain = self.render.attachNewNode(node)
        terrain.setColor(0.4, 0.4, 0.4, 1)  # Gray color
        
        # Create wireframe overlay
        wireframe = terrain.copyTo(self.render)
        wireframe.setRenderModeWireframe()
        wireframe.setColor(1, 1, 1, 0.3)  # White, semi-transparent
        wireframe.setTransparency(True)
        wireframe.setZ(0.01)  # Slight offset to prevent z-fighting
        
        # Set up collision detection
        terrain.setCollideMask(BitMask32.bit(1))
        
    def create_reference_lines(self):
        # Create vertex data
        format = GeomVertexFormat.getV3()
        vdata = GeomVertexData('lines', format, Geom.UHStatic)
        vertex = GeomVertexWriter(vdata, 'vertex')
        
        # Origin vertical line
        vertex.addData3(0, 0, -10)  # Bottom
        vertex.addData3(0, 0, 10)   # Top
        
        # 100m reference lines
        distance = 100
        # North line
        vertex.addData3(0, distance, 0)
        vertex.addData3(0, distance, 5)
        # South line
        vertex.addData3(0, -distance, 0)
        vertex.addData3(0, -distance, 5)
        # East line
        vertex.addData3(distance, 0, 0)
        vertex.addData3(distance, 0, 5)
        # West line
        vertex.addData3(-distance, 0, 0)
        vertex.addData3(-distance, 0, 5)
        
        # Create lines geometry
        lines = GeomLines(Geom.UHStatic)
        # Origin line
        lines.addVertices(0, 1)
        # Reference lines
        for i in range(2, 9, 2):
            lines.addVertices(i, i+1)
        
        # Create and attach geometry
        geom = Geom(vdata)
        geom.addPrimitive(lines)
        node = GeomNode('reference_lines')
        node.addGeom(geom)
        line_np = self.render.attachNewNode(node)
        line_np.setColor(1, 0, 0, 1)  # Red color
        
    def camera_setup(self):
        # Set up first-person camera
        self.eye_height = 1.7  # Eye height in meters
        
        # Initialize camera angles
        self.camH = 180  # Start facing -Y (north)
        self.camP = 0    # Level view
        
        # Position camera
        self.camera.setPos(0, 0, self.eye_height)
        self.camera.setH(self.camH)
        self.camera.setP(self.camP)
        
        # Disable default mouse control
        self.disableMouse()
        
    def setup_controls(self):
        # Movement controls
        self.keyMap = {
            "forward": False,
            "backward": False,
            "left": False,
            "right": False
        }
        
        # Key bindings
        self.accept("w", self.updateKeyMap, ["forward", True])
        self.accept("w-up", self.updateKeyMap, ["forward", False])
        self.accept("s", self.updateKeyMap, ["backward", True])
        self.accept("s-up", self.updateKeyMap, ["backward", False])
        self.accept("a", self.updateKeyMap, ["left", True])
        self.accept("a-up", self.updateKeyMap, ["left", False])
        self.accept("d", self.updateKeyMap, ["right", True])
        self.accept("d-up", self.updateKeyMap, ["right", False])
        self.accept("escape", self.quit)
        
        # Mouse look
        self.mouseDown = False
        self.accept("mouse1", self.onMouseDown)
        self.accept("mouse1-up", self.onMouseUp)
        self.lastMouseX = None
        self.lastMouseY = None
        
        # Add tasks
        self.taskMgr.add(self.moveTask, "moveTask")
        self.taskMgr.add(self.mouseLookTask, "mouseLookTask")
        
    def updateKeyMap(self, key, value):
        self.keyMap[key] = value
        
    def onMouseDown(self):
        self.mouseDown = True
        
    def onMouseUp(self):
        self.mouseDown = False
        
    def moveTask(self, task):
        dt = globalClock.getDt()
        speed = 5.0  # Movement speed in meters per second
        
        # Get camera's forward and right vectors based on heading
        heading_rad = math.radians(self.camH)
        pitch_rad = math.radians(self.camP)
        
        # Forward vector projected onto horizontal plane (ignoring pitch for movement)
        forward = Vec3(
            math.sin(heading_rad),  
            -math.cos(heading_rad),
            0  # Keep movement in horizontal plane
        )
        
        # Right vector is perpendicular to forward (rotate forward 90 degrees right)
        right = Vec3(
            forward.y,    # Rotate forward vector 90 degrees right
            -forward.x,   # to get the right vector
            0
        )
        
        # Calculate movement direction relative to camera view
        move_vec = Vec3(0, 0, 0)
        if self.keyMap["forward"]: move_vec -= forward
        if self.keyMap["backward"]: move_vec += forward
        if self.keyMap["left"]: move_vec += right
        if self.keyMap["right"]: move_vec -= right
        
        # Only check for height changes when actually moving
        if move_vec.length() > 0:
            move_vec.normalize()
            move_vec *= dt * speed
            desired_pos = self.camera.getPos() + move_vec
            
            # Check ground height at desired position
            self.groundRay.setOrigin(desired_pos + Point3(0, 0, 1000))
            self.groundRay.setDirection(Vec3(0, 0, -1))
            
            self.cTrav.traverse(self.render)
            entries = []
            for i in range(self.groundHandler.getNumEntries()):
                entry = self.groundHandler.getEntry(i)
                entries.append(entry)
            
            if entries:
                entries.sort(key=lambda x: x.getSurfacePoint(self.render).getZ())
                ground_height = entries[-1].getSurfacePoint(self.render).getZ()
                eye_height = 1.7  # Height above ground
                
                # Move to new position and adjust height
                self.camera.setPos(desired_pos)
                self.camera.setZ(ground_height + eye_height)
        
        # Update coordinate display
        pos = self.camera.getPos()
        self.coord_display.setText(
            f"Position: ({pos.x:.1f}, {pos.y:.1f}, {pos.z:.1f})\n"
            f"Heading: {self.camH:.1f}°\n"
            f"Pitch: {self.camP:.1f}°"
        )
        
        return Task.cont
        
    def mouseLookTask(self, task):
        if self.mouseWatcherNode.hasMouse():
            mouseX = self.mouseWatcherNode.getMouseX()
            mouseY = self.mouseWatcherNode.getMouseY()
            
            if self.mouseDown:
                if self.lastMouseX is not None and self.lastMouseY is not None:
                    deltaX = mouseX - self.lastMouseX
                    deltaY = mouseY - self.lastMouseY
                    
                    self.camH -= deltaX * 50
                    self.camH %= 360
                    
                    self.camP += deltaY * 50
                    self.camP = max(-89, min(89, self.camP))
                    
                    self.camera.setH(self.camH)
                    self.camera.setP(self.camP)
            
            self.lastMouseX = mouseX
            self.lastMouseY = mouseY
        
        return Task.cont
        
    def quit(self):
        self.userExit()

def main():
    app = SimpleCameraViewer()
    app.run()

if __name__ == '__main__':
    main() 