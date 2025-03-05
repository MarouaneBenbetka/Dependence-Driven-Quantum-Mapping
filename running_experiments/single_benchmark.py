import sys
import os

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
    
# backends
from qiskit.providers.fake_provider import Fake27QPulseV1,Fake5QV1,Fake20QV1


# poly_sabre
from src.isl_sabre.poly_circuit_preprocess import *
from src.isl_sabre.poly_circuit_utils import *
from src.isl_sabre.poly_sabre import POLY_SABRE


# original sabre
from src.original_sabre.sabre import run_sabre



def run_single_file(file_path):
    edges = Fake27QPulseV1().configuration().coupling_map
    data = json_file_to_isl(file_path)
    

    # poly sabre
    data = json_file_to_isl(file_path)
    poly_sabre = POLY_SABRE(edges,data)
    poly_swap_count = poly_sabre.run(heuristic_method="decay",verbose=1)
    
    
    # qiskit sabre
    single_trial_swap_count, multi_trial_swap_count = run_sabre(data, edges) 
    
    return poly_swap_count, single_trial_swap_count, multi_trial_swap_count 
    
    

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
            poly_swap_count, single_trial_swap_count, multi_trial_swap_count = run_single_file(input_file_path)
            
            # Write the results for this file into the results log
            results_log.write(
                f"{input_file_path}: poly_swap_count={poly_swap_count}, "
                f"single_trial_swap_count={single_trial_swap_count}, "
                f"multi_trial_swap_count={multi_trial_swap_count}\n"
            )
            
            results_log.flush()
    

if __name__ == "__main__":
    benchmark = "queko-bss-16qbt"
    input_directory = "benchmarks/polyhedral/" + benchmark
    output_directory = "experiment_results/" + benchmark
    
    main(input_directory, output_directory)