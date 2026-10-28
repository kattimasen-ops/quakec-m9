#!/usr/bin/env python3
# NZP-M9 Patches – QuakeC (HUD, Gore/Atmosphäre-Menü, Navigation, Powerup-Fixes)
# Idempotent. Stellt sicher, dass das Atmosphere & Gore Menü sichtbar und
# auswählbar ist, behebt überlappende Buttons im Video-Menü und
# die serverseitigen Crash-Ursachen.

import sys
import re
from pathlib import Path

def patch(path, anchor, replacement, description, marker):
    if not path.exists(): return
    content = path.read_text(encoding="utf-8")
    if marker in content: return
    if anchor in content:
        path.write_text(content.replace(anchor, replacement, 1), encoding="utf-8")
        print(f"[OK]   {description}")
    else:
        print(f"[WARN] {description}: Anker nicht gefunden.")

def patch_regex(path, pattern, replacement, description, marker):
    if not path.exists(): return
    content = path.read_text(encoding="utf-8")
    if marker in content: return
    new_content, count = re.subn(pattern, replacement, content, count=1, flags=re.DOTALL)
    if count >= 1:
        path.write_text(new_content, encoding="utf-8")
        print(f"[OK]   {description}")
    else:
        print(f"[WARN] {description}: Regex-Anker nicht gefunden.")

def ensure_line(path, line, description):
    if not path.exists(): return
    content = path.read_text(encoding="utf-8")
    if line in content: return
    path.write_text(content + "\n" + line + "\n", encoding="utf-8")
    print(f"[OK]   {description}")

def append_safe(path, content, description, marker):
    if not path.exists(): return
    text = path.read_text(encoding="utf-8")
    if marker in text: return
    path.write_text(text + "\n" + content, encoding="utf-8")
    print(f"[OK]   {description}")

BASE = Path("source/menu")
CLIENT = Path("source/client")
SERVER = Path("source/server")
PROGS = Path("progs")

MENU_COOP = BASE / "menu_coop.qc"
MENU_OPTS = BASE / "menu_opts.qc"
MENU_M9_ATMO = BASE / "menu_m9_atmo.qc"
SUI_SYS   = BASE / "sui_sys.qc"
MENU_VIDE = BASE / "menu_vide.qc"
MAIN_QC = BASE / "main.qc"
CLIENT_MAIN = CLIENT / "main.qc"
FTE_QC = CLIENT / "defs/fte.qc"
MENU_DEFS = BASE / "defs/menu_defs.qc"
MENU_CRED = BASE / "menu_cred.qc"
CLIENT_CUSTOM_QC = CLIENT / "defs/custom.qc"
SERVER_CUSTOM_QC = SERVER / "defs/custom.qc"
POWERUPS_QC = SERVER / "entities/powerups.qc"
ZOMBIE_CORE_QC = SERVER / "ai/zombie_core.qc"
WEAPON_CORE_QC = SERVER / "weapons/weapon_core.qc"

# ==========================================
# TEIL 0: BASIS & CUSTOM.QC
# ==========================================
ensure_line(FTE_QC, ".float is_in_menu;", "is_in_menu")
ensure_line(FTE_QC, "void(string soundname, float channel, float volume) localsound_enhanced = { localsound(soundname, channel, volume); };", "localsound_enhanced")
ensure_line(FTE_QC, "void(float dest) setkeydest = #602;", "setkeydest")

if MENU_DEFS.exists():
    content = MENU_DEFS.read_text(encoding="utf-8")
    content = content.replace("void() Menu_DrawMapPreview = { };", "")
    content = content.replace("float last_input_deviceid;", "")
    content = content.replace("void(float wantmode) m_toggle;", "")
    MENU_DEFS.write_text(content, encoding="utf-8")

ensure_line(MENU_DEFS, "float last_input_deviceid;", "last_input_deviceid")
ensure_line(MENU_DEFS, "void(float wantmode) m_toggle;", "m_toggle")
append_safe(MENU_DEFS, "\n#ifndef MENU\nvoid() Menu_DrawMapPreview = { };\n#endif\n", "Dummy", "void() Menu_DrawMapPreview = { };")

if MENU_CRED.exists():
    cred_content = MENU_CRED.read_text(encoding="utf-8")
    if "Credits are currently disabled" not in cred_content:
        MENU_CRED.write_text("void() Menu_Credits = { Menu_DrawBackground(); Menu_DrawTitle(\"CREDITS\"); Menu_DrawMapPanel(); sui_text([150, 100], MENU_TEXT_MEDIUM, \"Credits are currently disabled in this build.\", [1, 1, 1], 1, 0); Menu_Button(-1, \"cr_back\", \"BACK\", \"Return to Main Menu.\") ? current_menu = MENU_MAIN : 0; sui_pop_frame(); };", encoding="utf-8")

