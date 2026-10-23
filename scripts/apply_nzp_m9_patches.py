#!/usr/bin/env python3
# NZP-M9 Patches: Server-Browser Gamepad-Navigation & Performance-Optimierungen

import sys
from pathlib import Path

def patch(path: Path, anchor: str, replacement: str, description: str, marker: str, required: bool = True) -> None:
    if not path.exists():
        if required:
            print(f"[FATAL] {path} existiert nicht.")
            sys.exit(1)
        else:
            print(f"[SKIP] {description}: Datei {path} fehlt (optional).")
            return

    content = path.read_text(encoding="utf-8")
    if marker in content:
        print(f"[SKIP] {description}: bereits gepatcht")
        return

    count = content.count(anchor)
    if count == 0:
        if required:
            print(f"[FATAL] {description}: Anker NICHT gefunden in {path}")
            sys.exit(1)
        else:
            print(f"[SKIP] {description}: Anker nicht gefunden (optional, wird ignoriert)")
            return
    if count > 1:
        if required:
            print(f"[FATAL] {description}: Anker {count}× gefunden in {path}")
            sys.exit(1)
        else:
            print(f"[WARN] {description}: Anker {count}× gefunden (optional, überspringe)")
            return

    path.write_text(content.replace(anchor, replacement, 1), encoding="utf-8")
    print(f"[OK]   {description}")

def ensure_line(path: Path, line: str, description: str) -> None:
    if not path.exists():
        print(f"[FATAL] {path} existiert nicht.")
        sys.exit(1)
    content = path.read_text(encoding="utf-8")
    if line in content:
        print(f"[SKIP] {description}: bereits vorhanden")
        return
    path.write_text(content + "\n" + line + "\n", encoding="utf-8")
    print(f"[OK]   {description}")

def append_safe(path: Path, content: str, description: str, marker: str) -> None:
    if not path.exists():
        print(f"[FATAL] {path} existiert nicht.")
        sys.exit(1)
    text = path.read_text(encoding="utf-8")
    if marker in text:
        print(f"[SKIP] {description}: bereits vorhanden")
        return
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
MENU_MAIN = BASE / "main.qc"

# ==========================================
# TEIL 0: FEHLENDE DEKLARATIONEN & BUILTINS
# ==========================================

ensure_line(FTE_QC, ".float is_in_menu;", "Füge is_in_menu Feld hinzu")
ensure_line(FTE_QC, "void(string soundname, float channel, float volume) localsound_enhanced = { localsound(soundname, channel, volume); };", "Füge localsound_enhanced Wrapper hinzu")
ensure_line(FTE_QC, "void(float dest) setkeydest = #602;", "Füge setkeydest Builtin hinzu")

menu_defs_injection = """
// --- NZP-M9 Forward Declarations ---
void(float wantmode) m_toggle;
void(vector screensize, float notmenu) m_drawloading;
// -----------------------------------
"""
append_safe(MENU_DEFS, menu_defs_injection, "Füge menu_defs.qc Forward-Declarations hinzu", "NZP-M9 Forward Declarations")

menu_main_injection = """
// --- NZP-M9: Dummy-Implementierung für m_drawloading ---
void(vector screensize, float notmenu) m_drawloading = { };
// ------------------------------------------------------
"""
append_safe(MENU_MAIN, menu_main_injection, "Füge m_drawloading Definition in menu/main.qc hinzu", "NZP-M9 m_drawloading Definition")

patch(
    CLIENT_MAIN,
    anchor="float menu_active;",
    replacement="// float menu_active; (verschoben nach menu/main.qc)",
    description="Entferne doppelte menu_active Definition",
    marker="// float menu_active;",
    required=False,
)

# ==========================================
# TEIL 1: SERVER-BROWSER GAMEPAD NAVIGATION
# ==========================================

patch(
    MENU_COOP,
    anchor="int num_cached_servers;",
    replacement="int num_cached_servers;\nfloat coop_browse_selected;",
    description="A1: Variable coop_browse_selected",
    marker="float coop_browse_selected;",
)

