#!/usr/bin/env python3
# NZP-M9 Patches: Server-Browser Gamepad-Navigation & Performance-Optimierungen

import sys
from pathlib import Path

def patch(path: Path, anchor: str, replacement: str, description: str, marker: str, required: bool = True) -> None:
    if not path.exists():
        if required:
            print(f"[FATAL] {path} existiert nicht.")
            sys.exit(1)
        else:
            print(f"[SKIP] {description}: Datei {path} fehlt (optional).")
            return
    content = path.read_text(encoding="utf-8")
    if marker in content:
        print(f"[SKIP] {description}: bereits gepatcht")
        return
    count = content.count(anchor)
    if count == 0:
        if required:
            print(f"[FATAL] {description}: Anker NICHT gefunden in {path}")
            sys.exit(1)
        else:
            print(f"[SKIP] {description}: Anker nicht gefunden (optional, wird ignoriert)")
            return
    if count > 1:
        if required:
            print(f"[FATAL] {description}: Anker {count}× gefunden in {path}")
            sys.exit(1)
        else:
            print(f"[WARN] {description}: Anker {count}× gefunden (optional, überspringe)")
            return
    path.write_text(content.replace(anchor, replacement, 1), encoding="utf-8")
    print(f"[OK]   {description}")

def ensure_line(path: Path, line: str, description: str) -> None:
    if not path.exists():
        print(f"[FATAL] {path} existiert nicht.")
        sys.exit(1)
    content = path.read_text(encoding="utf-8")
    if line in content:
        print(f"[SKIP] {description}: bereits vorhanden")
        return
    path.write_text(content + "\n" + line + "\n", encoding="utf-8")
    print(f"[OK]   {description}")

def append_safe(path: Path, content: str, description: str, marker: str) -> None:
    if not path.exists():
        print(f"[FATAL] {path} existiert nicht.")
        sys.exit(1)
    text = path.read_text(encoding="utf-8")
    if marker in text:
        print(f"[SKIP] {description}: bereits vorhanden")
        return
    path.write_text(text + "\n" + content, encoding="utf-8")
    print(f"[OK]   {description}")

BASE = Path("source/menu")
CLIENT = Path("source/client")
MENU_COOP = BASE / "menu_coop.qc"
SUI_SYS   = BASE / "sui_sys.qc"
MENU_VIDE = BASE / "menu_vide.qc"
CLIENT_MAIN = CLIENT / "main.qc"
FTE_QC = CLIENT / "defs/fte.qc"
MENU_DEFS = BASE / "defs/menu_defs.qc"

# ==========================================
# TEIL 0: FEHLENDE DEKLARATIONEN & BUILTINS
# ==========================================

ensure_line(FTE_QC, ".float is_in_menu;", "Füge is_in_menu Feld hinzu")
ensure_line(FTE_QC, "void(string soundname, float channel, float volume) localsound_enhanced = { localsound(soundname, channel, volume); };", "Füge localsound_enhanced Wrapper hinzu")
ensure_line(FTE_QC, "void(float dest) setkeydest = #602;", "Füge setkeydest Builtin hinzu")

menu_defs_injection = """
// --- NZP-M9 Forward Declarations ---
void(float wantmode) m_toggle;
void(vector screensize, float notmenu) m_drawloading;
// -----------------------------------
"""
append_safe(MENU_DEFS, menu_defs_injection, "Füge menu_defs.qc Forward-Declarations hinzu", "NZP-M9 Forward Declarations")

# Dummy-Funktionen für GameSettings und Credits werden NICHT mehr benötigt,
# da menu_gset.qc und menu_cred.qc jetzt real existieren.

patch(
    CLIENT_MAIN,
    anchor="float menu_active;",
    replacement="// float menu_active; (verschoben nach menu/main.qc)",
    description="Entferne doppelte menu_active Definition",
    marker="// float menu_active;",
    required=False,
)

# ... (Restliche Patches für Server-Browser und Video-Menü bleiben unverändert) ...
