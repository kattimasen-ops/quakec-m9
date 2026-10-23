#!/usr/bin/env python3
# NZP-M9 Patches: HUD, HIT/KILL, Kill-Streak, Atmosphaere/Nebel,
# Coop-Browser-Navigation, A/B-Switch, Video-Optionen,
# POWERUPTOAST-Fix, Powerup-Runaway-Fix.
# Idempotent. Credits bleiben deaktiviert.

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
    else:
        print(f"[WARN] {description}: Anker nicht gefunden.")

def patch_regex(path: Path, pattern: str, replacement: str, description: str, marker: str) -> None:
    """Regex-basierter Patch mit Whitespace-Toleranz. Fuegt 'replacement' an der
    Stelle ein, die 'pattern' matcht. Verwendet \\1 als Backreference."""
    if not path.exists(): return
    content = path.read_text(encoding="utf-8")
    if marker in content: return
    new_content, count = re.subn(pattern, replacement, content, count=1, flags=re.DOTALL)
    if count >= 1:
        path.write_text(new_content, encoding="utf-8")
        print(f"[OK]   {description}")
    else:
        print(f"[WARN] {description}: Regex-Anker nicht gefunden.")

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
SERVER = Path("source/server")
MENU_COOP = BASE / "menu_coop.qc"
SUI_SYS   = BASE / "sui_sys.qc"
MENU_VIDE = BASE / "menu_vide.qc"
MAIN_QC = BASE / "main.qc"
CLIENT_MAIN = CLIENT / "main.qc"
FTE_QC = CLIENT / "defs/fte.qc"
MENU_DEFS = BASE / "defs/menu_defs.qc"
MENU_CRED = BASE / "menu_cred.qc"
CUSTOM_QC = CLIENT / "defs/custom.qc"
POWERUPS_QC = SERVER / "entities/powerups.qc"

# ==========================================
# TEIL 0: BASIS & CUSTOM.QC
# ==========================================
ensure_line(FTE_QC, ".float is_in_menu;", "Füge is_in_menu Feld hinzu")
ensure_line(FTE_QC, "void(string soundname, float channel, float volume) localsound_enhanced = { localsound(soundname, channel, volume); };", "Füge localsound_enhanced Wrapper hinzu")
ensure_line(FTE_QC, "void(float dest) setkeydest = #602;", "Füge setkeydest Builtin hinzu")

if MENU_DEFS.exists():
    content = MENU_DEFS.read_text(encoding="utf-8")
    content = content.replace("void() Menu_DrawMapPreview = { };", "")
    content = content.replace("float last_input_deviceid;", "")
    content = content.replace("void(float wantmode) m_toggle;", "")
    MENU_DEFS.write_text(content, encoding="utf-8")

ensure_line(MENU_DEFS, "float last_input_deviceid;", "Füge last_input_deviceid hinzu")
ensure_line(MENU_DEFS, "void(float wantmode) m_toggle;", "Füge m_toggle Deklaration hinzu")
append_safe(MENU_DEFS, "\n#ifndef MENU\nvoid() Menu_DrawMapPreview = { };\n#endif\n", "Füge menu_defs.qc Dummy hinzu", "void() Menu_DrawMapPreview = { };")

# Credits bleiben deaktiviert (Kurzversion)
if MENU_CRED.exists():
    cred_content = MENU_CRED.read_text(encoding="utf-8")
    if "Credits are currently disabled" not in cred_content:
        MENU_CRED.write_text("void() Menu_Credits = { Menu_DrawBackground(); Menu_DrawTitle(\"CREDITS\"); Menu_DrawMapPanel(); sui_text([150, 100], MENU_TEXT_MEDIUM, \"Credits are currently disabled in this build.\", [1, 1, 1], 1, 0); Menu_Button(-1, \"cr_back\", \"BACK\", \"Return to Main Menu.\") ? current_menu = MENU_MAIN : 0; sui_pop_frame(); };", encoding="utf-8")
        print("[OK]   Credits deaktiviert (Kurzversion)")

patch(CLIENT_MAIN, "float menu_active;", "// float menu_active;", "Entferne doppelte menu_active Definition", "// float menu_active;")