patch(
    MENU_COOP,
    anchor="void() Menu_Coop_Browse =\n{\n\tMenu_Coop_UpdateCache();",
    replacement=(
        "void() Menu_Coop_Browse =\n"
        "{\n"
        "\tstatic float _browse_init;\n"
        "\tif (!_browse_init) {\n"
        "\t\tcoop_browse_selected = -1;\n"
        "\t\t_browse_init = true;\n"
        "\t}\n"
        "\n"
        "\tMenu_Coop_UpdateCache();\n"
        "\n"
        "\tif (coop_browse_selected < -1) coop_browse_selected = -1;\n"
        "\tif (num_cached_servers > 0 && coop_browse_selected >= num_cached_servers)\n"
        "\t\tcoop_browse_selected = num_cached_servers - 1;"
    ),
    description="A2: Menu_Coop_Browse Init + Clamp",
    marker="_browse_init",
)

NAV_BLOCK = """

// --- NZP-M9: Gamepad-Navigation für Server-Browser ---
string(string cur, float direction) Menu_Coop_Browse_Navigate =
{
	float is_in_list = (strlen(cur) >= 14 && substring(cur, 0, 14) == "cbm_serverlist");
	float is_row = (strlen(cur) > 14);

	if (direction > 0) {
		if (is_in_list) {
			if (!is_row) {
				// Auf dem Container -> Springe in die erste Zeile
				if (num_cached_servers > 0) {
					coop_browse_selected = 0;
					return "cbm_serverlistscrl0";
				}
			} else {
				// In der Liste -> Springe zur nächsten Zeile
				if (coop_browse_selected + 1 >= num_cached_servers) {
					coop_browse_selected = -1;
					return "cbm_refresh";
				}
				coop_browse_selected += 1;
				return sprintf("cbm_serverlistscrl%d", coop_browse_selected);
			}
		}
		return "";
	}
	if (direction < 0) {
		if (is_in_list && is_row) {
			// In der Liste -> Springe zur vorherigen Zeile
			if (coop_browse_selected - 1 < 0) {
				coop_browse_selected = -1;
				return "cbm_serverlist";
			}
			coop_browse_selected -= 1;
			return sprintf("cbm_serverlistscrl%d", coop_browse_selected);
		}
		return "";
	}
	return "";
};

float() Menu_Coop_Browse_EnterContainer =
{
	if (num_cached_servers <= 0) return FALSE;
	coop_browse_selected = 0;
	return TRUE;
};
"""
patch(
    MENU_COOP,
    anchor="#undef PREVBUTTON_FUNC",
    replacement="#undef PREVBUTTON_FUNC" + NAV_BLOCK,
    description="B: Navigate- + EnterContainer-Funktionen",
    marker="Menu_Coop_Browse_Navigate",
)

patch(
    SUI_SYS,
    anchor="#define printf(x, ...) print(sprintf(x, __VA_ARGS__))\n\n#endif",
    replacement=(
        "#define printf(x, ...) print(sprintf(x, __VA_ARGS__))\n"
        "\n"
        "#endif\n"
        "\n"
        "// Forward declarations: NZP-M9 Server-Browser Gamepad-Navigation\n"
        "string(string cur, float direction) Menu_Coop_Browse_Navigate;\n"
        "float() Menu_Coop_Browse_EnterContainer;"
    ),
    description="C1: Forward-Declarations in sui_sys.qc",
    marker="Forward declarations: NZP-M9",
)

