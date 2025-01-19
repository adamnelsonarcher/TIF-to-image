from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from panda3d.core import Point3, Vec3, DirectionalLight, AmbientLight
from panda3d.core import GeomVertexFormat, GeomVertexData, GeomVertexWriter
from panda3d.core import Geom, GeomLines, GeomNode, GeomTriangles
from panda3d.core import TextNode, CollisionTraverser, CollisionNode
from panda3d.core import CollisionRay, CollisionHandlerQueue, BitMask32
from panda3d.core import CollisionPolygon
from direct.gui.OnscreenText import OnscreenText
import math
import random
import numpy as np
import rasterio
import os

class SimpleCameraViewer(ShowBase):
    def __init__(self, create_default_terrain=True, dem_data=None, pixel_size=None):
        ShowBase.__init__(self)
        
        # Store DEM data if provided
        self.dem_data = dem_data
        self.pixel_size = pixel_size
        
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
        
        # Enable debug visualization of collisions
        self.cTrav.showCollisions(self.render)
        
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
        
        # Create terrain only if requested
        if create_default_terrain:
            self.create_terrain()
        
        # Create reference lines
        self.create_reference_lines()
        
        # Set up camera
        self.camera_setup()
        
        # Set up controls
        self.setup_controls()
        
    def create_terrain(self):
        """
        This method is meant to be overridden by subclasses.
        The default implementation creates a simple terrain if DEM data is provided.
        """
        if self.dem_data is not None and self.pixel_size is not None:
            print(f"Creating terrain from DEM data with shape: {self.dem_data.shape}")
            print(f"Pixel size: {self.pixel_size}m")
            
            # Create vertex data
            format = GeomVertexFormat.getV3n3()
            vdata = GeomVertexData('terrain', format, Geom.UHStatic)
            vertex = GeomVertexWriter(vdata, 'vertex')
            normal = GeomVertexWriter(vdata, 'normal')
            
            # Calculate world coordinates using actual pixel size
            half_width = (self.dem_data.shape[1] * self.pixel_size) / 2
            half_height = (self.dem_data.shape[0] * self.pixel_size) / 2
            
            print(f"Creating terrain from {-half_width}m to {half_width}m in X")
            print(f"Creating terrain from {-half_height}m to {half_height}m in Y")
            
            # Create vertices
            min_height = float('inf')
            max_height = float('-inf')
            vertex_count = 0
            
            for y in range(self.dem_data.shape[0]):
                for x in range(self.dem_data.shape[1]):
                    # Convert array indices to world coordinates using actual pixel size
                    world_x = (x * self.pixel_size) - half_width
                    world_y = (y * self.pixel_size) - half_height
                    height = float(self.dem_data[y, x])
                    
                    min_height = min(min_height, height)
                    max_height = max(max_height, height)
                    
                    vertex.addData3(world_x, world_y, height)
                    vertex_count += 1
                    
                    # Calculate normal
                    if x > 0 and y > 0 and x < self.dem_data.shape[1]-1 and y < self.dem_data.shape[0]-1:
                        dx = (float(self.dem_data[y, x+1]) - float(self.dem_data[y, x-1])) / (2 * self.pixel_size)
                        dy = (float(self.dem_data[y+1, x]) - float(self.dem_data[y-1, x])) / (2 * self.pixel_size)
                        normal_vec = Vec3(-dx, -dy, 1)
                        if normal_vec.length() > 0:
                            normal_vec.normalize()
                            normal.addData3(normal_vec[0], normal_vec[1], normal_vec[2])
                        else:
                            normal.addData3(0, 0, 1)
                    else:
                        normal.addData3(0, 0, 1)
            
            print(f"Added {vertex_count} vertices")
            print(f"Height range: {min_height}m to {max_height}m")
            
            # Create triangles
            tris = GeomTriangles(Geom.UHStatic)
            triangle_count = 0
            width = self.dem_data.shape[1]
            for y in range(self.dem_data.shape[0] - 1):
                for x in range(self.dem_data.shape[1] - 1):
                    v0 = y * width + x
                    v1 = v0 + 1
                    v2 = (y + 1) * width + x
                    v3 = v2 + 1
                    
                    tris.addVertices(v0, v1, v2)
                    tris.addVertices(v1, v3, v2)
                    triangle_count += 2
            
            print(f"Added {triangle_count} triangles")
            
            # Create and attach geometry
            geom = Geom(vdata)
            geom.addPrimitive(tris)
            node = GeomNode('terrain')
            node.addGeom(geom)
            self.terrain = self.render.attachNewNode(node)
            self.terrain.setColor(0.4, 0.4, 0.4, 1)  # Gray color
            
            print("Terrain node created and attached")
            
            # Create wireframe overlay
            wireframe = self.terrain.copyTo(self.render)
            wireframe.setRenderModeWireframe()
            wireframe.setColor(1, 1, 1, 0.3)
            wireframe.setTransparency(True)
            wireframe.setZ(0.01)
            
            # Set up collision detection
            self.terrain.setCollideMask(BitMask32.bit(1))
            terrainCol = CollisionNode('terrainCol')
            terrainCol.setFromCollideMask(BitMask32.allOff())
            terrainCol.setIntoCollideMask(BitMask32.bit(1))
            terrainColNp = self.terrain.attachNewNode(terrainCol)
            
            # Create collision triangles
            for y in range(self.dem_data.shape[0] - 1):
                for x in range(self.dem_data.shape[1] - 1):
                    # Get the four corners of the current grid cell
                    v0 = Point3((x * self.pixel_size) - half_width, 
                               (y * self.pixel_size) - half_height, 
                               float(self.dem_data[y, x]))
                    v1 = Point3(((x+1) * self.pixel_size) - half_width, 
                               (y * self.pixel_size) - half_height, 
                               float(self.dem_data[y, x+1]))
                    v2 = Point3((x * self.pixel_size) - half_width, 
                               ((y+1) * self.pixel_size) - half_height, 
                               float(self.dem_data[y+1, x]))
                    v3 = Point3(((x+1) * self.pixel_size) - half_width, 
                               ((y+1) * self.pixel_size) - half_height, 
                               float(self.dem_data[y+1, x+1]))
                    
                    # Create two triangles for each grid cell
                    terrainCol.addSolid(CollisionPolygon(v0, v1, v2))
                    terrainCol.addSolid(CollisionPolygon(v1, v3, v2))
            
            print("Terrain collision setup complete")
        
    def create_reference_lines(self):
        # Create vertex data
        format = GeomVertexFormat.getV3()
        vdata = GeomVertexData('lines', format, Geom.UHStatic)
        vertex = GeomVertexWriter(vdata, 'vertex')
        
        # Origin vertical line
        vertex.addData3(0, 0, -10)  # Bottom
        vertex.addData3(0, 0, 10)   # Top
        
        # 100m reference lines
        distance = 100  # Distance from center
        height = 100.0  # 100 meter tall markers
        
        # Get ground heights at each marker position
        positions = [
            (0, distance),    # North
            (0, -distance),   # South
            (distance, 0),    # East
            (-distance, 0),   # West
        ]
        
        # Check ground height at each position
        for x, y in positions:
            ground_z = self.find_ground_height(x, y)
            # Add vertices for this marker
            vertex.addData3(x, y, ground_z)          # Bottom
            vertex.addData3(x, y, ground_z + height) # Top
        
        # Create lines geometry
        lines = GeomLines(Geom.UHStatic)
        # Origin line
        lines.addVertices(0, 1)
        # Reference lines (4 pairs of vertices after origin line)
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
        
        # Get camera's forward and right vectors based on heading only (ignore pitch)
        heading_rad = math.radians(self.camH)
        
        # Forward vector projected onto horizontal plane
        forward = Vec3(
            math.sin(heading_rad),  
            -math.cos(heading_rad),
            0
        )
        
        # Right vector is perpendicular to forward
        right = Vec3(
            forward.y,
            -forward.x,
            0
        )
        
        # Calculate movement direction relative to camera view
        move_vec = Vec3(0, 0, 0)
        if self.keyMap["forward"]: move_vec -= forward
        if self.keyMap["backward"]: move_vec += forward
        if self.keyMap["left"]: move_vec += right
        if self.keyMap["right"]: move_vec -= right
        
        # Only move if we have a movement vector
        if move_vec.length() > 0:
            move_vec.normalize()
            move_vec *= dt * speed
            current_pos = self.camera.getPos()
            desired_pos = current_pos + move_vec
            
            # First check if we can move to the new position
            new_ground_height = self.find_ground_height(desired_pos.x, desired_pos.y)
            current_ground_height = self.find_ground_height(current_pos.x, current_pos.y)
            
            # Calculate height difference
            height_diff = new_ground_height - current_ground_height
            max_climb = speed * dt  # Maximum climb rate per second
            
            if abs(height_diff) <= max_climb:
                # Safe to move to new position
                self.camera.setPos(desired_pos.x, desired_pos.y, new_ground_height + self.eye_height)
            else:
                # Too steep - try to slide along the terrain
                if height_diff > 0:
                    # Going uphill - stop or slide
                    slide_amount = 0.2  # How much we slide (0 to 1)
                    slide_pos = current_pos + (move_vec * slide_amount)
                    slide_ground_height = self.find_ground_height(slide_pos.x, slide_pos.y)
                    self.camera.setPos(slide_pos.x, slide_pos.y, slide_ground_height + self.eye_height)
                else:
                    # Going downhill - slide down
                    slide_pos = current_pos + (move_vec * 0.5)
                    slide_ground_height = self.find_ground_height(slide_pos.x, slide_pos.y)
                    self.camera.setPos(slide_pos.x, slide_pos.y, slide_ground_height + self.eye_height)
        
        # Always ensure we're at the correct height above ground
        current_pos = self.camera.getPos()
        ground_height = self.find_ground_height(current_pos.x, current_pos.y)
        self.camera.setZ(ground_height + self.eye_height)
        
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
                    
                    # Reset camera rotation and apply new rotation
                    self.camera.setH(self.camH)
                    self.camera.setP(self.camP)
        
            self.lastMouseX = mouseX
            self.lastMouseY = mouseY
        
        return Task.cont
        
    def quit(self):
        self.userExit()

    def find_ground_height(self, x, y):
        """Find the ground height at a given x,y position"""
        # Start ray from high above to ensure we catch the ground
        self.groundRay.setOrigin(Point3(x, y, 10000))
        self.groundRay.setDirection(Vec3(0, 0, -1))
        
        # Traverse the collision system
        self.cTrav.traverse(self.render)
        
        # Get all entries
        entries = []
        for i in range(self.groundHandler.getNumEntries()):
            entry = self.groundHandler.getEntry(i)
            entries.append(entry)
        
        if entries:
            # Sort entries by height and return the highest one
            entries.sort(key=lambda x: x.getSurfacePoint(self.render).getZ())
            return entries[-1].getSurfacePoint(self.render).getZ()
        
        print(f"Warning: No ground found at ({x}, {y})")
        return 0  # Return 0 if no ground found
    
    def set_initial_position(self, x, y):
        """Set the camera at a specific x,y position, finding correct ground height"""
        ground_z = self.find_ground_height(x, y)
        self.camera.setPos(x, y, ground_z + self.eye_height)
        print(f"Setting initial position: ({x}, {y}, {ground_z + self.eye_height})")