custom_globals = """
// NZP-M9 Custom Globals (Client)
float gore_enabled; float gore_kill_light; float gore_blood_count;
float dmg_text_time; string dmg_text_str; float dmg_indicator_alpha;
float dmg_last_health; float screen_shake_intensity; float hitmarker_sound_time;
float fov_punch_time; float kill_streak_count; float kill_streak_reset_time;
float kill_streak_display_time; float kill_streak_last_time; string kill_streak_text;
float heartbeat_time; float ambient_dust_time;
float nzp_is_indoor; float nzp_fog_check_time; float nzp_last_indoor_state; float nzp_fog_initialized;
"""
append_safe(CLIENT_CUSTOM_QC, custom_globals, "M9-Globals", "// NZP-M9 Custom Globals (Client)")

# ==========================================
# TEIL 1: COOP-BROWSER
# ==========================================
patch(MENU_COOP, "int num_cached_servers;", "int num_cached_servers;\nfloat coop_browse_selected;", "coop_browse_selected", "float coop_browse_selected;")
patch(MENU_COOP, "void() Menu_Coop_Browse =\n{\n\tMenu_Coop_UpdateCache();",
      "void() Menu_Coop_Browse =\n{\n\tstatic float _browse_init;\n\tif (!_browse_init) {\n\t\tcoop_browse_selected = -1;\n\t\t_browse_init = true;\n\t}\n\tMenu_Coop_UpdateCache();\n\tif (coop_browse_selected < -1) coop_browse_selected = -1;\n\tif (num_cached_servers > 0 && coop_browse_selected >= num_cached_servers)\n\t\tcoop_browse_selected = num_cached_servers - 1;",
      "Browse Init", "_browse_init")

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
patch(MENU_COOP, "#undef PREVBUTTON_FUNC", "#undef PREVBUTTON_FUNC" + NAV_BLOCK, "Navigate-Funktionen", "Menu_Coop_Browse_Navigate")
patch(MENU_COOP,
    '"NOTE: Keyboard or gamepad is not supported for server selection."',
    '"NOTE: D-Pad UP/DOWN to scroll servers, B to select, A to go back."',
    "Gamepad-Hinweis", "D-Pad UP/DOWN to scroll servers")

# ==========================================
# TEIL 2: SUI_SYS.QC (Navigation & A/B-SWAP)
# ==========================================
SUI_FORWARD_ANCHOR = "void() _sui_menukey_downarrow ="
SUI_FORWARD_REPLACEMENT = """// NZP-M9: Forward-Deklarationen
string(string cur, float direction) Menu_Coop_Browse_Navigate;
float() Menu_Coop_Browse_EnterContainer;
string(string prev_id) Menu_M9_Atmo_GetNextButton;
string(string next_id) Menu_M9_Atmo_GetPreviousButton;

void() _sui_menukey_downarrow ="""
patch(SUI_SYS, SUI_FORWARD_ANCHOR, SUI_FORWARD_REPLACEMENT, "SUI Forward", "Forward-Deklarationen")

# Downarrow: MENU_M9_ATMO Case
DOWNARROW_PATTERN = r'(void\s*\(\s*\)\s*_sui_menukey_downarrow\s*=\s*\{[\s\S]*?string\s+current_hovered_option\s*=\s*_hover_actions\s*\[\s*0\s*\]\s*;)'
DOWNARROW_REPLACEMENT = r'''\1
	if (current_menu == MENU_COOPBROWSE) {
		string nav = Menu_Coop_Browse_Navigate(current_hovered_option, 1);
		if (nav != "") { _hover_actions[0] = nav; last_hovered_id = ""; _hover_action_count = 1; return; }
	}
	if (current_menu == MENU_M9_ATMO) {
		_hover_actions[0] = Menu_M9_Atmo_GetNextButton(current_hovered_option);
		_hover_action_count = 1;
		return;
	}'''
patch_regex(SUI_SYS, DOWNARROW_PATTERN, DOWNARROW_REPLACEMENT, "Downarrow M9-ATMO", "Menu_M9_Atmo_GetNextButton(current_hovered_option)")

# Uparrow: MENU_M9_ATMO Case
UPARROW_PATTERN = r'(void\s*\(\s*\)\s*_sui_menukey_uparrow\s*=\s*\{[\s\S]*?string\s+current_hovered_option\s*=\s*_hover_actions\s*\[\s*0\s*\]\s*;)'
UPARROW_REPLACEMENT = r'''\1
	if (current_menu == MENU_COOPBROWSE) {
		string nav = Menu_Coop_Browse_Navigate(current_hovered_option, -1);
		if (nav != "") { _hover_actions[0] = nav; last_hovered_id = ""; _hover_action_count = 1; return; }
	}
	if (current_menu == MENU_M9_ATMO) {
		_hover_actions[0] = Menu_M9_Atmo_GetPreviousButton(current_hovered_option);
		_hover_action_count = 1;
		return;
	}'''
