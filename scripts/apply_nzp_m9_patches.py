#!/usr/bin/env python3
# NZP-M9 Patches: Server-Browser Gamepad-Navigation & Performance-Optimierungen

import sys
import re
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

def patch_regex(path: Path, pattern: str, replacement: str, description: str, marker: str):
    if not path.exists():
        print(f"[FATAL] {path} existiert nicht.")
        sys.exit(1)
    content = path.read_text(encoding="utf-8")
    if marker in content:
        print(f"[SKIP] {description}: bereits gepatcht")
        return
    new_content, count = re.subn(pattern, replacement, content, count=1, flags=re.DOTALL)
    if count == 1:
        path.write_text(new_content, encoding="utf-8")
        print(f"[OK]   {description}")
    else:
        print(f"[FATAL] {description}: Regex-Muster nicht gefunden in {path}")
        sys.exit(1)

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
MENU_CRED = BASE / "menu_cred.qc"

# ==========================================
# TEIL 0: FEHLENDE DEKLARATIONEN & BUILTINS
# ==========================================

if MENU_DEFS.exists():
    content = MENU_DEFS.read_text(encoding="utf-8")
    content = content.replace("void() Menu_DrawMapPreview = { };", "")
    content = content.replace("float last_input_deviceid;", "")
    content = content.replace("void(float wantmode) m_toggle;", "")
    content = content.replace("// --- NZP-M9 Forward Declarations & Missing Variables ---", "")
    content = content.replace("// -----------------------------------------------------", "")
    MENU_DEFS.write_text(content, encoding="utf-8")

ensure_line(FTE_QC, ".float is_in_menu;", "Füge is_in_menu Feld hinzu")
ensure_line(FTE_QC, "void(string soundname, float channel, float volume) localsound_enhanced = { localsound(soundname, channel, volume); };", "Füge localsound_enhanced Wrapper hinzu")
ensure_line(FTE_QC, "void(float dest) setkeydest = #602;", "Füge setkeydest Builtin hinzu")

ensure_line(MENU_DEFS, "float last_input_deviceid;", "Füge last_input_deviceid hinzu")
ensure_line(MENU_DEFS, "void(float wantmode) m_toggle;", "Füge m_toggle Deklaration hinzu")

menu_defs_injection = """
#ifndef MENU
// --- NZP-M9 Dummy für fehlende m_menu.qc Funktion ---
void() Menu_DrawMapPreview = { };
// ---------------------------------------------------
#endif
"""
append_safe(MENU_DEFS, menu_defs_injection, "Füge menu_defs.qc Dummy für Menu_DrawMapPreview hinzu", "NZP-M9 Dummy für fehlende")

patch(
    CLIENT_MAIN,
    anchor="float menu_active;",
    replacement="// float menu_active; (verschoben nach menu/main.qc)",
    description="Entferne doppelte menu_active Definition",
    marker="// float menu_active;",
    required=False,
)

cred_safe = """
void() Menu_Credits =
{
    Menu_DrawBackground();
    Menu_DrawTitle("CREDITS");
    Menu_DrawMapPanel();
    sui_text([150, 100], MENU_TEXT_MEDIUM, "Credits are currently disabled in this build.", [1, 1, 1], 1, 0);
    Menu_Button(-1, "cr_back", "BACK", "Return to Main Menu.") ? current_menu = MENU_MAIN : 0;
    sui_pop_frame();
};
"""
MENU_CRED.write_text(cred_safe, encoding="utf-8")
print("[OK]   menu_cred.qc durch sichere Version ersetzt")

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
				if (num_cached_servers > 0) {
					coop_browse_selected = 0;
					return "cbm_serverlistscrl0";
				}
			} else {
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
# TEIL 2: VIDEO-MENÜ OPTIMIERUNGEN (REGEX FÜR SICHERHEIT)
# ==========================================

patch_regex(
    MENU_VIDE,
    r"string menu_video_buttons\[\d+\] = \{.*?\};",
    'string menu_video_buttons[15] = {"vm_resol", "vm_fulls", "vm_shfps", "vm_maxps", "vm_vsync", "vm_fov", "vm_gamma", "vm_uwide", "vm_parts", "vm_decal", "vm_dynlgt", "vm_shdw", "vm_filtr", "vm_apply", "vm_back"};',
    "E1: Button-Array erweitern",
    '"vm_dynlgt", "vm_shdw"'
)

patch_regex(
    MENU_VIDE,
    r"float current_particles;\s*float current_decals;\s*float current_filter;",
    "float current_particles;\nfloat current_decals;\nfloat current_dynlight;\nfloat current_shadows;\nfloat current_filter;",
    "E2: current_dynlight & current_shadows Variablen",
    'float current_dynlight;'
)

patch_regex(
    MENU_VIDE,
    r"current_particles = cvar\(\"nzp_particles\"\);\s*current_decals = cvar\(\"nzp_decals\"\);\s*current_filter =",
    'current_particles = cvar("nzp_particles");\n    current_decals = cvar("nzp_decals");\n    current_dynlight = cvar("r_dynamic");\n    current_shadows = cvar("r_shadows");\n    current_filter =',
    "E3: Dynamic Lights & Shadows auslesen",
    'current_dynlight = cvar("r_dynamic");'
)

patch_regex(
    MENU_VIDE,
    r"void\(\) Menu_Video_UpdateUltrawide =",
    '''void() Menu_Video_UpdateDynLight =
{
    Menu_PlaySound(MENU_SND_ENTER);
    current_dynlight = !current_dynlight;
    cvar_set("r_dynamic", ftos(current_dynlight));
};

void() Menu_Video_UpdateShadows =
{
    Menu_PlaySound(MENU_SND_ENTER);
    current_shadows = !current_shadows;
    cvar_set("r_shadows", ftos(current_shadows));
};

void() Menu_Video_UpdateUltrawide =''',
    "E4: Funktionen für Dynamic Lights & Shadows",
    "Menu_Video_UpdateDynLight"
)

patch_regex(
    MENU_VIDE,
    r"// Texture Filtering\s*Menu_Button\(\d+, \"vm_filtr\".*?Menu_DrawOptionValue\(\d+, filt_string\);",
    '''// Dynamic Lights
    Menu_Button(11, "vm_dynlgt", "DYNAMIC LIGHTS", "Toggle Realtime Lights (Huge Performance Boost).") ? Menu_Video_UpdateDynLight() : 0;
    string dynlgt_string = "";
    if (current_dynlight) dynlgt_string = "ENABLED";
    else dynlgt_string = "DISABLED";
    Menu_DrawOptionValue(11, dynlgt_string);

    // Shadows
    Menu_Button(12, "vm_shdw", "SHADOWS", "Toggle Entity Shadows (Improves Performance).") ? Menu_Video_UpdateShadows() : 0;
    string shadows_string = "";
    if (current_shadows) shadows_string = "ENABLED";
    else shadows_string = "DISABLED";
    Menu_DrawOptionValue(12, shadows_string);

    // Texture Filtering
    Menu_Button(13, "vm_filtr", "TEXTURE FILTERING", "Choose 3D Environment Filtering Mode.") ? Menu_Video_UpdateFiltering() : 0;
    string filt_string = "";
    if (current_filter) filt_string = "NEAREST";
    else filt_string = "LINEAR";
    Menu_DrawOptionValue(13, filt_string);''',
    "E5: UI-Code für Dynamic Lights & Shadows einfügen",
    'vm_dynlgt", "DYNAMIC LIGHTS'
)

print("\n=== Alle Patches erfolgreich angewendet. ===")
sys.exit(0)
