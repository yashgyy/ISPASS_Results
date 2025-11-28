import os
import pandas as pd
import glob
import numpy as np

def calculate_ic_hit_percentage(ic_access, ic_miss):
    if ic_access == 0:
        return 0
    return ((ic_access - ic_miss) / ic_access) * 100

def calculate_dc_hit_percentage(dc_access, l2_access_from_dc_miss):
    if dc_access == 0:
        return 0
    return ((dc_access - l2_access_from_dc_miss) / dc_access) * 100

def calculate_l2_miss_percentage(l2_miss, l2_access):
    if l2_access == 0:
        return 0
    return (l2_miss / l2_access) * 100

def calculate_l2_hit_from_ic_miss_percentage(l2_hit_from_ic_miss, l2_access_from_ic_miss):
    if l2_access_from_ic_miss == 0:
        return 0
    return (l2_hit_from_ic_miss / l2_access_from_ic_miss) * 100

def calculate_l2_hit_from_dc_miss_percentage(l2_hit_from_dc_miss, l2_access_from_dc_miss):
    if l2_access_from_dc_miss == 0:
        return 0
    return (l2_hit_from_dc_miss / l2_access_from_dc_miss) * 100

def calculate_l2_hit_from_hwpf_percentage(l2_hit_from_hwpf, l2_access_from_hwpf):
    if l2_access_from_hwpf == 0:
        return 0
    return (l2_hit_from_hwpf / l2_access_from_hwpf) * 100

def is_valid_data_row(row_data, headers):
    if len(row_data) != len(headers):
        return False
    
    try:
        first_val = row_data[0].strip()
        if first_val and first_val != '':
            float(first_val)
            return True
    except (ValueError, IndexError):
        pass
    
    return False

def parse_csv_file(file_path, min_rows=1):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        system_aggregated_index = -1
        for i, line in enumerate(lines):
            if 'System (Aggregated)' in line:
                system_aggregated_index = i
                break
        
        if system_aggregated_index == -1:
            return None
        
        if system_aggregated_index + 1 >= len(lines):
            return None
            
        header_line = lines[system_aggregated_index + 1].strip()
        headers = [col.strip() for col in header_line.split(',')]
        
        data_rows = []
        for i in range(system_aggregated_index + 2, len(lines)):
            line = lines[i].strip()
            if line:
                row_data = [col.strip() for col in line.split(',')]
                if is_valid_data_row(row_data, headers):
                    data_rows.append(row_data)
        
        if len(data_rows) < min_rows:
            return None
        
        df = pd.DataFrame(data_rows, columns=headers)
        
        for col in df.columns:
            if col.strip():
                try:
                    df[col] = pd.to_numeric(df[col], errors='ignore')
                except:
                    pass
        
        return df
    
    except Exception as e:
        return None

def find_column_value(df, column_variants):
    """
    Try to find a column from a list of possible column names and return its mean value.
    Returns NaN if none of the variants are found.
    """
    for col_name in column_variants:
        if col_name in df.columns:
            return df[col_name].mean()
    return np.nan

