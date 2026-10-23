/*
	client/particles.qc
*/

// Stored outside of struct for stack efficency.
float   particle_optional_field;
float   particle_optional_entity;
vector  particle_position;

//
// Particles_MuzzleflashCallback()
//
void() Particles_MuzzleflashCallback =
{
    if (getstatf(STAT_WEAPONZOOM) == 2 || !cvar("r_drawviewmodel") || cvar("chase_active"))
        return;

    float weapon_side = particle_optional_field;
    float hit_entity = particle_optional_entity;

    getinputstate(servercommandframe);
    makevectors(input_angles);

    vector muzzleflash_offset;
	vector muzzleflash_position = getviewprop(VF_ORIGIN);

    if (weapon_side == 0 && IsDualWeapon(getstatf(STAT_ACTIVEWEAPON)))
		muzzleflash_offset = WepDef_GetLeftFlashOffset(getstatf(STAT_ACTIVEWEAPON))/1000;
	else
		muzzleflash_offset = GetWeaponFlash_Offset(getstatf(STAT_ACTIVEWEAPON))/1000;

	if(getstatf(STAT_WEAPONZOOM) == 1) {  
		muzzleflash_offset += GetWeaponADSOfs(getstatf(STAT_ACTIVEWEAPON))/1000;
	}
				
	muzzleflash_position += v_forward * muzzleflash_offset_z;
	muzzleflash_position += v_right * muzzleflash_offset_x;
	muzzleflash_position += v_up * muzzleflash_offset_y;

	float muzzleflash_type = rint(random() * 2);

	if (IsPapWeapon(getstatf(STAT_ACTIVEWEAPON))) {			
		pointparticles(particleeffectnum(strcat("muzzle.muzzle_pap_part", ftos(muzzleflash_type))), muzzleflash_position, '0 0 0', 1);
		if (random() > 0.5)
			dynamiclight_add(muzzleflash_position, 256, '0.7 0 0');
		else
			dynamiclight_add(muzzleflash_position, 256, '0 0 0.7');
	} else {
		pointparticles(particleeffectnum(strcat("muzzle.muzzle_part", ftos(muzzleflash_type))), muzzleflash_position, '0 0 0', 1);
		dynamiclight_add(muzzleflash_position, 256, '1.2 0.7 0.2');
	}

    if (GetFiretype(getstatf(STAT_ACTIVEWEAPON)) == FIRETYPE_GRENADE)
		return;
			
	if(hit_entity == 0) {
		pointparticles(particleeffectnum("weapons.impact"), particle_position, '0 0 0', 1);
		pointparticles(particleeffectnum("weapons.impact_decal"), particle_position, '0 0 0', 1);
	}
};

var struct
{
    float   particle_type;
    string  particle_string;
    void()  particle_func;
} csqc_particles[] =
{
    {CSQC_PART_MUZZLEFLASH, "", Particles_MuzzleflashCallback},
    {CSQC_PART_EXPLOSION, "weapons.explode", __NULL__},
    {CSQC_PART_BLOODIMPACT, "blood.blood_particle", __NULL__},
    {CSQC_PART_ZOMBIEGIB, "blood.gibs", __NULL__},
    {CSQC_PART_FIRE, "flames.flame_particle", __NULL__}
};

//
// Particles_RunParticle()
//
void(float particle_type, vector position, float optional_field, float optional_entity) Particles_RunParticle =
{
    // NZP-M9: Roter Lichtblitz bei Blut-Einschlag
    if (particle_type == CSQC_PART_BLOODIMPACT && gore_enabled) {
        dynamiclight_add(position, 150, '1 0 0');
    }
    
    // NZP-M9: Screen-Shake bei Explosionen
    if (particle_type == CSQC_PART_EXPLOSION) {
        screen_shake_intensity += 6;
    }

    if (csqc_particles[particle_type].particle_func == __NULL__)
        pointparticles(particleeffectnum(csqc_particles[particle_type].particle_string), position, '0 0 0', 1);
    else {
        particle_optional_field = optional_field;
        particle_optional_entity = optional_entity;
        particle_position = position;
        csqc_particles[particle_type].particle_func();
        particle_optional_field = particle_optional_entity = 0;
        particle_position = '0 0 0';
    }
};

//
// Particles_Init()
//
void() Particles_Init =
{
    int i;
	for(i = 0; i < 3; i++) {
		pointparticles(particleeffectnum(strcat("muzzle.muzzle_pap_part", itos(i))), '0 0 0', '0 0 0', 0);
		pointparticles(particleeffectnum(strcat("muzzle.muzzle_part", itos(i))), '0 0 0', '0 0 0', 0);
	}	
    for(i = 0; i < csqc_particles.length; i++) {
        pointparticles(particleeffectnum(csqc_particles[i].particle_string), '0 0 0', '0 0 0', 0);
    }			
};

//
// NZP-M9 CLIENT-SIDE GORE + SOUND + KILL STREAK
//
void() CSQC_SpawnClientGore =
{
    vector view_org = getviewprop(VF_ORIGIN);
    vector view_ang = getviewprop(VF_ANGLES);
    makevectors(view_ang);
    
    traceline(view_org, view_org + v_forward * 2048, MOVE_HITMODEL, world);
    
    if (trace_fraction < 1) {
        vector hit_pos = trace_endpos;
        
        // Hitmarker-Sound (mit Cooldown gegen Spam bei Maschinenpistolen)
        if (time > hitmarker_sound_time) {
            if (hitmark_type == 1) {
                localsound_enhanced("sounds/zombie/headshot.wav", 0, 0.7);
            } else {
                localsound_enhanced("sounds/weapons/knife/knife_hit.wav", 0, 0.5);
            }
            hitmarker_sound_time = time + 0.05;
        }
        
        // FOV-Punch bei jedem Schuss
        fov_punch_time = time + 0.08;
        
        if (hitmark_type == 1) {
            // Kill-Streak-Logik
            if (time > kill_streak_reset_time) {
                kill_streak_count = 1;
            } else {
                kill_streak_count += 1;
            }
            kill_streak_reset_time = time + 2.0;
            
            if (kill_streak_count == 2) {
                kill_streak_text = "DOUBLE KILL";
                kill_streak_display_time = time + 2.0;
            } else if (kill_streak_count == 3) {
                kill_streak_text = "TRIPLE KILL";
                kill_streak_display_time = time + 2.0;
            } else if (kill_streak_count >= 4) {
                kill_streak_text = "MULTI KILL!";
                kill_streak_display_time = time + 2.0;
            }
            
            // Gore-Effekt
            if (gore_enabled) {
                pointparticles(particleeffectnum("blood.gibs"), hit_pos, '0 0 0', 1);
                pointparticles(particleeffectnum("blood.gibs"), hit_pos + '0 0 15', '0 0 0', 1);
                dynamiclight_add(hit_pos, gore_kill_light, '1 0 0');
            }
        }
    }
};
