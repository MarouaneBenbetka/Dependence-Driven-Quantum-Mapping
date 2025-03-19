import os
import sys

PROJECT_ROOT = "/scratch/mb10325/Poly-Swap"
sys.path.append(PROJECT_ROOT)

import src.cython_isl_sabre.poly_circuit_utils as pcu
import src.cython_isl_sabre.poly_sabre as ps
import time
from qiskit.providers.fake_provider import Fake27QPulseV1,Fake5QV1,Fake20QV1

from state_of_the_art.sabre import run_sabre


def cython_run_single_file(file_path):
    edges = Fake27QPulseV1().configuration().coupling_map
    
    # poly sabre
    data = pcu.json_file_to_isl(file_path)
    poly_sabre = ps.POLY_SABRE(edges,data)
    poly_swap_count = poly_sabre.run(heuristic_method="decay",verbose=1)
    
    
    # qiskit sabre
    single_trial_swap_count, multi_trial_swap_count = run_sabre(data, edges) 
    
    return int(poly_swap_count), single_trial_swap_count, multi_trial_swap_count 


def main(input_directory, output_directory):
    # Ensure the output directory exists
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    
    # Define paths for the log files in the output directory
    running_log_path = os.path.join(output_directory, "running_log.txt")
    results_log_path = os.path.join(output_directory, "results.txt")
    
    # Open both log files in append mode
    with open(running_log_path, 'a') as running_log, open(results_log_path, 'a') as results_log:
        for filename in os.listdir(input_directory):
            input_file_path = os.path.join(input_directory, filename)
            
            # Log the file being processed
            running_log.write(f"Running {input_file_path}\n")
            running_log.flush()
            
            
            # Process the file and get the results
            poly_swap_count, single_trial_swap_count, multi_trial_swap_count = cython_run_single_file(input_file_path)
            
            # Write the results for this file into the results log
            results_log.write(
                f"{input_file_path}: poly_swap_count={poly_swap_count}, "
                f"single_trial_swap_count={single_trial_swap_count}, "
                f"multi_trial_swap_count={multi_trial_swap_count}\n"
            )
            
            results_log.flush()
    

if __name__ == "__main__":
    file_path = "benchmarks/polyhedral/queko-bss-16qbt/16QBT_100CYC_QSE_0.json"
    print(cython_run_single_file(file_path))
    
    