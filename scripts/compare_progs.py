#!/usr/bin/env python3
# Vergleicht zwei Quake-`.dat`-Dateien (dprograms_t-Format) feldgenau.
# Ziel: Absturzursachen beim Map-Load identifizieren (entityfields,
# sys_fields, sys_globals, Statement-Anzahl).

import struct
import sys
import os

# Feldtypen (Quake-Standard + FTE-Erweiterungen)
EV_NAMES = {
    0: "ev_void", 1: "ev_string", 2: "ev_float", 3: "ev_vector",
    4: "ev_entity", 5: "ev_field", 6: "ev_function", 7: "ev_pointer",
    8: "ev_integer", 9: "ev_quaternion", 10: "ev_double",
    11: "ev_nativefunction", 12: "ev_float32", 13: "ev_float64",
}

def parse_progs(path):
    with open(path, "rb") as f:
        data = f.read()
    if len(data) < 60:
        raise ValueError(f"{path} ist zu klein für einen Header ({len(data)} Bytes)")

    h = struct.unpack("<15i", data[:60])
    p = {
        "path": path,
        "size": len(data),
        "version": h[0],
        "crc": h[1],
        "ofs_statements": h[2],
        "num_statements": h[3],
        "ofs_globaldefs": h[4],
        "num_globaldefs": h[5],
        "ofs_fielddefs": h[6],
        "num_fielddefs": h[7],
        "ofs_functions": h[8],
        "num_functions": h[9],
        "ofs_strings": h[10],
        "num_strings": h[11],
        "ofs_globals": h[12],
        "num_globals": h[13],
        "entityfields": h[14],
    }

    # Strings
    raw = data[p["ofs_strings"]:p["ofs_strings"] + p["num_strings"]]
    p["strings"] = raw.decode("latin-1").split("\0")

    def read_defs(offset, count):
        out = []
        for i in range(count):
            off = offset + i * 8
            if off + 8 > len(data):
                break
            type_, ofs, s_name = struct.unpack("<hhi", data[off:off+8])
            name = p["strings"][s_name] if 0 <= s_name < len(p["strings"]) else f"<invalid:{s_name}>"
            out.append({"type": type_, "ofs": ofs, "name": name})
        return out

    p["fielddefs"] = read_defs(p["ofs_fielddefs"], p["num_fielddefs"])
    p["globaldefs"] = read_defs(p["ofs_globaldefs"], p["num_globaldefs"])
    return p

def find_marker(defs, marker):
    for i, d in enumerate(defs):
        if d["name"] == marker:
            return i
    return None

def fmt_type(t):
    return EV_NAMES.get(t, f"type_{t}")

