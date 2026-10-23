#!/usr/bin/env python3
# NZP-M9 Patches: Server-Browser, Performance & Custom Handheld Edits

import sys
import re
from pathlib import Path

def patch(path: Path, anchor: str, replacement: str, description: str, marker: str) -> None:
    if not path.exists(): return
    content = path.read_text(encoding="utf-8")
    if marker in content: return
    if anchor in content:
        path.write_text(content.replace(anchor, replacement, 1), encoding="utf-8")
        print(f"[OK]   {description}")

def patch_regex(path: Path, pattern: str, replacement: str, description: str, marker: str):
    if not path.exists(): sys.exit(1)
    content = path.read_text(encoding="utf-8")
    if marker in content:
        print(f"[SKIP] {description}: bereits gepatcht")
        return
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
MENU_MAIN_MENU = BASE / "m_menu.qc"
MAIN_QC = BASE / "main.qc"
CLIENT_MAIN = CLIENT / "main.qc"
FTE_QC = CLIENT / "defs/fte.qc"
MENU_DEFS = BASE / "defs/menu_defs.qc"
MENU_CRED = BASE / "menu_cred.qc"

# ==========================================
# TEIL 0: AUFRÄUMEN & BASIS
# ==========================================

# 1. menu_defs.qc bereinigen
if MENU_DEFS.exists():
    content = MENU_DEFS.read_text(encoding="utf-8")
    content = content.replace("void() Menu_DrawMapPreview = { };", "")
    content = content.replace("float last_input_deviceid;", "")
    content = content.replace("void(float wantmode) m_toggle;", "")
    MENU_DEFS.write_text(content, encoding="utf-8")

ensure_line(FTE_QC, ".float is_in_menu;", "Füge is_in_menu Feld hinzu")
ensure_line(FTE_QC, "void(string soundname, float channel, float volume) localsound_enhanced = { localsound(soundname, channel, volume); };", "Füge localsound_enhanced Wrapper hinzu")
ensure_line(FTE_QC, "void(float dest) setkeydest = #602;", "Füge setkeydest Builtin hinzu")

ensure_line(MENU_DEFS, "float last_input_deviceid;", "Füge last_input_deviceid hinzu")
ensure_line(MENU_DEFS, "void(float wantmode) m_toggle;", "Füge m_toggle Deklaration hinzu")

append_safe(MENU_DEFS, "\n#ifndef MENU\nvoid() Menu_DrawMapPreview = { };\n#endif\n", "Füge menu_defs.qc Dummy hinzu", "void() Menu_DrawMapPreview = { };")

patch(CLIENT_MAIN, "float menu_active;", "// float menu_active;", "Entferne doppelte menu_active Definition", "// float menu_active;")

MENU_CRED.write_text("void() Menu_Credits = { Menu_DrawBackground(); Menu_DrawTitle(\"CREDITS\"); Menu_DrawMapPanel(); sui_text([150, 100], MENU_TEXT_MEDIUM, \"Credits are currently disabled in this build.\", [1, 1, 1], 1, 0); Menu_Button(-1, \"cr_back\", \"BACK\", \"Return to Main Menu.\") ? current_menu = MENU_MAIN : 0; sui_pop_frame(); };", encoding="utf-8")

# ==========================================
# TEIL 1: SERVER-BROWSER GAMEPAD NAVIGATION
# ==========================================

patch(MENU_COOP, "int num_cached_servers;", "int num_cached_servers;\nfloat coop_browse_selected;", "A1: Variable coop_browse_selected", "float coop_browse_selected;")
patch(MENU_COOP, "void() Menu_Coop_Browse =\n{\n\tMenu_Coop_UpdateCache();", 
      "void() Menu_Coop_Browse =\n{\n\tstatic float _browse_init;\n\tif (!_browse_init) {\n\t\tcoop_browse_selected = -1;\n\t\t_browse_init = true;\n\t}\n\tMenu_Coop_UpdateCache();\n\tif (coop_browse_selected < -1) coop_browse_selected = -1;\n\tif (num_cached_servers > 0 && coop_browse_selected >= num_cached_servers)\n\t\tcoop_browse_selected = num_cached_servers - 1;",
      "A2: Menu_Coop_Browse Init + Clamp", "_browse_init")

