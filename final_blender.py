import bpy
import sys
import os
import math
import random

def reset_scene():
    """Clears the scene completely."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for bpy_data_iter in (bpy.data.objects, bpy.data.meshes, bpy.data.materials, bpy.data.cameras):
        for id_data in bpy_data_iter:
            bpy_data_iter.remove(id_data)

def setup_render_settings(output_path="output_collision.mp4", fps=30, duration_sec=4):
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
    scene.render.resolution_x = 1080
    scene.render.resolution_y = 1080
    scene.render.fps = fps
    scene.frame_start = 1
    scene.frame_end = fps * duration_sec
    
    scene.render.image_settings.file_format = 'FFMPEG'
    scene.render.ffmpeg.format = 'MPEG4'
    scene.render.ffmpeg.codec = 'H264'
    scene.render.ffmpeg.constant_rate_factor = 'MEDIUM'
    scene.render.filepath = os.path.abspath(output_path)

def create_environment():
    if not bpy.context.scene.world:
        bpy.context.scene.world = bpy.data.worlds.new("World")
    world = bpy.context.scene.world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.2, 0.2, 0.2, 1)
    
    bpy.ops.mesh.primitive_plane_add(size=100, location=(0, 0, 0))
    floor = bpy.context.active_object
    floor.name = "Floor"
    bpy.ops.rigidbody.object_add()
    floor.rigid_body.type = 'PASSIVE'
    floor.rigid_body.friction = 0.8
    floor.rigid_body.restitution = 0.5
    
    mat = bpy.data.materials.new(name="FloorMat")
    mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs['Base Color'].default_value = (0.1, 0.15, 0.2, 1)
    floor.data.materials.append(mat)

    bpy.ops.object.light_add(type='SUN', location=(5, 5, 10))
    bpy.context.active_object.data.energy = 15.0
    
    bpy.ops.object.light_add(type='AREA', location=(-4, -4, 6))
    area = bpy.context.active_object
    area.data.energy = 2000.0
    area.data.size = 10

    bpy.ops.object.camera_add(location=(0, -10, 4))
    bpy.context.scene.camera = bpy.context.active_object

def get_smart_scale_from_mass(mass):
    mass = float(mass)
    if mass < 1.0: return 0.4
    if mass < 10.0: return 0.8
    if mass < 100.0: return 1.6
    if mass < 1000.0: return 2.5
    return 3.5

def orient_object_matrix(obj, mass, start_location, visual_facing, is_left_object):
    """
    Applies rotation based on the User's derived Matrix Logic.
    ANCHOR A (Unicorn/Right): Z=90
    ANCHOR B (Robot/Left): Z=0
    """
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    
    # --- 1. ZERO OUT ---
    # As you discovered, we do NOT want X or Y rotation.
    obj.rotation_euler = (0, 0, 0)
    
    # --- 2. THE MATRIX ---
    visual_facing = visual_facing.lower()
    z_rot = 0
    
    if is_left_object:
        # --- CASE A: Moving Right (+X) ---
        # Based on Unicorn (Gemini="Right") needing 90.
        
        if "right" in visual_facing:
            z_rot = -90   # User Verified Anchor
        elif "left" in visual_facing:
            z_rot = 90  # Logic: Flip 180 from Anchor
        else: # "front"
            z_rot = 0   # Logic: Assume Front needs same turn as Right
            
    else:
        # --- CASE B: Moving Left (-X) ---
        # Based on Robot (Gemini="Left") needing 0.
        
        if "left" in visual_facing:
            z_rot = -90    # User Verified Anchor
        elif "right" in visual_facing:
            z_rot = 90  # Logic: Flip 180 from Anchor
        else: # "front"
            z_rot = 180  # Logic: Turn 90 to face Left
    
    # Apply the Z rotation
    obj.rotation_euler = (0, 0, math.radians(z_rot))
    
    # --- 3. SCALE & PLACE ---
    target_dim = get_smart_scale_from_mass(mass)
    max_dim = max(obj.dimensions)
    if max_dim > 0:
        scale_factor = target_dim / max_dim
        obj.scale = (scale_factor, scale_factor, scale_factor)
        bpy.ops.object.transform_apply(scale=True)
    
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')
    obj.location = start_location
    
    # --- 4. MATERIAL ---
    if not obj.data.materials:
        mat = bpy.data.materials.new(name=f"{obj.name}_Mat")
        mat.diffuse_color = (random.random(), random.random(), random.random(), 1)
        obj.data.materials.append(mat)
        
    return target_dim

def setup_physics_animation(obj_a, obj_b, props_a, props_b, size_a, size_b):
    # PHYSICS
    for obj, props in [(obj_a, props_a), (obj_b, props_b)]:
        bpy.context.view_layer.objects.active = obj
        bpy.ops.rigidbody.object_add()
        rb = obj.rigid_body
        rb.mass = float(props['mass'])
        rb.friction = float(props['fric'])
        rb.restitution = float(props['bounce'])
        rb.collision_shape = 'CONVEX_HULL'
        rb.use_margin = True
        rb.collision_margin = 0.001

    # ANIMATION (FAST & OVERSHOOT)
    start_frame = 1
    impact_frame = 15
    
    overshoot_a = (1.0, 0, obj_a.location.z)
    overshoot_b = (-1.0, 0, obj_b.location.z)

    # A
    obj_a.rigid_body.kinematic = True
    obj_a.keyframe_insert("rigid_body.kinematic", frame=start_frame)
    obj_a.keyframe_insert("location", frame=start_frame)
    obj_a.keyframe_insert("rotation_euler", frame=start_frame) # Keyframe rotation too
    
    obj_a.location = overshoot_a
    obj_a.keyframe_insert("location", frame=impact_frame + 5)
    
    obj_a.rigid_body.kinematic = False
    obj_a.keyframe_insert("rigid_body.kinematic", frame=impact_frame)

    # B
    obj_b.rigid_body.kinematic = True
    obj_b.keyframe_insert("rigid_body.kinematic", frame=start_frame)
    obj_b.keyframe_insert("location", frame=start_frame)
    obj_b.keyframe_insert("rotation_euler", frame=start_frame) 
    
    obj_b.location = overshoot_b
    obj_b.keyframe_insert("location", frame=impact_frame + 5)
    
    obj_b.rigid_body.kinematic = False
    obj_b.keyframe_insert("rigid_body.kinematic", frame=impact_frame)
    
    # Camera
    max_size = max(size_a, size_b)
    cam = bpy.context.scene.camera
    cam.location = (0, -5 - (max_size * 3), 2 + max_size)
    
    for c in cam.constraints: cam.constraints.remove(c)
    con = cam.constraints.new(type='TRACK_TO')
    con.target = bpy.data.objects["Floor"]
    con.track_axis = 'TRACK_NEGATIVE_Z'
    con.up_axis = 'UP_Y'

def bake_physics():
    print("[BLENDER] Baking Physics...")
    scene = bpy.context.scene
    if not scene.rigidbody_world: bpy.ops.rigidbody.world_add()
    
    # Force Clear
    bpy.ops.ptcache.free_bake_all()
    
    scene.rigidbody_world.point_cache.frame_start = 1
    scene.rigidbody_world.point_cache.frame_end = 250
    try: bpy.ops.ptcache.bake_all(bake=True)
    except Exception as e: print(f"[!] Bake Warning: {e}")

def main():
    try:
        argv = sys.argv
        if "--" in argv: args = argv[argv.index("--") + 1:]
        else: raise ValueError("No args")
        
        # REVERTED TO 'FACE' ARGUMENTS (Strings)
        # args: path, mass, bounce, fric, facing_string
        path_a, m_a, b_a, f_a, face_a = args[0], args[1], args[2], args[3], args[4]
        path_b, m_b, b_b, f_b, face_b = args[5], args[6], args[7], args[8], args[9]
    except Exception as e:
        print(f"[!] Arg Error: {e}")
        return

    reset_scene()
    setup_render_settings()
    create_environment()
    
    # A (Left -> Right)
    if not os.path.exists(path_a): print("Missing A"); return
    bpy.ops.wm.obj_import(filepath=path_a)
    obj_a = bpy.context.selected_objects[0]
    obj_a.name = "Object_A"
    size_a = get_smart_scale_from_mass(m_a)
    start_loc_a = (-1 * (size_a + 2.5), 0, size_a/2)
    
    orient_object_matrix(obj_a, m_a, start_loc_a, face_a, is_left_object=True)
    
    # B (Right -> Left)
    if not os.path.exists(path_b): print("Missing B"); return
    bpy.ops.wm.obj_import(filepath=path_b)
    obj_a.select_set(False)
    obj_b = bpy.context.selected_objects[0]
    if obj_b == obj_a:
        for o in bpy.context.scene.objects:
            if o != obj_a and o.name != "Floor": obj_b = o
    obj_b.name = "Object_B"
    size_b = get_smart_scale_from_mass(m_b)
    start_loc_b = ((size_b + 2.5), 0, size_b/2)
    
    orient_object_matrix(obj_b, m_b, start_loc_b, face_b, is_left_object=False)

    # Simulate
    props_a = {'mass': m_a, 'bounce': b_a, 'fric': f_a}
    props_b = {'mass': m_b, 'bounce': b_b, 'fric': f_b}
    setup_physics_animation(obj_a, obj_b, props_a, props_b, size_a, size_b)
    bake_physics()
    
    print("[BLENDER] Rendering...")
    bpy.ops.render.render(animation=True)

if __name__ == "__main__":
    main()