#!/usr/bin/env python3
# NZP-M9 Patches: Alle Features (Gore, HUD, Match-Fix, Atmosphäre)

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

def force_replace_regex(path: Path, pattern: str, replacement: str, description: str):
    if not path.exists(): sys.exit(1)
    content = path.read_text(encoding="utf-8")
    new_content, count = re.subn(pattern, replacement, content, count=1, flags=re.DOTALL)
    if count >= 1:
        path.write_text(new_content, encoding="utf-8")
        print(f"[OK]   {description}")
    else:
        print(f"[FATAL] {description}: Konnte nicht ersetzt werden!")

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
CLIENT_PARTICLES = CLIENT / "particles.qc"
FTE_QC = CLIENT / "defs/fte.qc"
MENU_DEFS = BASE / "defs/menu_defs.qc"
MENU_CRED = BASE / "menu_cred.qc"
CUSTOM_QC = CLIENT / "defs/custom.qc"

# ==========================================
# TEIL 0: BASIS & CUSTOM.QC
# ==========================================
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
# TEIL 1: SERVER-BROWSER & A/B Tausch
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

patch(SUI_SYS, "float(float evtype, float scanx, float chary, float devid) sui_input_event =\n{\n\tswitch (evtype)",
    """float(float evtype, float scanx, float chary, float devid) sui_input_event =
{
\tif (evtype == IE_KEYDOWN || evtype == IE_KEYUP) {
\t\tif (scanx == K_GP_A) scanx = K_ESCAPE;
\t\telse if (scanx == K_GP_B) scanx = K_ENTER;
\t}
\tswitch (evtype)""",
    "FIX: A/B Button Swap", "// NZP-M9: A = Zurueck")

# ==========================================
# TEIL 2: VIDEO-MENÜ
# ==========================================
content = MENU_MAIN_MENU.read_text(encoding="utf-8")
content = content.replace("50 + (order * 25)", "50 + (order * 20)")
content = content.replace("-50 + (order * 25)", "-50 + (order * 20)")
content = content.replace("is_hovered ? [1, 0, 0] : [1, 1, 1]", "is_hovered ? [0.8, 0.2, 1] : [1, 1, 1]") 
content = content.replace("[0.4, 0, 0]", "[0.6, 0, 0.8]") 
MENU_MAIN_MENU.write_text(content, encoding="utf-8")

force_replace_regex(MENU_VIDE, r"string menu_video_buttons\[\d+\] = \{.*?\};", 'string menu_video_buttons[16] = {"vm_resol", "vm_fulls", "vm_shfps", "vm_maxps", "vm_vsync", "vm_fov", "vm_gamma", "vm_uwide", "vm_parts", "vm_decal", "vm_dynlgt", "vm_shdw", "vm_bob", "vm_filtr", "vm_apply", "vm_back"};', "E1: Button-Array überschreiben")
force_replace_regex(MENU_VIDE, r"float current_selected_vidmode;.*?float current_filter;", '''float current_selected_vidmode;
float current_fullscreen;
float current_showfps;
float current_vsync;
float current_ultrawide;
float current_particles;
float current_decals;
float current_dynlight;
float current_shadows;
float current_bob;
float current_filter;''', "E2: Variablen überschreiben")
force_replace_regex(MENU_VIDE, r"void\(\) Menu_Video_StoreCurrentSettings =\s*\{.*?\}", '''void() Menu_Video_StoreCurrentSettings =
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
}''', "E3: StoreCurrentSettings überschreiben")
if "Menu_Video_UpdateDynLight" not in MENU_VIDE.read_text(encoding="utf-8"):
    patch(MENU_VIDE, "void() Menu_Video_UpdateUltrawide =", '''void() Menu_Video_UpdateDecals = { Menu_PlaySound(MENU_SND_ENTER); current_decals = !current_decals; cvar_set("nzp_decals", ftos(current_decals)); };
void() Menu_Video_UpdateDynLight = { Menu_PlaySound(MENU_SND_ENTER); current_dynlight = !current_dynlight; cvar_set("r_dynamic", ftos(current_dynlight)); };
void() Menu_Video_UpdateShadows = { Menu_PlaySound(MENU_SND_ENTER); current_shadows = !current_shadows; cvar_set("r_shadows", ftos(current_shadows)); };
void() Menu_Video_UpdateBob = { Menu_PlaySound(MENU_SND_ENTER); current_bob = !current_bob; cvar_set("cl_bobup", current_bob ? "0.02" : "0"); cvar_set("cl_bobside", current_bob ? "0.02" : "0"); };
void() Menu_Video_UpdateUltrawide =''', "E4: Update-Funktionen", "Menu_Video_UpdateDynLight")

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
force_replace_regex(MENU_VIDE, r"void\(\) Menu_Video\s*=\s*\{.*?\n\};", menu_video_function, "E5: Menu_Video überschreiben")
patch(MAIN_QC, 'build_datetime = fgets(file);', 'build_datetime = "M9 Pro Custom Build";\n        // build_datetime = fgets(file);', "Custom Version String", "M9 Pro Custom Build")

