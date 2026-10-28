import bpy
import sys
import os

MD3_SAFE_LIMIT = 480.0

def main():
    try:
        bpy.ops.preferences.addon_enable(module="io_scene_md3")
        print("MD3 Add-on aktiviert.")
    except Exception as e:
        print(f"WARNUNG: Add-on nicht aktiviert: {e}")

    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    output_dir = argv[0] if argv else os.path.join(os.getcwd(), "output_models")
    os.makedirs(output_dir, exist_ok=True)

    meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    if not meshes:
        print("FEHLER: Keine Mesh-Objekte gefunden.")
        sys.exit(1)

    base_obj = meshes[0]
    scale_mesh_to_fit(base_obj, MD3_SAFE_LIMIT)

    z_values = [v.co.z for v in base_obj.data.vertices]
    z_min, z_max = min(z_values), max(z_values)
    z_range = z_max - z_min
    print(f"Z-Bereich: {z_min:.2f} bis {z_max:.2f} (Höhe: {z_range:.2f})")

    zones = {
        "legs":  (z_min, z_min + z_range * 0.33),
        "torso": (z_min + z_range * 0.33, z_min + z_range * 0.66),
        "head":  (z_min + z_range * 0.66, z_max)
    }

    for name, (z_low, z_high) in zones.items():
        split_mesh(base_obj, name, z_low, z_high, output_dir)

def scale_mesh_to_fit(obj, safe_limit):
    max_dim = max(obj.dimensions.x, obj.dimensions.y, obj.dimensions.z)
    if max_dim <= safe_limit:
        print("Mesh passt bereits. Keine Skalierung nötig.")
        return
    factor = safe_limit / max_dim
    print(f"Skaliere um Faktor {factor:.6f}")
    for vert in obj.data.vertices:
        vert.co.x *= factor
        vert.co.y *= factor
        vert.co.z *= factor
    obj.scale = (1.0, 1.0, 1.0)
    bpy.context.view_layer.update()

def split_mesh(base_obj, name, z_low, z_high, output_dir):
    new_mesh = base_obj.data.copy()
    new_obj = bpy.data.objects.new(f"zombie_{name}", new_mesh)
    bpy.context.collection.objects.link(new_obj)

    bpy.context.view_layer.objects.active = new_obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')

    for vert in new_mesh.vertices:
        if z_low <= vert.co.z <= z_high:
            vert.select = True

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.delete(type='VERT')
    bpy.ops.object.mode_set(mode='OBJECT')

    export_md3(new_obj, os.path.join(output_dir, f"{name}.md3"))

def export_md3(obj, filepath):
    for o in bpy.context.scene.objects:
        o.hide_set(True)
    obj.hide_set(False)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    with bpy.context.temp_override(active_object=obj, selected_objects=[obj]):
        try:
            bpy.ops.export_scene.md3(
                filepath=filepath,
                enable_convert=False,
                adjust_scale_bug=False
            )
            print(f"OK: {filepath} exportiert.")
        except Exception as e:
            print(f"FEHLER {filepath}: {e}")

    for o in bpy.context.scene.objects:
        o.hide_set(False)

if __name__ == "__main__":
    main()
