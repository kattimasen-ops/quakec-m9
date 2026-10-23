#!/usr/bin/env python3
# NZP-M9 Patches: Server-Browser, Performance, Custom Handheld Edits & Advanced Particles

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

def force_replace_regex(path: Path, pattern: str, replacement: str, description: str):
    if not path.exists(): sys.exit(1)
    content = path.read_text(encoding="utf-8")
    new_content, count = re.subn(pattern, replacement, content, count=1, flags=re.DOTALL)
    if count >= 1:
        path.write_text(new_content, encoding="utf-8")
        print(f"[OK]   {description}")
    else:
        print(f"[FATAL] {description}: Konnte nicht ersetzt werden!")
        sys.exit(1)

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
PARTICLES_DIR = Path("particles")

# ==========================================
# TEIL 0: AUFRÄUMEN & BASIS
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
# TEIL 2: VIDEO-MENÜ & CUSTOM OPTIONEN
# ==========================================

# Zeilenabstand im Menü verkleinern
content = MENU_MAIN_MENU.read_text(encoding="utf-8")
content = content.replace("50 + (order * 25)", "50 + (order * 20)")
content = content.replace("-50 + (order * 25)", "-50 + (order * 20)")
# Lila Farben
content = content.replace("is_hovered ? [1, 0, 0] : [1, 1, 1]", "is_hovered ? [0.8, 0.2, 1] : [1, 1, 1]") 
content = content.replace("[0.4, 0, 0]", "[0.6, 0, 0.8]") 
MENU_MAIN_MENU.write_text(content, encoding="utf-8")

force_replace_regex(
    MENU_VIDE,
    r"string menu_video_buttons\[\d+\] = \{.*?\};",
    'string menu_video_buttons[16] = {"vm_resol", "vm_fulls", "vm_shfps", "vm_maxps", "vm_vsync", "vm_fov", "vm_gamma", "vm_uwide", "vm_parts", "vm_decal", "vm_dynlgt", "vm_shdw", "vm_bob", "vm_filtr", "vm_apply", "vm_back"};',
    "E1: Button-Array überschreiben"
)

force_replace_regex(
    MENU_VIDE,
    r"float current_selected_vidmode;.*?float current_filter;",
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
    "E2: Variablen überschreiben"
)

force_replace_regex(
    MENU_VIDE,
    r"void\(\) Menu_Video_StoreCurrentSettings =\s*\{.*?\}",
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
    "E3: StoreCurrentSettings überschreiben"
)

if "Menu_Video_UpdateDynLight" not in MENU_VIDE.read_text(encoding="utf-8"):
    patch(MENU_VIDE, "void() Menu_Video_UpdateUltrawide =", '''void() Menu_Video_UpdateDecals = { Menu_PlaySound(MENU_SND_ENTER); current_decals = !current_decals; cvar_set("nzp_decals", ftos(current_decals)); };
void() Menu_Video_UpdateDynLight = { Menu_PlaySound(MENU_SND_ENTER); current_dynlight = !current_dynlight; cvar_set("r_dynamic", ftos(current_dynlight)); };
void() Menu_Video_UpdateShadows = { Menu_PlaySound(MENU_SND_ENTER); current_shadows = !current_shadows; cvar_set("r_shadows", ftos(current_shadows)); };
void() Menu_Video_UpdateBob = { Menu_PlaySound(MENU_SND_ENTER); current_bob = !current_bob; cvar_set("cl_bobup", current_bob ? "0.02" : "0"); cvar_set("cl_bobside", current_bob ? "0.02" : "0"); };

void() Menu_Video_UpdateUltrawide =''', "E4: Update-Funktionen hinzufügen", "Menu_Video_UpdateDynLight")

