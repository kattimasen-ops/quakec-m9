import bpy
import sys
import os

def main():
    # Argumente nach dem "--" entgegennehmen
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    output_dir = argv[0] if argv else "/workspace/output_models"
    os.makedirs(output_dir, exist_ok=True)

    # 1. Alle Mesh-Objekte in der Szene finden
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    if not meshes:
        print("FEHLER: Keine Mesh-Objekte in der .blend-Datei gefunden.")
        sys.exit(1)

    # Das erste Mesh als Basis nehmen
    base_obj = meshes[0]
    vertex_groups = list(base_obj.vertex_groups.keys())
    print(f"Gefundene Vertex-Gruppen: {vertex_groups}")

    if not vertex_groups:
        # Fallback: Das gesamte Mesh als ein MD3 exportieren
        print("WARNUNG: Keine Vertex-Gruppen gefunden. Exportiere als Ganzes.")
        export_md3(base_obj, os.path.join(output_dir, "zombie_full.md3"))
        return

    # 2. Für jede Vertex-Gruppe ein separates Objekt erstellen und exportieren
    for vg_name in vertex_groups:
        # Dupliziere das Basis-Objekt
        new_obj = base_obj.copy()
        new_obj.data = base_obj.data.copy()
        new_obj.name = f"zombie_{vg_name}"
        bpy.context.collection.objects.link(new_obj)

        # Entferne alle anderen Vertex-Gruppen (behalte nur die aktuelle)
        for vg in list(new_obj.vertex_groups):
            if vg.name != vg_name:
                new_obj.vertex_groups.remove(vg)

        # Exportiere das neue Objekt als MD3
        export_md3(new_obj, os.path.join(output_dir, f"{vg_name}.md3"))


def export_md3(obj, filepath):
    """Exportiert ein einzelnes Objekt als MD3-Datei."""
    # Deselektiere alles, wähle nur das Zielobjekt aus
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    # Der MD3-Exporter von neumond/blender-md3 heißt 'export_scene.id3_md3'
    try:
        bpy.ops.export_scene.id3_md3(
            filepath=filepath,
            preset="MATERIALS",
            only_selected=True,
            limits="STUPID",
            start_frame=0,
            end_frame=0,
            individual=False
        )
        print(f"OK: {filepath} exportiert.")
    except Exception as e:
        print(f"FEHLER beim Export von {filepath}: {e}")


if __name__ == "__main__":
    main()
