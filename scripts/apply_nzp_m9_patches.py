#!/usr/bin/env python3
# NZP-M9 Server-Browser Gamepad-Navigation — Patch-Skript
# Wendet 4 Patches an: A (menu_coop.qc) + B (menu_coop.qc) + C/D (sui_sys.qc)
# Sicher: bricht mit Exit 1 ab, wenn ein Anker nicht eindeutig ist.

import sys
from pathlib import Path

def patch(path: Path, anchor: str, replacement: str, description: str, marker: str) -> None:
    if not path.exists():
        print(f"[FATAL] {path} existiert nicht. Erwartet Pfad: source/menu/...")
        print(f"        Repo-Root ist: {Path.cwd()}")
        sys.exit(1)

    content = path.read_text(encoding="utf-8")

    # Idempotenz: wenn Marker schon vorhanden, Patch wurde bereits angewendet
    if marker in content:
        print(f"[SKIP] {description}: bereits gepatcht")
        return

    count = content.count(anchor)
    if count == 0:
        print(f"[FATAL] {description}: Anker NICHT gefunden in {path}")
        print(f"        Anker (erste 120 Zeichen): {anchor[:120]!r}")
        sys.exit(1)
    if count > 1:
        print(f"[FATAL] {description}: Anker {count}× gefunden in {path} (erwartet: 1)")
        sys.exit(1)

    path.write_text(content.replace(anchor, replacement, 1), encoding="utf-8")
    print(f"[OK]   {description}")


BASE = Path("source/menu")
MENU_COOP = BASE / "menu_coop.qc"
SUI_SYS   = BASE / "sui_sys.qc"

# ---------- Patch A1: Variable deklarieren ----------
patch(
    MENU_COOP,
    anchor="int num_cached_servers;",
    replacement="int num_cached_servers;\nint coop_browse_selected;",
    description="A1: Variable coop_browse_selected",
    marker="int coop_browse_selected;",
)

# ---------- Patch A2: Menu_Coop_Browse Init + Clamp ----------
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

# ---------- Patch B: Navigate/Enter-Container-Funktionen anhängen ----------
NAV_BLOCK = """

// --- NZP-M9: Gamepad-Navigation für Server-Browser ---
string(string cur, float direction) Menu_Coop_Browse_Navigate =
{
	float is_in_list = (strlen(cur) >= 14 && substring(cur, 0, 14) == "cbm_serverlist");
	float is_row = (strlen(cur) > 14);

	if (direction > 0) {
		if (is_in_list && is_row) {
			if (coop_browse_selected + 1 >= num_cached_servers) {
				coop_browse_selected = -1;
				return "cbm_refresh";
			}
			coop_browse_selected += 1;
			return sprintf("cbm_serverlistscrl%d", coop_browse_selected);
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

# ---------- Patch C1: Forward-Declarations in sui_sys.qc ----------
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

# ---------- Patch C2: downarrow ----------
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

# ---------- Patch C3: uparrow ----------
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

# ---------- Patch D: enter auf Container wählt erste Zeile ----------
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

print("\n=== Alle 6 Patches erfolgreich angewendet. ===")
sys.exit(0)