menu_video_function = '''
void() Menu_Video =
{
    if (!menu_video_init)
        Menu_Video_Init();
    
    Menu_DrawBackground();
    Menu_DrawTitle("VIDEO OPTIONS");

    Menu_DrawMapPanel();

    Menu_Button(1, "vm_resol", "RESOLUTION", "Window size adjustment.") ? Menu_Video_UpdateVideoMode() : 0;
    if (current_selected_vidmode > menu_video_modes) current_selected_vidmode = 0;
    string resolution_string = sprintf("%dx%d (%d:%d)", video_modes[current_selected_vidmode].size[0], 
    video_modes[current_selected_vidmode].size[1], video_modes[current_selected_vidmode].ratio[0], 
    video_modes[current_selected_vidmode].ratio[1]);
    Menu_DrawOptionValue(1, resolution_string);

    Menu_Button(2, "vm_fulls", "FULLSCREEN", "Change Fullscreen Mode.") ? Menu_Video_UpdateFullscreen() : 0;
    string fullscreen_string = "";
    switch(current_fullscreen) {
        case 0: fullscreen_string = "DISABLED"; break;
        case 1: fullscreen_string = "ENABLED"; break;
        case 2: fullscreen_string = "BORDERLESS"; break;
        default: break;
    }
    Menu_DrawOptionValue(2, fullscreen_string);

    Menu_Button(3, "vm_shfps", "SHOW FPS", "Toggles display of FPS Values.") ? Menu_Video_UpdateShowFPS() : 0;
    string showfps_string = "";
    switch(current_showfps) {
        case 0: showfps_string = "DISABLED"; break;
        case 1: showfps_string = "ENABLED"; break;
        case 2: showfps_string = "VERBOSE"; break;
        default: break;
    }
    Menu_DrawOptionValue(3, showfps_string);

    Menu_Button(4, "vm_maxps", "MAX FPS", "Configure Maximum FPS Value.") ? 0 : 0;
    Menu_CvarSlider(4, "vm_maxps", [10, 500, 490], "cl_maxfps", true, false, false);

    Menu_Button(5, "vm_vsync", "VSYNC", "Sync Framerate with Display.") ? Menu_Video_UpdateVsync() : 0;
    string vsync_string = "";
    if (current_vsync) vsync_string = "ENABLED";
    else vsync_string = "DISABLED";
    Menu_DrawOptionValue(5, vsync_string);

    Menu_Button(6, "vm_fov", "FIELD OF VIEW", "Change Camera Field of View.") ? 0 : 0;
    Menu_CvarSlider(6, "vm_fov", [10, 150, 140], "fov", true, false, false);

    Menu_Button(7, "vm_gamma", "GAMMA", "Adjust game Black Level.") ? 0 : 0;
    Menu_CvarSlider(7, "vm_gamma", [0.3, 2, 17], "gamma", false, true, false);

    Menu_Button(8, "vm_uwide", "ULTRAWIDE MODE", "Condenses HUD closer to center of Display.") ? Menu_Video_UpdateUltrawide() : 0;
    string wide_string = "";
    if (current_ultrawide) wide_string = "ENABLED";
    else wide_string = "DISABLED";
    Menu_DrawOptionValue(8, wide_string);

    Menu_Button(9, "vm_parts", "PARTICLES", "Toggle Particle Effects for Performance.") ? Menu_Video_UpdateParticles() : 0;
    string part_string = "";
    if (current_particles) part_string = "ENABLED";
    else part_string = "DISABLED";
    Menu_DrawOptionValue(9, part_string);

    Menu_Button(10, "vm_decal", "DECALS", "Toggle Bullet Holes and Blood.") ? Menu_Video_UpdateDecals() : 0;
    string decal_string = "";
    if (current_decals) decal_string = "ENABLED";
    else decal_string = "DISABLED";
    Menu_DrawOptionValue(10, decal_string);

    Menu_Button(11, "vm_dynlgt", "DYNAMIC LIGHTS", "Toggle Realtime Lights.") ? Menu_Video_UpdateDynLight() : 0;
    string dynlgt_string = "";
    if (current_dynlight) dynlgt_string = "ENABLED";
    else dynlgt_string = "DISABLED";
    Menu_DrawOptionValue(11, dynlgt_string);

    Menu_Button(12, "vm_shdw", "SHADOWS", "Toggle Entity Shadows.") ? Menu_Video_UpdateShadows() : 0;
    string shadows_string = "";
    if (current_shadows) shadows_string = "ENABLED";
    else shadows_string = "DISABLED";
    Menu_DrawOptionValue(12, shadows_string);

    Menu_Button(13, "vm_bob", "WEAPON BOB", "Toggle Weapon Swaying.") ? Menu_Video_UpdateBob() : 0;
    string bob_string = "";
    if (current_bob) bob_string = "ENABLED";
    else bob_string = "DISABLED";
    Menu_DrawOptionValue(13, bob_string);

    Menu_Button(14, "vm_filtr", "TEXTURE FILTERING", "Choose 3D Environment Filtering Mode.") ? Menu_Video_UpdateFiltering() : 0;
    string filt_string = "";
    if (current_filter) filt_string = "NEAREST";
    else filt_string = "LINEAR";
    Menu_DrawOptionValue(14, filt_string);

    Menu_DrawDivider(14.25);
    
    Menu_Button(15, "vm_apply", "APPLY", "Save & Apply Settings.") ? Menu_Video_ApplySettings() : 0;
    Menu_Button(16, "vm_back", "BACK", "Return to Configuration Menu.") ? current_menu = MENU_OPTIONS : 0;

    sui_pop_frame();	
};'''