patch_regex(SUI_SYS, UPARROW_PATTERN, UPARROW_REPLACEMENT, "Uparrow M9-ATMO", "Menu_M9_Atmo_GetPreviousButton(current_hovered_option)")

AB_PATTERN = r'(float\s*\(\s*float\s+evtype\s*,\s*float\s+scanx\s*,\s*float\s+chary\s*,\s*float\s+devid\s*\)\s*sui_input_event\s*=\s*\{)'
AB_REPLACEMENT = r'''\1
	if (evtype == IE_KEYDOWN || evtype == IE_KEYUP) {
		if (scanx == K_GP_A) scanx = K_ESCAPE;
		else if (scanx == K_GP_B) scanx = K_ENTER;
	}'''
patch_regex(SUI_SYS, AB_PATTERN, AB_REPLACEMENT, "A/B-Swap", "// NZP-M9: A = Zurueck")

# ==========================================
# TEIL 3: VIDEO-MENÜ (Überlappung der Apply/Back-Buttons beheben)
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
float current_fullscreen; float current_showfps; float current_vsync;
float current_ultrawide; float current_particles; float current_decals;
float current_dynlight; float current_shadows; float current_bob; float current_filter;''',
                         content, count=1, flags=re.DOTALL)
    MENU_VIDE.write_text(content, encoding="utf-8")
    print("[OK]   Video-Array")

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
        print("[OK]   StoreSettings")

if "Menu_Video_UpdateDynLight" not in MENU_VIDE.read_text(encoding="utf-8"):
    patch(MENU_VIDE, "void() Menu_Video_UpdateUltrawide =", '''void() Menu_Video_UpdateDecals = { Menu_PlaySound(MENU_SND_ENTER); current_decals = !current_decals; cvar_set("nzp_decals", ftos(current_decals)); };
void() Menu_Video_UpdateDynLight = { Menu_PlaySound(MENU_SND_ENTER); current_dynlight = !current_dynlight; cvar_set("r_dynamic", ftos(current_dynlight)); };
void() Menu_Video_UpdateShadows = { Menu_PlaySound(MENU_SND_ENTER); current_shadows = !current_shadows; cvar_set("r_shadows", ftos(current_shadows)); };
void() Menu_Video_UpdateBob = { Menu_PlaySound(MENU_SND_ENTER); current_bob = !current_bob; cvar_set("cl_bobup", current_bob ? "0.02" : "0"); cvar_set("cl_bobside", current_bob ? "0.02" : "0"); };
void() Menu_Video_UpdateUltrawide =''', "Update-Funktionen", "Menu_Video_UpdateDynLight")

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
    Menu_Button(15, "vm_apply", "APPLY", "Save & Apply Settings.") ? Menu_Video_ApplySettings() : 0;
    Menu_Button(16, "vm_back", "BACK", "Return to Configuration Menu.") ? current_menu = MENU_OPTIONS : 0;
    sui_pop_frame();	
};'''
    content = MENU_VIDE.read_text(encoding="utf-8")
    new_content, count = re.subn(r"void\(\) Menu_Video\s*=\s*\{.*?\n\};", menu_video_function, content, count=1, flags=re.DOTALL)
    if count >= 1:
        MENU_VIDE.write_text(new_content, encoding="utf-8")
        print("[OK]   Menu_Video (Apply/Back korrekt positioniert)")

# Falls das Menü bereits gepatcht wurde, aber noch die alten Koordinaten (-2/-1) hat:
patch(MENU_VIDE,
    """    Menu_Button(-2, "vm_apply", "APPLY", "Save & Apply Settings.") ? Menu_Video_ApplySettings() : 0;
    Menu_Button(-1, "vm_back", "BACK", "Return to Configuration Menu.") ? current_menu = MENU_OPTIONS : 0;""",
    """    Menu_Button(15, "vm_apply", "APPLY", "Save & Apply Settings.") ? Menu_Video_ApplySettings() : 0;
    Menu_Button(16, "vm_back", "BACK", "Return to Configuration Menu.") ? current_menu = MENU_OPTIONS : 0;""",
    "Apply/Back Koordinaten korrigiert", 'Menu_Button(15, "vm_apply"')

patch(MAIN_QC, 'build_datetime = fgets(file);', 'build_datetime = "M9 Pro Custom Build";\n        // build_datetime = fgets(file);', "Version String", "M9 Pro Custom Build")