NAV_BLOCK = """
string(string cur, float direction) Menu_Coop_Browse_Navigate =
{
	float is_in_list = (strlen(cur) >= 14 && substring(cur, 0, 14) == "cbm_serverlist");
	float is_row = (strlen(cur) > 14);
	if (direction > 0) {
		if (is_in_list) {
			if (!is_row) {
				if (num_cached_servers > 0) { coop_browse_selected = 0; return "cbm_serverlistscrl0"; }
			} else {
				if (coop_browse_selected + 1 >= num_cached_servers) { coop_browse_selected = -1; return "cbm_refresh"; }
				coop_browse_selected += 1;
				return sprintf("cbm_serverlistscrl%d", coop_browse_selected);
			}
		}
		return "";
	}
	if (direction < 0) {
		if (is_in_list && is_row) {
			if (coop_browse_selected - 1 < 0) { coop_browse_selected = -1; return "cbm_serverlist"; }
			coop_browse_selected -= 1;
			return sprintf("cbm_serverlistscrl%d", coop_browse_selected);
		}
		return "";
	}
	return "";
}
float() Menu_Coop_Browse_EnterContainer = { if (num_cached_servers <= 0) return FALSE; coop_browse_selected = 0; return TRUE; };
"""
patch(MENU_COOP, "#undef PREVBUTTON_FUNC", "#undef PREVBUTTON_FUNC" + NAV_BLOCK, "B: Navigate- + EnterContainer-Funktionen", "Menu_Coop_Browse_Navigate")

patch(SUI_SYS, "#define printf(x, ...) print(sprintf(x, __VA_ARGS__))\n\n#endif",
      "#define printf(x, ...) print(sprintf(x, __VA_ARGS__))\n\n#endif\n\nstring(string cur, float direction) Menu_Coop_Browse_Navigate;\nfloat() Menu_Coop_Browse_EnterContainer;",
      "C1: Forward-Declarations in sui_sys.qc", "Menu_Coop_Browse_Navigate;")

patch(SUI_SYS, "void() _sui_menukey_downarrow =\n{\n\tstring current_hovered_option = _hover_actions[0];\n\n\tswitch(current_menu) {",
      "void() _sui_menukey_downarrow =\n{\n\tstring current_hovered_option = _hover_actions[0];\n\tif (current_menu == MENU_COOPBROWSE) {\n\t\tstring nav = Menu_Coop_Browse_Navigate(current_hovered_option, 1);\n\t\tif (nav != \"\") { _hover_actions[0] = nav; last_hovered_id = \"\"; _hover_action_count = 1; return; }\n\t}\n\tswitch(current_menu) {",
      "C2: downarrow erweitern", "Menu_Coop_Browse_Navigate(current_hovered_option, 1)")
patch(SUI_SYS, "void() _sui_menukey_uparrow =\n{\n\tstring current_hovered_option = _hover_actions[0];\n\n\tswitch(current_menu) {",
      "void() _sui_menukey_uparrow =\n{\n\tstring current_hovered_option = _hover_actions[0];\n\tif (current_menu == MENU_COOPBROWSE) {\n\t\tstring nav = Menu_Coop_Browse_Navigate(current_hovered_option, -1);\n\t\tif (nav != \"\") { _hover_actions[0] = nav; last_hovered_id = \"\"; _hover_action_count = 1; return; }\n\t}\n\tswitch(current_menu) {",
      "C3: uparrow erweitern", "Menu_Coop_Browse_Navigate(current_hovered_option, -1)")
