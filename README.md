# Automated NSCP 2015 Column Demand vs. Capacity (D/C) Analyzer for STAAD.Pro

A robust, data-driven post-processing pipeline designed to automate structural compliance audits for concrete buildings. This tool connects to **STAAD.Pro CONNECT Edition** via a hybrid architecture (Local Disk Data Parsing + Windows COM Layer Clipboard Overrides), completely bypassing broken or cracked software type-library limitations (`'int' object is not callable` errors).

The engine parses the raw structure, dynamically calculates the ultimate factored axial compression capacity envelope pursuant to the **National Structural Code of the Philippines (NSCP 2015) Chapter 4**, filters out unwanted floor beam records, and generates an executive dashboard sorted by maximum structural stress.

---

## Key Engineering Automation Features

- **Automated Geometric Member ID Classification:** Bypasses unstable GUI selection buffers by opening the `.std` file directly on the disk. It screens coordinates to isolate perfectly vertical structural frames (parallel to the Global Y-axis).
- **Multi-Profile Dynamic Grouping:** Automatically reads the `MEMBER PROPERTY` text blocks, isolates unique section dimensions (e.g., \(300\times300\text{ mm}\) vs. \(400\times300\text{ mm}\)), and writes them natively into a structured layout layer (`config.json`).
- **Live Vectorized NSCP 2015 Verification Engine:** Automatically executes the tied concrete column factored capacity equation (\(\phi P_{n,max}\)) based on concrete grade (\(f'_c\)), reinforcing steel yield bounds (\(f_y\)), and reinforcement ratios (\(\rho_g\)) mapped per group:
  \[\phi P_{n,max} = 0.80 \cdot \phi \cdot \left[ 0.85 \cdot f'_c \cdot (A_g - A_{st}) + f_y \cdot A_{st} \right]\]
- **High-Utility Portfolio Sorting:** Decouples sorting arrays to automatically float the most heavily stressed or critical elements straight to the top row of your Excel report matrix.

---

## Step-by-Step Execution Guide

### 1. Workstation Initialization
Clone this repository to your machine, open a Command Prompt inside the directory path, and execute the universal package alignment launcher:
```bash
py -m pip install -r requirements.txt
```

### 2. Auto-Detect Columns and Cross-Sections
Place a copy of your model's **`.std`** input text file inside this project folder. Open **STAAD.Pro** with your analyzed model running in the background. Execute the geometric classifier scanner:
```bash
py column_finder.py
```
*Result:* The script reads your structure, identifies all vertical columns, maps their exact cross-sectional sizes, and updates your `config.json` rules dynamically.

### 3. Generate the Executive Portfolio Dashboard
1. Inside your active STAAD post-processing window, click on the **Envelope** results tab layout on your sidebar.
2. Click once inside the table, press **`Ctrl + A`** (select all extreme rows) and hit **`Ctrl + C`** (copy to clipboard).
3. Switch to your code terminal and run the extraction injector module:
```bash
py column_extractor.py
```

---

## Sample Production Output Dashboard

The script compiles the nested data arrays and updates a beautifully formatted spreadsheet report file named `Column_DC_Dashboard.xlsx` in your folder. The terminal will output a sorted data matrix stream:

```text
📊 Processing dynamic cross-sectional capacity baselines...
 📐 Group 'C300x300 Columns': 300x300 mm -> Capacity Limit: 1114.2 kN

📋 Accessing active system clipboard data stream...
✅ Successfully mapped headers -> Beam: 'Beam', L/C Identifier: 'Env'

--- MULTI-PROFILE CRITICAL COLUMN ENVELOPE SUMMARY (SORTED BY HIGHEST STRESS) ---
 Member_ID     Section_Type            Load_Case  Pu_kN  Mux_kNm  Muz_kNm  Capacity_Limit_kN  D_C_Ratio Status
        18 C300x300 Columns Envelope Type Max +ve 361.89     5.40     0.33             1114.2      0.325   PASS
        10 C300x300 Columns Envelope Type Max +ve 319.46     3.85     7.40             1114.2      0.287   PASS
         2 C300x300 Columns Envelope Type Max +ve 298.69     2.14     6.68             1114.2      0.268   PASS
        55 C300x300 Columns Envelope Type Max +ve 194.84     4.89    10.62             1114.2      0.175   PASS
         1 C300x300 Columns Envelope Type Max +ve 183.77     0.00     0.00             1114.2      0.165   PASS

🎉 Success! Scaled post-processing dashboard exported to:
📌 E:\Work\AI Automation Projects\The Automatic RC Column Demand vs Capacity Ratio\Column_DC_Dashboard.xlsx
```

---

## 🛠️ Built With
- **Python 3.13** (64-bit platform core architecture)
- **Pandas DataFrames** (Vectorized string mapping matrix filtering)
- **PyWin32 Library Interface** (Low-level Windows clipboard automation engine)
