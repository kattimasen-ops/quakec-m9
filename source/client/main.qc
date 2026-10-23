/* client/main.qc
   main csqc code
   ... (Lizenzkopf unverändert) ...
*/

float need_vid_reload;

void() ToggleMenu =
{
	if (serverkey("constate") != "disconnected") {
		if (player_count == 1) localcmd("cmd pause\n");
		if(current_menu == MENU_NONE) {
			current_menu = MENU_PAUSE;
			setcursormode(TRUE, cvar_string("cl_cursor"), __NULL__, cvar("cl_cursor_scale"));
		} else {
			menu_paus_submenu = 0;
			current_menu = MENU_NONE;
			setcursormode(FALSE);
		}
	}
}

// ... (Rest der Datei bis zur Event-Verarbeitung) ...

// ==========================================
// KORREKTUR: CSQC_Parse_Event
// ==========================================
noref void() CSQC_Parse_Event =
{
	float event_type = readbyte();
	switch (event_type)
	{
		case CSQC_EVENT_PARTICLE:
			float particle_type = readbyte();
			float part_pos_x = readcoord();
			float part_pos_y = readcoord();
			float part_pos_z = readcoord();
			float part_optional = readbyte();
			float part_entity = readentitynum();
			vector particle_pos = [part_pos_x, part_pos_y, part_pos_z];
			Particles_RunParticle(particle_type, particle_pos, part_optional, part_entity);
			break;
		case CSQC_EVENT_USEPRINT:
			useprint_type = readbyte();
			useprint_cost = readshort();
			useprint_time = time + 0.1;
			break;
		case CSQC_EVENT_REGISTERUSEPRINT:
			float useprint_index = readbyte();
			useprint_strings[useprint_index] = readstring();
			vector useprint_color;
			useprint_color_x = readbyte() / 255;
			useprint_color_y = readbyte() / 255;
			useprint_color_z = readbyte() / 255;
			useprint_colors[useprint_index] = useprint_color;
			break;
		case CSQC_EVENT_ROUNDCHANGE:
			rounds = readbyte();
			break;
		case CSQC_EVENT_BROADCASTMESSAGE:
			broadcast_type = readbyte();
			broadcast_time = time + 5;
			broadcast_num = readbyte();
			break;
		// ==========================================
		// KORRIGIERTER HITMARK-BLOCK
		// ==========================================
		case CSQC_EVENT_HITMARK: // Annahme: Dieser Event-Typ existiert bereits oder wird serverseitig gesendet
			// WICHTIG: break am Anfang, damit die Funktion bei Ignorierung sauber verlassen wird.
			if (hitmark_ignore_time > time) {
				break;
			}

			hitmark_type = readbyte();

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
			break;
		default:
			break;
	}
};

// ==========================================
// KORREKTUR: CSQC_UpdateView (HUD)
// ==========================================
noref void(float width, float height, float menushown) CSQC_UpdateView =
{
	clearscene();
	g_width = width;
	g_height = height;

	camang = getproperty(VF_ANGLES);
	setviewprop(VF_DRAWENGINESBAR, 0);
	setviewprop(VF_DRAWCROSSHAIR, 0);

	float sensitivity_factor;
	if (current_menu != MENU_NONE) sensitivity_factor = 0;
	else sensitivity_factor = (1 + SCALE_CONSTANT * getstatf(STAT_VIEWZOOM)) / (1 + SCALE_CONSTANT);
	if (gamepad_enabled && getstatf(STAT_FACINGENEMY) && cvar("in_aimassist") == 1) sensitivity_factor *= 0.5;
	setsensitivityscaler(sensitivity_factor);

	// Kamera-Effekte (Screen-Shake & FOV-Punch)
	float base_fov = autocvar(fov, 90) * getstatf(STAT_VIEWZOOM);
	if (time < fov_punch_time) {
		float punch_factor = (fov_punch_time - time) / 0.08;
		base_fov = base_fov - (punch_factor * 8);
	}
	setviewprop(VF_AFOV, base_fov);
	cvar_set("r_viewmodel_fov", ftos(cvar("r_viewmodel_default_fov") * getstatf(STAT_VIEWZOOM)));

	if (screen_shake_intensity > 0) {
		camang[0] += (random() * 2 - 1) * screen_shake_intensity * 0.3;
		camang[1] += (random() * 2 - 1) * screen_shake_intensity * 0.3;
		camang[2] += (random() * 2 - 1) * screen_shake_intensity * 0.1;
	}
	setviewprop(VF_ANGLES, camang);

	// ... (Stopwatch, Entities, ViewModel etc. unverändert) ...
	addentities(MASK_ENGINE);
	setproperty(VF_ORIGIN, playerOrigin + [0, 0, getstatf(STAT_VIEWHEIGHT)]);
	ViewModel_Draw();
	DropRecoilKick();
	Camera_SniperSway();
	camang[0] += gun_kick[0];
	camang[1] += gun_kick[1];
	camang[2] += gun_kick[2];
	camang[0] += sniper_sway[0];
	camang[1] += sniper_sway[1];
	camang[2] += sniper_sway[2];
	Camera_AimSnap(camang);
	camang[0] += cam_snap_difference[0];
	camang[1] += cam_snap_difference[1];
	camang[2] += cam_snap_difference[2];
	setviewprop(VF_ANGLES, camang);

	if (cvar("chase_active")) {
		Chase_Update();
	}

	renderscene();

	// ==========================================
	// KORREKTUR: HUD mit sui_begin/sui_end
	// ==========================================
	float current_health = getstatf(STAT_HEALTH);

	// Damage-Indikator (Rand)
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

	// Ambient Dust
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
		vector cx_color = [0.8, 0.2, 1];
		if (current_health < 30) cx_color = [1, 0, 0];

		drawfill([g_width*0.5 - 1, g_height*0.5 - spread - 6], [2, 6], cx_color, 1, 0);
		drawfill([g_width*0.5 - 1, g_height*0.5 + spread], [2, 6], cx_color, 1, 0);
		drawfill([g_width*0.5 - spread - 6, g_height*0.5 - 1], [6, 2], cx_color, 1, 0);
		drawfill([g_width*0.5 + spread, g_height*0.5 - 1], [6, 2], cx_color, 1, 0);
		drawfill([g_width*0.5 - 1, g_height*0.5 - 1], [2, 2], cx_color, 0.5, 0);
	}

	// HUD-Texte (Kills, Zeit, Damage-Text, Kill-Streak)
	if (serverkey("pausestate") != "1") {
		sui_begin(g_width, g_height); // WICHTIG: Frame öffnen
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

		sui_end(); // WICHTIG: Frame schließen
	}
};

// ... (Rest der Datei) ...
