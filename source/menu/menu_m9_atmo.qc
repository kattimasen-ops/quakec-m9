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
            ret = menu_m9_atmo_buttons[i + 1];
            break;
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
            ret = menu_m9_atmo_buttons[i - 1];
            break;
        }
    }
    return ret;
};

void() Menu_M9_Atmo_Performance = {
    Menu_PlaySound(MENU_SND_ENTER);
    cvar_set("nzp_particles", "0");
    cvar_set("nzp_decals", "0");
    cvar_set("r_fog", "0");
    cvar_set("r_fog_start", "2048");
    cvar_set("r_fog_end", "4096");
    cvar_set("r_fog_color", "0.3 0.3 0.35");
};

void() Menu_M9_Atmo_Balanced = {
    Menu_PlaySound(MENU_SND_ENTER);
    cvar_set("nzp_particles", "1");
    cvar_set("nzp_decals", "1");
    cvar_set("r_fog", "1");
    cvar_set("r_fog_start", "500");
    cvar_set("r_fog_end", "3000");
    cvar_set("r_fog_color", "0.45 0.45 0.50");
};

void() Menu_M9_Atmo_Cinematic = {
    Menu_PlaySound(MENU_SND_ENTER);
    cvar_set("nzp_particles", "1");
    cvar_set("nzp_decals", "1");
    cvar_set("r_fog", "1");
    cvar_set("r_fog_start", "80");
    cvar_set("r_fog_end", "700");
    cvar_set("r_fog_color", "0.15 0.15 0.20");
};

void() Menu_M9_Atmo_ToggleParticles = {
    Menu_PlaySound(MENU_SND_ENTER);
    cvar_set("nzp_particles", cvar("nzp_particles") ? "0" : "1");
};

void() Menu_M9_Atmo_ToggleDecals = {
    Menu_PlaySound(MENU_SND_ENTER);
    cvar_set("nzp_decals", cvar("nzp_decals") ? "0" : "1");
};

void() Menu_M9_Atmo_ToggleFog = {
    Menu_PlaySound(MENU_SND_ENTER);
    cvar_set("r_fog", cvar("r_fog") ? "0" : "1");
};

void() Menu_M9_Atmo_CycleFogDensity = {
    Menu_PlaySound(MENU_SND_ENTER);
    float current = cvar("r_fog_start");
    if (current >= 500) {
        cvar_set("r_fog_start", "80");
        cvar_set("r_fog_end", "700");
        cvar_set("r_fog_color", "0.15 0.15 0.20");
    } else if (current >= 80) {
        cvar_set("r_fog_start", "500");
        cvar_set("r_fog_end", "3000");
        cvar_set("r_fog_color", "0.45 0.45 0.50");
    } else {
        cvar_set("r_fog_start", "2048");
        cvar_set("r_fog_end", "4096");
        cvar_set("r_fog_color", "0.3 0.3 0.35");
    }
};

void() Menu_M9_Atmo_CycleGore = {
    Menu_PlaySound(MENU_SND_ENTER);
    float current = cvar("nzp_decals");
    if (current >= 1) {
        cvar_set("nzp_decals", "0");
    } else {
        cvar_set("nzp_decals", "1");
    }
};

void() Menu_M9_Atmosphere = {
    Menu_DrawBackground();
    Menu_DrawTitle("ATMOSPHERE & GORE");
    Menu_DrawMapPanel();

    Menu_Button(1, "m9_atmo_perf", "PERFORMANCE PRESET", "Disables particles, decals and fog for maximum FPS.") ? Menu_M9_Atmo_Performance() : 0;
    Menu_Button(2, "m9_atmo_balanced", "BALANCED PRESET", "Default atmosphere and gore settings.") ? Menu_M9_Atmo_Balanced() : 0;
    Menu_Button(3, "m9_atmo_cinematic", "CINEMATIC PRESET", "Dense fog, full particles and decals.") ? Menu_M9_Atmo_Cinematic() : 0;

    Menu_DrawDivider(3.25);

    Menu_Button(4, "m9_atmo_particles", "PARTICLES", "Toggle ambient dust and particle effects.") ? Menu_M9_Atmo_ToggleParticles() : 0;
    Menu_DrawOptionValue(4, cvar("nzp_particles") ? "ENABLED" : "DISABLED");

    Menu_Button(5, "m9_atmo_decals", "DECALS", "Toggle bullet holes and blood decals.") ? Menu_M9_Atmo_ToggleDecals() : 0;
    Menu_DrawOptionValue(5, cvar("nzp_decals") ? "ENABLED" : "DISABLED");

    Menu_Button(6, "m9_atmo_fog", "FOG", "Toggle volumetric fog.") ? Menu_M9_Atmo_ToggleFog() : 0;
    Menu_DrawOptionValue(6, cvar("r_fog") ? "ENABLED" : "DISABLED");

    Menu_Button(7, "m9_atmo_fog_density", "FOG DENSITY", "Cycle between Performance, Balanced and Cinematic fog.") ? Menu_M9_Atmo_CycleFogDensity() : 0;
    float fog_start = cvar("r_fog_start");
    string fog_label = "PERFORMANCE";
    if (fog_start < 500) fog_label = "CINEMATIC";
    else if (fog_start < 2048) fog_label = "BALANCED";
    Menu_DrawOptionValue(7, fog_label);

    Menu_Button(8, "m9_atmo_gore_level", "GORE LEVEL", "Toggle gore intensity (decals on/off).") ? Menu_M9_Atmo_CycleGore() : 0;
    Menu_DrawOptionValue(8, cvar("nzp_decals") ? "FULL" : "REDUCED");

    Menu_Button(-1, "m9_atmo_back", "BACK", "Return to Configuration Menu.") ? current_menu = MENU_OPTIONS : 0;

    sui_pop_frame();
};