# ==========================================
# TEIL 3: MAIN.QC - INITIALISIERUNG
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
""",
    "Initialisiere Variablen in CSQC_Init", "// NZP-M9 Initialisierungen")

# ==========================================
# TEIL 4: CSQC_Parse_Event (BUGFIX: KEIN RETURN!)
# ==========================================
patch(CLIENT_MAIN, 'case 3:\n\t\t\t\t\tif (hitmark_ignore_time > time)\n\t\t\t\t\t\treturn;\n\n\t\t\t\t\thitmark_type = var_1;',
    """case 3:
					if (hitmark_ignore_time <= time) {
						hitmark_type = var_1;
						
						// Sound
						if (time > hitmarker_sound_time) {
							if (hitmark_type == 1) localsound_enhanced("sounds/zombie/headshot.wav", 0, 0.7);
							else localsound_enhanced("sounds/weapons/knife/knife_hit.wav", 0, 0.5);
							hitmarker_sound_time = time + 0.1;
						}
						
						fov_punch_time = time + 0.08;

						// Kill Streak mit strikter Deduplizierung
						if (hitmark_type == 1) {
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
						
						CSQC_SpawnClientGore();
						
						if (hitmark_type == 1) dmg_text_str = "KILL";
						else dmg_text_str = "HIT";
						dmg_text_time = time + 0.8;
						
						if (hitmark_type == 1) {
							hitmark_time = time + 0.2;
							hitmark_ignore_time = time + 0.2;
						} else {
							hitmark_time = time + 0.3;
						}
					}
					break;""",
    "CSQC_Parse_Event: BUGFIX (kein return) + Kill-Streak dedupe", "hitmark_ignore_time <= time")

# ==========================================
# TEIL 5: CSQC_UpdateView (Kamera, HUD, Crosshair, Atmosphäre)
# ==========================================
# 5.1 Kamera (Screen-Shake & FOV-Punch)
patch(CLIENT_MAIN, "\tCamera_AimSnap(camang);\n\n\tcamang[0] += cam_snap_difference[0];\n\tcamang[1] += cam_snap_difference[1];\n\tcamang[2] += cam_snap_difference[2];\n\n\tsetviewprop(VF_ANGLES, camang);",
    """\tCamera_AimSnap(camang);
	camang[0] += cam_snap_difference[0];
	camang[1] += cam_snap_difference[1];
	camang[2] += cam_snap_difference[2];
	
	if (screen_shake_intensity > 0) {
		camang[0] += (random() * 2 - 1) * screen_shake_intensity * 0.3;
		camang[1] += (random() * 2 - 1) * screen_shake_intensity * 0.3;
		camang[2] += (random() * 2 - 1) * screen_shake_intensity * 0.1;
	}
	setviewprop(VF_ANGLES, camang);

	float base_fov = autocvar(fov, 90) * getstatf(STAT_VIEWZOOM);
	if (time < fov_punch_time) {
		float punch_factor = (fov_punch_time - time) / 0.08;
		base_fov = base_fov - (punch_factor * 8);
	}
	setviewprop(VF_AFOV, base_fov);""",
    "CSQC_UpdateView: Kamera-Effekte", "// NZP-M9: Screen-Shake")

# 5.2 Fadenkreuz deaktivieren
patch(CLIENT_MAIN, "setviewprop(VF_DRAWCROSSHAIR, 0);", "setviewprop(VF_DRAWCROSSHAIR, 0);\n\tsetviewprop(VF_DRAWCROSSHAIR, 0);", "Disable default Crosshair", "setviewprop(VF_DRAWCROSSHAIR, 0);\n\tsetviewprop(VF_DRAWCROSSHAIR, 0);")

# 5.3 HUD & Custom Crosshair & Low-Health
patch(CLIENT_MAIN, "\tif (cvar(\"chase_active\")) {\n\t\tChase_Update();\n\t}\n\n\t//does what you think it does\n\trenderscene();",
    """\tif (cvar("chase_active")) {
\t\tChase_Update();
\t}

	//does what you think it does
\trenderscene();

\t// --- NZP-M9 CUSTOM HUD ---
	
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
	
	// Low-Health Effekt
	if (current_health < 30 && !(getstatf(STAT_PERKS) & P_DEAD) && !getstatf(STAT_WEAPONZOOM)) {
		float pulse = (sin(cltime * 8) + 1) * 0.5;
		drawfill([0, 0], [g_width, g_height], [1, 0, 0], pulse * 0.4, 0);
		if (time > heartbeat_time) {
			localsound_enhanced("sounds/player/heart.wav", 0, 1.0);
			heartbeat_time = time + 1.0;
		}
	}
	
	// Ambient Dust (Atmosphäre)
	if (time > ambient_dust_time && cvar("nzp_particles")) {
		ambient_dust_time = time + 0.1;
		vector view_ang = getviewprop(VF_ANGLES);
		makevectors(view_ang);
		vector dust_pos = getviewprop(VF_ORIGIN) + v_forward * 200 + v_right * (random()*400-200) + v_up * (random()*400-200);
		pointparticles(particleeffectnum("weapons.impact"), dust_pos, '0 0 0', 1);
	}
	
	// Custom Dynamic Crosshair
	if (!getstatf(STAT_WEAPONZOOM) && !cvar("chase_active")) {
		float spread = 4.0 + vlen(playerVelocity) * 0.05 + fabs(gun_kick[0]) * 2.0;
		vector cx_color = [0.8, 0.2, 1]; // Lila
		if (current_health < 30) cx_color = [1, 0, 0]; // Rot bei Low-Health
		
		drawfill([g_width*0.5 - 1, g_height*0.5 - spread - 6], [2, 6], cx_color, 1, 0); // Top
		drawfill([g_width*0.5 - 1, g_height*0.5 + spread], [2, 6], cx_color, 1, 0); // Bottom
		drawfill([g_width*0.5 - spread - 6, g_height*0.5 - 1], [6, 2], cx_color, 1, 0); // Left
		drawfill([g_width*0.5 + spread, g_height*0.5 - 1], [6, 2], cx_color, 1, 0); // Right
		drawfill([g_width*0.5 - 1, g_height*0.5 - 1], [2, 2], cx_color, 0.5, 0); // Dot
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
		sui_end();
	}""",
    "CSQC_UpdateView: Custom HUD, Crosshair, Low-Health & Dust", "--- NZP-M9 CUSTOM HUD ---")

patch(CLIENT_MAIN, "noref void() CSQC_WorldLoaded =", "void() CSQC_SpawnClientGore;\n\nnoref void() CSQC_WorldLoaded =", "Forward-Deklaration für CSQC_SpawnClientGore", "void() CSQC_SpawnClientGore;")

print("\n=== Alle Patches erfolgreich angewendet. ===")
sys.exit(0)
