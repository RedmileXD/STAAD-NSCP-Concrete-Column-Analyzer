import os
import json

def parse_member_list(member_string):
    """Converts a STAAD member list string like '1 2 4 TO 7 9' into a clean Python list [1, 2, 4, 5, 6, 7, 9]."""
    tokens = member_string.split()
    members = []
    i = 0
    while i < len(tokens):
        if tokens[i] == "TO" and i > 0 and i + 1 < len(tokens):
            start = members[-1]
            end = int(tokens[i+1])
            members.extend(list(range(start + 1, end + 1)))
            i += 2
        else:
            try:
                members.append(int(tokens[i]))
            except ValueError:
                pass
            i += 1
    return members

def parse_staad_file_for_columns():
    print("🔍 Beginning disk search for your active STAAD model file...")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    
    std_files = [f for f in os.listdir(script_dir) if f.endswith('.std')]
    if not std_files and os.path.exists(parent_dir):
        std_files = [f for f in os.listdir(parent_dir) if f.endswith('.std')]
        
    if not std_files:
        print("❌ Error: No .std model text file found in this directory!")
        return

    target_file = os.path.join(script_dir, std_files[0]) if std_files[0] in os.listdir(script_dir) else os.path.join(parent_dir, std_files[0])
    print(f"📦 Found active model data text structure: {os.path.basename(target_file)}")

    with open(target_file, 'r') as f:
        lines = f.readlines()

    nodes = {}
    members = {}
    member_properties = {} # Key: Member_ID, Value: (width_mm, depth_mm)
    
    mode = None
    property_buffer = ""
    
    for line in lines:
        clean_line = line.strip().upper()
        if not clean_line or clean_line.startswith('*'):
            continue
            
        # State tracking setup
        if "JOINT COORDINATES" in clean_line:
            mode = "nodes"
            continue
        elif "MEMBER INCIDENCES" in clean_line:
            mode = "members"
            continue
        elif "MEMBER PROPERTY" in clean_line:
            mode = "properties"
            property_buffer = clean_line.replace("MEMBER PROPERTY", "")
            continue
        elif mode == "properties" and any(keyword in clean_line for keyword in ["START", "DEFINE", "CONSTANTS", "SUPPORTS", "LOAD"]):
            # Process the very last block of property rows when exiting the section
            mode = None
        
        # 1. Parse Node coordinates
        if mode == "nodes":
            blocks = clean_line.split(';')
            for block in blocks:
                parts = block.split()
                if len(parts) >= 4:
                    try:
                        nodes[int(parts[0])] = (float(parts[1]), float(parts[2]), float(parts[3]))
                    except ValueError: continue

        # 2. Parse Member Incidence configurations
        elif mode == "members":
            blocks = clean_line.split(';')
            for block in blocks:
                parts = block.split()
                if len(parts) >= 3:
                    try:
                        members[int(parts[0])] = (int(parts[1]), int(parts[2]))
                    except ValueError: continue

        # 3. Collect Member Property rows into a combined text string buffer
        elif mode == "properties":
            property_buffer += " " + clean_line

    # 4. Parse the Property Buffer to identify dimensions
    # Split by PRIS entries to decouple member lists from their sizes
    if property_buffer:
        # Standardize hyphens and line continuations
        property_buffer = property_buffer.replace(" -\n", " ").replace(" - ", " ")
        blocks = property_buffer.split("PRIS")
        
        for j in range(len(blocks) - 1):
            current_mem_list_str = blocks[j].split()
            next_property_str = blocks[j+1].split()
            
            # Find where the previous member list ends
            # If it's not the first block, filter out properties belonging to the earlier segment
            if j > 0:
                # Find the index of the last dimension property token from the previous loop
                for k, token in enumerate(current_mem_list_str):
                    if "ZD" in token:
                        current_mem_list_str = current_mem_list_str[k+1:]
                        break
            
            mem_list_clean = " ".join(current_mem_list_str)
            parsed_member_ids = parse_member_list(mem_list_clean)
            
            # Extract cross-sectional dimensions out of the string segments
            yd_val, zd_val = 0.0, 0.0
            for t, token in enumerate(next_property_str):
                if "YD" in token:
                    yd_val = float(next_property_str[t+1]) if t+1 < len(next_property_str) else float(token.split("YD")[-1])
                if "ZD" in token:
                    zd_val = float(next_property_str[t+1]) if t+1 < len(next_property_str) else float(token.split("ZD")[-1])
            
            # Convert dimensions from meters to millimeters
            width_mm = int(yd_val * 1000)
            depth_mm = int(zd_val * 1000)
            
            for m_id in parsed_member_ids:
                member_properties[m_id] = (width_mm, depth_mm)

    # 5. Isolate Vertical Columns and Group by Dimensions!
    groups_dict = {} # Key: (width, depth), Value: List of Member IDs
    
    print("📐 Running cross-sectional property and height delta validation filters...")
    for mem_id, (n1, n2) in members.items():
        if n1 in nodes and n2 in nodes:
            x1, y1, z1 = nodes[n1]
            x2, y2, z2 = nodes[n2]
            
            height_delta = abs(y1 - y2)
            plan_delta_x = abs(x1 - x2)
            plan_delta_z = abs(z1 - z2)
            
            # If it passes our vertical geometry column check
            if height_delta > 0.1 and plan_delta_x < 0.01 and plan_delta_z < 0.01:
                # Pull its exact cross-sectional dimension from our property map
                dimensions = member_properties.get(mem_id, (300, 300)) # Fallback default
                
                if dimensions not in groups_dict:
                    groups_dict[dimensions] = []
                groups_dict[dimensions].append(mem_id)

    # 6. Format the structured multi-profile config data block
    column_groups_json = []
    for (w, d), ids in groups_dict.items():
        section_title = f"C{w}x{d} Columns"
        column_groups_json.append({
            "section_name": section_title,
            "width_mm": w,
            "depth_mm": d,
            "column_ids": sorted(ids)
        })
        print(f" 📐 Auto-Grouped: {section_title} -> {len(ids)} members identified.")

    config_data = {
        "concrete_f_c_mpa": 21.0,
        "steel_f_y_mpa": 415.0,
        "steel_ratio_percent": 1.5,
        "column_groups": column_groups_json
    }
    
    with open("config.json", "w") as f:
        json.dump(config_data, f, indent=4)
    print("\n💾 Success! Clean multi-profile 'config.json' file generated and saved!")

if __name__ == "__main__":
    parse_staad_file_for_columns()
