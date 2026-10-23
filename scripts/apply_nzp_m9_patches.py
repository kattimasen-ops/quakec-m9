#!/usr/bin/env python3
# NZP-M9 Patches: Server-Browser Gamepad-Navigation & Performance-Optimierungen

import sys
import re
from pathlib import Path

def patch(path: Path, anchor: str, replacement: str, description: str, marker: str, required: bool = True) -> None:
    if not path.exists(): return
    content = path.read_text(encoding="utf-8")
    if marker in content: return
    if anchor in content:
        path.write_text(content.replace(anchor, replacement, 1), encoding="utf-8")
        print(f"[OK]   {description}")

def patch_regex(path: Path, pattern: str, replacement: str, description: str, marker: str):
    if not path.exists(): sys.exit(1)
    content = path.read_text(encoding="utf-8")
    if marker in content: return
    new_content, count = re.subn(pattern, replacement, content, count=1, flags=re.DOTALL)
    if count == 1:
        path.write_text(new_content, encoding="utf-8")
        print(f"[OK]   {description}")

def ensure_line(path: Path, line: str, description: str) -> None:
    if not path.exists(): return
    content = path.read_text(encoding="utf-8")
    if line in content: return
    path.write_text(content + "\n" + line + "\n", encoding="utf-8")
    print(f"[OK]   {description}")

def append_safe(path: Path, content: str, description: str, marker: str) -> None:
    if not path.exists(): return
    text = path.read_text(encoding="utf-8")
    if marker in text: return
    path.write_text(text + "\n" + content, encoding="utf-8")
    print(f"[OK]   {description}")

BASE = Path("source/menu")
CLIENT = Path("source/client")
MENU_COOP = BASE / "menu_coop.qc"
SUI_SYS   = BASE / "sui_sys.qc"
MENU_VIDE = BASE / "menu_vide.qc"
CLIENT_MAIN = CLIENT / "main.qc"
FTE_QC = CLIENT / "defs/fte.qc"
MENU_DEFS = BASE / "defs/menu_defs.qc"
MENU_CRED = BASE / "menu_cred.qc"

# Teil 0: Basis
if MENU_DEFS.exists():
    content = MENU_DEFS.read_text(encoding="utf-8")
    content = content.replace("void() Menu_DrawMapPreview = { };", "").replace("float last_input_deviceid;", "").replace("void(float wantmode) m_toggle;", "")
    MENU_DEFS.write_text(content, encoding="utf-8")

ensure_line(FTE_QC, ".float is_in_menu;", "Füge is_in_menu hinzu")
ensure_line(FTE_QC, "void(string soundname, float channel, float volume) localsound_enhanced = { localsound(soundname, channel, volume); };", "Füge localsound_enhanced hinzu")
ensure_line(FTE_QC, "void(float dest) setkeydest = #602;", "Füge setkeydest hinzu")
ensure_line(MENU_DEFS, "float last_input_deviceid;", "Füge last_input_deviceid hinzu")
ensure_line(MENU_DEFS, "void(float wantmode) m_toggle;", "Füge m_toggle hinzu")

append_safe(MENU_DEFS, "\n#ifndef MENU\nvoid() Menu_DrawMapPreview = { };\n#endif\n", "Dummy Menu_DrawMapPreview", "void() Menu_DrawMapPreview = { };")
patch(CLIENT_MAIN, "float menu_active;", "// float menu_active;", "Entferne menu_active", "// float menu_active;", required=False)
MENU_CRED.write_text("void() Menu_Credits = { Menu_DrawBackground(); Menu_DrawTitle(\"CREDITS\"); sui_text([150,100], MENU_TEXT_MEDIUM, \"Disabled.\", [1,1,1], 1, 0); Menu_Button(-1, \"cr_back\", \"BACK\", \"\") ? current_menu = MENU_MAIN : 0; sui_pop_frame(); };\n", encoding="utf-8")

# Teil 1: Server-Browser
patch(MENU_COOP, "int num_cached_servers;", "int num_cached_servers;\nfloat coop_browse_selected;", "coop_browse_selected", "float coop_browse_selected;")
patch(MENU_COOP, "void() Menu_Coop_Browse =\n{\n\tMenu_Coop_UpdateCache();", "void() Menu_Coop_Browse =\n{\n\tstatic float _b;\n\tif (!_b) { coop_browse_selected = -1; _b = true; }\n\tMenu_Coop_UpdateCache();\n\tif (coop_browse_selected < -1) coop_browse_selected = -1;\n\tif (num_cached_servers > 0 && coop_browse_selected >= num_cached_servers) coop_browse_selected = num_cached_servers - 1;", "Browse Init", "_b")