custom_globals = """
// NZP-M9 Custom Globals
float gore_enabled;
float gore_kill_light;
float gore_blood_count;
float dmg_text_time;
string dmg_text_str;
float dmg_indicator_alpha;
float dmg_last_health;
float screen_shake_intensity;
float hitmarker_sound_time;
float fov_punch_time;
float kill_streak_count;
float kill_streak_reset_time;
float kill_streak_display_time;
float kill_streak_last_time;
string kill_streak_text;
float heartbeat_time;
float ambient_dust_time;

// NZP-M9 Atmosphäre & Nebel
float nzp_is_indoor;
float nzp_fog_check_time;
float nzp_last_indoor_state;
float nzp_fog_initialized;
"""
append_safe(CUSTOM_QC, custom_globals, "Füge M9-Globals zu custom.qc hinzu", "// NZP-M9 Custom Globals")

# ==========================================
# TEIL 1: COOP-BROWSER (menu_coop.qc)
# ==========================================
patch(MENU_COOP, "int num_cached_servers;", "int num_cached_servers;\nfloat coop_browse_selected;", "A1: Variable coop_browse_selected", "float coop_browse_selected;")

patch(MENU_COOP, "void() Menu_Coop_Browse =\n{\n\tMenu_Coop_UpdateCache();",
      "void() Menu_Coop_Browse =\n{\n\tstatic float _browse_init;\n\tif (!_browse_init) {\n\t\tcoop_browse_selected = -1;\n\t\t_browse_init = true;\n\t}\n\tMenu_Coop_UpdateCache();\n\tif (coop_browse_selected < -1) coop_browse_selected = -1;\n\tif (num_cached_servers > 0 && coop_browse_selected >= num_cached_servers)\n\t\tcoop_browse_selected = num_cached_servers - 1;",
      "A2: Menu_Coop_Browse Init + Clamp", "_browse_init")

NAV_BLOCK = """
string(string cur, float direction) Menu_Coop_Browse_Navigate =
{
\tfloat is_in_list = (strlen(cur) >= 14 && substring(cur, 0, 14) == "cbm_serverlist");
\tfloat is_row = (strlen(cur) > 14);
\tif (direction > 0) {
\t\tif (is_in_list) {
\t\t\tif (!is_row) {
\t\t\t\tif (num_cached_servers > 0) { coop_browse_selected = 0; return "cbm_serverlistscrl0"; }
\t\t\t} else {
\t\t\t\tif (coop_browse_selected + 1 >= num_cached_servers) { coop_browse_selected = -1; return "cbm_refresh"; }
\t\t\t\tcoop_browse_selected += 1;
\t\t\t\treturn sprintf("cbm_serverlistscrl%d", coop_browse_selected);
\t\t\t}
\t\t}
\t\treturn "";
\t}
\tif (direction < 0) {
\t\tif (is_in_list && is_row) {
\t\t\tif (coop_browse_selected - 1 < 0) { coop_browse_selected = -1; return "cbm_serverlist"; }
\t\t\tcoop_browse_selected -= 1;
\t\t\treturn sprintf("cbm_serverlistscrl%d", coop_browse_selected);
\t\t}
\t\treturn "";
\t}
\treturn "";
}
float() Menu_Coop_Browse_EnterContainer = { if (num_cached_servers <= 0) return FALSE; coop_browse_selected = 0; return TRUE; };
"""
patch(MENU_COOP, "#undef PREVBUTTON_FUNC", "#undef PREVBUTTON_FUNC" + NAV_BLOCK, "B: Navigate- + EnterContainer-Funktionen", "Menu_Coop_Browse_Navigate")

# ==========================================
# TEIL 1c: SERVER-BROWSER HINWEIS AKTUALISIEREN
# ==========================================
patch(MENU_COOP,
    '"NOTE: Keyboard or gamepad is not supported for server selection."',
    '"NOTE: D-Pad UP/DOWN to scroll servers, B to select, A to go back."',
    "Server Browser: Gamepad-Hinweis aktualisieren",
    "D-Pad UP/DOWN to scroll servers")

# ==========================================
# TEIL 2: SUI_SYS.QC – NAVIGATION & A/B-SWITCH (Regex-basiert)
# ==========================================
SUI_FORWARD = """

// ==========================================
// NZP-M9: Forward-Deklarationen für Coop-Browser-Navigation
// ==========================================
string(string cur, float direction) Menu_Coop_Browse_Navigate;
float() Menu_Coop_Browse_EnterContainer;
"""
append_safe(SUI_SYS, SUI_FORWARD, "SUI: Forward-Deklarationen am Dateiende", "// NZP-M9: Forward-Deklarationen für Coop-Browser-Navigation")