patch(
    SUI_SYS,
    anchor="void() _sui_menukey_downarrow =\n{\n\tstring current_hovered_option = _hover_actions[0];\n\n\tswitch(current_menu) {",
    replacement=(
        "void() _sui_menukey_downarrow =\n"
        "{\n"
        "\tstring current_hovered_option = _hover_actions[0];\n"
        "\n"
        "\t// NZP-M9: Server-Browser Zeilen-Navigation\n"
        "\tif (current_menu == MENU_COOPBROWSE) {\n"
        "\t\tstring nav = Menu_Coop_Browse_Navigate(current_hovered_option, 1);\n"
        "\t\tif (nav != \"\") {\n"
        "\t\t\t_hover_actions[0] = nav;\n"
        "\t\t\tlast_hovered_id = \"\";\n"
        "\t\t\t_hover_action_count = 1;\n"
        "\t\t\treturn;\n"
        "\t\t}\n"
        "\t}\n"
        "\n"
        "\tswitch(current_menu) {"
    ),
    description="C2: downarrow erweitern",
    marker="string nav = Menu_Coop_Browse_Navigate(current_hovered_option, 1);",
)

patch(
    SUI_SYS,
    anchor="void() _sui_menukey_uparrow =\n{\n\tstring current_hovered_option = _hover_actions[0];\n\n\tswitch(current_menu) {",
    replacement=(
        "void() _sui_menukey_uparrow =\n"
        "{\n"
        "\tstring current_hovered_option = _hover_actions[0];\n"
        "\n"
        "\t// NZP-M9: Server-Browser Zeilen-Navigation\n"
        "\tif (current_menu == MENU_COOPBROWSE) {\n"
        "\t\tstring nav = Menu_Coop_Browse_Navigate(current_hovered_option, -1);\n"
        "\t\tif (nav != \"\") {\n"
        "\t\t\t_hover_actions[0] = nav;\n"
        "\t\t\tlast_hovered_id = \"\";\n"
        "\t\t\t_hover_action_count = 1;\n"
        "\t\t\treturn;\n"
        "\t\t}\n"
        "\t}\n"
        "\n"
        "\tswitch(current_menu) {"
    ),
    description="C3: uparrow erweitern",
    marker="string nav = Menu_Coop_Browse_Navigate(current_hovered_option, -1);",
)

patch(
    SUI_SYS,
    anchor="void() _sui_menukey_enter =\n{\n\tif (_hover_actions[0] == \"\")\n\t\t_sui_menukey_downarrow();\n\n\t_click_actions[0] =  _hover_actions[0];\n\t_click_action_count = 1;\n\t_last_clicked_action_count = 1;\n};",
    replacement=(
        "void() _sui_menukey_enter =\n"
        "{\n"
        "\tif (_hover_actions[0] == \"\")\n"
        "\t\t_sui_menukey_downarrow();\n"
        "\n"
        "\t// NZP-M9: A auf Container wählt erste Zeile\n"
        "\tif (current_menu == MENU_COOPBROWSE && _hover_actions[0] == \"cbm_serverlist\") {\n"
        "\t\tif (Menu_Coop_Browse_EnterContainer())\n"
        "\t\t\t_hover_actions[0] = \"cbm_serverlistscrl0\";\n"
        "\t}\n"
        "\n"
        "\t_click_actions[0] =  _hover_actions[0];\n"
        "\t_click_action_count = 1;\n"
        "\t_last_clicked_action_count = 1;\n"
        "};"
    ),
    description="D: enter auf Container",
    marker="NZP-M9: A auf Container wählt erste Zeile",
)

# ==========================================
# TEIL 2: VIDEO-MENÜ OPTIMIERUNGEN
# ==========================================

patch(
    MENU_VIDE,
    anchor='string menu_video_buttons[12] = {"vm_resol", "vm_fulls", "vm_shfps", "vm_maxps", "vm_vsync", "vm_fov", "vm_gamma", "vm_uwide", "vm_parts", "vm_filtr", "vm_apply", "vm_back"};',
    replacement='string menu_video_buttons[13] = {"vm_resol", "vm_fulls", "vm_shfps", "vm_maxps", "vm_vsync", "vm_fov", "vm_gamma", "vm_uwide", "vm_parts", "vm_decal", "vm_filtr", "vm_apply", "vm_back"};',
    description="E1: Button-Array um Decals erweitern",
    marker='"vm_decal", "vm_filtr"',
)

