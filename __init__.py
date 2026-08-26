

import bpy
import os
import math
import mathutils
from bpy_extras import view3d_utils

# --- OPERATOR: Handles the Raycast, Spawning, and Redo Panel ---
class VIEW3D_OT_spawn_scale_reference(bpy.types.Operator):
    """Click to spawn a scale reference"""
    bl_idname = "view3d.spawn_scale_reference"
    bl_label = "Spawn Scale Reference"
    bl_options = {'REGISTER', 'UNDO'}

    # Options for the tool settings bar / redo panel
    ref_type: bpy.props.EnumProperty(
        name="Reference Type",
        items=[
            ('MALE_FRONT', "Male Front (180cm)", "", 1),
            ('MALE_SIDE', "Male Side (180cm)", "", 2),
            ('FEMALE_FRONT', "Female Front (160cm)", "", 3),
            ('FEMALE_SIDE', "Female Side (160cm)", "", 4),
            ('HAND', "Hand (20cm)", "", 5),
        ],
        default='MALE_FRONT'
    )

    # Hidden properties to store the raycast data so the Redo panel can re-execute
    hit_loc: bpy.props.FloatVectorProperty(options={'HIDDEN'})
    hit_normal: bpy.props.FloatVectorProperty(options={'HIDDEN'})
    view_z_rot: bpy.props.FloatProperty(options={'HIDDEN'})

    def invoke(self, context, event):
        # 1. Setup Raycast from Mouse Position
        scene = context.scene
        region = context.region
        rv3d = context.region_data
        coord = event.mouse_region_x, event.mouse_region_y

        view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
        ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
        depsgraph = context.evaluated_depsgraph_get()

        # 2. Fire the Raycast
        hit, location, normal, index, obj, matrix = scene.ray_cast(depsgraph, ray_origin, view_vector)

        if not hit:
            self.report({'WARNING'}, "Click on a mesh to spawn reference.")
            return {'CANCELLED'}

        # 3. Store the data from the click
        self.hit_loc = location
        self.hit_normal = normal
        
        # Capture the Z rotation of the current viewport camera
        view_matrix = rv3d.view_matrix.inverted()
        self.view_z_rot = view_matrix.to_euler().z

        # 4. Pass execution to the main function
        return self.execute(context)

    def execute(self, context):
        addon_dir = os.path.dirname(__file__)
        data = {
            'MALE_FRONT': ("Front_Male.png", 1.8),
            'MALE_SIDE': ("Side_Walk_Male.png", 1.8),
            'FEMALE_FRONT': ("Front_Female.png", 1.6),
            'FEMALE_SIDE': ("Side_Walk_Female.png", 1.6),
            'HAND': ("Hand.png", 0.2),
        }
        
        filename, scale = data[self.ref_type]
        filepath = os.path.join(addon_dir, filename)

        if not os.path.exists(filepath):
            self.report({'ERROR'}, f"Image not found: {filename}")
            return {'CANCELLED'}

        # Load Image (or use existing)
        img = bpy.data.images.get(filename)
        if img is None:
            img = bpy.data.images.load(filepath)

        # Spawn the Image Empty using the stored location
        bpy.ops.object.empty_add(type='IMAGE', align='WORLD', location=self.hit_loc)
        empty = context.active_object
        empty.name = f"Ref_{filename.split('.')[0]}"
        empty.data = img
        empty.empty_display_size = scale
        
        # Display Overrides
        empty.show_in_front = True
        empty.use_empty_image_alpha = True
        empty.color = (1.0, 1.0, 1.0, 0.5)

        # Handle Orientation and Location Shift
        if self.ref_type == 'HAND':
            # Align flat against the surface normal
            empty.rotation_euler = mathutils.Vector(self.hit_normal).to_track_quat('Z', 'Y').to_euler()
        else:
            # Stand upright (90 deg on X) and face the viewport (view_z_rot on Z)
            empty.rotation_euler = (math.radians(90), 0, self.view_z_rot)
            
            # Shift up on global Z-axis by half of total length so feet touch surface
            empty.location.z += (scale / 2)

        # --- COLLECTION MANAGEMENT ---
        col_name = "Reference Scale Empties"
        target_col = bpy.data.collections.get(col_name)
        
        # Create the collection in the root Scene Collection if it doesn't exist
        if not target_col:
            target_col = bpy.data.collections.new(col_name)
            context.scene.collection.children.link(target_col)
            
        # Link the new empty to our target collection
        if empty.name not in target_col.objects:
            target_col.objects.link(empty)
            
        # Unlink it from all other collections (like the active one it spawned in)
        for col in empty.users_collection:
            if col != target_col:
                col.objects.unlink(empty)

        return {'FINISHED'}

# --- TOOL: Adds the icon to the Left Toolbar ---
class VIEW3D_PT_ScaleTool(bpy.types.WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'OBJECT'
    bl_idname = "tool.scale_reference"
    bl_label = "Reference Scale"
    bl_description = "Spawn 2D scale references on surfaces"
    
    # Updated to your requested native icon
    bl_icon = "brush.paint_weight.average"
    bl_widget = None
    
    # Binds our operator to the Left Mouse Button when tool is active
    bl_keymap = (
        ("view3d.spawn_scale_reference", {"type": 'LEFTMOUSE', "value": 'PRESS'}, None),
    )

    @classmethod
    def draw_settings(cls, context, layout, tool):
        # Adds the drop-down menu to the top header bar
        props = tool.operator_properties("view3d.spawn_scale_reference")
        layout.prop(props, "ref_type", text="Graphic")

# --- REGISTRATION ---
classes = (
    VIEW3D_OT_spawn_scale_reference,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.utils.register_tool(VIEW3D_PT_ScaleTool, after={"builtin.measure"})

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    bpy.utils.unregister_tool(VIEW3D_PT_ScaleTool)

if __name__ == "__main__":
    register()