def extract_and_calculate_metrics(df, filename):
    extracted_data = {'filename': filename}
    
    # Debug: Print available columns for AMDC files
    if 'AMDC_AMDS' in filename:
        print(f"\nDEBUG - Processing {filename}:")
        print("Available columns:")
        for i, col in enumerate(df.columns):
            if 'HWPF' in col or 'hwpf' in col:
                print(f"  {i}: {col}")
    
    # Define all possible column name variants for each metric
    column_variants = {
        'utilization_pct': ['Utilization (%)'],
        'ipc_sys_user': ['IPC (Sys + User)'],
        'ic_access': ['IC Access (pti)'],
        'ic_miss': ['IC Miss (pti)'],
        'dc_access': ['DC Access (pti)'],
        'l2_access': ['L2 Access (pti)'],
        'l2_access_from_ic_miss': ['L2 Access from IC Miss (pti)'],
        'l2_access_from_dc_miss': ['L2 Access from DC Miss (pti)'],
        'l2_access_from_hwpf': ['L2 Access from HWPF (pti)', 'L2 Access from L2 HWPF (pti)'],
        'l2_miss': ['L2 Miss (pti)'],
        'l2_hit_from_ic_miss_raw': ['L2 Hit from IC Miss (pti)'],
        'l2_hit_from_dc_miss_raw': ['L2 Hit from DC Miss (pti)'],
        'l2_hit_from_hwpf_raw': ['L2 Hit from HWPF (pti)', 'L2 Hit from L2 HWPF (pti)'],
        'l3_miss_pct': ['L3 Miss %'],
        'total_mem_bw': ['Total Mem Bw (GB/s)'],
        'total_mem_rdbw': ['Total Mem RdBw (GB/s)'],
        'total_mem_wrbw': ['Total Mem WrBw (GB/s)']
    }
    
    # Extract all raw metrics using column variants
    for key, variants in column_variants.items():
        extracted_data[key] = find_column_value(df, variants)
        
        # Debug HWPF extraction for AMDC files
        if 'AMDC_AMDS' in filename and 'hwpf' in key:
            print(f"  {key}: trying {variants}")
            for variant in variants:
                if variant in df.columns:
                    print(f"    FOUND: {variant} = {df[variant].mean()}")
                else:
                    print(f"    NOT FOUND: {variant}")
            print(f"    FINAL VALUE: {extracted_data[key]}")
    
    # Calculate derived metrics
    try:
        # IC Hit %
        if not (pd.isna(extracted_data['ic_access']) or pd.isna(extracted_data['ic_miss'])):
            extracted_data['ic_hit_pct'] = calculate_ic_hit_percentage(
                extracted_data['ic_access'], 
                extracted_data['ic_miss']
            )
        else:
            extracted_data['ic_hit_pct'] = np.nan
        
        # DC Hit %
        if not (pd.isna(extracted_data['dc_access']) or pd.isna(extracted_data['l2_access_from_dc_miss'])):
            extracted_data['dc_hit_pct'] = calculate_dc_hit_percentage(
                extracted_data['dc_access'], 
                extracted_data['l2_access_from_dc_miss']
            )
        else:
            extracted_data['dc_hit_pct'] = np.nan
        
        # L2 Miss %
        if not (pd.isna(extracted_data['l2_miss']) or pd.isna(extracted_data['l2_access'])):
            extracted_data['l2_miss_pct'] = calculate_l2_miss_percentage(
                extracted_data['l2_miss'], 
                extracted_data['l2_access']
            )
        else:
            extracted_data['l2_miss_pct'] = np.nan
        
        # L2 Hit% from IC Miss
        if not (pd.isna(extracted_data['l2_hit_from_ic_miss_raw']) or pd.isna(extracted_data['l2_access_from_ic_miss'])):
            extracted_data['l2_hit_from_ic_miss_pct'] = calculate_l2_hit_from_ic_miss_percentage(
                extracted_data['l2_hit_from_ic_miss_raw'], 
                extracted_data['l2_access_from_ic_miss']
            )
        else:
            extracted_data['l2_hit_from_ic_miss_pct'] = np.nan
        
        # L2 Hit% from DC Miss
        if not (pd.isna(extracted_data['l2_hit_from_dc_miss_raw']) or pd.isna(extracted_data['l2_access_from_dc_miss'])):
            extracted_data['l2_hit_from_dc_miss_pct'] = calculate_l2_hit_from_dc_miss_percentage(
                extracted_data['l2_hit_from_dc_miss_raw'], 
                extracted_data['l2_access_from_dc_miss']
            )
        else:
            extracted_data['l2_hit_from_dc_miss_pct'] = np.nan
        
        # L2 Hit% from HWPF
        if not (pd.isna(extracted_data['l2_hit_from_hwpf_raw']) or pd.isna(extracted_data['l2_access_from_hwpf'])):
            extracted_data['l2_hit_from_hwpf_pct'] = calculate_l2_hit_from_hwpf_percentage(
                extracted_data['l2_hit_from_hwpf_raw'], 
                extracted_data['l2_access_from_hwpf']
            )
            # Debug HWPF calculation for AMDC files
            if 'AMDC_AMDS' in filename:
                print(f"  HWPF CALCULATION:")
                print(f"    l2_hit_from_hwpf_raw: {extracted_data['l2_hit_from_hwpf_raw']}")
                print(f"    l2_access_from_hwpf: {extracted_data['l2_access_from_hwpf']}")
                print(f"    l2_hit_from_hwpf_pct: {extracted_data['l2_hit_from_hwpf_pct']}")
        else:
            extracted_data['l2_hit_from_hwpf_pct'] = np.nan
            if 'AMDC_AMDS' in filename:
                print(f"  HWPF CALCULATION FAILED:")
                print(f"    l2_hit_from_hwpf_raw: {extracted_data['l2_hit_from_hwpf_raw']}")
                print(f"    l2_access_from_hwpf: {extracted_data['l2_access_from_hwpf']}")
            
    except Exception as e:
        if 'AMDC_AMDS' in filename:
            print(f"  ERROR in calculations: {e}")
        pass
    
    return extracted_data

def main():
    input_dir = "Raw_Files"
    output_dir = "Results_Parsed"
    
    if not os.path.exists(input_dir):
        return
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    amds_pattern = os.path.join(input_dir, "AMDS*.csv")
    amdc_pattern = os.path.join(input_dir, "AMDC*.csv")
    
    amds_files = glob.glob(amds_pattern)
    amdc_files = glob.glob(amdc_pattern)
    csv_files = sorted(amds_files + amdc_files)
    
    if not csv_files:
        return
    
    all_metrics = []
    
    for csv_file in csv_files:
        filename = os.path.basename(csv_file)
        df = parse_csv_file(csv_file, min_rows=1)
        
        if df is not None:
            metrics = extract_and_calculate_metrics(df, filename)
            all_metrics.append(metrics)
    
    if all_metrics:
        summary_df = pd.DataFrame(all_metrics)
        
        column_order = [
            'filename', 'utilization_pct', 'ipc_sys_user',
            'ic_hit_pct', 'dc_hit_pct', 'l2_miss_pct', 'l3_miss_pct',
            'l2_hit_from_ic_miss_pct', 'l2_hit_from_dc_miss_pct', 'l2_hit_from_hwpf_pct',
            'total_mem_bw', 'total_mem_rdbw', 'total_mem_wrbw',
            'ic_access', 'ic_miss', 'dc_access', 'l2_access',
            'l2_access_from_ic_miss', 'l2_access_from_dc_miss', 'l2_access_from_hwpf', 'l2_miss',
            'l2_hit_from_ic_miss_raw', 'l2_hit_from_dc_miss_raw', 'l2_hit_from_hwpf_raw'
        ]
        
        available_columns = [col for col in column_order if col in summary_df.columns]
        summary_df = summary_df[available_columns]
        
        summary_file = os.path.join(output_dir, "performance_metrics_summary.csv")
        summary_df.to_csv(summary_file, index=False)

if __name__ == "__main__":
    main()