# Regex-basierter Anker: toleriert beliebigen Whitespace zwischen Funktionskopf,
# Variablendeklaration und switch. Fuegt den Coop-Browser-Block direkt nach
# "string current_hovered_option = _hover_actions[0];" ein.
DOWNARROW_PATTERN = r'(void\s*\(\s*\)\s*_sui_menukey_downarrow\s*=\s*\{[\s\S]*?string\s+current_hovered_option\s*=\s*_hover_actions\s*\[\s*0\s*\]\s*;)'
DOWNARROW_REPLACEMENT = r'''\1
	if (current_menu == MENU_COOPBROWSE) {
		string nav = Menu_Coop_Browse_Navigate(current_hovered_option, 1);
		if (nav != "") { _hover_actions[0] = nav; last_hovered_id = ""; _hover_action_count = 1; return; }
	}'''
patch_regex(SUI_SYS, DOWNARROW_PATTERN, DOWNARROW_REPLACEMENT,
      "C2: Downarrow um Coop-Browser-Navigation erweitern (Regex)",
      "Menu_Coop_Browse_Navigate(current_hovered_option, 1)")

UPARROW_PATTERN = r'(void\s*\(\s*\)\s*_sui_menukey_uparrow\s*=\s*\{[\s\S]*?string\s+current_hovered_option\s*=\s*_hover_actions\s*\[\s*0\s*\]\s*;)'
UPARROW_REPLACEMENT = r'''\1
	if (current_menu == MENU_COOPBROWSE) {
		string nav = Menu_Coop_Browse_Navigate(current_hovered_option, -1);
		if (nav != "") { _hover_actions[0] = nav; last_hovered_id = ""; _hover_action_count = 1; return; }
	}'''
patch_regex(SUI_SYS, UPARROW_PATTERN, UPARROW_REPLACEMENT,
      "C3: Uparrow um Coop-Browser-Navigation erweitern (Regex)",
      "Menu_Coop_Browse_Navigate(current_hovered_option, -1)")

# Enter-Handler: fuegt Container-Enter-Logik hinzu
ENTER_PATTERN = r'(void\s*\(\s*\)\s*_sui_menukey_enter\s*=\s*\{[\s\S]*?if\s*\(\s*_hover_actions\s*\[\s*0\s*\]\s*==\s*""\s*\)[\s\S]*?_sui_menukey_downarrow\s*\(\s*\)\s*;)'
ENTER_REPLACEMENT = r'''\1
	if (current_menu == MENU_COOPBROWSE && _hover_actions[0] == "cbm_serverlist") {
		if (Menu_Coop_Browse_EnterContainer()) _hover_actions[0] = "cbm_serverlistscrl0";
	}'''
patch_regex(SUI_SYS, ENTER_PATTERN, ENTER_REPLACEMENT,
      "D: Enter um Container-Enter erweitern (Regex)",
      "Menu_Coop_Browse_EnterContainer())")

# A/B-Swap: Regex-basiert, damit Whitespace-Variationen toleriert werden
AB_PATTERN = r'(float\s*\(\s*float\s+evtype\s*,\s*float\s+scanx\s*,\s*float\s+chary\s*,\s*float\s+devid\s*\)\s*sui_input_event\s*=\s*\{)'
AB_REPLACEMENT = r'''\1
	if (evtype == IE_KEYDOWN || evtype == IE_KEYUP) {
		if (scanx == K_GP_A) scanx = K_ESCAPE;
		else if (scanx == K_GP_B) scanx = K_ENTER;
	}'''
patch_regex(SUI_SYS, AB_PATTERN, AB_REPLACEMENT,
      "FIX: A/B Button Swap (A=Zurück, B=Bestätigen)",
      "// NZP-M9: A = Zurueck")

# ==========================================
# TEIL 3: VIDEO-MENÜ
# ==========================================
if MENU_VIDE.exists():
    content = MENU_VIDE.read_text(encoding="utf-8")
    if "vm_decal" not in content:
        content = re.sub(r"string menu_video_buttons\[\d+\] = \{.*?\};",
                         'string menu_video_buttons[16] = {"vm_resol", "vm_fulls", "vm_shfps", "vm_maxps", "vm_vsync", "vm_fov", "vm_gamma", "vm_uwide", "vm_parts", "vm_decal", "vm_dynlgt", "vm_shdw", "vm_bob", "vm_filtr", "vm_apply", "vm_back"};',
                         content, count=1, flags=re.DOTALL)
    if "float current_fullscreen;" not in content:
        content = re.sub(r"float current_selected_vidmode;.*?float current_filter;",
                         '''float current_selected_vidmode;
float current_fullscreen;
float current_showfps;
float current_vsync;
float current_ultrawide;
float current_particles;
float current_decals;
float current_dynlight;
float current_shadows;
float current_bob;
float current_filter;''',
                         content, count=1, flags=re.DOTALL)
    MENU_VIDE.write_text(content, encoding="utf-8")
    print("[OK]   E1/E2: Video-Button-Array & Variablen geprüft")