NAV = "\nstring(string cur, float dir) Menu_Coop_Browse_Navigate = {\n\tfloat in_l = (strlen(cur) >= 14 && substring(cur, 0, 14) == \"cbm_serverlist\");\n\tfloat is_r = (strlen(cur) > 14);\n\tif (dir > 0) {\n\t\tif (in_l) {\n\t\t\tif (!is_r) { if (num_cached_servers > 0) { coop_browse_selected = 0; return \"cbm_serverlistscrl0\"; } }\n\t\t\telse { if (coop_browse_selected + 1 >= num_cached_servers) { coop_browse_selected = -1; return \"cbm_refresh\"; } coop_browse_selected += 1; return sprintf(\"cbm_serverlistscrl%d\", coop_browse_selected); }\n\t\t}\n\t\treturn \"\";\n\t}\n\tif (dir < 0) {\n\t\tif (in_l && is_r) {\n\t\t\tif (coop_browse_selected - 1 < 0) { coop_browse_selected = -1; return \"cbm_serverlist\"; }\n\t\t\tcoop_browse_selected -= 1; return sprintf(\"cbm_serverlistscrl%d\", coop_browse_selected);\n\t\t}\n\t\treturn \"\";\n\t}\n\treturn \"\";\n}\nfloat() Menu_Coop_Browse_EnterContainer = { if (num_cached_servers <= 0) return FALSE; coop_browse_selected = 0; return TRUE; };\n"
patch(MENU_COOP, "#undef PREVBUTTON_FUNC", "#undef PREVBUTTON_FUNC" + NAV, "Navigate Funcs", "Menu_Coop_Browse_Navigate")

patch(SUI_SYS, "#define printf(x, ...) print(sprintf(x, __VA_ARGS__))\n\n#endif", "#define printf(x, ...) print(sprintf(x, __VA_ARGS__))\n\n#endif\n\nstring(string cur, float direction) Menu_Coop_Browse_Navigate;\nfloat() Menu_Coop_Browse_EnterContainer;\n", "Forward Decls", "Menu_Coop_Browse_Navigate;")
patch(SUI_SYS, "void() _sui_menukey_downarrow =\n{\n\tstring current_hovered_option = _hover_actions[0];\n\n\tswitch(current_menu) {", "void() _sui_menukey_downarrow =\n{\n\tstring current_hovered_option = _hover_actions[0];\n\tif (current_menu == MENU_COOPBROWSE) { string nav = Menu_Coop_Browse_Navigate(current_hovered_option, 1); if (nav != \"\") { _hover_actions[0] = nav; last_hovered_id = \"\"; _hover_action_count = 1; return; } }\n\tswitch(current_menu) {", "Down arrow", "Menu_Coop_Browse_Navigate(current_hovered_option, 1)")
patch(SUI_SYS, "void() _sui_menukey_uparrow =\n{\n\tstring current_hovered_option = _hover_actions[0];\n\n\tswitch(current_menu) {", "void() _sui_menukey_uparrow =\n{\n\tstring current_hovered_option = _hover_actions[0];\n\tif (current_menu == MENU_COOPBROWSE) { string nav = Menu_Coop_Browse_Navigate(current_hovered_option, -1); if (nav != \"\") { _hover_actions[0] = nav; last_hovered_id = \"\"; _hover_action_count = 1; return; } }\n\tswitch(current_menu) {", "Up arrow", "Menu_Coop_Browse_Navigate(current_hovered_option, -1)")
patch(SUI_SYS, "void() _sui_menukey_enter =\n{\n\tif (_hover_actions[0] == \"\")\n\t\t_sui_menukey_downarrow();\n\n\t_click_actions[0] =  _hover_actions[0];\n\t_click_action_count = 1;\n\t_last_clicked_action_count = 1;\n};", "void() _sui_menukey_enter =\n{\n\tif (_hover_actions[0] == \"\") _sui_menukey_downarrow();\n\tif (current_menu == MENU_COOPBROWSE && _hover_actions[0] == \"cbm_serverlist\") { if (Menu_Coop_Browse_EnterContainer()) _hover_actions[0] = \"cbm_serverlistscrl0\"; }\n\t_click_actions[0] = _hover_actions[0]; _click_action_count = 1; _last_clicked_action_count = 1;\n};", "Enter key", "Menu_Coop_Browse_EnterContainer())")

# Teil 2: Video-Menü
patch_regex(MENU_VIDE, r"string menu_video_buttons\[\d+\] = \{.*?\};", 'string menu_video_buttons[15] = {"vm_resol", "vm_fulls", "vm_shfps", "vm_maxps", "vm_vsync", "vm_fov", "vm_gamma", "vm_uwide", "vm_parts", "vm_decal", "vm_dynlgt", "vm_shdw", "vm_filtr", "vm_apply", "vm_back"};', "Buttons Array", '"vm_dynlgt", "vm_shdw"')

