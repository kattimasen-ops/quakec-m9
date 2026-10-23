#!/usr/bin/env python3
# NZP-M9 Patches: Alle Features (HUD, HIT/KILL, Kill-Streak, Atmosphäre/Nebel,
# Coop-Browser-Navigation, A/B-Switch, Video-Optionen)
# Gore-Effekte laufen unverändert über das bestehende Partikelsystem.
# Idempotent. WICHTIG: main.qc und sui_sys.qc müssen die offizielle Struktur haben.

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
MAIN_QC = BASE / "main.qc"
CLIENT_MAIN = CLIENT / "main.qc"
FTE_QC = CLIENT / "defs/fte.qc"
MENU_DEFS = BASE / "defs/menu_defs.qc"
MENU_CRED = BASE / "menu_cred.qc"
CUSTOM_QC = CLIENT / "defs/custom.qc"

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

MENU_CRED.write_text("void() Menu_Credits = { Menu_DrawBackground(); Menu_DrawTitle(\"CREDITS\"); Menu_DrawMapPanel(); sui_text([150, 100], MENU_TEXT_MEDIUM, \"Credits are currently disabled in this build.\", [1, 1, 1], 1, 0); Menu_Button(-1, \"cr_back\", \"BACK\", \"Return to Main Menu.\") ? current_menu = MENU_MAIN : 0; sui_pop_frame(); };", encoding="utf-8")

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
# TEIL 2: SUI_SYS.QC – NAVIGATION & A/B-SWITCH
# ==========================================
SUI_FORWARD = """

// ==========================================
// NZP-M9: Forward-Deklarationen für Coop-Browser-Navigation
// ==========================================
string(string cur, float direction) Menu_Coop_Browse_Navigate;
float() Menu_Coop_Browse_EnterContainer;
"""
append_safe(SUI_SYS, SUI_FORWARD, "SUI: Forward-Deklarationen am Dateiende", "// NZP-M9: Forward-Deklarationen für Coop-Browser-Navigation")

DOWNARROW_ANCHOR = "void() _sui_menukey_downarrow = {\n\tstring current_hovered_option = _hover_actions[0];\n\tswitch(current_menu) {"
DOWNARROW_REPLACEMENT = """void() _sui_menukey_downarrow = {
\tstring current_hovered_option = _hover_actions[0];
\tif (current_menu == MENU_COOPBROWSE) {
\t\tstring nav = Menu_Coop_Browse_Navigate(current_hovered_option, 1);
\t\tif (nav != "") { _hover_actions[0] = nav; last_hovered_id = ""; _hover_action_count = 1; return; }
\t}
\tswitch(current_menu) {"""
patch(SUI_SYS, DOWNARROW_ANCHOR, DOWNARROW_REPLACEMENT,
      "C2: Downarrow um Coop-Browser-Navigation erweitern",
      "Menu_Coop_Browse_Navigate(current_hovered_option, 1)")

UPARROW_ANCHOR = "void() _sui_menukey_uparrow = {\n\tstring current_hovered_option = _hover_actions[0];\n\tswitch(current_menu) {"
UPARROW_REPLACEMENT = """void() _sui_menukey_uparrow = {
\tstring current_hovered_option = _hover_actions[0];
\tif (current_menu == MENU_COOPBROWSE) {
\t\tstring nav = Menu_Coop_Browse_Navigate(current_hovered_option, -1);
\t\tif (nav != "") { _hover_actions[0] = nav; last_hovered_id = ""; _hover_action_count = 1; return; }
\t}
\tswitch(current_menu) {"""
patch(SUI_SYS, UPARROW_ANCHOR, UPARROW_REPLACEMENT,
      "C3: Uparrow um Coop-Browser-Navigation erweitern",
      "Menu_Coop_Browse_Navigate(current_hovered_option, -1)")