patch(SUI_SYS, "void() _sui_menukey_enter =\n{\n\tif (_hover_actions[0] == \"\")\n\t\t_sui_menukey_downarrow();\n\n\t_click_actions[0] =  _hover_actions[0];\n\t_click_action_count = 1;\n\t_last_clicked_action_count = 1;\n};",
      "void() _sui_menukey_enter =\n{\n\tif (_hover_actions[0] == \"\") _sui_menukey_downarrow();\n\tif (current_menu == MENU_COOPBROWSE && _hover_actions[0] == \"cbm_serverlist\") {\n\t\tif (Menu_Coop_Browse_EnterContainer()) _hover_actions[0] = \"cbm_serverlistscrl0\";\n\t}\n\t_click_actions[0] = _hover_actions[0]; _click_action_count = 1; _last_clicked_action_count = 1;\n};",
      "D: enter auf Container", "Menu_Coop_Browse_EnterContainer())")

# ==========================================
# TEIL 2: VIDEO-MENÜ & CUSTOM OPTIONEN (Reset & Rebuild)
# ==========================================

# 1. Button-Array (16 Buttons)
patch_regex(
    MENU_VIDE,
    r"string menu_video_buttons\[\d+\] = \{.*?\};",
    'string menu_video_buttons[16] = {"vm_resol", "vm_fulls", "vm_shfps", "vm_maxps", "vm_vsync", "vm_fov", "vm_gamma", "vm_uwide", "vm_parts", "vm_decal", "vm_dynlgt", "vm_shdw", "vm_bob", "vm_filtr", "vm_apply", "vm_back"};',
    "E1: Button-Array erweitern", '"vm_bob"'
)

# 2. Variablen sauber einfügen (vor StoreCurrentSettings)
menu_vide_content = MENU_VIDE.read_text(encoding="utf-8")
# Alle alten current_bla Zeilen löschen, um Dopplungen zu vermeiden
menu_vide_content = re.sub(r"^float current_(decals|dynlight|shadows|bob|aimassist);\s*$", "", menu_vide_content, flags=re.MULTILINE)

# Die neuen Variablen sauber vor der Funktion einfügen
if "float current_decals;" not in menu_vide_content:
    menu_vide_content = menu_vide_content.replace(
        "void() Menu_Video_StoreCurrentSettings =",
        "float current_decals;\nfloat current_dynlight;\nfloat current_shadows;\nfloat current_bob;\n\nvoid() Menu_Video_StoreCurrentSettings ="
    )
MENU_VIDE.write_text(menu_vide_content, encoding="utf-8")
print("[OK]   Variablen sauber deklariert")

# 3. Werte beim Öffnen auslesen
patch_regex(
    MENU_VIDE,
    r"void\(\) Menu_Video_StoreCurrentSettings =\s*\{(.*?)\}",
    '''void() Menu_Video_StoreCurrentSettings =
{
    current_fullscreen = cvar("vid_fullscreen");
    current_showfps = cvar("show_fps");
    current_vsync = cvar("vid_vsync");
    current_ultrawide = cvar("vid_ultrawide_limiter");
    current_particles = cvar("nzp_particles");
    current_decals = cvar("nzp_decals");
    current_dynlight = cvar("r_dynamic");
    current_shadows = cvar("r_shadows");
    current_bob = (cvar("cl_bobup") > 0);
    current_filter = (substring(strtoupper(cvar_string("gl_texturemode")), 0, 10) == "GL_NEAREST");
}''',
    "E3: StoreCurrentSettings reparieren",
    'current_bob = (cvar("cl_bobup") > 0);'
)