# ==========================================
# TEIL 4: CLIENT_MAIN – INITIALISIERUNG & POWERUPTOAST
# ==========================================
patch(CLIENT_MAIN, "void(float apiver, string enginename, float enginever) CSQC_Init =\n{",
    """void(float apiver, string enginename, float enginever) CSQC_Init =
{
	gore_enabled = 1; gore_kill_light = 300; gore_blood_count = 2;
	dmg_text_time = 0; dmg_text_str = ""; dmg_indicator_alpha = 0;
	dmg_last_health = 100; screen_shake_intensity = 0; hitmarker_sound_time = 0;
	fov_punch_time = 0; kill_streak_count = 0; kill_streak_reset_time = 0;
	kill_streak_display_time = 0; kill_streak_last_time = 0; kill_streak_text = "";
	heartbeat_time = 0; ambient_dust_time = 0;
	nzp_is_indoor = FALSE; nzp_fog_check_time = 0;
	nzp_last_indoor_state = FALSE; nzp_fog_initialized = FALSE;
	autocvar(nzp_fog_enabled, 1);
""",
    "CSQC_Init", "// NZP-M9 Initialisierungen")

patch(CLIENT_MAIN, 'autocvar(in_aimassist, 0);',
    'autocvar(in_aimassist, 1);\n\tcvar_set("in_aimassist", "1");',
    "Aim Assist", 'cvar_set("in_aimassist", "1");')

PARSE_PATTERN = r'(case\s+CSQC_EVENT_BROADCASTMESSAGE\s*:\s*broadcast_type\s*=\s*readbyte\s*\(\s*\)\s*;\s*broadcast_time\s*=\s*time\s*\+\s*5\s*;\s*broadcast_num\s*=\s*readbyte\s*\(\s*\)\s*;\s*break\s*;)'
PARSE_REPLACEMENT = r'''\1
		case CSQC_EVENT_POWERUPTOAST:
			hud_toast_string = readstring();
			hud_toast_starttime = time;
			hud_toast_endtime = time + 3;
			break;'''
patch_regex(CLIENT_MAIN, PARSE_PATTERN, PARSE_REPLACEMENT, "POWERUPTOAST", "case CSQC_EVENT_POWERUPTOAST:")

# ==========================================
# TEIL 5: ATMOSPHÄRE & HUD
# ==========================================
ATMO_FUNCS = """
float() CSQC_IsIndoor =
{
	vector start = playerOrigin + [0, 0, 16];
	vector end = start + [0, 0, 4096];
	traceline(start, end, false, world);
	if (trace_fraction == 1) return FALSE;
	if (pointcontents(trace_endpos) == CONTENT_SKY) return FALSE;
	return TRUE;
};

void() CSQC_UpdateAtmosphere =
{
	if (time < nzp_fog_check_time) return;
	nzp_fog_check_time = time + 0.5;
	if (!cvar("nzp_fog_enabled")) {
		if (cvar("r_fog")) cvar_set("r_fog", "0");
		return;
	}
	float indoor = CSQC_IsIndoor();
	nzp_is_indoor = indoor;
	if (indoor != nzp_last_indoor_state || !nzp_fog_initialized) {
		nzp_last_indoor_state = indoor;
		nzp_fog_initialized = TRUE;
		if (indoor) {
			cvar_set("r_fog", "1"); cvar_set("r_fog_color", "0.15 0.15 0.20");
			cvar_set("r_fog_start", "80"); cvar_set("r_fog_end", "700");
		} else {
			cvar_set("r_fog", "1"); cvar_set("r_fog_color", "0.45 0.45 0.50");
			cvar_set("r_fog_start", "500"); cvar_set("r_fog_end", "3000");
		}
	}
};

"""
patch(CLIENT_MAIN, "noref void(float width, float height, float menushown) CSQC_UpdateView =",
    ATMO_FUNCS + "noref void(float width, float height, float menushown) CSQC_UpdateView =",
    "Atmosphäre-Funktionen", "float() CSQC_IsIndoor =")

HUD_ADDITION = """	CSQC_UpdateAtmosphere();
	renderscene();

	// --- NZP-M9 CUSTOM HUD ---
	if (time < hitmark_time) {
		if (hitmark_type == 1) dmg_text_str = "KILL";
		else dmg_text_str = "HIT";
		dmg_text_time = time + 0.8;
	}
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
		dmg_indicator_alpha = 0.6; screen_shake_intensity += 3;
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
			if (player_ent.playernum == player_localnum + 1) { real_kills = player_ent.kills; break; }
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
		sui_end();
	}"""
patch(CLIENT_MAIN, "\t//does what you think it does\n\trenderscene();", HUD_ADDITION, "HUD", "--- NZP-M9 CUSTOM HUD ---")