# NEU: Wir prüfen JEDE Variable einzeln!
if "float current_decals;" not in MENU_VIDE.read_text(encoding="utf-8"):
    patch(MENU_VIDE, "float current_filter;", "float current_decals;\nfloat current_filter;", "current_decals Variable", "float current_decals;")
if "float current_dynlight;" not in MENU_VIDE.read_text(encoding="utf-8"):
    patch(MENU_VIDE, "float current_filter;", "float current_dynlight;\nfloat current_filter;", "current_dynlight Variable", "float current_dynlight;")
if "float current_shadows;" not in MENU_VIDE.read_text(encoding="utf-8"):
    patch(MENU_VIDE, "float current_filter;", "float current_shadows;\nfloat current_filter;", "current_shadows Variable", "float current_shadows;")

# Werte beim Öffnen auslesen
if 'current_decals = cvar("nzp_decals");' not in MENU_VIDE.read_text(encoding="utf-8"):
    patch(MENU_VIDE, 'current_filter =', 'current_decals = cvar("nzp_decals");\n    current_filter =', "decals read", 'current_decals = cvar("nzp_decals");')
if 'current_dynlight = cvar("r_dynamic");' not in MENU_VIDE.read_text(encoding="utf-8"):
    patch(MENU_VIDE, 'current_filter =', 'current_dynlight = cvar("r_dynamic");\n    current_shadows = cvar("r_shadows");\n    current_filter =', "dynlight read", 'current_dynlight = cvar("r_dynamic");')

patch_regex(MENU_VIDE, r"void\(\) Menu_Video_UpdateUltrawide =", "void() Menu_Video_UpdateDecals = { Menu_PlaySound(MENU_SND_ENTER); current_decals = !current_decals; cvar_set(\"nzp_decals\", ftos(current_decals)); };\nvoid() Menu_Video_UpdateDynLight = { Menu_PlaySound(MENU_SND_ENTER); current_dynlight = !current_dynlight; cvar_set(\"r_dynamic\", ftos(current_dynlight)); };\nvoid() Menu_Video_UpdateShadows = { Menu_PlaySound(MENU_SND_ENTER); current_shadows = !current_shadows; cvar_set(\"r_shadows\", ftos(current_shadows)); };\nvoid() Menu_Video_UpdateUltrawide =", "Update Functions", "Menu_Video_UpdateDynLight")

patch_regex(MENU_VIDE, r"// Dynamic Lights\s*Menu_Button\(\d+, \"vm_dynlgt\".*?Menu_DrawOptionValue\(\d+, filt_string\);", "// Decals\n    Menu_Button(10, \"vm_decal\", \"DECALS\", \"Toggle Bullet Holes and Blood.\") ? Menu_Video_UpdateDecals() : 0;\n    Menu_DrawOptionValue(10, current_decals ? \"ENABLED\" : \"DISABLED\");\n\n    // Dynamic Lights\n    Menu_Button(11, \"vm_dynlgt\", \"DYNAMIC LIGHTS\", \"Toggle Realtime Lights.\") ? Menu_Video_UpdateDynLight() : 0;\n    Menu_DrawOptionValue(11, current_dynlight ? \"ENABLED\" : \"DISABLED\");\n\n    // Shadows\n    Menu_Button(12, \"vm_shdw\", \"SHADOWS\", \"Toggle Entity Shadows.\") ? Menu_Video_UpdateShadows() : 0;\n    Menu_DrawOptionValue(12, current_shadows ? \"ENABLED\" : \"DISABLED\");\n\n    // Texture Filtering\n    Menu_Button(13, \"vm_filtr\", \"TEXTURE FILTERING\", \"Choose Filtering Mode.\") ? Menu_Video_UpdateFiltering() : 0;\n    Menu_DrawOptionValue(13, current_filter ? \"NEAREST\" : \"LINEAR\");", "UI block", 'vm_decal", "DECALS')

patch_regex(MENU_VIDE, r"Menu_DrawDivider\([-\d.]+\);", "Menu_DrawDivider(13.25);", "divider", "Menu_DrawDivider(13.25);")
patch_regex(MENU_VIDE, r'Menu_Button\([-\d.]+, "vm_apply"', 'Menu_Button(14.5, "vm_apply"', "apply pos", 'Menu_Button(14.5, "vm_apply"')
patch_regex(MENU_VIDE, r'Menu_Button\([-\d.]+, "vm_back"', 'Menu_Button(15.5, "vm_back"', "back pos", 'Menu_Button(15.5, "vm_back"')

print("\n=== Alle Patches erfolgreich angewendet. ===")