# 4. Update-Funktionen
patch_regex(
    MENU_VIDE,
    r"void\(\) Menu_Video_UpdateUltrawide =",
    '''void() Menu_Video_UpdateDecals = { Menu_PlaySound(MENU_SND_ENTER); current_decals = !current_decals; cvar_set("nzp_decals", ftos(current_decals)); };
void() Menu_Video_UpdateDynLight = { Menu_PlaySound(MENU_SND_ENTER); current_dynlight = !current_dynlight; cvar_set("r_dynamic", ftos(current_dynlight)); };
void() Menu_Video_UpdateShadows = { Menu_PlaySound(MENU_SND_ENTER); current_shadows = !current_shadows; cvar_set("r_shadows", ftos(current_shadows)); };
void() Menu_Video_UpdateBob = { Menu_PlaySound(MENU_SND_ENTER); current_bob = !current_bob; cvar_set("cl_bobup", current_bob ? "0.02" : "0"); cvar_set("cl_bobside", current_bob ? "0.02" : "0"); };
void() Menu_Video_UpdateUltrawide =''',
    "E4: Update-Funktionen", "Menu_Video_UpdateBob"
)

# 5. UI-Code anpassen
patch_regex(
    MENU_VIDE,
    r"// Decals.*?Menu_DrawOptionValue\(\d+, filt_string\);",
    '''// Decals
    Menu_Button(10, "vm_decal", "DECALS", "Toggle Blood/Bullet Holes.") ? Menu_Video_UpdateDecals() : 0;
    Menu_DrawOptionValue(10, current_decals ? "ENABLED" : "DISABLED");

    // Dynamic Lights
    Menu_Button(11, "vm_dynlgt", "DYNAMIC LIGHTS", "Toggle Realtime Lights.") ? Menu_Video_UpdateDynLight() : 0;
    Menu_DrawOptionValue(11, current_dynlight ? "ENABLED" : "DISABLED");

    // Shadows
    Menu_Button(12, "vm_shdw", "SHADOWS", "Toggle Entity Shadows.") ? Menu_Video_UpdateShadows() : 0;
    Menu_DrawOptionValue(12, current_shadows ? "ENABLED" : "DISABLED");

    // Weapon Bob
    Menu_Button(13, "vm_bob", "WEAPON BOB", "Toggle Weapon Swaying.") ? Menu_Video_UpdateBob() : 0;
    Menu_DrawOptionValue(13, current_bob ? "ENABLED" : "DISABLED");

    // Texture Filtering
    Menu_Button(14, "vm_filtr", "TEXTURE FILTERING", "Choose Filter Mode.") ? Menu_Video_UpdateFiltering() : 0;
    Menu_DrawOptionValue(14, current_filter ? "NEAREST" : "LINEAR");''',
    "E5: UI-Code einfügen", 'vm_bob", "WEAPON BOB'
)

# Buttons nach unten schieben
patch_regex(MENU_VIDE, r"Menu_DrawDivider\([-\d.]+\);", "Menu_DrawDivider(14.25);", "E6: Divider", "14.25")
patch_regex(MENU_VIDE, r'Menu_Button\([-\d.]+, "vm_apply"', 'Menu_Button(15.5, "vm_apply"', "E7: APPLY", '15.5')
patch_regex(MENU_VIDE, r'Menu_Button\([-\d.]+, "vm_back"', 'Menu_Button(16.5, "vm_back"', "E8: BACK", '16.5')

# ==========================================
# TEIL 3: CUSTOM HANDHELD EDITS (Lila & Version)
# ==========================================

# 1. Lila Farben für Menü-Highlights (statt Rot)
content = MENU_MAIN_MENU.read_text(encoding="utf-8")
content = content.replace("is_hovered ? [1, 0, 0] : [1, 1, 1]", "is_hovered ? [0.8, 0.2, 1] : [1, 1, 1]") 
content = content.replace("[0.4, 0, 0]", "[0.6, 0, 0.8]") 
MENU_MAIN_MENU.write_text(content, encoding="utf-8")
print("[OK]   Menü-Farben auf Lila geändert")

# 2. Versionstext im Hauptmenü ändern
patch(
    MAIN_QC,
    'build_datetime = fgets(file);',
    'build_datetime = "M9 Pro Custom Build";\n        // build_datetime = fgets(file);',
    "Custom Version String im Menü",
    "M9 Pro Custom Build"
)

print("\n=== Alle Patches erfolgreich angewendet. ===")
sys.exit(0)