# ==========================================
# TEIL 6: POWERUPS (Runaway-Loop & Max-Ammo-Toast)
# ==========================================
RUNAWAY_PATTERN = r'float\s+perk_to_give\s*=\s*0;[\s\S]{0,300}?float\s+found_perk_for_player\s*=\s*false;[\s\S]*?while\s*\(\s*!\s*found_perk_for_player\s*\)\s*\{[\s\S]*?if\s*\(\s*perk_to_give\s*!=\s*0\s*\)\s*found_perk_for_player\s*=\s*true;\s*\}'
RUNAWAY_REPLACEMENT = """float perk_to_give = 0;
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
patch_regex(POWERUPS_QC, RUNAWAY_PATTERN, RUNAWAY_REPLACEMENT, "Runaway-Fix", "NZP-M9 FIX: Deterministische")

MAXAMMO_TOAST_ANCHOR = """	if (powerup_id == PU_MAXAMMO && game_modifiers.gameplay.powerups.powerup_max_ammo.show_toast)
		return game_modifiers.gameplay.powerups.powerup_max_ammo.toast;"""
MAXAMMO_TOAST_REPLACEMENT = """	// NZP-M9 FIX: Max Ammo Toast deaktivieren (verhindert Netzwerk-Desync-Crash)
	if (powerup_id == PU_MAXAMMO)
		return "";"""
patch(POWERUPS_QC, MAXAMMO_TOAST_ANCHOR, MAXAMMO_TOAST_REPLACEMENT,
      "Max Ammo Toast deaktivieren", "// NZP-M9 FIX: Max Ammo Toast deaktivieren")

# ==========================================
# TEIL 7: BEIN-DISMEMBERMENT (Crawler-Transformation)
# ==========================================
MAKECRAWLER_FWD_ANCHOR = """void() W_PutOut;
float(entity who, float weapon) Zombie_HeadCanGib;"""
MAKECRAWLER_FWD_REPLACEMENT = """void() W_PutOut;
float(entity who, float weapon) Zombie_HeadCanGib;
void(entity who) makeCrawler;"""
patch(WEAPON_CORE_QC, MAKECRAWLER_FWD_ANCHOR, MAKECRAWLER_FWD_REPLACEMENT,
      "makeCrawler Forward-Deklaration", "void(entity who) makeCrawler;")

ensure_line(SERVER_CUSTOM_QC, ".entity legs;", "legs Entity-Feld")

LEGS_SPAWN_ANCHOR = """	zSpawn.rarm = spawn();
	zSpawn.rarm.classname = "in_ai_zombie_rarm";
	zSpawn.rarm.owner = zSpawn;
	zSpawn.rarm.solid = SOLID_NOT;
	zSpawn.rarm.movetype = MOVETYPE_STEP;
	zSpawn.rarm.takedamage = DAMAGE_NO;

#ifndef FTE
	updateLimb (zSpawn, 2, zSpawn.rarm);
#endif // FTE
"""
LEGS_SPAWN_REPLACEMENT = LEGS_SPAWN_ANCHOR + """
	// NZP-M9: Bein-Entity
	zSpawn.legs = spawn();
	zSpawn.legs.classname = "in_ai_zombie_legs";
	zSpawn.legs.owner = zSpawn;
	zSpawn.legs.solid = SOLID_NOT;
	zSpawn.legs.movetype = MOVETYPE_STEP;
	zSpawn.legs.takedamage = DAMAGE_NO;
"""
patch(ZOMBIE_CORE_QC, LEGS_SPAWN_ANCHOR, LEGS_SPAWN_REPLACEMENT, "Legs spawn", 'zSpawn.legs = spawn();')

LEGS_HITBOX_ANCHOR = """	szombie.rarm.solid = SOLID_CORPSE;
	szombie.rarm.movetype = MOVETYPE_STEP;
	szombie.rarm.classname = "ai_zombie_rarm";
	szombie.rarm.takedamage = DAMAGE_YES;
"""
LEGS_HITBOX_REPLACEMENT = LEGS_HITBOX_ANCHOR + """
	// NZP-M9: Bein-Hitbox (unsichtbar)
	szombie.legs.solid = SOLID_CORPSE;
	szombie.legs.movetype = MOVETYPE_STEP;
	szombie.legs.classname = "ai_zombie_legs";
	szombie.legs.takedamage = DAMAGE_YES;
	setsize(szombie.legs, '-8 -8 -32', '8 8 0');