if 'current_decals = cvar("nzp_decals");' not in MENU_VIDE.read_text(encoding="utf-8"):
    content = MENU_VIDE.read_text(encoding="utf-8")
    new_content, count = re.subn(r"void\(\) Menu_Video_StoreCurrentSettings =\s*\{.*?\}",
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
}''', content, count=1, flags=re.DOTALL)
    if count >= 1:
        MENU_VIDE.write_text(new_content, encoding="utf-8")
        print("[OK]   E3: StoreCurrentSettings")
    else:
        print("[WARN] E3: StoreCurrentSettings Anker nicht gefunden")

if "Menu_Video_UpdateDynLight" not in MENU_VIDE.read_text(encoding="utf-8"):
    patch(MENU_VIDE, "void() Menu_Video_UpdateUltrawide =", '''void() Menu_Video_UpdateDecals = { Menu_PlaySound(MENU_SND_ENTER); current_decals = !current_decals; cvar_set("nzp_decals", ftos(current_decals)); };
void() Menu_Video_UpdateDynLight = { Menu_PlaySound(MENU_SND_ENTER); current_dynlight = !current_dynlight; cvar_set("r_dynamic", ftos(current_dynlight)); };
void() Menu_Video_UpdateShadows = { Menu_PlaySound(MENU_SND_ENTER); current_shadows = !current_shadows; cvar_set("r_shadows", ftos(current_shadows)); };
void() Menu_Video_UpdateBob = { Menu_PlaySound(MENU_SND_ENTER); current_bob = !current_bob; cvar_set("cl_bobup", current_bob ? "0.02" : "0"); cvar_set("cl_bobside", current_bob ? "0.02" : "0"); };
void() Menu_Video_UpdateUltrawide =''', "E4: Update-Funktionen", "Menu_Video_UpdateDynLight")

if "vm_decal" not in MENU_VIDE.read_text(encoding="utf-8"):
    menu_video_function = '''