patch(
    MENU_VIDE,
    anchor='float current_particles;\nfloat current_filter;',
    replacement='float current_particles;\nfloat current_decals;\nfloat current_filter;',
    description="E2: current_decals Variable",
    marker='float current_decals;',
)

patch(
    MENU_VIDE,
    anchor='current_particles = cvar("nzp_particles");\n    current_filter =',
    replacement='current_particles = cvar("nzp_particles");\n    current_decals = cvar("nzp_decals");\n    current_filter =',
    description="E3: Decals-Wert auslesen",
    marker='current_decals = cvar("nzp_decals");',
)

patch(
    MENU_VIDE,
    anchor='void() Menu_Video_UpdateUltrawide =',
    replacement='void() Menu_Video_UpdateDecals =\n{\n    Menu_PlaySound(MENU_SND_ENTER);\n    current_decals = !current_decals;\n    cvar_set("nzp_decals", ftos(current_decals));\n};\n\nvoid() Menu_Video_UpdateUltrawide =',
    description="E4: Funktion Menu_Video_UpdateDecals",
    marker='Menu_Video_UpdateDecals',
)

patch(
    MENU_VIDE,
    anchor='// Max FPS\n    if (cvar("vid_vsync") == 0) {\n        Menu_Button(4, "vm_maxps", "MAX FPS", "Configure Maximum FPS Value.") ? 0 : 0;\n        Menu_CvarSlider(4, "vm_maxps", [10, 500, 490], "cl_maxfps", true, false, false);\n    } else {\n        Menu_GreyButton(4, "[VSYNC ON] MAX FPS");\n    }',
    replacement='// Max FPS\n    Menu_Button(4, "vm_maxps", "MAX FPS", "Configure Maximum FPS Value.") ? 0 : 0;\n    Menu_CvarSlider(4, "vm_maxps", [10, 500, 490], "cl_maxfps", true, false, false);',
    description="E5: Max FPS nicht mehr durch VSync blockieren",
    marker='Menu_CvarSlider(4, "vm_maxps", [10, 500, 490]',
)

patch(
    MENU_VIDE,
    anchor='if (cvar("vid_vsync") && ret == "vm_maxps")\n        ret = "vm_vsync";\n\n    return ret;',
    replacement='return ret;',
    description="E6: VSync-Navigations-Fix (Next)",
    marker='// Nav fix next',
)

patch(
    MENU_VIDE,
    anchor='if (cvar("vid_vsync") && ret == "vm_maxps")\n        ret = "vm_shfps";\n\n    return ret;',
    replacement='return ret;',
    description="E7: VSync-Navigations-Fix (Prev)",
    marker='// Nav fix prev',
)

patch(
    MENU_VIDE,
    anchor='// Texture Filtering\n    Menu_Button(10, "vm_filtr", "TEXTURE FILTERING", "Choose 3D Environment Filtering Mode.") ? Menu_Video_UpdateFiltering() : 0;\n    string filt_string = "";\n    if (current_filter) filt_string = "NEAREST";\n    else filt_string = "LINEAR";\n    Menu_DrawOptionValue(10, filt_string);',
    replacement='// Decals\n    Menu_Button(10, "vm_decal", "DECALS", "Toggle Bullet Holes and Blood (Saves Performance).") ? Menu_Video_UpdateDecals() : 0;\n    string decal_string = "";\n    if (current_decals) decal_string = "ENABLED";\n    else decal_string = "DISABLED";\n    Menu_DrawOptionValue(10, decal_string);\n\n    // Texture Filtering\n    Menu_Button(11, "vm_filtr", "TEXTURE FILTERING", "Choose 3D Environment Filtering Mode.") ? Menu_Video_UpdateFiltering() : 0;\n    string filt_string = "";\n    if (current_filter) filt_string = "NEAREST";\n    else filt_string = "LINEAR";\n    Menu_DrawOptionValue(11, filt_string);',
    description="E8: Decals-Button ins Menü einfügen",
    marker='Menu_Button(10, "vm_decal"',
)

print("\n=== Alle Patches erfolgreich angewendet. ===")
sys.exit(0)