"""
patch(ZOMBIE_CORE_QC, LEGS_HITBOX_ANCHOR, LEGS_HITBOX_REPLACEMENT, "Legs hitbox", 'szombie.legs.solid = SOLID_CORPSE;')

ZOMBIE_THINK_ANCHOR = """void() Zombie_Think = //called every frame for zombies
{
	if (Zombie_ProcessDistanceDespawn())
		return;
"""
ZOMBIE_THINK_REPLACEMENT = """void() Zombie_Think = //called every frame for zombies
{
	if (Zombie_ProcessDistanceDespawn())
		return;

	// NZP-M9: Bein-Hitbox dem Zombie folgen lassen
	if (self.legs)
		setorigin(self.legs, self.origin);
"""
patch(ZOMBIE_CORE_QC, ZOMBIE_THINK_ANCHOR, ZOMBIE_THINK_REPLACEMENT, "Legs folgen", "// NZP-M9: Bein-Hitbox dem Zombie folgen lassen")

LEGS_CLEANUP_ANCHOR = """	if (self.classname != "ai_dog") {
		setmodel(self.larm,"");
		setmodel(self.rarm,"");
		setmodel(self.head,"");

#ifdef FTE

		remove(self.larm);
		remove(self.rarm);
		remove(self.head);

#else

		updateLimb (self, 0, world);
		updateLimb (self, 1, world);
		updateLimb (self, 2, world);

#endif // FTE

	}
"""
LEGS_CLEANUP_REPLACEMENT = """	if (self.classname != "ai_dog") {
		setmodel(self.larm,"");
		setmodel(self.rarm,"");
		setmodel(self.head,"");
		if (self.legs) setmodel(self.legs, "");

#ifdef FTE
		remove(self.larm);
		remove(self.rarm);
		remove(self.head);
		if (self.legs) remove(self.legs);
#else
		updateLimb (self, 0, world);
		updateLimb (self, 1, world);
		updateLimb (self, 2, world);
#endif // FTE

	}
"""
patch(ZOMBIE_CORE_QC, LEGS_CLEANUP_ANCHOR, LEGS_CLEANUP_REPLACEMENT, "Legs cleanup", "if (self.legs) setmodel(self.legs, \"\");")

LEGS_DAMAGE_ANCHOR = """			if (body_ent.rarm.washit) {
				total_dmg += body_ent.rarm.hitamount;
				body_ent.rarm.health -= body_ent.rarm.hitamount;

				if (WepDef_WeaponCanGibEnemy(self.weapon) && body_ent.rarm.owner.larm.deadflag && body_ent.rarm.deadflag) {
					
					makevectors(body_ent.rarm.owner.angles);
					where = body_ent.rarm.owner.origin + (body_ent.rarm.view_ofs_x * v_right) + (body_ent.rarm.view_ofs_y * v_forward) + (body_ent.rarm.view_ofs_z * v_up);
					spawn_gibs(where);
					if (hit_sound != "sounds/zombie/headshot.wav") hit_sound = "sounds/zombie/gib.wav";
					
					body_ent.rarm.deadflag = false;
					body_ent.rarm.solid = SOLID_NOT;
					setmodel(body_ent.rarm,"");
					body_ent.rarm.frame = 0;

#ifndef FTE

					updateLimb (body_ent.rarm.owner, 2, world);

#endif // FTE

				}

				body_ent.rarm.washit = 0;
				body_ent.rarm.hitamount = 0;
			}
"""
LEGS_DAMAGE_REPLACEMENT = LEGS_DAMAGE_ANCHOR + """
			// NZP-M9: Beine (Hitbox-only) - Gib + Crawler-Transformation
			if (body_ent.legs && body_ent.legs.washit) {
				total_dmg += body_ent.legs.hitamount;
				body_ent.legs.health -= body_ent.legs.hitamount;

				if (WepDef_WeaponCanGibEnemy(self.weapon) && body_ent.legs.deadflag) {
					makevectors(body_ent.legs.owner.angles);
					where = body_ent.legs.owner.origin
						+ (body_ent.legs.view_ofs_x * v_right)
						+ (body_ent.legs.view_ofs_y * v_forward)
						+ (body_ent.legs.view_ofs_z * v_up);
					spawn_gibs(where);
					hit_sound = "sounds/zombie/gib.wav";

					body_ent.legs.deadflag = false;
					body_ent.legs.solid = SOLID_NOT;
					setmodel(body_ent.legs, "");
					body_ent.legs.frame = 0;

					// NZP-M9: Zombie zum Crawler machen
					if (body_ent.classname == "ai_zombie" && body_ent.health > 0 && body_ent.crawling == 0) {
						makeCrawler(body_ent);
					}
				}

				body_ent.legs.washit = 0;
				body_ent.legs.hitamount = 0;
			}
"""
patch(WEAPON_CORE_QC, LEGS_DAMAGE_ANCHOR, LEGS_DAMAGE_REPLACEMENT, "Legs Parse_Damage + Crawler", "NZP-M9: Beine (Hitbox-only) - Gib + Crawler-Transformation")

# ==========================================
# TEIL 8: GORE/ATMOSPHÄRE-MENÜ (MENU_M9_ATMO)
# ==========================================
# 8.1 Enum erweitern
MENU_DEFS_PATTERN = r'(MENU_GAMESETTINGS\s*)\}'
MENU_DEFS_REPLACEMENT = r'\1, MENU_M9_ATMO }'
patch_regex(MENU_DEFS, MENU_DEFS_PATTERN, MENU_DEFS_REPLACEMENT, "MENU_M9_ATMO", "MENU_M9_ATMO")
patch(MENU_DEFS, 'void(float wantmode) m_toggle;',
      'void(float wantmode) m_toggle;\nvoid() Menu_M9_Atmosphere;\nstring(string prev_id) Menu_M9_Atmo_GetNextButton;\nstring(string next_id) Menu_M9_Atmo_GetPreviousButton;',
      "Menu_M9_Atmosphere Forward", "void() Menu_M9_Atmosphere;")

# 8.2 menu_m9_atmo.qc erstellen
if not MENU_M9_ATMO.exists():
    MENU_M9_ATMO.write_text(r'''// NZP-M9: Atmosphere & Gore Menü
string menu_m9_atmo_buttons[9] = {
    "m9_atmo_perf", "m9_atmo_balanced", "m9_atmo_cinematic",
    "m9_atmo_particles", "m9_atmo_decals", "m9_atmo_fog",
    "m9_atmo_fog_density", "m9_atmo_gore_level", "m9_atmo_back"
};
string(string prev_id) Menu_M9_Atmo_GetNextButton = {
    if (prev_id == "") return menu_m9_atmo_buttons[0];
    string ret = menu_m9_atmo_buttons[0];
    for(float i = 0; i < menu_m9_atmo_buttons.length; i++) {
        if (menu_m9_atmo_buttons[i] == prev_id) {
            if (i + 1 >= menu_m9_atmo_buttons.length) break;
            ret = menu_m9_atmo_buttons[i + 1]; break;
        }
    }
    return ret;
};
string(string next_id) Menu_M9_Atmo_GetPreviousButton = {
    if (next_id == "") return menu_m9_atmo_buttons[menu_m9_atmo_buttons.length - 1];
    string ret = menu_m9_atmo_buttons[menu_m9_atmo_buttons.length - 1];
    for(float i = menu_m9_atmo_buttons.length - 1; i > 0; i--) {
        if (menu_m9_atmo_buttons[i] == next_id) {
            if (i - 1 < 0) break;
            ret = menu_m9_atmo_buttons[i - 1]; break;
        }
    }
    return ret;
};
void() Menu_M9_Atmo_Performance = { Menu_PlaySound(MENU_SND_ENTER); cvar_set("nzp_particles", "0"); cvar_set("nzp_decals", "0"); cvar_set("nzp_fog_enabled", "0"); cvar_set("r_fog", "0"); cvar_set("cl_gibfilter", "1"); };
void() Menu_M9_Atmo_Balanced = { Menu_PlaySound(MENU_SND_ENTER); cvar_set("nzp_particles", "1"); cvar_set("nzp_decals", "1"); cvar_set("nzp_fog_enabled", "1"); cvar_set("r_fog", "1"); cvar_set("r_fog_start", "500"); cvar_set("r_fog_end", "3000"); cvar_set("r_fog_color", "0.45 0.45 0.50"); cvar_set("cl_gibfilter", "0"); };
void() Menu_M9_Atmo_Cinematic = { Menu_PlaySound(MENU_SND_ENTER); cvar_set("nzp_particles", "1"); cvar_set("nzp_decals", "1"); cvar_set("nzp_fog_enabled", "1"); cvar_set("r_fog", "1"); cvar_set("r_fog_start", "80"); cvar_set("r_fog_end", "700"); cvar_set("r_fog_color", "0.15 0.15 0.20"); cvar_set("cl_gibfilter", "0"); };
void() Menu_M9_Atmo_ToggleParticles = { Menu_PlaySound(MENU_SND_ENTER); if (cvar("nzp_particles")) cvar_set("nzp_particles", "0"); else cvar_set("nzp_particles", "1"); };
void() Menu_M9_Atmo_ToggleDecals = { Menu_PlaySound(MENU_SND_ENTER); if (cvar("nzp_decals")) cvar_set("nzp_decals", "0"); else cvar_set("nzp_decals", "1"); };
void() Menu_M9_Atmo_ToggleFog = { Menu_PlaySound(MENU_SND_ENTER); if (cvar("nzp_fog_enabled")) cvar_set("nzp_fog_enabled", "0"); else cvar_set("nzp_fog_enabled", "1"); };
void() Menu_M9_Atmo_CycleFogDensity = { Menu_PlaySound(MENU_SND_ENTER); float current = cvar("r_fog_start"); if (current >= 500) { cvar_set("r_fog_start", "80"); cvar_set("r_fog_end", "700"); cvar_set("r_fog_color", "0.15 0.15 0.20"); } else if (current >= 80) { cvar_set("r_fog_start", "500"); cvar_set("r_fog_end", "3000"); cvar_set("r_fog_color", "0.45 0.45 0.50"); } else { cvar_set("r_fog_start", "2048"); cvar_set("r_fog_end", "4096"); cvar_set("r_fog_color", "0.3 0.3 0.35"); } };
void() Menu_M9_Atmo_ToggleGore = { Menu_PlaySound(MENU_SND_ENTER); if (cvar("cl_gibfilter")) cvar_set("cl_gibfilter", "0"); else cvar_set("cl_gibfilter", "1"); };
void() Menu_M9_Atmosphere = {
    Menu_DrawBackground(); Menu_DrawTitle("ATMOSPHERE & GORE"); Menu_DrawMapPanel();
    Menu_Button(1, "m9_atmo_perf", "PERFORMANCE", "Maximum FPS: disables fog, particles and decals.") ? Menu_M9_Atmo_Performance() : 0;
    Menu_Button(2, "m9_atmo_balanced", "BALANCED", "Default atmosphere, full particles and decals.") ? Menu_M9_Atmo_Balanced() : 0;
    Menu_Button(3, "m9_atmo_cinematic", "CINEMATIC", "Dense fog, full particles, full gore.") ? Menu_M9_Atmo_Cinematic() : 0;
    Menu_DrawDivider(3.25);
    Menu_Button(4, "m9_atmo_particles", "PARTICLES", "Toggle ambient dust.") ? Menu_M9_Atmo_ToggleParticles() : 0;
    Menu_DrawOptionValue(4, cvar("nzp_particles") ? "ENABLED" : "DISABLED");
    Menu_Button(5, "m9_atmo_decals", "DECALS", "Toggle blood decals.") ? Menu_M9_Atmo_ToggleDecals() : 0;
    Menu_DrawOptionValue(5, cvar("nzp_decals") ? "ENABLED" : "DISABLED");
    Menu_Button(6, "m9_atmo_fog", "FOG", "Toggle volumetric fog.") ? Menu_M9_Atmo_ToggleFog() : 0;
    Menu_DrawOptionValue(6, cvar("nzp_fog_enabled") ? "ENABLED" : "DISABLED");
    Menu_Button(7, "m9_atmo_fog_density", "FOG DENSITY", "Cycle fog density.") ? Menu_M9_Atmo_CycleFogDensity() : 0;
    float fog_start = cvar("r_fog_start"); string fog_label = "PERFORMANCE";
    if (fog_start < 500) fog_label = "CINEMATIC"; else if (fog_start < 2048) fog_label = "BALANCED";
    Menu_DrawOptionValue(7, fog_label);
    Menu_Button(8, "m9_atmo_gore_level", "GORE FILTER", "Toggle gib filter.") ? Menu_M9_Atmo_ToggleGore() : 0;
    Menu_DrawOptionValue(8, cvar("cl_gibfilter") ? "FILTERED" : "FULL");
    Menu_Button(-1, "m9_atmo_back", "BACK", "Return to Configuration Menu.") ? current_menu = MENU_OPTIONS : 0;
    sui_pop_frame();
};
''', encoding="utf-8")

# 8.3 menu_opts.qc: Array + Button (fortlaufende Order!)
patch(MENU_OPTS,
    'string menu_opts_buttons[6] = {"om_video", "om_audio", "om_binds", "om_acces", "om_console", "om_back"};',
    'string menu_opts_buttons[7] = {"om_video", "om_audio", "om_binds", "om_acces", "om_m9atmo", "om_console", "om_back"};',
    "menu_opts_buttons-Array erweitern",
    '"om_m9atmo", "om_console"')

patch(MENU_OPTS,
    'Menu_Button(4, "om_acces", "ACCESSIBILITY", "Content, Interface, and Readability options.") ? current_menu = MENU_ACCESSIBILITY : 0;',
    'Menu_Button(4, "om_acces", "ACCESSIBILITY", "Content, Interface, and Readability options.") ? current_menu = MENU_ACCESSIBILITY : 0;\n    Menu_Button(5, "om_m9atmo", "ATMOSPHERE & GORE", "Fog, particles and gore options.") ? current_menu = MENU_M9_ATMO : 0;',
    "Atmo-Button einfügen",
    '"om_m9atmo"')

patch(MENU_OPTS, 'Menu_DrawDivider(5);', 'Menu_DrawDivider(6);', "Divider", 'Menu_DrawDivider(6);')
patch(MENU_OPTS, 'Menu_Button(5.25, "om_console"', 'Menu_Button(6.25, "om_console"', "Console-Button", 'Menu_Button(6.25, "om_console"')

# 8.4 In .src-Dateien einbinden
for src_path in [PROGS / "menu.src", PROGS / "csqc.src"]:
    if src_path.exists():
        content = src_path.read_text(encoding="utf-8")
        if "menu_m9_atmo.qc" not in content and "menu_opts.qc" in content:
            content = content.replace("menu_opts.qc", "menu_m9_atmo.qc\nmenu_opts.qc", 1)
            src_path.write_text(content, encoding="utf-8")
            print(f"[OK]   {src_path.name}: menu_m9_atmo.qc eingebunden")

print("\n=== Alle Patches erfolgreich angewendet (idempotent). ===")
sys.exit(0)
