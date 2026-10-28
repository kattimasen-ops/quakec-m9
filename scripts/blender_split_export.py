import bpy
import sys
import os

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
    vertex_groups = list(base_obj.vertex_groups.keys())
    print(f"Gefundene Vertex-Gruppen: {vertex_groups}")

    if not vertex_groups:
        print("WARNUNG: Keine Vertex-Gruppen. Exportiere gesamtes Mesh.")
        export_md3(base_obj, os.path.join(output_dir, "zombie_full.md3"))
        return

    # 5. Für jede Vertex-Gruppe exportieren
    for vg_name in vertex_groups:
        new_obj = base_obj.copy()
        new_obj.data = base_obj.data.copy()
        new_obj.name = f"zombie_{vg_name}"
        bpy.context.collection.objects.link(new_obj)

        for vg in list(new_obj.vertex_groups):
            if vg.name != vg_name:
                new_obj.vertex_groups.remove(vg)

        export_md3(new_obj, os.path.join(output_dir, f"{vg_name}.md3"))


def export_md3(obj, filepath):
    """Exportiert ein Objekt als MD3. Blendet alle anderen Objekte aus."""
    # Alle Objekte unsichtbar machen
    for o in bpy.context.scene.objects:
        o.hide_set(True)

    # Nur das Zielobjekt sichtbar machen
    obj.hide_set(False)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    # Korrekter Operator: export_scene.md3 (nicht id3_md3)
    with bpy.context.temp_override(active_object=obj, selected_objects=[obj]):
        try:
            bpy.ops.export_scene.md3(
                filepath=filepath,
                enable_convert=False,      # Original-Skalierung beibehalten
                adjust_scale_bug=False     # Keine 1.016-Korrektur
            )
            print(f"OK: {filepath} exportiert.")
        except Exception as e:
            print(f"FEHLER beim Export von {filepath}: {e}")

    # Sichtbarkeit wiederherstellen
    for o in bpy.context.scene.objects:
        o.hide_set(False)


if __name__ == "__main__":
    main()
