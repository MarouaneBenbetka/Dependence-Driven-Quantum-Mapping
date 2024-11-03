import time
import csv
import os
import json
import islpy as isl
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from src.tools.io_tools import *
from src.tools.graph_tools import *
from src.tools.swap_tools import *
from src.tools.backend_generation import *
from src.swap_calc.simulation import *
from src.swap_calc.sabre import *

ROOT_FOLDER_PATH = "benchmarks/polyhedral/ibmqx_big"
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = f"out/benchmark_results_{TIMESTAMP}.csv"
ERROR_LOG_FILE = f"out/error_log_{TIMESTAMP}.csv"

def process_file(sc, edges, benchmark_name, file_path):
    try:
        data = json_file_to_isl(file_path)
        domain, read_dep, access = filter_multi_qubit_gates(data["domain"], data["read_dependencies"], data["schedule"])

        if domain is None:
            return None, None, None

        num_qubits = get_qubits_needed(read_dep) + 1
        mapping = isl.Map(f"{{ q[i] -> [i] : 0<=i<={num_qubits} }}")

        access = access.apply_range(mapping).coalesce()
        access1 = access.lexmin().coalesce()
        access2 = access.lexmax().coalesce()

        # SABRE execution
        start = time.time()
        saber_swap_count = run_saber(edges, data['qasm_code'])
        saber_time = time.time() - start

        # Simulation execution
        start = time.time()
        simulation_swap_count = sc.run(access1, access2, mapping)
        simulation_time = time.time() - start

        return (benchmark_name, os.path.basename(file_path), simulation_time, simulation_swap_count, saber_time, saber_swap_count), None

    except Exception as e:
        return None, (benchmark_name, os.path.basename(file_path), str(e))


def main():
    N, edges = generate_backend_edges()
    topology = edges_adjancy_list(N, edges)
    sc = SwapCalculator(topology)

    with open(LOG_FILE, mode='a+', newline='') as log_file, open(ERROR_LOG_FILE, mode='a+', newline='') as error_log_file:
        writer = csv.writer(log_file)
        error_writer = csv.writer(error_log_file)
        writer.writerow(["Benchmark", "File", "Execution Time", "Swap Count", "SABRE Execution Time", "SABRE Swap Count"])
        error_writer.writerow(["Benchmark", "File", "Error"])

        futures = []
        with ProcessPoolExecutor(max_workers=8) as executor:
            for root, _, files in os.walk(ROOT_FOLDER_PATH):
                benchmark_name = os.path.basename(root)
                for filename in files:
                    if filename.endswith(".json"):
                        file_path = os.path.join(root, filename)
                        print(f"Scheduling processing for {file_path} in benchmark {benchmark_name}...")
                        futures.append(executor.submit(process_file, sc, edges, benchmark_name, file_path))

            for future in as_completed(futures):
                result, error = future.result()
                if result:
                    writer.writerow(result)
                    log_file.flush()
                elif error:
                    error_writer.writerow(error)
                    error_log_file.flush()
                else:
                    print("Skipped a file due to filtering out domain data.")

if __name__ == "__main__":
    main()