force_replace_regex(
    MENU_VIDE,
    r"void\(\) Menu_Video\s*=\s*\{.*?\n\};",
    menu_video_function,
    "E5: Menu_Video überschreiben (Layout fixen)"
)

patch(MAIN_QC, 'build_datetime = fgets(file);', 'build_datetime = "M9 Pro Custom Build";\n        // build_datetime = fgets(file);', "Custom Version String im Menü", "M9 Pro Custom Build")

# ==========================================
# TEIL 3: ADVANCED PARTICLES (GORE & EFFECTS)
# ==========================================

# 1. Partikel-Verzeichnis erstellen falls nicht vorhanden
PARTICLES_DIR.mkdir(parents=True, exist_ok=True)

# 2. Spikeset-Datei schreiben (basiert auf deinem Upload)
spikeset_content = """// spikeset, originally by Spike
// with contributions from TimeServ, purplehaze, Jedilamma
// and some others I probably forgot to mention
r_part rocketsmoke
{
	texture "particles/fteparticlefont.tga"
	tcoords 97 97 191 191 256
	step 8
	scale 7.5
	alpha 0.8
	die 2
	randomvel 3
	rgb 10 10 10
	blend modulate
	spawnmode spiral
	scalefactor 1
	spawnvel 5
}
r_part rockettrail
{
	texture "particles/fteparticlefont.tga"
	tcoords 97 97 191 191 256
	step 4
	scale 30
	alpha 0.3
	die 1.4
	diesubrand 0.7
	randomvel 1
	rgb 255 50 10
	rgbdelta -230 -45 -9
	gravity -25
	scalefactor 1
	assoc rocketsmoke
	spawnvel 10
}
r_part t_rocket
{
	texture "particles/fteparticlefont.tga"
	tcoords 97 97 191 191 256
	step 2
	scale 10
	alpha 0.6
	die 0.25
	rgb 255 192 128
	rgbdelta -14 -300 -300
	blend add
	assoc rockettrail
	scalefactor 0.8
	scaledelta -10
}
r_part rockettail
{
	texture "particles/fteparticlefont.tga"
	tcoords 97 97 191 191 256
	step 7
	scale 10
	alpha 0.3
	die 10
	randomvel 64
	veladd 512
	rgb 192 192 192
	gravity 100
	cliptype rockettail
}
r_part t_altrocket
{
	texture "particles/fteparticlefont.tga"
	tcoords 97 97 191 191 256
	step 4
	scale 10
	alpha 0.3
	die 0.7
	randomvel 32
	veladd 32
	rgb 255 198 128
	rgbdelta -64 0 0
	gravity -100
	blend add
	assoc rockettail
}
r_part railtrailinner
{
	step 30
	scale 5
	die 1
	alpha 0.5
	rgb 255 255 255
	blend add
	type beam
	spawnvel 2 2
}
r_part railtrail240
{
	step 15
	scale 3
	die 1
	alpha 0
	rgb 32 32 255
	rampmode delta
	ramp -255 -255 0 -2.5 0
	ramp 0 0 0 0.65 0
	ramp 0 0 0 0.65 0
	ramp 0 0 0 0.65 0
	ramp 0 0 -128 0.65 10
	blend add
	type beam
	spawnmode spiral
	spawnparam1 256
	spawnparam2 240
	spawnvel 12
	assoc railtrailinner
}
r_part railtrail120
{
	step 15
	scale 3
	die 1
	alpha 0
	rgb 32 32 255
	rampmode delta
	ramp -255 -255 0 -2.5 0
	ramp 0 0 0 0.65 0
	ramp 0 0 0 0.65 0
	ramp 0 0 0 0.65 0
	ramp 0 0 -128 0.65 10
	blend add
	type beam
	spawnmode spiral
	spawnparam1 256
	spawnparam2 120
	spawnvel 12
	assoc railtrail240
}
r_part te_railtrail
{
	step 15
	scale 3
	die 1
	alpha 0
	rgb 32 32 255
	rampmode delta
	ramp -255 -255 0 -2.5 0
	ramp 0 0 0 0.65 0
	ramp 0 0 0 0.65 0
	ramp 0 0 0 0.65 0
	ramp 0 0 -128 0.65 10
	blend add
	type beam
	spawnmode spiral
	spawnparam1 256
	spawnvel 12
	assoc railtrail120
}
r_part shortfume
{
	texture "particles/fteparticlefont.tga"
	tcoords 97 97 191 191 256
	scale 15
	scaledelta 20
	alpha 0.5
	step 8
	die 0.3
	randomvel 12
	scaledelta 0.81
	rgb 150 150 150
}
r_part t_grenade
{
	texture "particles/fteparticlefont.tga"
	tcoords 97 97 191 191 256
	step 24
	scale 16
	scaledelta 4
	alpha 0.3
	die 4
	randomvel 8
	veladd 15
	rgb 140 140 140
	rgbdelta -55 -55 -55
	gravity -50
	scalefactor 0.0
	assoc shortfume
}
r_part t_gib
{
	texture "particles/fteparticlefont.tga"
	tcoords 1 1 63 63 256 2 64
	step 32
	scale 64
	alpha 0.6
	die 1
	randomvel 64
	veladd 10
	rotationspeed 90
	rotationstart 0 360
	rgb 128 0 0
	gravity 200
	scalefactor 0.8
	scaledelta -10
	stains 5
}
r_part t_zomgib
{
	texture "particles/fteparticlefont.tga"
	tcoords 1 1 63 63 256 2 64
	step 64
	scale 64
	alpha 0.6
	die 1
	randomvel 64
	veladd 10
	rotationspeed 90
	rotationstart 0 360
	rgb 32 0 0
	gravity 200
	scalefactor 0.8
	scaledelta -10
	stains 5
}
r_part t_tracer
{
	texture "particles/fteparticlefont.tga"
	tcoords 1 97 95 191 256
	scale 15
	step 5
	alpha 0.6
	rgb 192 192 48
	die 1
	veladd 50
	randomvel 50
	friction 4
	scalefactor 0.825
}
r_part t_tracer2
{
	texture "particles/fteparticlefont.tga"
	tcoords 1 97 95 191 256
	scale 15
	step 5
	alpha 0.6
	die 1
	rgb 192 96 48
	veladd 50
	randomvel 50
	friction 4
	scalefactor 0.825
}
r_part t_tracer3
{
	texture "particles/fteparticlefont.tga"
	tcoords 1 97 95 191 256
	scale 10
	scaledelta -10
	step 5
	alpha 0.9
	die 0.75
	rgb 192 96 192
	veladd 20
	randomvel 5
	spawnmode spiral
	spawnvel 60 0
	friction 4
	scalefactor 0.825
}
r_part te_lightningblood
{
	texture "particles/fteparticlefont.tga"
	tcoords 193 97 255 159 256
	count 3
	scale 20
	alpha 0.4
	die 2
	randomvel 32
	veladd 32
	rgb 192 0 0
	rgbdelta -128 0 0
	gravity 100
	friction 1
	stains 1
	blend add
}
r_part te_blood
{
	texture "particles/fteparticlefont.tga"
	tcoords 193 97 255 159 256
	count 10
	scale 10
	alpha 0.3
	die 2
	randomvel 40
	rgb 220 0 0
	rgbdelta -100 0 0
	gravity 200
	stains 2
	scalefactor 0.9
	rotationstart 0 360
}
r_part pe_73
{
	texture "particles/fteparticlefont.tga"
	tcoords 193 97 255 159 256
	count 1
	scale 20
	alpha 0.3
	die 2
	randomvel 40
	rgb 220 0 0
	rgbdelta -100 0 0
	gravity 200
	stains 2
	scalefactor 0.9
	rotationstart 0 360
}
r_part ember
{
	count 1
	texture "particles/fteparticlefont.tga"
	tcoords 97 97 191 191 256
	rgb 255 128 76
	alpha 0
	scale 15
	scalefactor 1
	friction 8
	gravity 50
	die 1
	blend add
	randomvel 5
	veladd 1
	rampmode delta
	ramp 0 0 0 -0.5 0
	ramp 0 0 0 0.1 0
	ramp 0 0 0 0.1 0
	ramp 0 0 0 0.1 0
	ramp 0 0 0 0.1 0
	ramp 0 0 0 0.1 0
}
r_part expgib
{
	cliptype expgib
	texture "particles/fteparticlefont.tga"
	tcoords 97 97 191 191 256
	alpha 0
	count 16
	die 1
	randomvel 128
	gravity 50
	friction 2
	emit ember
	emitinterval 0.01
	spawnmode circle
}
r_part te_explosion
{
	texture "particles/fteparticlefont.tga"
	tcoords 97 97 191 191 256
	count 1
	scale 200
	scalefactor 1
	die 1
	rgb 255 128 76
	rgbdelta 0 -32 -32
	friction 1
	blend add
	assoc expgib
}
r_part gunshotsmoke
{
	texture "particles/fteparticlefont.tga"
	tcoords 1 65 31 95 256 8 32
	count 3
	scale 25
	scalefactor 1
	die 0.8
	alpha 0.12
	rgb 32 32 32
	blend add
	spawnmode ball
	spawnorg 2
	spawnvel 20
	veladd -20
}
r_part te_gunshot
{
	type texturedspark
	texture "particles/fteparticlefont.tga"
	tcoords 1 65 31 95 256 8 32
	count 3
	scale 2
	scalefactor 1
	alpha 0.5
	die 0.8
	rgb 255 128 0
	blend add
	spawnmode ball
	spawnorg 1
	spawnvel 100
	veladd -80
	friction 0.3
	gravity 400
	assoc gunshotsmoke
}
r_part spikecore
{
	texture "particles/fteparticlefont.tga"
	tcoords 1 97 95 191 256
	count 1
	scale 1
	scalefactor 1
	scaledelta 190
	die 0.1
	alpha 0.6
	rgb 255 128 0
	blend add
	assoc gunshotsmoke
}
r_part te_spike
{
	type sparkfan
	count 10
	scale 1
	scalefactor 1
	alpha 0.5
	die 0.2
	rgb 255 128 0
	blend add
	spawnmode ball
	spawnorg 12
	spawnvel 300
	assoc spikecore
}
r_part te_lavasplash
{
	texture "particles/fteparticlefont.tga"
	tcoords 129 1 191 63 256
	count 654
	scale 15
	alpha 0.7
	die 4
	randomvel 64
	rgb 255 128 128
	gravity 50
	blend add
	spawnorg 192 64
	up 48
}
r_part teleportsplashdown
{
	texture "particles/fteparticlefont.tga"
	tcoords 193 1 255 63 256
	count 32
	scale 32
	scalefactor 1
	alpha 0.3
	die 1
	veladd -52
	rgb 255 255 255
	friction 1
	spawnorg 32 0
	spawnmode uniformcircle
}
r_part te_teleportsplash
{
	texture "particles/fteparticlefont.tga"
	tcoords 193 1 255 63 256
	count 32
	scale 32
	scalefactor 1
	alpha 0.3
	die 1
	veladd 52
	rgb 255 255 255
	friction 1
	spawnorg 32 0
	spawnmode uniformcircle
	assoc teleportsplashdown
}
r_part cu_flame
{
	texture "particles/fteparticlefont.tga"
	tcoords 129 1 191 63 256
	count 1024
	scale 0.4
	scalerand 6
	scalefactor 1
	alpha 0.4
	die 0.8
	randomvel 4 24
	veladd -24
	rgb 255 128 76
	blend add
	up -8
	spawnorg 6 0
	spawnvel -15 0
}
r_part cu_torch
{
	texture "particles/fteparticlefont.tga"
	tcoords 129 1 191 63 256
	count 256
	scale 3
	scalefactor 1
	alpha 0.7
	die 0.5
	randomvel 8
	veladd -32
	rgb 255 128 76
	blend add
	spawnmode circle
	spawnorg 4 1
	spawnvel -12 -8
}
r_part explodesprite
{
	texture "particles/fteparticlefont.tga"
	tcoords 97 97 191 191 256
	count 180
	scale 70
	scaledelta -140
	scalefactor 1
	alpha 0.2
	die 0.5
	randomvel 23
	veladd -20
	rgb 255 128 76
	blend add
	spawnorg 4 1
	spawnvel -8 -2
	up -8
}
r_part ef_entityparticles
{
	texture "particles/fteparticlefont.tga"
	tcoords 1 97 95 191 256
	count 1
	scale 15
	alpha 0.2
	die 0
	veladd 16
	rgb 255 128 128
	blend add
}
r_part empshocktrail
{
	texture "particles/fteparticlefont.tga"
	tcoords 193 1 255 63 256
	step 3.2
	scale 3
	alpha 0.7
	die 0.2
	rgb 64 0 255
	blend add
	scalefactor 1
	spawnorg 12 0
}
r_part empcore
{
	texture "particles/fteparticlefont.tga"
	tcoords 193 1 255 63 256
	count 90
	scale 55
	scaledelta -110
	die 0.55
	rgb 168 128 255
	spawnmode circle
	spawnorg 12
	spawnvel -192
	blend add
	scalefactor 0.8
	emit empshocktrail
	emitinterval -1
}
r_part empflash
{
	die 0.1
	texture "particles/fteparticlefont.tga"
	tcoords 193 1 255 63 256
	alpha 1
	count 1
	scale 400
	scaledelta -4000
	alphadelta 0
	rgb 192 160 255
	blend add
	scalefactor 1
	assoc empcore
}
r_part te_tarexplosion
{
	texture "particles/fteparticlefont.tga"
	tcoords 1 97 95 191 256
	count 120
	scale 35
	die 0.75
	alpha 0.4
	rgb 128 0 255
	rampmode delta
	ramp -32 0 0 0
	ramp -32 0 0 0
	ramp -32 0 0 2
	friction -0.9
	blend add
	spawnmode uniformcircle
	spawnorg 24 0
	spawnvel 280 0
	scalefactor 1
	emit empshocktrail
	emitinterval -1
	assoc empflash
}
r_part pe_default
{
	texture "particles/fteparticlefont.tga"
	tcoords 1 97 95 191 256
	count 1
	scale 4
	veladd 15
	die 0.4
	alphadelta 0
	diesubrand 0.4
	gravity 40
	spawnorg 8
}
r_part pe_defaulttrail
{
	texture "particles/fteparticlefont.tga"
	tcoords 1 97 95 191 256
	step 12
	die 1
	scale 10
	scaledelta -10
	veladd 15
	spawnorg 1
	scalefactor 0.8
}
r_part pe_pointfile
{
	texture "particles/fteparticlefont.tga"
	tcoords 1 97 95 191 256
	count 1
	scale 50
	die 30
	alphadelta 0
	rgb 255 255 0
}
r_effect "progs/s_explod.spr" explodesprite 1
r_effect "progs/flame.spr" explodesprite 1
r_effect "progs/flame2.mdl" cu_flame 1
r_effect "progs/flame.mdl" cu_torch
r_trail "progs/e_spike1.mdl" te_railtrail
"""

(PARTICLES_DIR / "m9_spikeset.cfg").write_text(spikeset_content, encoding="utf-8")
print("[OK]   Partikel-Set 'm9_spikeset.cfg' erstellt (Spike's Gore & Explosions)")

# 3. CSQC_Init patchen, um das Partikel-Set beim Start zu laden
patch(
    CLIENT_MAIN,
    "void(float apiver, string enginename, float enginever) CSQC_Init =\n{",
    'void(float apiver, string enginename, float enginever) CSQC_Init =\n{\n\tlocalcmd("r_particledesc m9_spikeset\\n");',
    "Lade Custom Particles in CSQC_Init",
    'r_particledesc m9_spikeset'
)

print("\n=== Alle Patches erfolgreich angewendet. ===")
sys.exit(0)
