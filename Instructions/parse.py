#!/usr/bin/env python3
"""
Script to process AMDC_AMDS* and AMDS_AMDC* files and create a CSV with instruction breakdowns.
"""

import os
import re
import csv
from pathlib import Path


def parse_instruction_file(filepath):
    """
    Parse an instruction file and extract the relevant metrics.
    Handles both tab-separated text files and CSV files.
    
    Returns a dictionary with the extracted values.
    """
    data = {}
    
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    # Determine file type based on extension
    is_csv = filepath.suffix.lower() == '.csv'
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        # Parse based on file type
        if is_csv:
            # Parse CSV format (comma-separated)
            # Format: value,,metric_name,other_value,number,,
            parts = line.split(',')
            if len(parts) >= 3:
                value = parts[0].strip()
                metric_name = parts[2].strip() if len(parts) > 2 else ''
            else:
                continue
        else:
            # Parse text format (tab-separated)
            # Format: value\t\tmetric_name\tother_value\tnumber
            parts = line.split('\t')
            if len(parts) < 2:
                continue
            # Clean up the parts
            parts = [p.strip() for p in parts if p.strip()]
            if len(parts) >= 2:
                value = parts[0]
                metric_name = parts[1]
            else:
                continue
        
        # Extract the main metrics - only store the first column value
        if value and metric_name:
            try:
                if 'ex_ret_instr' in metric_name or metric_name == 'instructions':
                    # This is total instructions
                    data['total_instructions'] = int(value)
                elif 'ex_ret_brn' in metric_name:
                    # Branch instructions
                    data['branch_instructions'] = int(value)
                elif 'ld_dispatch' in metric_name:
                    # Load operations
                    data['load_ops'] = int(value)
                elif 'store_dispatch' in metric_name:
                    # Store operations
                    data['store_ops'] = int(value)
            except (ValueError, IndexError) as e:
                # Skip lines that can't be parsed
                continue
    
    return data


def calculate_percentages(data):
    """
    Calculate the percentages and ALU operations from the parsed data.
    """
    result = {}
    
    # Get the values for calculations
    total = data.get('total_instructions', 0)
    branch = data.get('branch_instructions', 0)
    load = data.get('load_ops', 0)
    store = data.get('store_ops', 0)
    
    if total > 0:
        # Calculate ALU operations (remaining instructions)
        alu = total - branch - load - store
        
        # Calculate percentages
        result['percent_branch'] = (branch / total) * 100
        result['percent_load'] = (load / total) * 100
        result['percent_store'] = (store / total) * 100
        result['percent_alu'] = (alu / total) * 100
        
        # Store raw values
        result['total_instructions'] = total
        result['branch_instructions'] = branch
        result['load_ops'] = load
        result['store_ops'] = store
        result['alu_ops'] = alu
        
    else:
        # Return zeros if no data
        result = {
            'percent_branch': 0,
            'percent_load': 0,
            'percent_store': 0,
            'percent_alu': 0,
            'total_instructions': 0,
            'branch_instructions': 0,
            'load_ops': 0,
            'store_ops': 0,
            'alu_ops': 0
        }
    
    return result


def process_files():
    """
    Process all AMDC_AMDS* and AMDS_AMDC* files in the current directory.
    Handles both text files and CSV files.
    """
    current_dir = Path('.')
    results = []
    
    # Find all matching files (including CSV files)
    amdc_amds_files = list(current_dir.glob('AMDC_AMDS*'))
    amds_amdc_files = list(current_dir.glob('AMDS_AMDC*'))
    
    all_files = amdc_amds_files + amds_amdc_files
    
    if not all_files:
        print("No matching files found in the current directory.")
        return
    
    print(f"Found {len(all_files)} file(s) to process:")
    
    for filepath in all_files:
        print(f"  Processing: {filepath.name}")
        
        try:
            # Parse the file
            data = parse_instruction_file(filepath)
            
            if not data:
                print(f"    Warning: No data extracted from {filepath.name}")
                continue
            
            # Calculate percentages and ALU ops
            result = calculate_percentages(data)
            
            # Add filename and file type
            result['filename'] = filepath.name
            if filepath.name.startswith('AMDC_AMDS'):
                result['file_type'] = 'AMDC_AMDS'
            else:
                result['file_type'] = 'AMDS_AMDC'
            
            results.append(result)
            
        except Exception as e:
            print(f"    Error processing {filepath.name}: {e}")
    
    return results


def write_csv(results, output_filename='instruction_analysis.csv'):
    """
    Write the results to a CSV file.
    """
    if not results:
        print("No results to write.")
        return
    
    # Define the CSV columns - removed the _2 columns
    fieldnames = [
        'filename',
        'file_type',
        'percent_branch',
        'percent_load',
        'percent_store',
        'percent_alu',
        'total_instructions',
        'branch_instructions',
        'load_ops',
        'store_ops',
        'alu_ops'
    ]
    
    with open(output_filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        # Write header
        writer.writeheader()
        
        # Write data rows
        for row in results:
            # Round percentages to 2 decimal places
            row['percent_branch'] = round(row['percent_branch'], 2)
            row['percent_load'] = round(row['percent_load'], 2)
            row['percent_store'] = round(row['percent_store'], 2)
            row['percent_alu'] = round(row['percent_alu'], 2)
            
            writer.writerow(row)
    
    print(f"\nCSV file '{output_filename}' created successfully!")
    print("\nSummary of results:")
    print("-" * 80)
    print(f"{'Filename':<30} {'Branch%':<10} {'Load%':<10} {'Store%':<10} {'ALU%':<10}")
    print("-" * 80)
    
    for row in results:
        print(f"{row['filename']:<30} {row['percent_branch']:<10.2f} {row['percent_load']:<10.2f} {row['percent_store']:<10.2f} {row['percent_alu']:<10.2f}")


def main():
    """
    Main function to run the script.
    """
    print("Processing instruction files...")
    print("=" * 80)
    
    results = process_files()
    
    if results:
        write_csv(results)
        print("\nProcessing complete!")
    else:
        print("\nNo data was processed.")


if __name__ == "__main__":
    main()