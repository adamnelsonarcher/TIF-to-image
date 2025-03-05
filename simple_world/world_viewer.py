from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from panda3d.core import Point3, Vec3, DirectionalLight, AmbientLight
from panda3d.core import TextNode, CollisionTraverser, CollisionNode
from panda3d.core import CollisionRay, CollisionHandlerQueue, BitMask32
from direct.gui.OnscreenText import OnscreenText
import math
import os
from panda3d.core import GeomVertexFormat, GeomVertexData, Geom, GeomLines, GeomVertexWriter, GeomNode, GeomTriangles

class WorldViewer(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        
        # Actor's heading (direction it's facing)
        self.actorH = 180  # Start facing -Y
        
        # Create screenshots directory if it doesn't exist
        self.screenshot_dir = "simple_world/screenshots"
        if not os.path.exists(self.screenshot_dir):
            os.makedirs(self.screenshot_dir)
        
        # Add collision detection
        self.cTrav = CollisionTraverser()
        self.groundRay = CollisionRay()
        self.groundCol = CollisionNode('groundRay')
        self.groundCol.addSolid(self.groundRay)
        self.groundCol.setFromCollideMask(BitMask32.bit(1))
        self.groundCol.setIntoCollideMask(BitMask32.allOff())
        self.groundColNp = self.render.attachNewNode(self.groundCol)
        self.groundHandler = CollisionHandlerQueue()
        self.cTrav.addCollider(self.groundColNp, self.groundHandler)
        
        # Set up basic scene
        self.setBackgroundColor(0.5, 0.8, 1)  # Light blue sky
        
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
        
        # Create ground and terrain
        self.create_ground()
        
        # Create player model (simple box for now)
        self.create_player()
        
        # Set up camera
        self.camera_setup()
        
        # Set up controls
        self.setup_controls()
        
        # Screenshot counter
        self.screenshot_count = 0
        
        # Add coordinate display
        self.coord_display = OnscreenText(
            text="",
            style=1,
            fg=(1, 1, 1, 1),
            pos=(-1.3, 0.95),
            align=TextNode.ALeft,
            scale=.05
        )
        
        # Add reference objects
        self.create_reference_objects()
    
    def create_ground(self):
        # Create terrain mesh
        terrain_node = self.create_terrain_mesh()
        self.terrain = self.render.attachNewNode(terrain_node)
        self.terrain.setColor(0.3, 0.6, 0.3)  # Green color
        self.terrain.setCollideMask(BitMask32.bit(1))  # Make terrain collidable
        
        # Create grid lines
        format = GeomVertexFormat.getV3()
        vdata = GeomVertexData('grid', format, Geom.UHStatic)
        vertex = GeomVertexWriter(vdata, 'vertex')
        
        # Create grid lines every 5 meters
        grid_size = 100  # 100x100 meter grid
        spacing = 5      # 5 meter spacing
        
        # Create lines
        for i in range(-grid_size, grid_size + spacing, spacing):
            # X lines
            vertex.addData3(i, -grid_size, 0.01)
            vertex.addData3(i, grid_size, 0.01)
            # Y lines
            vertex.addData3(-grid_size, i, 0.01)
            vertex.addData3(grid_size, i, 0.01)
        
        # Create lines geometry
        lines = GeomLines(Geom.UHStatic)
        for i in range(0, vdata.getNumRows(), 2):
            lines.addVertices(i, i+1)
        
        # Create and attach geometry
        geom = Geom(vdata)
        geom.addPrimitive(lines)
        node = GeomNode('grid')
        node.addGeom(geom)
        grid_np = self.render.attachNewNode(node)
        grid_np.setColor(0.2, 0.2, 0.2, 1)  # Dark gray lines
        
    def create_player(self):
        # Create a simple box for the player
        from panda3d.core import GeomVertexFormat, GeomVertexData
        from panda3d.core import Geom, GeomTriangles, GeomVertexWriter, GeomNode
        
        format = GeomVertexFormat.getV3n3()
        vdata = GeomVertexData('player', format, Geom.UHStatic)
        vertex = GeomVertexWriter(vdata, 'vertex')
        normal = GeomVertexWriter(vdata, 'normal')
        
        # Add the vertices for a 1x1x2 meter box
        size_x = 0.5
        size_y = 0.5
        size_z = 1.7
        
        # Define the vertices
        vertex.addData3(-size_x, -size_y, 0)
        vertex.addData3(size_x, -size_y, 0)
        vertex.addData3(size_x, size_y, 0)
        vertex.addData3(-size_x, size_y, 0)
        vertex.addData3(-size_x, -size_y, size_z)
        vertex.addData3(size_x, -size_y, size_z)
        vertex.addData3(size_x, size_y, size_z)
        vertex.addData3(-size_x, size_y, size_z)
        
        # Define the normals
        for i in range(8):
            normal.addData3(0, 0, 1)
        
        # Create the triangles
        tris = GeomTriangles(Geom.UHStatic)
        
        # Define the triangles
        indices = [0,1,2, 0,2,3,  # Bottom
                  4,5,6, 4,6,7,  # Top
                  0,4,5, 0,5,1,  # Front
                  1,5,6, 1,6,2,  # Right
                  2,6,7, 2,7,3,  # Back
                  3,7,4, 3,4,0]  # Left
        
        for i in indices:
            tris.addVertex(i)
        
        # Create and attach geometry
        geom = Geom(vdata)
        geom.addPrimitive(tris)
        node = GeomNode('player')
        node.addGeom(geom)
        self.player = self.render.attachNewNode(node)
        self.player.setColor(0.8, 0.2, 0.2)  # Red color
        self.player.setPos(0, 0, 0)  # Start at ground level
        
        # Add direction indicator (a thick line pointing forward)
        format = GeomVertexFormat.getV3()
        vdata = GeomVertexData('direction', format, Geom.UHStatic)
        vertex = GeomVertexWriter(vdata, 'vertex')
        
        # Create a single thick line at head height
        height = 1.7  # Head height
        vertex.addData3(0, 0, height)  # Start at actor's position
        vertex.addData3(0, 2, height)  # 2 meters forward
        
        # Create line geometry
        lines = GeomLines(Geom.UHStatic)
        lines.addVertices(0, 1)
        
        # Create and attach geometry
        geom = Geom(vdata)
        geom.addPrimitive(lines)
        node = GeomNode('direction_indicator')
        node.addGeom(geom)
        
        self.direction_indicator = self.player.attachNewNode(node)
        self.direction_indicator.setColor(1, 1, 0, 1)  # Yellow line
        # Make the line thicker
        self.direction_indicator.setRenderModeThickness(5)  # Adjust thickness as needed
        
    def camera_setup(self):
        # Initialize camera angles
        self.camH = 180  # Start facing -Y
        self.camP = -30  # Look down slightly
        self.camDist = 10  # Distance from player
        
        # Set initial camera position higher
        self.update_camera_position()
        
        # Disable default mouse control
        self.disableMouse()
        
    def update_camera_position(self):
        # Calculate camera position based on player position and camera angles
        heading_rad = math.radians(self.camH)
        pitch_rad = math.radians(self.camP)
        
        # Calculate camera offset
        cam_x = -math.sin(heading_rad) * math.cos(pitch_rad) * self.camDist
        cam_y = -math.cos(heading_rad) * math.cos(pitch_rad) * self.camDist
        cam_z = -math.sin(pitch_rad) * self.camDist
        
        # Position camera
        player_pos = self.player.getPos()
        self.camera.setPos(
            player_pos.getX() + cam_x,
            player_pos.getY() + cam_y,
            max(1.7, player_pos.getZ() - cam_z + 1.7)  # Ensure minimum height
        )
        
        # Look at player's head level
        self.camera.lookAt(
            player_pos.getX(),
            player_pos.getY(),
            player_pos.getZ() + 1.7  # Look at head height
        )
        
    def setup_controls(self):
        # Movement controls
        self.keyMap = {
            "forward": False,
            "backward": False,
            "left": False,
            "right": False,
            "cam_left": False,
            "cam_right": False,
            "turn_left": False,
            "turn_right": False,
            "cam_up": False,    # New
            "cam_down": False   # New
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
        self.accept("q", self.updateKeyMap, ["turn_left", True])
        self.accept("q-up", self.updateKeyMap, ["turn_left", False])
        self.accept("e", self.updateKeyMap, ["turn_right", True])
        self.accept("e-up", self.updateKeyMap, ["turn_right", False])
        self.accept("p", self.take_picture)
        self.accept("escape", self.quit)
        
        # Add to existing key bindings
        self.accept("arrow_up", self.updateKeyMap, ["cam_up", True])
        self.accept("arrow_up-up", self.updateKeyMap, ["cam_up", False])
        self.accept("arrow_down", self.updateKeyMap, ["cam_down", True])
        self.accept("arrow_down-up", self.updateKeyMap, ["cam_down", False])
        
        # Mouse look
        self.mouseDown = False
        self.accept("mouse3", self.onMouseDown)  # Right mouse button
        self.accept("mouse3-up", self.onMouseUp)
        self.lastMouseX = None
        self.lastMouseY = None
        
        # Add tasks
        self.taskMgr.add(self.moveTask, "moveTask")
        self.taskMgr.add(self.mouseLookTask, "mouseLookTask")
        
    def updateKeyMap(self, key, value):
        self.keyMap[key] = value
        
    def moveTask(self, task):
        dt = globalClock.getDt()
        speed = 5.0
        turn_speed = 100.0
        pitch_speed = 50.0
        
        # Update actor rotation
        if self.keyMap["turn_left"]:
            self.actorH += turn_speed * dt
        if self.keyMap["turn_right"]:
            self.actorH -= turn_speed * dt
        
        # Keep heading in 0-360 range
        self.actorH %= 360
        
        # Update actor model rotation
        self.player.setH(self.actorH)
        
        # Add after the actor rotation code but before movement calculation
        if self.keyMap["cam_up"]:
            self.camP = max(self.camP - pitch_speed * dt, -85)
        if self.keyMap["cam_down"]:
            self.camP = min(self.camP + pitch_speed * dt, 85)
        
        # Calculate movement direction relative to actor orientation
        heading_rad = math.radians(self.actorH)
        forward = Vec3(math.sin(heading_rad), math.cos(heading_rad), 0)
        right = Vec3(math.cos(heading_rad), -math.sin(heading_rad), 0)
        
        # Calculate movement
        move_vec = Vec3(0, 0, 0)
        if self.keyMap["forward"]: move_vec += forward
        if self.keyMap["backward"]: move_vec -= forward
        if self.keyMap["left"]: move_vec -= right
        if self.keyMap["right"]: move_vec += right
        
        # Apply movement to player with ground collision
        if move_vec.length() > 0:
            move_vec.normalize()
            move_vec *= dt * speed
            new_pos = self.player.getPos() + move_vec
            
            # Update ground ray from high above current position
            self.groundRay.setOrigin(Point3(new_pos.x, new_pos.y, 100))
            self.groundRay.setDirection(Vec3(0, 0, -1))
            
            # Process collisions
            self.cTrav.traverse(self.render)
            if self.groundHandler.getNumEntries() > 0:
                entry = self.groundHandler.getEntry(0)
                ground_z = entry.getSurfacePoint(entry.getIntoNodePath()).z
                new_pos.z = ground_z  # Place directly on ground
                self.player.setPos(new_pos)
        
        # Update camera position
        self.update_camera_position()
        
        # Update coordinate display
        pos = self.player.getPos()
        self.coord_display.setText(
            f"Position: ({pos.x:.1f}, {pos.y:.1f}, {pos.z:.1f})\n"
            f"Heading: {self.actorH:.1f}°"
        )
        
        return Task.cont
        
    def take_picture(self):
        # Store current camera position and rotation
        original_pos = self.camera.getPos()
        original_hpr = self.camera.getHpr()
        
        # Move camera to actor's view
        actor_pos = self.player.getPos()
        self.camera.setPos(actor_pos.getX(), actor_pos.getY(), actor_pos.getZ() + 1.7)
        self.camera.setHpr(self.actorH, 0, 0)
        
        # Take screenshot and record metadata
        base.graphicsEngine.renderFrame()
        filename = os.path.join(self.screenshot_dir, f"screenshot_{self.screenshot_count}.jpg")
        self.screenshot(filename, defaultFilename=False)
        
        # Print photo metadata
        pos = self.player.getPos()
        print(f"Photo taken at:")
        print(f"Position: ({pos.x:.1f}, {pos.y:.1f}, {pos.z:.1f})")
        print(f"Heading: {self.actorH:.1f}°")
        print(f"Saved as: {filename}")
        
        self.screenshot_count += 1
        
        # Restore observer camera
        self.camera.setPos(original_pos)
        self.camera.setHpr(original_hpr)
    
    def quit(self):
        self.userExit()

    def create_reference_objects(self):
        # Create markers at 25m intervals
        format = GeomVertexFormat.getV3()
        vdata = GeomVertexData('markers_25m', format, Geom.UHStatic)
        vertex = GeomVertexWriter(vdata, 'vertex')
        
        # Create 25m markers
        for x in [-25, 25]:
            for y in [-25, 25]:
                # Vertical post
                vertex.addData3(x, y, 0)
                vertex.addData3(x, y, 3)  # 3m tall post
        
        # Create lines geometry
        lines = GeomLines(Geom.UHStatic)
        for i in range(0, 8, 2):
            lines.addVertices(i, i+1)
        
        # Create and attach geometry
        geom = Geom(vdata)
        geom.addPrimitive(lines)
        node = GeomNode('markers_25m')
        node.addGeom(geom)
        markers_25m = self.render.attachNewNode(node)
        markers_25m.setColor(1, 0, 0, 1)  # Red markers
        
        # Create 1km markers
        vdata = GeomVertexData('markers_1km', format, Geom.UHStatic)
        vertex = GeomVertexWriter(vdata, 'vertex')
        
        # Create 1km markers
        for x in [-1000, 1000]:
            for y in [-1000, 1000]:
                # Vertical post
                vertex.addData3(x, y, 0)
                vertex.addData3(x, y, 50)  # 50m tall post for visibility
        
        # Create lines geometry
        lines = GeomLines(Geom.UHStatic)
        for i in range(0, 8, 2):
            lines.addVertices(i, i+1)
        
        # Create and attach geometry
        geom = Geom(vdata)
        geom.addPrimitive(lines)
        node = GeomNode('markers_1km')
        node.addGeom(geom)
        markers_1km = self.render.attachNewNode(node)
        markers_1km.setColor(0, 0, 1, 1)  # Blue markers

    def create_terrain_mesh(self, size=200, resolution=5):
        format = GeomVertexFormat.getV3n3()
        vdata = GeomVertexData('terrain', format, Geom.UHStatic)
        vertex = GeomVertexWriter(vdata, 'vertex')
        normal = GeomVertexWriter(vdata, 'normal')
        
        # Create vertices with height variations
        for y in range(-size//2, size//2 + resolution, resolution):
            for x in range(-size//2, size//2 + resolution, resolution):
                # Create gentle rolling hills using sine waves
                z = (math.sin(x * 0.05) + math.sin(y * 0.05)) * 2  # 2m amplitude
                
                vertex.addData3(x, y, z)
                
                # Calculate normal for lighting
                # Get approximate slope using sine derivatives
                dx = math.cos(x * 0.05) * 0.1  # partial derivative wrt x
                dy = math.cos(y * 0.05) * 0.1  # partial derivative wrt y
                normal_vec = Vec3(-dx, -dy, 1).normalize()
                normal.addData3(*normal_vec)
        
        # Create triangles
        tris = GeomTriangles(Geom.UHStatic)
        rows = size // resolution
        cols = size // resolution
        
        for y in range(rows):
            for x in range(cols):
                # Get indices for current quad
                v0 = x + y * (cols + 1)
                v1 = v0 + 1
                v2 = v0 + (cols + 1)
                v3 = v2 + 1
                
                # Create two triangles for quad
                tris.addVertices(v0, v1, v2)
                tris.addVertices(v1, v3, v2)
        
        # Create and return geometry
        geom = Geom(vdata)
        geom.addPrimitive(tris)
        node = GeomNode('terrain')
        node.addGeom(geom)
        return node

    def onMouseDown(self):
        self.mouseDown = True
        
    def onMouseUp(self):
        self.mouseDown = False
        self.lastMouseX = None
        self.lastMouseY = None

    def mouseLookTask(self, task):
        if self.mouseWatcherNode.hasMouse() and self.mouseDown:
            mouseX = self.mouseWatcherNode.getMouseX()
            mouseY = self.mouseWatcherNode.getMouseY()
            
            if self.lastMouseX is not None:
                deltaX = mouseX - self.lastMouseX
                deltaY = mouseY - self.lastMouseY
                
                self.camH += deltaX * 100  # Horizontal rotation
                self.camP = max(-60, min(0, self.camP - deltaY * 100))  # Vertical rotation with limits
                
            self.lastMouseX = mouseX
            self.lastMouseY = mouseY
            
        return Task.cont

def main():
    app = WorldViewer()
    app.run()

if __name__ == '__main__':
    main() 