def main():
    try:
        # Load DEM data with subsample for testing
        dem_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dem_data.tif')
        
        print(f"Loading DEM file: {dem_file}")
        with rasterio.open(dem_file) as dem_dataset:
            # Calculate actual resolution based on known physical size
            full_shape = dem_dataset.shape
            total_length = 17000  # 17km in meters
            pixel_size = total_length / full_shape[0]  # meters per pixel
            
            print(f"DEM dimensions: {full_shape}")
            print(f"Calculated resolution: {pixel_size:.2f}m per pixel")
            
            # Get a 4km x 4km test section from the center
            center_row = full_shape[0] // 2
            center_col = full_shape[1] // 2
            window_size = max(3, int(4000 / pixel_size))  # Ensure enough pixels for 4km
            
            window = rasterio.windows.Window(
                center_col - window_size//2,
                center_row - window_size//2,
                window_size,
                window_size
            )
            
            dem_data = dem_dataset.read(1, window=window)
            transform = dem_dataset.window_transform(window)
            
            print(f"\nTerrain Information:")
            print(f"Test section shape: {dem_data.shape}")
            print(f"Test section size: {dem_data.shape[1] * pixel_size:.1f}m x {dem_data.shape[0] * pixel_size:.1f}m")
        
        # Create viewer with DEM data and calculated pixel size
        app = SimpleCameraViewer(create_default_terrain=True, dem_data=dem_data, pixel_size=pixel_size)
        app.run()
        
    except Exception as e:
        print(f"Error loading DEM data: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main() 