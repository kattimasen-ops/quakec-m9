#!/usr/bin/env python3
# Vergleicht zwei Quake-`.dat`-Dateien (dprograms_t-Format) feldgenau.
# Fokus: entityfields, sys_fields, sys_globals, Statement-Anzahl,
# neue Felder/Globals vor end_sys_fields (typische Absturzursache).

import struct
import sys
import os

EV_NAMES = {
    0: "ev_void", 1: "ev_string", 2: "ev_float", 3: "ev_vector",
    4: "ev_entity", 5: "ev_field", 6: "ev_function", 7: "ev_pointer",
    8: "ev_integer", 9: "ev_quaternion", 10: "ev_double",
    11: "ev_nativefunction", 12: "ev_float32", 13: "ev_float64",
    14: "ev_float32b", 15: "ev_float64b", 16: "ev_entityb",
    17: "ev_float3b",
}

def type_name(t):
    return EV_NAMES.get(t, f"ev_unknown({t})")

def parse_progs(path):
    with open(path, "rb") as f:
        data = f.read()
    if len(data) < 60:
        raise ValueError(f"{path}: nur {len(data)} Bytes – Header unvollständig (min. 60)")

    h = struct.unpack("<15i", data[:60])
    p = {
        "path": path,
        "size": len(data),
        "version": h[0],
        "crc": h[1],
        "ofs_statements": h[2],  "num_statements": h[3],
        "ofs_globaldefs": h[4],  "num_globaldefs": h[5],
        "ofs_fielddefs":  h[6],  "num_fielddefs":  h[7],
        "ofs_functions":  h[8],  "num_functions":  h[9],
        "ofs_strings":    h[10], "num_strings":    h[11],
        "ofs_globals":    h[12], "num_globals":    h[13],
        "entityfields":   h[14],
    }

    raw = data[p["ofs_strings"]:p["ofs_strings"] + p["num_strings"]]
    p["strings"] = raw.decode("latin-1").split("\0")

    def read_defs(offset, count):
        out = []
        for i in range(count):
            off = offset + i * 8
            if off + 8 > len(data):
                break
            type_, ofs, s_name = struct.unpack("<hhi", data[off:off+8])
            name = p["strings"][s_name] if 0 <= s_name < len(p["strings"]) else f"<inv:{s_name}>"
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

def diff_sys_fields(ref, cur, out):
    out.append("\n--- SYSTEM-FELDER (bis inkl. end_sys_fields) ---")
    r_idx = find_marker(ref["fielddefs"], "end_sys_fields")
    c_idx = find_marker(cur["fielddefs"], "end_sys_fields")
    out.append(f"  end_sys_fields Position: Referenz={r_idx}, Aktuell={c_idx}")

    if r_idx is None or c_idx is None:
        out.append("  ❌ end_sys_fields nicht gefunden – Datei unvollständig oder korrupt.")
        return False

    if r_idx != c_idx:
        out.append(f"  ❌ ANZAHL UNTERSCHIEDLICH: {r_idx + 1} vs {c_idx + 1}")
        out.append("     Jedes zusätzliche/fehlende Feld verschiebt alle nachfolgenden Offsets.")
        return False

    out.append(f"  ✅ Anzahl identisch ({r_idx + 1} Felder)")
    bad = []
    for i in range(r_idx + 1):
        rf, cf = ref["fielddefs"][i], cur["fielddefs"][i]
        if (rf["name"], rf["type"], rf["ofs"]) != (cf["name"], cf["type"], cf["ofs"]):
            bad.append((i, rf, cf))
    if not bad:
        out.append("  ✅ Alle Felder identisch (Name, Typ, Offset).")
        return True

    out.append(f"  ❌ {len(bad)} abweichende Felder:")
    for i, rf, cf in bad[:25]:
        out.append(f"    [{i:>3}] Ref: {rf['name']:<28} {type_name(rf['type']):<15} ofs={rf['ofs']}")
        out.append(f"          Cur: {cf['name']:<28} {type_name(cf['type']):<15} ofs={cf['ofs']}")
    if len(bad) > 25:
        out.append(f"    ... ({len(bad) - 25} weitere)")
    return False

def diff_sys_globals(ref, cur, out):
    out.append("\n--- SYSTEM-GLOBALS (bis inkl. end_sys_globals) ---")
    r_g = find_marker(ref["globaldefs"], "end_sys_globals")
    c_g = find_marker(cur["globaldefs"], "end_sys_globals")
    out.append(f"  end_sys_globals Position: Referenz={r_g}, Aktuell={c_g}")
    if r_g is None or c_g is None:
        out.append("  ❌ end_sys_globals nicht gefunden.")
        return False
    if r_g != c_g:
        out.append(f"  ❌ Anzahl unterschiedlich: {r_g + 1} vs {c_g + 1}")
        return False
    out.append(f"  ✅ Anzahl identisch ({r_g + 1} Globals)")
    bad = 0
    for i in range(r_g + 1):
        rg, cg = ref["globaldefs"][i], cur["globaldefs"][i]
        if (rg["name"], rg["type"], rg["ofs"]) != (cg["name"], cg["type"], cg["ofs"]):
            bad += 1
            if bad <= 10:
                out.append(f"    [{i:>3}] Ref: {rg['name']:<25} ofs={rg['ofs']}")
                out.append(f"          Cur: {cg['name']:<25} ofs={cg['ofs']}")
    if bad == 0:
        out.append("  ✅ Alle System-Globals identisch.")
    else:
        out.append(f"  ❌ {bad} abweichende System-Globals.")
    return bad == 0

