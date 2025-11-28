#!/usr/bin/env python3
"""
Parse performance and energy CSV files from Raw_Files folder
and create a consolidated Excel file in Results_Parsed folder
"""

import pandas as pd
import os
import glob
import re
from datetime import datetime

def parse_energy_file(filepath):
    """Parse energy CSV files to extract energy in Joules"""
    data = {}
    filename = os.path.basename(filepath)
    
    # Extract algorithm name from filename
    if '_energy_' in filename:
        parts = filename.replace('.csv', '').split('_energy_')
        data['Config'] = parts[0]
        data['Algorithm'] = parts[1] if len(parts) > 1 else 'unknown'
        data['Type'] = 'energy'
    
    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
            for line in lines:
                if 'Joules' in line:
                    parts = line.strip().split(',')
                    data['Energy_Joules'] = float(parts[0])
                    break
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
    
    return data

def parse_performance_file(filepath):
    """Parse performance CSV files to extract branch statistics"""
    data = {}
    filename = os.path.basename(filepath)
    
    # Extract algorithm name from filename
    if '_performance_' in filename or '_perfomance_' in filename:  # Note: handling typo
        parts = filename.replace('.csv', '').replace('_perfomance_', '_performance_').split('_performance_')
        data['Config'] = parts[0]
        data['Algorithm'] = parts[1] if len(parts) > 1 else 'unknown'
        data['Type'] = 'performance'
    
    branch_instructions = None
    branch_misses = None
    
    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
            for line in lines:
                if 'branch-instructions' in line:
                    parts = line.strip().split(',')
                    branch_instructions = int(parts[0])
                    data['Branch_Instructions'] = branch_instructions
                elif 'branch-misses' in line:
                    parts = line.strip().split(',')
                    branch_misses = int(parts[0])
                    data['Branch_Misses'] = branch_misses
                    # Extract the percentage if available
                    if len(parts) > 4:
                        try:
                            data['Misses_Percentage_Reported'] = float(parts[4])
                        except:
                            pass
    
        # Calculate miss percentage
        if branch_instructions and branch_misses:
            data['Misses_Percentage_Calculated'] = (branch_misses / branch_instructions) * 100
    
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
    
    return data

def main():
    # Define file patterns to search for
    patterns = [
        'AMDC_AMDS_performance_pb*.csv',
        'AMDC_AMDS_perfomance_pb*.csv',  # Handle typo in filename
        'AMDS_AMDC_performance_pc*.csv',
        'AMDS_AMDC_perfomance_pc*.csv',  # Handle typo in filename
        'AMDC_AMDS_pb_energy*.csv',
        'AMDS_AMDC_pb_energy*.csv',
        'AMDC_AMDS_pb_performance*.csv',
        'AMDS_AMDC_pb_performance*.csv'
    ]
    
    raw_files_dir = 'Raw_Files'
    results_dir = 'Results_Parsed'
    
    # Ensure directories exist
    os.makedirs(raw_files_dir, exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)
    
    # Dictionary to store data grouped by config and algorithm
    grouped_data = {}
    
    # Process each pattern
    for pattern in patterns:
        files = glob.glob(os.path.join(raw_files_dir, pattern))
        print(f"Found {len(files)} files matching pattern: {pattern}")
        
        for filepath in files:
            print(f"Processing: {os.path.basename(filepath)}")
            
            # Determine file type and parse accordingly
            if 'energy' in filepath.lower():
                data = parse_energy_file(filepath)
            elif 'performance' in filepath.lower() or 'perfomance' in filepath.lower():
                data = parse_performance_file(filepath)
            else:
                continue
            
            if data and 'Config' in data and 'Algorithm' in data:
                # Create a key for grouping
                key = (data['Config'], data['Algorithm'])
                
                # Initialize group if not exists
                if key not in grouped_data:
                    grouped_data[key] = {
                        'Config': data['Config'],
                        'Algorithm': data['Algorithm'],
                        'Performance_File': '',
                        'Energy_File': ''
                    }
                
                # Merge the data based on type
                if data.get('Type') == 'performance':
                    grouped_data[key]['Performance_File'] = os.path.basename(filepath)
                    grouped_data[key]['Branch_Instructions'] = data.get('Branch_Instructions', None)
                    grouped_data[key]['Branch_Misses'] = data.get('Branch_Misses', None)
                    grouped_data[key]['Misses_%'] = data.get('Misses_Percentage_Calculated', None)
                elif data.get('Type') == 'energy':
                    grouped_data[key]['Energy_File'] = os.path.basename(filepath)
                    grouped_data[key]['Energy_Joules'] = data.get('Energy_Joules', None)
    
    if not grouped_data:
        print("No data files found to process!")
        return
    
    # Convert grouped data to list for DataFrame
    all_data = list(grouped_data.values())
    
    # Create DataFrame
    df = pd.DataFrame(all_data)
    
    # Reorganize columns in desired order
    column_order = [
        'Config',
        'Algorithm', 
        'Branch_Instructions',
        'Branch_Misses',
        'Misses_%',
        'Energy_Joules',
        'Performance_File',
        'Energy_File'
    ]
    
    # Only keep columns that exist
    column_order = [col for col in column_order if col in df.columns]
    
    # Add any remaining columns
    for col in df.columns:
        if col not in column_order:
            column_order.append(col)
    
    df = df[column_order]
    
    # Sort by Config and Algorithm
    df = df.sort_values(['Config', 'Algorithm'])
    
    # Generate output filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(results_dir, f'parsed_performance_energy_data_{timestamp}.xlsx')
    
    # Write to Excel with formatting
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Parsed_Data', index=False)
        
        # Get the workbook and worksheet
        workbook = writer.book
        worksheet = writer.sheets['Parsed_Data']
        
        # Adjust column widths
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
        
        # Format percentage column
        from openpyxl.styles import numbers
        for row in worksheet.iter_rows(min_row=2):
            for idx, cell in enumerate(row):
                # Format Misses_% column (should be column E, index 4)
                if idx == 4 and cell.value is not None:  
                    cell.number_format = '0.00%'
    
    print(f"\nParsing complete!")
    print(f"Output file: {output_file}")
    print(f"Total models processed: {len(df)}")
    
    # Display summary
    print("\nSummary of parsed data:")
    print(df.to_string())
    
    return output_file

if __name__ == "__main__":
    main()