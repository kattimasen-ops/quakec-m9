import bpy
import sys
import os

# MD3 erlaubt maximal 512 Einheiten pro Achse. Wir bleiben mit 480 auf der sicheren Seite.
MD3_SAFE_LIMIT = 480.0

def main():
    # 1. Add-on aktivieren
    try:
        bpy.ops.preferences.addon_enable(module="io_scene_md3")
        print("MD3 Add-on aktiviert.")
    except Exception as e:
        print(f"WARNUNG: Add-on konnte nicht aktiviert werden: {e}")

    # 2. Argumente nach dem "--" entgegennehmen
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    output_dir = argv[0] if argv else os.path.join(os.getcwd(), "output_models")

    # 3. Ausgabeordner prüfen
    os.makedirs(output_dir, exist_ok=True)
    test_file = os.path.join(output_dir, ".write_test")
    try:
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        print(f"Ausgabeordner bereit: {output_dir}")
    except Exception as e:
        print(f"FEHLER: Ausgabeordner nicht beschreibbar: {e}")
        sys.exit(1)

    # 4. Mesh-Objekte finden
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    if not meshes:
        print("FEHLER: Keine Mesh-Objekte gefunden.")
        sys.exit(1)

    base_obj = meshes[0]

    # 5. Mesh auf MD3-Größe skalieren
    scale_mesh_to_fit(base_obj, MD3_SAFE_LIMIT)

    vertex_groups = list(base_obj.vertex_groups.keys())
    print(f"Gefundene Vertex-Gruppen: {vertex_groups}")

    if not vertex_groups:
        print("WARNUNG: Keine Vertex-Gruppen. Exportiere gesamtes Mesh.")
        export_md3(base_obj, os.path.join(output_dir, "zombie_full.md3"))
        return

    # 6. Für jede Vertex-Gruppe exportieren
    for vg_name in vertex_groups:
        new_obj = base_obj.copy()
        new_obj.data = base_obj.data.copy()
        new_obj.name = f"zombie_{vg_name}"
        bpy.context.collection.objects.link(new_obj)

        for vg in list(new_obj.vertex_groups):
            if vg.name != vg_name:
                new_obj.vertex_groups.remove(vg)

        export_md3(new_obj, os.path.join(output_dir, f"{vg_name}.md3"))


def scale_mesh_to_fit(obj, safe_limit):
    """Skaliert die Mesh-Daten herunter, falls sie die MD3-Grenze überschreiten."""
    # Maximale Ausdehnung in einer Achse ermitteln
    dims = obj.dimensions
    max_dim = max(dims.x, dims.y, dims.z)
    print(f"Mesh-Größe (Blender-Einheiten): {dims.x:.2f} x {dims.y:.2f} x {dims.z:.2f}")

    if max_dim <= safe_limit:
        print("Mesh passt bereits in den MD3-Modellraum. Keine Skalierung nötig.")
        return

    # Skalierungsfaktor berechnen und auf die Mesh-Daten anwenden
    factor = safe_limit / max_dim
    print(f"Skaliere Mesh um Faktor {factor:.6f} auf max. {safe_limit} Einheiten.")

    for vert in obj.data.vertices:
        vert.co.x *= factor
        vert.co.y *= factor
        vert.co.z *= factor

    # Objekt-Transformation zurücksetzen, damit der Exporter die neuen Koordinaten nutzt
    obj.scale = (1.0, 1.0, 1.0)
    bpy.context.view_layer.update()
    print(f"Neue Mesh-Größe: {obj.dimensions.x:.2f} x {obj.dimensions.y:.2f} x {obj.dimensions.z:.2f}")


def export_md3(obj, filepath):
    """Exportiert ein Objekt als MD3. Blendet alle anderen Objekte aus."""
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
            print(f"FEHLER beim Export von {filepath}: {e}")

    for o in bpy.context.scene.objects:
        o.hide_set(False)


if __name__ == "__main__":
    main()
