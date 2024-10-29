import time 
import csv
import os

import islpy as isl

from src.tools.io_tools import *
from src.tools.graph_tools import *
from src.tools.swap_tools import *
from src.tools.backend_generation import *
from src.swap_calc.simulation import *
from src.swap_calc.sabre import *


ROOT_FOLDER_PATH = "benchmarks/polyhedral"
LOG_FILE = "benchmark_results.csv"
ERROR_LOG_FILE = 'error_log.csv'

def main():

    N, edges = generate_backend_edges()
    topology = edges_adjancy_list(N, edges)

    sc = SwapCalculator(topology)

    with open(LOG_FILE, mode='w', newline='') as log_file, open(ERROR_LOG_FILE, mode='w', newline='') as error_log_file:
        writer = csv.writer(log_file)
        error_writer = csv.writer(error_log_file)
        writer.writerow(["Benchmark", "File", "Execution Time", "Swap Count", "SABRE Execution Time", "SABRE Swap Count"])
        error_writer.writerow(["Benchmark", "File", "Error"])

        for root, _, files in os.walk(ROOT_FOLDER_PATH):
            benchmark_name = os.path.basename(root)
            
            for filename in files:
                if filename.endswith(".json"):
                    file_path = os.path.join(root, filename)
                    print(f"Processing {file_path} in benchmark {benchmark_name}...")
                    try:
                        data = json_file_to_isl(file_path)
                        domain, read_dep, access = filter_multi_qubit_gates(data["domain"], data["read_dependencies"], data["schedule"])
                        
                        if domain is None:
                            continue

                        num_qubits = get_qubits_needed(read_dep)+1
                        mapping = isl.Map(f"{{ q[i] -> [i] : 0<=i<={num_qubits} }}")
                        
                        access = access.apply_range(mapping).coalesce()
                        access1 = access.lexmin().coalesce()
                        access2 = access.lexmax().coalesce()

                        start = time.time()
                        saber_swap_count = run_saber(edges,data['qasm_code'])
                        saber_time = time.time()-start
                        
                        print(f"Sabber Swap Count {saber_swap_count}")


                        start = time.time()
                        simulation_swap_count = sc.run(access1, access2, mapping)
                        simulation_time = time.time()-start
                        print(f"Simulation Swap Count {simulation_swap_count}")

                    
                        writer.writerow([benchmark_name, filename, simulation_time, simulation_swap_count ,saber_time, saber_swap_count])
                        log_file.flush() 

                    except Exception as e:
                        error_writer.writerow([benchmark_name, filename, str(e)])
                        error_log_file.flush()
                        print(f"Error processing {file_path}: {e}")


                    






if __name__ == "__main__":
    main()

