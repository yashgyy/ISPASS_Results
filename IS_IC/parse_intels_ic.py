import csv
import sys
import os
import glob

def parse_and_calculate_metrics(input_file_path):
    """
    Parses a CSV file from 'perf stat', calculates performance metrics,
    and returns them as a dictionary.

    Args:
        input_file_path (str): The path to the input CSV file.

    Returns:
        dict: A dictionary of the calculated performance metrics.
              Returns None if the file cannot be processed.
    """
    if not os.path.exists(input_file_path):
        return None

    events = {}
    try:
        with open(input_file_path, 'r') as f:
            # Filter out comment lines and empty lines
            reader = csv.reader(filter(lambda row: row.strip() and not row.strip().startswith('#'), f))
            for row in reader:
                try:
                    value_str = row[0].strip()
                    event_name = row[2].strip()

                    if '<not supported>' in value_str:
                        events[event_name] = 0
                    else:
                        events[event_name] = int(value_str)
                except (IndexError, ValueError):
                    # Ignore lines that don't fit the expected event format
                    continue
    except Exception as e:
        return None

    if not events:
        return None

    # --- Calculation (keeping original logic exactly) ---
    metrics = {'filename': os.path.basename(input_file_path)}
    def safe_divide(numerator, denominator):
        return (numerator / denominator) * 100 if denominator else 0.0

    try:
        # L1 Instruction Cache Miss Percentage
        ic_loads = events.get('cpu_atom/icache.accesses/', 0) - events.get('cpu_atom/icache.misses/', 0)
        metrics['IC_Miss_Percentage'] = safe_divide(events.get('cpu_atom/icache.misses/', 0), ic_loads)

        # L1 Data Cache Miss Percentage
        metrics['DC_Miss_Percentage'] = safe_divide(events.get('cpu_core/L1-dcache-load-misses/', 0), events.get('cpu_core/L1-dcache-loads/', 0))

        # L2 Miss Percentage
        metrics['L2_Miss_Percentage'] = safe_divide(events.get('cpu_core/l2_rqsts.miss/', 0), events.get('cpu_core/l2_rqsts.references/', 0))

        # L3 Miss Percentage
        metrics['L3_Miss_Percentage'] = safe_divide(events.get('cpu_core/LLC-load-misses/', 0), events.get('cpu_core/LLC-loads/', 0))

        # L2 Miss Rate from IC Misses
        metrics['L2_Miss_Rate_from_IC_Miss'] = safe_divide(events.get('cpu_core/l2_rqsts.code_rd_miss/', 0), events.get('cpu_atom/icache.misses/', 0))

        # L2 Miss Rate from DC Misses
        metrics['L2_Miss_Rate_from_DC_Miss'] = safe_divide(events.get('cpu_core/l2_rqsts.demand_data_rd_miss/', 0), events.get('cpu_core/L1-dcache-load-misses/', 0))
        
        # Calculate Hit Percentages (complement of miss percentages)
        metrics['IC_Hit_Percentage'] = 100.0 - metrics['IC_Miss_Percentage']
        metrics['DC_Hit_Percentage'] = 100.0 - metrics['DC_Miss_Percentage']
        metrics['L2_Hit_Percentage'] = 100.0 - metrics['L2_Miss_Percentage']
        metrics['L3_Hit_Percentage'] = 100.0 - metrics['L3_Miss_Percentage']
        
    except KeyError as e:
        pass

    return metrics

def write_summary_csv(output_file_path, all_metrics):
    """
    Writes all calculated metrics to a summary CSV file.

    Args:
        output_file_path (str): The path for the output CSV file.
        all_metrics (list): List of dictionaries containing metrics for each file.
    """
    if not all_metrics:
        return

    try:
        # Get all unique metric keys
        all_keys = set()
        for metrics in all_metrics:
            all_keys.update(metrics.keys())
        
        # Sort keys to have filename first, then alphabetically
        sorted_keys = ['filename'] + sorted([k for k in all_keys if k != 'filename'])
        
        with open(output_file_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=sorted_keys)
            writer.writeheader()
            for metrics in all_metrics:
                writer.writerow(metrics)
                
    except Exception as e:
        pass

def main():
    """
    Main function to process all CSV files starting with IS or IN.
    """
    input_dir = "Raw_Files"
    output_dir = "Results_Parsed"
    
    # Check if Raw_Files directory exists
    if not os.path.exists(input_dir):
        return
    
    # Create output directory
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Find all CSV files starting with IS_AMDC_micro or IC_AMDC_micro
    is_amdc_pattern = os.path.join(input_dir, "IC_IS__micro*.csv")
    ic_amdc_pattern = os.path.join(input_dir, "IC_IS_micro*.csv")
    
    is_amdc_files = glob.glob(is_amdc_pattern)
    ic_amdc_files = glob.glob(ic_amdc_pattern)
    csv_files = sorted(is_amdc_files + ic_amdc_files)
    
    if not csv_files:
        return
    
    all_metrics = []
    
    # Process each CSV file
    for csv_file in csv_files:
        metrics = parse_and_calculate_metrics(csv_file)
        if metrics:
            all_metrics.append(metrics)
    
    # Write summary file
    if all_metrics:
        summary_file = os.path.join(output_dir, "perf_metrics_summary_micro.csv")
        write_summary_csv(summary_file, all_metrics)

if __name__ == "__main__":
    main()