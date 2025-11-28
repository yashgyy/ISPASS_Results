import csv
import sys
import os
import glob

def parse_bandwidth_csv(input_file_path):
    """
    Parses a CSV file containing bandwidth-related perf events.

    Args:
        input_file_path (str): The path to the input CSV file.

    Returns:
        dict: A dictionary of event counts, or None if the file is invalid.
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

    return events

def calculate_bandwidth(events, time_elapsed):
    """
    Calculates memory bandwidth in GB/s from raw perf event counts.

    Args:
        events (dict): A dictionary of event names to their integer counts.
        time_elapsed (float): The total duration of the perf run in seconds.

    Returns:
        dict: A dictionary containing the calculated bandwidth metrics.
    """
    metrics = {}
    BYTES_PER_CAS = 64
    GIGABYTE = 1024**3
    
    def safe_divide(numerator, denominator):
        return numerator / denominator if denominator else 0.0

    try:
        # Read Bandwidth
        read_bytes = events.get('unc_m_cas_count.rd_reg', 0) * BYTES_PER_CAS
        metrics['Read_Bandwidth_GBs'] = safe_divide(read_bytes, time_elapsed * GIGABYTE)
        
        # Write Bandwidth
        write_bytes = events.get('unc_m_cas_count.wr_wmm', 0) * BYTES_PER_CAS
        metrics['Write_Bandwidth_GBs'] = safe_divide(write_bytes, time_elapsed * GIGABYTE)
        
        # Total Bandwidth
        total_bytes = events.get('unc_m_cas_count.all', 0) * BYTES_PER_CAS
        metrics['Total_Bandwidth_GBs'] = safe_divide(total_bytes, time_elapsed * GIGABYTE)
    
    except KeyError as e:
        return {}
        
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
    Main function to process all CSV files starting with IS_AMDC_micro or IC_AMDC_micro.
    """
    input_dir = "Raw_Files"
    output_dir = "Results_Parsed"
    
    # The duration is hardcoded to 300 seconds
    duration = 300.0
    
    # Check if Raw_Files directory exists
    if not os.path.exists(input_dir):
        return
    
    # Create output directory
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Find all CSV files starting with IS_AMDC_micro or IC_AMDC_micro
    is_amdc_pattern = os.path.join(input_dir, "IS_AMDC_bandwidth*.csv")
    ic_amdc_pattern = os.path.join(input_dir, "IC_AMDS_bandwidth*.csv")
    
    is_amdc_files = glob.glob(is_amdc_pattern)
    ic_amdc_files = glob.glob(ic_amdc_pattern)
    csv_files = sorted(is_amdc_files + ic_amdc_files)
    
    if not csv_files:
        return
    
    all_metrics = []
    
    # Process each CSV file
    for csv_file in csv_files:
        events = parse_bandwidth_csv(csv_file)
        if events:
            calculated_metrics = calculate_bandwidth(events, duration)
            if calculated_metrics:
                calculated_metrics['filename'] = os.path.basename(csv_file)
                all_metrics.append(calculated_metrics)
    
    # Write summary file
    if all_metrics:
        summary_file = os.path.join(output_dir, "bandwidth_metrics_summary.csv")
        write_summary_csv(summary_file, all_metrics)

if __name__ == "__main__":
    main()