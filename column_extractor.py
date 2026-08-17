import os
import json
import pandas as pd
from io import StringIO

CONFIG_FILE = "config.json"
EXCEL_OUTPUT = "Column_DC_Dashboard.xlsx"

def calculate_nscp_capacity(width, depth, fc, fy, steel_ratio):
    """Calculates the NSCP 2015 factored ultimate axial capacity limit (phi Pn max)."""
    ag = width * depth
    ast = ag * (steel_ratio / 100.0)
    phi = 0.65 # Tied columns
    nominal_pn = (0.85 * fc * (ag - ast)) + (fy * ast)
    return round((0.80 * phi * nominal_pn) / 1000.0, 1) # Output in kN

def load_multi_profile_config():
    """Reads the configuration block and maps individual column limits."""
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError("Please ensure your config.json file is present!")

    with open(CONFIG_FILE, 'r') as f:
        cfg = json.load(f)

    fc = cfg["concrete_f_c_mpa"]
    fy = cfg["steel_f_y_mpa"]
    ratio = cfg["steel_ratio_percent"]

    member_to_capacity = {}
    member_to_section = {}
    master_member_list = []

    print("📊 Processing dynamic cross-sectional capacity baselines...")
    for group in cfg["column_groups"]:
        name = group["section_name"]
        w = group["width_mm"]
        d = group["depth_mm"]
        raw_ids = group["column_ids"]

        flattened_ids = []
        for item in raw_ids:
            if isinstance(item, list): flattened_ids.extend(item)
            else: flattened_ids.append(item)

        capacity_kn = calculate_nscp_capacity(w, d, fc, fy, ratio)
        print(f" 📐 Group '{name}': {w}x{d} mm -> Capacity Limit: {capacity_kn} kN")

        for col_id in flattened_ids:
            member_to_capacity[int(col_id)] = capacity_kn
            member_to_section[int(col_id)] = name
            master_member_list.append(int(col_id))

    return master_member_list, member_to_capacity, member_to_section

def extract_column_forces_from_envelope_table():
    try:
        member_list, capacity_map, section_map = load_multi_profile_config()
    except Exception as err:
        print(f"❌ Initialization Failed: {err}")
        return
    
    force_data = []

    try:
        import win32clipboard
        print("\n📋 Accessing active system clipboard data stream...")
        
        win32clipboard.OpenClipboard()
        raw_data = win32clipboard.GetClipboardData()
        win32clipboard.CloseClipboard()
        
        clean_string = StringIO(raw_data.strip())
        df_clip = pd.read_csv(clean_string, sep="\t")
        df_clip.columns = [str(col).strip() for col in df_clip.columns]
        
        # 🌐 BROAD SPECTRUM HEADER LOOKUP MAPPING
        beam_col = next((c for c in df_clip.columns if c.lower().startswith('beam') or c.lower() == 'id'), None)
        lc_col = next((c for c in df_clip.columns if any(k in c.lower() for k in ['l/c', 'case', 'load', 'env'])), None)
        fx_col = next((c for c in df_clip.columns if 'fx' in c.lower() or 'axial' in c.lower()), None)
        my_col = next((c for c in df_clip.columns if 'my' in c.lower() or 'moment-y' in c.lower() or 'bending-y' in c.lower()), None)
        
        # Safe extraction for Mz to avoid list-wrapper errors
        mz_col_list = [c for c in df_clip.columns if 'mz' in c.lower() or 'moment-z' in c.lower() or 'bending-z' in c.lower()]
        mz_col = mz_col_list[0] if mz_col_list else None

        # Verify that all target headers successfully synchronized
        if not all([beam_col, lc_col, fx_col, my_col, mz_col]):
            raise ValueError(f"Could not map all necessary headers. Found: {df_clip.columns.tolist()}")

        print(f"✅ Successfully mapped headers -> Beam: '{beam_col}', L/C Identifier: '{lc_col}'")
        
        df_clip[beam_col] = pd.to_numeric(df_clip[beam_col], errors='coerce')
        df_clip = df_clip[df_clip[beam_col].isin(member_list)]
        
        for _, row in df_clip.iterrows():
            force_data.append({
                "Member_ID": int(row[beam_col]),
                "Load_Case": f"Envelope Type {str(row[lc_col]).strip()}", # Clean label identifier
                "Pu_kN": abs(float(row[fx_col])),
                "Mux_kNm": abs(float(row[my_col])),
                "Muz_kNm": abs(float(row[mz_col]))
            })
            
    except Exception as e:
        print(f"❌ Clipboard matrix extraction failed: {e}")
        print("💡 Click inside your 'Envelope' table, press Ctrl+A, then Ctrl+C first!")
        return

    if not force_data:
        print("❌ Filtered results are empty. Ensure your clipboard contains data from the 'Envelope' table.")
        return

    df = pd.DataFrame(force_data)
    
    # Process ultimate dynamic envelopes cleanly
    summary_df = df.groupby("Member_ID").agg({
        "Load_Case": "first",
        "Pu_kN": "max",
        "Mux_kNm": "max",
        "Muz_kNm": "max"
    }).reset_index()

    summary_df["Pu_kN"] = summary_df["Pu_kN"].round(2)
    summary_df["Mux_kNm"] = summary_df["Mux_kNm"].round(2)
    summary_df["Muz_kNm"] = summary_df["Muz_kNm"].round(2)

    summary_df["Section_Type"] = summary_df["Member_ID"].map(section_map)
    summary_df["Capacity_Limit_kN"] = summary_df["Member_ID"].map(capacity_map)
    
    summary_df["D_C_Ratio"] = round(summary_df["Pu_kN"] / summary_df["Capacity_Limit_kN"], 3)
    summary_df["Status"] = summary_df["D_C_Ratio"].apply(lambda x: "PASS" if x < 1.0 else "FAIL")

    columns_ordered = ["Member_ID", "Section_Type", "Load_Case", "Pu_kN", "Mux_kNm", "Muz_kNm", "Capacity_Limit_kN", "D_C_Ratio", "Status"]
    summary_df = summary_df[columns_ordered]

    # 🧠 THE SORTING FIX: Organizes rows from highest structural stress to lowest stress automatically
    summary_df = summary_df.sort_values(by="D_C_Ratio", ascending=False).reset_index(drop=True)

    print("\n--- CRITICAL COLUMN ENVELOPE SUMMARY (SORTED BY HIGHEST STRESS) ---")
    print(summary_df.to_string(index=False))
    print("-------------------------------------------------------------")

    summary_df.to_excel(EXCEL_OUTPUT, index=False)
    print(f"\n🎉 Success! Post-processing sheet exported to:\n📌 {os.path.abspath(EXCEL_OUTPUT)}")

if __name__ == "__main__":
    extract_column_forces_from_envelope_table()