def compare(ref, cur):
    out = []
    out.append("=" * 78)
    out.append(f"REFERENZ (funktionierend): {ref['path']}")
    out.append(f"AKTUELL   (stürzt ab):     {cur['path']}")
    out.append("=" * 78)

    # 1) Header-Werte
    out.append("\n--- HEADER ---")
    out.append(f"{'Feld':<20} {'Referenz':>15} {'Aktuell':>15} {'Differenz':>12}")
    out.append("-" * 66)
    for key in ["size", "version", "crc", "num_statements", "num_globaldefs",
                "num_fielddefs", "num_functions", "num_strings", "num_globals",
                "entityfields"]:
        r, c = ref[key], cur[key]
        diff = c - r
        marker = "  <<< ABWEICHUNG" if r != c else ""
        out.append(f"{key:<20} {r:>15} {c:>15} {diff:>+12}{marker}")

    # 2) entityfields ist der kritischste Wert
    out.append("\n--- KRITISCH: entityfields (Größe der Entity-Struktur) ---")
    if ref["entityfields"] != cur["entityfields"]:
        out.append(f"  REFERENZ: {ref['entityfields']} Felder")
        out.append(f"  AKTUELL:  {cur['entityfields']} Felder")
        out.append("  ❌ UNTERSCHIED! Die Engine allokiert Entities mit dieser Anzahl.")
        out.append("     Wenn die alte Binary gegen eine andere Größe kompiliert wurde,")
        out.append("     greift sie auf Offsets zu, die außerhalb des allozierten Speichers liegen.")
    else:
        out.append(f"  ✅ Identisch ({ref['entityfields']} Felder)")

    # 3) sys_fields
    out.append("\n--- SYSTEM-FELDER (vor end_sys_fields) ---")
    r_idx = find_marker(ref["fielddefs"], "end_sys_fields")
    c_idx = find_marker(cur["fielddefs"], "end_sys_fields")
    out.append(f"  end_sys_fields: Referenz={r_idx}, Aktuell={c_idx}")
    if r_idx is None or c_idx is None:
        out.append("  ❌ end_sys_fields nicht gefunden – Datei ist unvollständig oder korrupt.")
    elif r_idx != c_idx:
        out.append(f"  ❌ Anzahl der System-Felder weicht ab ({r_idx} vs. {c_idx}).")
        out.append("     Das verschiebt ALLE Builtin-Feldzugriffe der Engine.")
    else:
        out.append(f"  ✅ Anzahl identisch ({r_idx} Felder)")
        mismatches = 0
        for i in range(r_idx + 1):
            rf, cf = ref["fielddefs"][i], cur["fielddefs"][i]
            if (rf["name"], rf["type"], rf["ofs"]) != (cf["name"], cf["type"], cf["ofs"]):
                mismatches += 1
                if mismatches <= 10:
                    out.append(f"  ❌ [{i}] Ref={rf['name']}/{fmt_type(rf['type'])}/ofs={rf['ofs']}"
                               f"  Cur={cf['name']}/{fmt_type(cf['type'])}/ofs={cf['ofs']}")
        if mismatches == 0:
            out.append("  ✅ Alle System-Felder identisch (Name, Typ, Offset).")
        else:
            out.append(f"  ❌ {mismatches} abweichende System-Felder!")

    # 4) sys_globals
    out.append("\n--- SYSTEM-GLOBALS (vor end_sys_globals) ---")
    r_g = find_marker(ref["globaldefs"], "end_sys_globals")
    c_g = find_marker(cur["globaldefs"], "end_sys_globals")
    out.append(f"  end_sys_globals: Referenz={r_g}, Aktuell={c_g}")
    if r_g is None or c_g is None:
        out.append("  ❌ end_sys_globals nicht gefunden.")
    elif r_g != c_g:
        out.append(f"  ❌ Anzahl der System-Globals weicht ab ({r_g} vs. {c_g}).")
    else:
        out.append(f"  ✅ Anzahl identisch ({r_g} Globals)")

    # 5) Neue Felder in der aktuellen Datei (typischer Patch-Verdacht)
    out.append("\n--- NEUE FELDER in der aktuellen Datei (nicht in Referenz) ---")
    ref_names = {d["name"] for d in ref["fielddefs"]}
    new_fields = [d for d in cur["fielddefs"] if d["name"] not in ref_names]
    if not new_fields:
        out.append("  (keine)")
    else:
        for d in new_fields[:30]:
            pos = cur["fielddefs"].index(d)
            in_sys = c_idx is not None and pos <= c_idx
            warn = "  <<< VOR end_sys_fields!" if in_sys else ""
            out.append(f"  + {d['name']:<30} {fmt_type(d['type']):<12} ofs={d['ofs']:<5}{warn}")
        out.append(f"  Gesamt: {len(new_fields)} neue Felder")

    # 6) Neue Globals
    out.append("\n--- NEUE GLOBALS in der aktuellen Datei ---")
    ref_g_names = {g["name"] for g in ref["globaldefs"]}
    new_globals = [g for g in cur["globaldefs"] if g["name"] not in ref_globals := ref_g_names]
    if not new_globals:
        out.append("  (keine)")
    else:
        for g in new_globals[:30]:
            pos = cur["globaldefs"].index(g)
            in_sys = c_g is not None and pos <= c_g
            warn = "  <<< VOR end_sys_globals!" if in_sys else ""
            out.append(f"  + {g['name']:<30} {fmt_type(g['type']):<12} ofs={g['ofs']:<5}{warn}")
        out.append(f"  Gesamt: {len(new_globals)} neue Globals")

    # 7) Unbekannte Feldtypen (FTE-spezifisch für alte Binary?)
    out.append("\n--- UNBEKANNTE FELDTYPEN (nicht in Standard-Liste) ---")
    unknown = set()
    for d in cur["fielddefs"] + cur["globaldefs"]:
        if d["type"] not in EV_NAMES:
            unknown.add(d["type"])
    if not unknown:
        out.append("  (keine – alle Typen sind Standard/FTE-bekannt)")
    else:
        for t in sorted(unknown):
            out.append(f"  ❌ Typ {t} ist unbekannt. Die alte Binary kennt ihn möglicherweise nicht.")

    return "\n".join(out)

def main():
    if len(sys.argv) != 3:
        sys.exit("Aufruf: compare_progs.py <referenz.dat> <aktuell.dat>")
    ref_path, cur_path = sys.argv[1], sys.argv[2]
    for p in (ref_path, cur_path):
        if not os.path.exists(p):
            sys.exit(f"FEHLER: {p} fehlt.")

    ref = parse_progs(ref_path)
    cur = parse_progs(cur_path)

    report = compare(ref, cur)
    print(report)

    # Kritische Fehler: entityfields-Differenz oder sys_fields-Verschiebung
    r_idx = find_marker(ref["fielddefs"], "end_sys_fields")
    c_idx = find_marker(cur["fielddefs"], "end_sys_fields")
    critical = (
        ref["entityfields"] != cur["entityfields"]
        or r_idx != c_idx
        or r_idx is None or c_idx is None
    )
    if critical:
        print("\n❌ KRITISCHE ABWEICHUNG – dieser Fehler erklärt den Map-Load-Absturz.")
        sys.exit(1)
    else:
        print("\n✅ Keine kritische Abweichung gefunden.")
        sys.exit(0)

if __name__ == "__main__":
    main()
