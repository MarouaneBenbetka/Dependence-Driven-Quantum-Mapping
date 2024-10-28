import os
import csv
from main import main  # Assumes `main` is defined in main.py

# Root folder containing benchmark folders with JSON files
ROOT_FOLDER_PATH = "benchmarks/polyhedral"
LOG_FILE = "benchmark_results.csv"



# Initialize the CSV file
with open(LOG_FILE, mode='w', newline='') as log_file:
    writer = csv.writer(log_file)
    writer.writerow(["Benchmark", "File", "Execution Time", "Swap Count", "Iteration Count"])

    # Walk through all folders and files in the root directory
    for root, _, files in os.walk(ROOT_FOLDER_PATH):
        # Get the name of the current benchmark folder
        benchmark_name = os.path.basename(root)


        # Process each JSON file in the current folder
        for filename in files:
            if filename.endswith(".json"):
                file_path = os.path.join(root, filename)
                print(f"Processing {file_path} in benchmark {benchmark_name}...")

                # Run the `main` function and capture output
                exec_time, swap_count, iteration = main(file_path)

                # Write results to CSV file, including benchmark folder name
                writer.writerow([benchmark_name, filename, exec_time, swap_count, iteration])

print(f"Benchmark completed. Results saved in {LOG_FILE}.")