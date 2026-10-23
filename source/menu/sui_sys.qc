// Shpuld's Simple UI lib - sui
// ... (Lizenzkopf unverändert) ...

#ifdef MENU
const float IE_KEYDOWN = 0;
// ... (Rest der IE_*-Konstanten) ...
#define printf(x, ...) print(sprintf(x, __VA_ARGS__))

// ==========================================
// M9-PATCH: Forward-Deklarationen für Coop-Browser-Navigation
// ==========================================
string(string cur, float direction) Menu_Coop_Browse_Navigate;
float() Menu_Coop_Browse_EnterContainer;
#endif

float _sui_draw_initialized;
// ... (Rest der Datei bis zu den Tastenhandlern) ...

void() _sui_menukey_downarrow =
{
	string current_hovered_option = _hover_actions[0];
	// ==========================================
	// M9-PATCH: Erweiterung für Coop-Browser
	// ==========================================
	if (current_menu == MENU_COOPBROWSE) {
		string nav = Menu_Coop_Browse_Navigate(current_hovered_option, 1);
		if (nav != "") {
			_hover_actions[0] = nav;
			last_hovered_id = "";
			_hover_action_count = 1;
			return;
		}
	}
	switch(current_menu) {
		// ... (bestehende cases) ...
	}
	_hover_action_count = 1;
};

void() _sui_menukey_uparrow =
{
	string current_hovered_option = _hover_actions[0];
	// ==========================================
	// M9-PATCH: Erweiterung für Coop-Browser
	// ==========================================
	if (current_menu == MENU_COOPBROWSE) {
		string nav = Menu_Coop_Browse_Navigate(current_hovered_option, -1);
		if (nav != "") {
			_hover_actions[0] = nav;
			last_hovered_id = "";
			_hover_action_count = 1;
			return;
		}
	}
	switch(current_menu) {
		// ... (bestehende cases) ...
	}
	_hover_action_count = 1;
};

void() _sui_menukey_enter =
{
	if (_hover_actions[0] == "")
		_sui_menukey_downarrow();

	// ==========================================
	// M9-PATCH: Enter auf Container
	// ==========================================
	if (current_menu == MENU_COOPBROWSE && _hover_actions[0] == "cbm_serverlist") {
		if (Menu_Coop_Browse_EnterContainer())
			_hover_actions[0] = "cbm_serverlistscrl0";
	}

	_click_actions[0] = _hover_actions[0];
	_click_action_count = 1;
	_last_clicked_action_count = 1;
};

// ... (Rest der Datei, inkl. sui_input_event) ...
