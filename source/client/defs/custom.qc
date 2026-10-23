/*
	client/defs/custom.qc
*/

#pragma warning disable Q302

float g_width, g_height;

float weapon;

float tracercounter;
.float rate;
.vector targetpos;

entity cl_viewent;
entity cl_viewent2;

float matchmake_enabled;
float double_tap_version;

float useprint_type;
float useprint_cost;
float useprint_time;
string useprint_strings[256];
vector useprint_colors[256];

float active_gamemode;

float bettyprompt_time;

float hud_toast_endtime;
float hud_toast_starttime;
string hud_toast_string;
float hud_perk_orientation;
vector hud_round_color;

float nameprint_time;
float HUD_Change_time; 
float hitmark_time;
float hitmark_ignore_time;
float hitmark_type;
float recoil_kick_time;
float crosshair_pulse_grenade;
float zoom_2_time;

float broadcast_time;
float broadcast_type;
float broadcast_num;

string character_name;

#define MAX_REVIVE_ICONS	16

var struct revive_s {
	float draw;
	float timer;
	float state;
} revive_icons[MAX_REVIVE_ICONS];

float weaponframetime;
float weapon2frametime;
float oldweaponframe;
float oldweapon2frame;
float curweaponframe;
float curweapon2frame;
float interpolating;
float interpolating2;

float rounds;
float perks;
float rounds_change;
float player_count;
float score_show;

#define MAX_ACHIEVEMENTS    42

var struct achievementlist_t
{
    string      img;
    float       unlocked;
    string      name;
    string      description;
    float       progress;
} achievements[MAX_ACHIEVEMENTS];

float active_achievement;
float current_achievement_page;
float achievement_pages;

float sniper_hold_breath;

float K_LEFTDOWN, K_RIGHTDOWN, K_BACKDOWN, K_FORWARDDOWN;

vector TEXT_PURPLE    = [0.46, 0, 0.46];
vector TEXT_LIGHTBLUE = [0, 0.46, 0.70];
vector TEXT_ORANGE    = [0.92, 0.74, 0];
vector TEXT_GREEN     = [0, 0.90, 0.13];
vector TEXT_RED       = [1, 0, 0];
vector TEXT_LIGHTRED  = [1, 0.50, 0.50];
vector TEXT_YELLOW    = [1, 0.87, 0.13];

float screenflash_type;
float screenflash_color;
float screenflash_duration;
float screenflash_worktime;
float screenflash_starttime;

.float stance;

vector camang;

string chaptertitle;
string location;
string date;
string person;

string huddir;

int platform_is_web;

float stopwatch_sec;
int stopwatch_min;
int stopwatch_hr;

float stopwatch_round_sec;
int stopwatch_round_min;
int stopwatch_round_hr;
int stopwatch_round_isactive;
float stopwatch_round_starttime;

float GPButtonHeldBeginTime[24];
float last_input_deviceid;

string build_datetime;

vector gun_kick;

float hide_viewmodel;

vector playerOrigin;
vector playerOriginOld;
vector playerVelocity;

// ============================================================
// NZP-M9 CUSTOM ADDITIONS
// ============================================================

// HUD - Damage Numbers
float dmg_text_time;
string dmg_text_str;

// Gore-Mod Steuerung
float gore_enabled;
float gore_kill_light;

// Damage-Indicator (roter Rand bei HP-Verlust)
float dmg_indicator_alpha;
float dmg_last_health;

// Screen-Shake bei Explosionen
float screen_shake_intensity;

// Hitmarker-Sound Cooldown
float hitmarker_sound_time;

// FOV-Punch beim Feuern
float fov_punch_time;

// Kill-Streak-Anzeige
float kill_streak_count;
float kill_streak_reset_time;
float kill_streak_display_time;
string kill_streak_text;