void() Menu_Video =
{
    if (!menu_video_init) Menu_Video_Init();
    Menu_DrawBackground(); Menu_DrawTitle("VIDEO OPTIONS"); Menu_DrawMapPanel();

    Menu_Button(1, "vm_resol", "RESOLUTION", "Window size adjustment.") ? Menu_Video_UpdateVideoMode() : 0;
    if (current_selected_vidmode > menu_video_modes) current_selected_vidmode = 0;
    Menu_DrawOptionValue(1, sprintf("%dx%d (%d:%d)", video_modes[current_selected_vidmode].size[0], video_modes[current_selected_vidmode].size[1], video_modes[current_selected_vidmode].ratio[0], video_modes[current_selected_vidmode].ratio[1]));

    Menu_Button(2, "vm_fulls", "FULLSCREEN", "Change Fullscreen Mode.") ? Menu_Video_UpdateFullscreen() : 0;
    Menu_DrawOptionValue(2, (current_fullscreen == 0) ? "DISABLED" : (current_fullscreen == 1) ? "ENABLED" : "BORDERLESS");

    Menu_Button(3, "vm_shfps", "SHOW FPS", "Toggles display of FPS Values.") ? Menu_Video_UpdateShowFPS() : 0;
    Menu_DrawOptionValue(3, (current_showfps == 0) ? "DISABLED" : (current_showfps == 1) ? "ENABLED" : "VERBOSE");

    Menu_Button(4, "vm_maxps", "MAX FPS", "Configure Maximum FPS Value.") ? 0 : 0;
    Menu_CvarSlider(4, "vm_maxps", [10, 500, 490], "cl_maxfps", true, false, false);

    Menu_Button(5, "vm_vsync", "VSYNC", "Sync Framerate with Display.") ? Menu_Video_UpdateVsync() : 0;
    Menu_DrawOptionValue(5, current_vsync ? "ENABLED" : "DISABLED");

    Menu_Button(6, "vm_fov", "FIELD OF VIEW", "Change Camera Field of View.") ? 0 : 0;
    Menu_CvarSlider(6, "vm_fov", [10, 150, 140], "fov", true, false, false);

    Menu_Button(7, "vm_gamma", "GAMMA", "Adjust game Black Level.") ? 0 : 0;
    Menu_CvarSlider(7, "vm_gamma", [0.3, 2, 17], "gamma", false, true, false);

    Menu_Button(8, "vm_uwide", "ULTRAWIDE MODE", "Condenses HUD closer to center of Display.") ? Menu_Video_UpdateUltrawide() : 0;
    Menu_DrawOptionValue(8, current_ultrawide ? "ENABLED" : "DISABLED");

    Menu_Button(9, "vm_parts", "PARTICLES", "Toggle Particle Effects for Performance.") ? Menu_Video_UpdateParticles() : 0;
    Menu_DrawOptionValue(9, current_particles ? "ENABLED" : "DISABLED");

    Menu_Button(10, "vm_decal", "DECALS", "Toggle Bullet Holes and Blood.") ? Menu_Video_UpdateDecals() : 0;
    Menu_DrawOptionValue(10, current_decals ? "ENABLED" : "DISABLED");

    Menu_Button(11, "vm_dynlgt", "DYNAMIC LIGHTS", "Toggle Realtime Lights.") ? Menu_Video_UpdateDynLight() : 0;
    Menu_DrawOptionValue(11, current_dynlight ? "ENABLED" : "DISABLED");

    Menu_Button(12, "vm_shdw", "SHADOWS", "Toggle Entity Shadows.") ? Menu_Video_UpdateShadows() : 0;
    Menu_DrawOptionValue(12, current_shadows ? "ENABLED" : "DISABLED");

    Menu_Button(13, "vm_bob", "WEAPON BOB", "Toggle Weapon Swaying.") ? Menu_Video_UpdateBob() : 0;
    Menu_DrawOptionValue(13, current_bob ? "ENABLED" : "DISABLED");

    Menu_Button(14, "vm_filtr", "TEXTURE FILTERING", "Choose 3D Environment Filtering Mode.") ? Menu_Video_UpdateFiltering() : 0;
    Menu_DrawOptionValue(14, current_filter ? "NEAREST" : "LINEAR");

    Menu_DrawDivider(14.25);
    Menu_Button(15, "vm_apply", "APPLY", "Save & Apply Settings.") ? Menu_Video_ApplySettings() : 0;
    Menu_Button(16, "vm_back", "BACK", "Return to Configuration Menu.") ? current_menu = MENU_OPTIONS : 0;

    sui_pop_frame();	
};'''
    content = MENU_VIDE.read_text(encoding="utf-8")
    new_content, count = re.subn(r"void\(\) Menu_Video\s*=\s*\{.*?\n\};", menu_video_function, content, count=1, flags=re.DOTALL)
    if count >= 1:
        MENU_VIDE.write_text(new_content, encoding="utf-8")
        print("[OK]   E5: Menu_Video überschreiben")
    else:
        print("[WARN] E5: Menu_Video Anker nicht gefunden")

patch(MAIN_QC, 'build_datetime = fgets(file);', 'build_datetime = "M9 Pro Custom Build";\n        // build_datetime = fgets(file);', "Custom Version String", "M9 Pro Custom Build")

# ==========================================
# TEIL 4: CLIENT_MAIN – INITIALISIERUNG
# ==========================================
patch(CLIENT_MAIN, "void(float apiver, string enginename, float enginever) CSQC_Init =\n{",
    """void(float apiver, string enginename, float enginever) CSQC_Init =
{
	// NZP-M9 Initialisierungen
	gore_enabled = 1;
	gore_kill_light = 300;
	gore_blood_count = 2;
	dmg_text_time = 0;
	dmg_text_str = "";
	dmg_indicator_alpha = 0;
	dmg_last_health = 100;
	screen_shake_intensity = 0;
	hitmarker_sound_time = 0;
	fov_punch_time = 0;
	kill_streak_count = 0;
	kill_streak_reset_time = 0;
	kill_streak_display_time = 0;
	kill_streak_last_time = 0;
	kill_streak_text = "";
	heartbeat_time = 0;
	ambient_dust_time = 0;
	nzp_is_indoor = FALSE;
	nzp_fog_check_time = 0;
	nzp_last_indoor_state = FALSE;
	nzp_fog_initialized = FALSE;
""",
    "Initialisiere Variablen in CSQC_Init", "// NZP-M9 Initialisierungen")

# ==========================================
# TEIL 5: CSQC_Parse_Event – POWERUPTOAST-Case hinzufügen
# ==========================================
# Der Server sendet beim Einsammeln eines Power-ups CSQC_EVENT_POWERUPTOAST.
# Der Client muss den String lesen, sonst kommt es zu "Bad server message".
# Regex-basierter Anker: fuegt nach dem BROADCASTMESSAGE-Case ein.
PARSE_PATTERN = r'(case\s+CSQC_EVENT_BROADCASTMESSAGE\s*:\s*broadcast_type\s*=\s*readbyte\s*\(\s*\)\s*;\s*broadcast_time\s*=\s*time\s*\+\s*5\s*;\s*broadcast_num\s*=\s*readbyte\s*\(\s*\)\s*;\s*break\s*;)'
PARSE_REPLACEMENT = r'''\1
		case CSQC_EVENT_POWERUPTOAST:
			hud_toast_string = readstring();
			hud_toast_starttime = time;
			hud_toast_endtime = time + 3;
			break;'''
patch_regex(CLIENT_MAIN, PARSE_PATTERN, PARSE_REPLACEMENT,
    "CSQC_Parse_Event: POWERUPTOAST-Case hinzufügen (Fix für Bad server message)",
    "case CSQC_EVENT_POWERUPTOAST:")

# ==========================================
# TEIL 6: ATMOSPHÄRE-FUNKTIONEN (additiv)
# ==========================================
ATMO_FUNCS = """
// ==========================================
// NZP-M9: Atmosphäre & Nebel
// ==========================================

float() CSQC_IsIndoor =
{
	vector start = playerOrigin + [0, 0, 16];
	vector end = start + [0, 0, 4096];
	traceline(start, end, false, world);

	if (trace_fraction == 1) {
		return FALSE;
	}

	if (pointcontents(trace_endpos) == CONTENT_SKY) {
		return FALSE;
	}

	return TRUE;
};

void() CSQC_UpdateAtmosphere =
{
	if (time < nzp_fog_check_time) {
		return;
	}
	nzp_fog_check_time = time + 0.5;

	float indoor = CSQC_IsIndoor();
	nzp_is_indoor = indoor;

	if (indoor != nzp_last_indoor_state || !nzp_fog_initialized) {
		nzp_last_indoor_state = indoor;
		nzp_fog_initialized = TRUE;

		if (indoor) {
			cvar_set("r_fog", "1");
			cvar_set("r_fog_color", "0.15 0.15 0.20");
			cvar_set("r_fog_start", "80");
			cvar_set("r_fog_end", "700");
		} else {
			cvar_set("r_fog", "1");
			cvar_set("r_fog_color", "0.45 0.45 0.50");
			cvar_set("r_fog_start", "500");
			cvar_set("r_fog_end", "3000");
		}
	}
};

// ==========================================
"""
patch(CLIENT_MAIN, "noref void(float width, float height, float menushown) CSQC_UpdateView =",
    ATMO_FUNCS + "noref void(float width, float height, float menushown) CSQC_UpdateView =",
    "Atmosphäre-Funktionen vor CSQC_UpdateView einfügen",
    "// NZP-M9: Atmosphäre & Nebel")

# ==========================================
# TEIL 7: HUD + HIT/KILL + KILL-STREAK (additiv)
# ==========================================
HUD_ADDITION = """	// NZP-M9: Atmosphäre vor dem Rendern aktualisieren
	CSQC_UpdateAtmosphere();

	//does what you think it does
	renderscene();

	// --- NZP-M9 CUSTOM HUD ---

	// HIT/KILL-Text basierend auf vorhandenen Hitmarkern
	if (time < hitmark_time) {
		if (hitmark_type == 1) dmg_text_str = "KILL";
		else dmg_text_str = "HIT";
		dmg_text_time = time + 0.8;
	}

	// Kill-Streak-Logik (nur bei Kills, dedupliziert)
	if (hitmark_type == 1 && time < hitmark_time) {
		if (time - kill_streak_last_time > 0.5) {
			if (time > kill_streak_reset_time) kill_streak_count = 1;
			else kill_streak_count += 1;

			kill_streak_last_time = time;
			kill_streak_reset_time = time + 3.0;

			if (kill_streak_count == 2) { kill_streak_text = "DOUBLE KILL"; kill_streak_display_time = time + 2.5; }
			else if (kill_streak_count == 3) { kill_streak_text = "TRIPLE KILL"; kill_streak_display_time = time + 2.5; }
			else if (kill_streak_count >= 4) { kill_streak_text = "MULTI KILL!"; kill_streak_display_time = time + 2.5; }
		}
	}

	float current_health = getstatf(STAT_HEALTH);
	if (current_health < dmg_last_health) {
		dmg_indicator_alpha = 0.6;
		screen_shake_intensity += 3;
	}
	dmg_last_health = current_health;
	dmg_indicator_alpha -= frametime * 2;
	if (dmg_indicator_alpha < 0) dmg_indicator_alpha = 0;

	if (dmg_indicator_alpha > 0) {
		float edge_size = 20;
		drawfill([0, 0], [g_width, edge_size], [1, 0, 0], dmg_indicator_alpha, 0);
		drawfill([0, g_height - edge_size], [g_width, edge_size], [1, 0, 0], dmg_indicator_alpha, 0);
		drawfill([0, edge_size], [edge_size, g_height - edge_size*2], [1, 0, 0], dmg_indicator_alpha, 0);
		drawfill([g_width - edge_size, edge_size], [edge_size, g_height - edge_size*2], [1, 0, 0], dmg_indicator_alpha, 0);
	}

	screen_shake_intensity -= frametime * 25;
	if (screen_shake_intensity < 0) screen_shake_intensity = 0;

	if (current_health < 30 && !(getstatf(STAT_PERKS) & P_DEAD) && !getstatf(STAT_WEAPONZOOM)) {
		float pulse = (sin(cltime * 8) + 1) * 0.5;
		drawfill([0, 0], [g_width, g_height], [1, 0, 0], pulse * 0.4, 0);
		if (time > heartbeat_time) {
			localsound_enhanced("sounds/player/heart.wav", 0, 1.0);
			heartbeat_time = time + 1.0;
		}
	}

	// Ambient Dust (nur im Außenbereich)
	if (!nzp_last_indoor_state && time > ambient_dust_time && cvar("nzp_particles")) {
		ambient_dust_time = time + 0.1;
		vector view_ang = getviewprop(VF_ANGLES);
		makevectors(view_ang);
		vector dust_pos = getviewprop(VF_ORIGIN) + v_forward * 200 + v_right * (random()*400-200) + v_up * (random()*400-200);
		pointparticles(particleeffectnum("weapons.impact"), dust_pos, '0 0 0', 1);
	}

	if (!getstatf(STAT_WEAPONZOOM) && !cvar("chase_active")) {
		float spread = 4.0 + vlen(playerVelocity) * 0.05 + fabs(gun_kick[0]) * 2.0;
		vector cx_color = [0.8, 0.2, 1];
		if (current_health < 30) cx_color = [1, 0, 0];

		drawfill([g_width*0.5 - 1, g_height*0.5 - spread - 6], [2, 6], cx_color, 1, 0);
		drawfill([g_width*0.5 - 1, g_height*0.5 + spread], [2, 6], cx_color, 1, 0);
		drawfill([g_width*0.5 - spread - 6, g_height*0.5 - 1], [6, 2], cx_color, 1, 0);
		drawfill([g_width*0.5 + spread, g_height*0.5 - 1], [6, 2], cx_color, 1, 0);
		drawfill([g_width*0.5 - 1, g_height*0.5 - 1], [2, 2], cx_color, 0.5, 0);
	}

	if (serverkey("pausestate") != "1") {
		sui_begin(g_width, g_height);
		sui_set_align([SUI_ALIGN_END, SUI_ALIGN_START]);

		float real_kills = 0;
		entity player_ent = find(world, classname, "player");
		while (player_ent != world) {
			if (player_ent.playernum == player_localnum + 1) {
				real_kills = player_ent.kills;
				break;
			}
			player_ent = find(player_ent, classname, "player");
		}

		sui_text([-10, 10], MENU_TEXT_MEDIUM, sprintf("KILLS: %d", real_kills), [0.8, 0.2, 1], 1, 0);

		float mins = floor(cltime / 60);
		float secs = floor(cltime % 60);
		sui_text([-10, 30], MENU_TEXT_SMALL, sprintf("TIME: %02d:%02d", mins, secs), [1, 1, 1], 1, 0);

		if (time < dmg_text_time) {
			float diff = dmg_text_time - time;
			float offset_y = 60 - ((0.8 - diff) * 40);
			vector dmg_color = [1, 0.2, 1];
			if (dmg_text_str == "KILL") dmg_color = [1, 0, 0];
			sui_set_align([SUI_ALIGN_CENTER, SUI_ALIGN_CENTER]);
			sui_text([0, -offset_y], MENU_TEXT_MEDIUM, dmg_text_str, dmg_color, diff, 0);
		}

		if (time < kill_streak_display_time) {
			sui_set_align([SUI_ALIGN_CENTER, SUI_ALIGN_CENTER]);
			sui_text([0, -120], MENU_TEXT_LARGE, kill_streak_text, [1, 0.5, 0], 1, 0);
		}

		// Power-Up Toast (Fix für POWERUPTOAST)
		if (time < hud_toast_endtime && hud_toast_string != "") {
			float toast_alpha = 1;
			if (hud_toast_endtime - time < 1) toast_alpha = hud_toast_endtime - time;
			sui_set_align([SUI_ALIGN_CENTER, SUI_ALIGN_START]);
			sui_text([0, 80], MENU_TEXT_MEDIUM, hud_toast_string, [1, 1, 0.5], toast_alpha, 0);
		}

		sui_end();
	}"""

patch(CLIENT_MAIN, "\t//does what you think it does\n\trenderscene();",
    HUD_ADDITION,
    "HUD-Block inkl. HIT/KILL + Kill-Streak + Toast nach renderscene() einfügen",
    "--- NZP-M9 CUSTOM HUD ---")

# ==========================================
# TEIL 8: POWERUPS.QC – RUNAWAY-LOOP-FIX
# ==========================================
RUNAWAY_PATTERN = r'(float\s+perk_to_give\s*=\s*0;\s*float\s+found_perk_for_player\s*=\s*false;\s*)while\s*\(\s*!\s*found_perk_for_player\s*\)\s*\{[\s\S]*?if\s*\(\s*perk_to_give\s*!=\s*0\s*\)\s*found_perk_for_player\s*=\s*true;\s*\}'

RUNAWAY_REPLACEMENT = """float perk_to_give = 0;

		// NZP-M9 FIX: Deterministische, uniforme Auswahl aus den verfuegbaren
		// Perks. Die frueher verwendete while-Schleife konnte endlos laufen
		// ("runaway loop error"). perks_can_give ist hier garantiert > 0.
		float num_avail = 0;
		if (perks_can_give & P_REVIVE) num_avail++;
		if (perks_can_give & P_JUG) num_avail++;
		if (perks_can_give & P_SPEED) num_avail++;
		if (perks_can_give & P_DOUBLE) num_avail++;
		if (perks_can_give & P_STAMIN) num_avail++;
		if (perks_can_give & P_FLOP) num_avail++;
		if (perks_can_give & P_DEAD) num_avail++;
		if (perks_can_give & P_MULE) num_avail++;

		float pick = floor(random() * num_avail);
		if (pick >= num_avail) pick = num_avail - 1;

		float current = 0;

		if (perks_can_give & P_REVIVE) { if (current == pick) { self.sequence = 1; perk_to_give = P_REVIVE; } current++; }
		if (perks_can_give & P_JUG)    { if (current == pick) { self.sequence = 2; perk_to_give = P_JUG; }    current++; }
		if (perks_can_give & P_SPEED)  { if (current == pick) { self.sequence = 3; perk_to_give = P_SPEED; }  current++; }
		if (perks_can_give & P_DOUBLE) { if (current == pick) { self.has_doubletap_damage_buff = true; self.sequence = 4; perk_to_give = P_DOUBLE; } current++; }
		if (perks_can_give & P_STAMIN) { if (current == pick) { self.sequence = 5; perk_to_give = P_STAMIN; } current++; }
		if (perks_can_give & P_FLOP)   { if (current == pick) { self.sequence = 6; perk_to_give = P_FLOP; }   current++; }
		if (perks_can_give & P_DEAD)   { if (current == pick) { self.sequence = 7; perk_to_give = P_DEAD; }   current++; }
		if (perks_can_give & P_MULE)   { if (current == pick) { self.sequence = 8; perk_to_give = P_MULE; }   current++; }"""

patch_regex(POWERUPS_QC, RUNAWAY_PATTERN, RUNAWAY_REPLACEMENT,
    "Powerups: Runaway-Loop deterministisch beheben (Regex)",
    "NZP-M9 FIX: Deterministische")

print("\n=== Alle Patches erfolgreich angewendet (idempotent). ===")
sys.exit(0)