def list_new_fields(ref, cur, out):
    out.append("\n--- NEUE FELDER in progs.dat (nicht in qwprogs.dat.bak) ---")
    ref_names = {d["name"] for d in ref["fielddefs"]}
    new = [d for d in cur["fielddefs"] if d["name"] not in ref_names]
    if not new:
        out.append("  (keine)")
        return
    c_idx = find_marker(cur["fielddefs"], "end_sys_fields")
    for d in new:
        pos = cur["fielddefs"].index(d)
        in_sys = c_idx is not None and pos <= c_idx
        warn = "  <<< VOR end_sys_fields!" if in_sys else ""
        out.append(f"  + {d['name']:<30} {type_name(d['type']):<15} ofs={d['ofs']:<5}{warn}")
    out.append(f"  Gesamt: {len(new)} neue Felder")

def list_new_globals(ref, cur, out):
    out.append("\n--- NEUE GLOBALS in progs.dat (nicht in qwprogs.dat.bak) ---")
    ref_names = {g["name"] for g in ref["globaldefs"]}
    new = [g for g in cur["globaldefs"] if g["name"] not in ref_names]
    if not new:
        out.append("  (keine)")
        return
    c_g = find_marker(cur["globaldefs"], "end_sys_globals")
    for g in new:
        pos = cur["globaldefs"].index(g)
        in_sys = c_g is not None and pos <= c_g
        warn = "  <<< VOR end_sys_globals!" if in_sys else ""
        out.append(f"  + {g['name']:<30} {type_name(g['type']):<15} ofs={g['ofs']:<5}{warn}")
    out.append(f"  Gesamt: {len(new)} neue Globals")

def list_unknown_types(cur, out):
    out.append("\n--- UNBEKANNTE FELDTYPEN (nicht in Standard-Liste) ---")
    unknown = sorted({d["type"] for d in cur["fielddefs"] + cur["globaldefs"]
                      if d["type"] not in EV_NAMES})
    if not unknown:
        out.append("  ✅ (keine)")
        return
    for t in unknown:
        out.append(f"  ❌ Typ {t} (numerisch) – alte Binary kennt ihn möglicherweise nicht")

def main():
    if len(sys.argv) != 3:
        sys.exit("Aufruf: compare_progs.py <aktuell.dat> <referenz.dat>")

    cur_path, ref_path = sys.argv[1], sys.argv[2]
    for p in (cur_path, ref_path):
        if not os.path.exists(p):
            sys.exit(f"FEHLER: {p} fehlt.")

    ref = parse_progs(ref_path)
    cur = parse_progs(cur_path)

    out = []
    out.append("=" * 78)
    out.append(f"REFERENZ (funktioniert): {ref_path}   {ref['size']} Bytes")
    out.append(f"AKTUELL   (stürzt ab):   {cur_path}   {cur['size']} Bytes")
    out.append(f"Größen-Differenz:        {cur['size'] - ref['size']:+d} Bytes")
    out.append("=" * 78)

    out.append("\n--- HEADER ---")
    out.append(f"{'Feld':<20} {'Referenz':>15} {'Aktuell':>15} {'Diff':>10}")
    out.append("-" * 62)
    for key in ["size", "version", "crc", "num_statements", "num_globaldefs",
                "num_fielddefs", "num_functions", "num_strings", "num_globals",
                "entityfields"]:
        r, c = ref[key], cur[key]
        diff = c - r
        mark = "  <<<" if r != c else ""
        out.append(f"{key:<20} {r:>15} {c:>15} {diff:>+10}{mark}")

    out.append("\n--- KRITISCH: entityfields ---")
    if ref["entityfields"] != cur["entityfields"]:
        out.append(f"  ❌ UNTERSCHIED: {ref['entityfields']} vs {cur['entityfields']}")
        out.append("     Die alte Binary allokiert Entities mit der Referenz-Größe.")
        out.append("     Jede Abweichung führt zu Speicherzugriffen außerhalb des Puffers.")
    else:
        out.append(f"  ✅ Identisch: {ref['entityfields']}")

    sys_fields_ok = diff_sys_fields(ref, cur, out)
    sys_globals_ok = diff_sys_globals(ref, cur, out)
    list_new_fields(ref, cur, out)
    list_new_globals(ref, cur, out)
    list_unknown_types(cur, out)

    out.append("\n" + "=" * 78)
    out.append("ZUSAMMENFASSUNG")
    out.append("=" * 78)
    critical = (ref["entityfields"] != cur["entityfields"]) or (not sys_fields_ok) or (not sys_globals_ok)
    if critical:
        out.append("❌ KRITISCHE ABWEICHUNG gefunden – das erklärt den Absturz beim Map-Load.")
        out.append("   Die Binary erwartet eine bestimmte Entity-Struktur; die aktuelle Datei")
        out.append("   liefert eine andere. → Patch muss Felder nach end_sys_fields verschieben")
        out.append("   oder die Binary mit angepasster entityfields-Größe neu kompilieren.")
    else:
        out.append("✅ Keine kritischen Abweichungen im Header oder den System-Definitionen.")
        out.append("   Ursache liegt woanders (z. B. Statement-Format, Builtin-Nummern,")
        out.append("   oder unterschiedliche Compiler-Optionen).")

    report = "\n".join(out)
    print(report)

if __name__ == "__main__":
    main()