ENTER_ANCHOR = "void() _sui_menukey_enter = {\n\tif (_hover_actions[0] == \"\")\n\t\t_sui_menukey_downarrow();\n\n\t_click_actions[0] =  _hover_actions[0];\n\t_click_action_count = 1;\n\t_last_clicked_action_count = 1;\n};"
ENTER_REPLACEMENT = """void() _sui_menukey_enter = {
\tif (_hover_actions[0] == "")
\t\t_sui_menukey_downarrow();
\tif (current_menu == MENU_COOPBROWSE && _hover_actions[0] == "cbm_serverlist") {
\t\tif (Menu_Coop_Browse_EnterContainer()) _hover_actions[0] = "cbm_serverlistscrl0";
\t}
\t_click_actions[0] =  _hover_actions[0];
\t_click_action_count = 1;
\t_last_clicked_action_count = 1;
};"""
patch(SUI_SYS, ENTER_ANCHOR, ENTER_REPLACEMENT,
      "D: Enter um Container-Enter erweitern",
      "Menu_Coop_Browse_EnterContainer())")

AB_ANCHOR = "float(float evtype, float scanx, float chary, float devid) sui_input_event =\n{\n\tswitch (evtype)"
AB_REPLACEMENT = """float(float evtype, float scanx, float chary, float devid) sui_input_event =
{
\tif (evtype == IE_KEYDOWN || evtype == IE_KEYUP) {
\t\tif (scanx == K_GP_A) scanx = K_ESCAPE;
\t\telse if (scanx == K_GP_B) scanx = K_ENTER;
\t}
\tswitch (evtype)"""
patch(SUI_SYS, AB_ANCHOR, AB_REPLACEMENT,
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
\t// NZP-M9 Initialisierungen
\tgore_enabled = 1;
\tgore_kill_light = 300;
\tgore_blood_count = 2;
\tdmg_text_time = 0;
\tdmg_text_str = "";
\tdmg_indicator_alpha = 0;
\tdmg_last_health = 100;
\tscreen_shake_intensity = 0;
\thitmarker_sound_time = 0;
\tfov_punch_time = 0;
\tkill_streak_count = 0;
\tkill_streak_reset_time = 0;
\tkill_streak_display_time = 0;
\tkill_streak_last_time = 0;
\tkill_streak_text = "";
\theartbeat_time = 0;
\tambient_dust_time = 0;
\tnzp_is_indoor = FALSE;
\tnzp_fog_check_time = 0;
\tnzp_last_indoor_state = FALSE;
\tnzp_fog_initialized = FALSE;
""",
    "Initialisiere Variablen in CSQC_Init", "// NZP-M9 Initialisierungen")

# ==========================================
# TEIL 5: CSQC_Parse_Event – NUR return -> break
# ==========================================
HITMARK_ANCHOR = "case 3:\n\t\t\t\t\tif (hitmark_ignore_time > time)\n\t\t\t\t\t\treturn;\n\n\t\t\t\t\thitmark_type = var_1;"
HITMARK_REPLACEMENT = """case 3:
					if (hitmark_ignore_time > time)
						break;

					hitmark_type = var_1;"""
patch(CLIENT_MAIN, HITMARK_ANCHOR, HITMARK_REPLACEMENT,
      "CSQC_Parse_Event: return -> break (kein neuer Case)",
      "hitmark_ignore_time > time)\n\t\t\t\t\t\tbreak;")

# ==========================================
# TEIL 6: ATMOSPHÄRE-FUNKTIONEN (additiv)
# ==========================================
ATMO_FUNCS = """
// ==========================================
// NZP-M9: Atmosphäre & Nebel
// ==========================================

float() CSQC_IsIndoor =
{
\tvector start = playerOrigin + [0, 0, 16];
\tvector end = start + [0, 0, 4096];
\ttraceline(start, end, false, world);

\tif (trace_fraction == 1) {
\t\treturn FALSE;
\t}

\tif (pointcontents(trace_endpos) == CONTENT_SKY) {
\t\treturn FALSE;
\t}

\treturn TRUE;
};

void() CSQC_UpdateAtmosphere =
{
\tif (time < nzp_fog_check_time) {
\t\treturn;
\t}
\tnzp_fog_check_time = time + 0.5;

\tfloat indoor = CSQC_IsIndoor();
\tnzp_is_indoor = indoor;

\tif (indoor != nzp_last_indoor_state || !nzp_fog_initialized) {
\t\tnzp_last_indoor_state = indoor;
\t\tnzp_fog_initialized = TRUE;

\t\tif (indoor) {
\t\t\tcvar_set("r_fog", "1");
\t\t\tcvar_set("r_fog_color", "0.15 0.15 0.20");
\t\t\tcvar_set("r_fog_start", "80");
\t\t\tcvar_set("r_fog_end", "700");
\t\t} else {
\t\t\tcvar_set("r_fog", "1");
\t\t\tcvar_set("r_fog_color", "0.45 0.45 0.50");
\t\t\tcvar_set("r_fog_start", "500");
\t\t\tcvar_set("r_fog_end", "3000");
\t\t}
\t}
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
HUD_ADDITION = """\t// NZP-M9: Atmosphäre vor dem Rendern aktualisieren
\tCSQC_UpdateAtmosphere();

\t//does what you think it does
\trenderscene();

\t// --- NZP-M9 CUSTOM HUD ---
\t
\t// HIT/KILL-Text basierend auf vorhandenen Hitmarkern
\tif (time < hitmark_time) {
\t\tif (hitmark_type == 1) dmg_text_str = "KILL";
\t\telse dmg_text_str = "HIT";
\t\tdmg_text_time = time + 0.8;
\t}

\t// Kill-Streak-Logik (nur bei Kills, dedupliziert)
\tif (hitmark_type == 1 && time < hitmark_time) {
\t\tif (time - kill_streak_last_time > 0.5) {
\t\t\tif (time > kill_streak_reset_time) kill_streak_count = 1;
\t\t\telse kill_streak_count += 1;

\t\t\tkill_streak_last_time = time;
\t\t\tkill_streak_reset_time = time + 3.0;

\t\t\tif (kill_streak_count == 2) { kill_streak_text = "DOUBLE KILL"; kill_streak_display_time = time + 2.5; }
\t\t\telse if (kill_streak_count == 3) { kill_streak_text = "TRIPLE KILL"; kill_streak_display_time = time + 2.5; }
\t\t\telse if (kill_streak_count >= 4) { kill_streak_text = "MULTI KILL!"; kill_streak_display_time = time + 2.5; }
\t\t}
\t}

\tfloat current_health = getstatf(STAT_HEALTH);
\tif (current_health < dmg_last_health) {
\t\tdmg_indicator_alpha = 0.6;
\t\tscreen_shake_intensity += 3;
\t}
\tdmg_last_health = current_health;
\tdmg_indicator_alpha -= frametime * 2;
\tif (dmg_indicator_alpha < 0) dmg_indicator_alpha = 0;

\tif (dmg_indicator_alpha > 0) {
\t\tfloat edge_size = 20;
\t\tdrawfill([0, 0], [g_width, edge_size], [1, 0, 0], dmg_indicator_alpha, 0);
\t\tdrawfill([0, g_height - edge_size], [g_width, edge_size], [1, 0, 0], dmg_indicator_alpha, 0);
\t\tdrawfill([0, edge_size], [edge_size, g_height - edge_size*2], [1, 0, 0], dmg_indicator_alpha, 0);
\t\tdrawfill([g_width - edge_size, edge_size], [edge_size, g_height - edge_size*2], [1, 0, 0], dmg_indicator_alpha, 0);
\t}

\tscreen_shake_intensity -= frametime * 25;
\tif (screen_shake_intensity < 0) screen_shake_intensity = 0;

\tif (current_health < 30 && !(getstatf(STAT_PERKS) & P_DEAD) && !getstatf(STAT_WEAPONZOOM)) {
\t\tfloat pulse = (sin(cltime * 8) + 1) * 0.5;
\t\tdrawfill([0, 0], [g_width, g_height], [1, 0, 0], pulse * 0.4, 0);
\t\tif (time > heartbeat_time) {
\t\t\tlocalsound_enhanced("sounds/player/heart.wav", 0, 1.0);
\t\t\theartbeat_time = time + 1.0;
\t\t}
\t}

\t// Ambient Dust (nur im Außenbereich)
\tif (!nzp_last_indoor_state && time > ambient_dust_time && cvar("nzp_particles")) {
\t\tambient_dust_time = time + 0.1;
\t\tvector view_ang = getviewprop(VF_ANGLES);
\t\tmakevectors(view_ang);
\t\tvector dust_pos = getviewprop(VF_ORIGIN) + v_forward * 200 + v_right * (random()*400-200) + v_up * (random()*400-200);
\t\tpointparticles(particleeffectnum("weapons.impact"), dust_pos, '0 0 0', 1);
\t}

\tif (!getstatf(STAT_WEAPONZOOM) && !cvar("chase_active")) {
\t\tfloat spread = 4.0 + vlen(playerVelocity) * 0.05 + fabs(gun_kick[0]) * 2.0;
\t\tvector cx_color = [0.8, 0.2, 1];
\t\tif (current_health < 30) cx_color = [1, 0, 0];

\t\tdrawfill([g_width*0.5 - 1, g_height*0.5 - spread - 6], [2, 6], cx_color, 1, 0);
\t\tdrawfill([g_width*0.5 - 1, g_height*0.5 + spread], [2, 6], cx_color, 1, 0);
\t\tdrawfill([g_width*0.5 - spread - 6, g_height*0.5 - 1], [6, 2], cx_color, 1, 0);
\t\tdrawfill([g_width*0.5 + spread, g_height*0.5 - 1], [6, 2], cx_color, 1, 0);
\t\tdrawfill([g_width*0.5 - 1, g_height*0.5 - 1], [2, 2], cx_color, 0.5, 0);
\t}

\tif (serverkey("pausestate") != "1") {
\t\tsui_begin(g_width, g_height);
\t\tsui_set_align([SUI_ALIGN_END, SUI_ALIGN_START]);

\t\tfloat real_kills = 0;
\t\tentity player_ent = find(world, classname, "player");
\t\twhile (player_ent != world) {
\t\t\tif (player_ent.playernum == player_localnum + 1) {
\t\t\t\treal_kills = player_ent.kills;
\t\t\t\tbreak;
\t\t\t}
\t\t\tplayer_ent = find(player_ent, classname, "player");
\t\t}

\t\tsui_text([-10, 10], MENU_TEXT_MEDIUM, sprintf("KILLS: %d", real_kills), [0.8, 0.2, 1], 1, 0);

\t\tfloat mins = floor(cltime / 60);
\t\tfloat secs = floor(cltime % 60);
\t\tsui_text([-10, 30], MENU_TEXT_SMALL, sprintf("TIME: %02d:%02d", mins, secs), [1, 1, 1], 1, 0);

\t\tif (time < dmg_text_time) {
\t\t\tfloat diff = dmg_text_time - time;
\t\t\tfloat offset_y = 60 - ((0.8 - diff) * 40);
\t\t\tvector dmg_color = [1, 0.2, 1];
\t\t\tif (dmg_text_str == "KILL") dmg_color = [1, 0, 0];
\t\t\tsui_set_align([SUI_ALIGN_CENTER, SUI_ALIGN_CENTER]);
\t\t\tsui_text([0, -offset_y], MENU_TEXT_MEDIUM, dmg_text_str, dmg_color, diff, 0);
\t\t}

\t\tif (time < kill_streak_display_time) {
\t\t\tsui_set_align([SUI_ALIGN_CENTER, SUI_ALIGN_CENTER]);
\t\t\tsui_text([0, -120], MENU_TEXT_LARGE, kill_streak_text, [1, 0.5, 0], 1, 0);
\t\t}
\t\tsui_end();
\t}"""

patch(CLIENT_MAIN, "\t//does what you think it does\n\trenderscene();",
    HUD_ADDITION,
    "HUD-Block inkl. HIT/KILL + Kill-Streak nach renderscene() einfügen",
    "--- NZP-M9 CUSTOM HUD ---")

print("\n=== Alle Patches erfolgreich angewendet (idempotent). ===")
sys.exit(0)
