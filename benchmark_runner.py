import os
import csv
import argparse
import datetime
from time import time

from qiskit.providers.fake_provider import Fake27QPulseV1, Fake5QV1, Fake20QV1
from qiskit_ibm_runtime import QiskitRuntimeService

from state_of_the_art.sabre import run_sabre
from src.isl_routing.mapping.routing import POLY_QMAP
from src.isl_routing.utils.isl_data_loader import json_file_to_isl
from src.isl_routing.utils.circuit_utils import *
from src.isl_routing.backend.load_backend import load_backend_edges


def run_single_file(file_path, initial_mapping_method="sabre"):
    edges = load_backend_edges("ibm_sherbrooke")
    data = json_file_to_isl(file_path)

    poly_mapper = POLY_QMAP(edges, data)
    poly_swap_count = poly_mapper.run(
        heuristic_method="decay", verbose=0, initial_mapping_method=initial_mapping_method)

    closure_swap_count = poly_mapper.run(
        heuristic_method="closure", verbose=0, initial_mapping_method=initial_mapping_method)

    more_excuted_swap_count = poly_mapper.run(
        heuristic_method="more_excuted", verbose=0, initial_mapping_method=initial_mapping_method)

    sabre_swap_count = 0
    sabre_results = run_sabre(data, edges)

    if initial_mapping_method == "sabre":
        sabre_swap_count = sabre_results['SabreLayout + SingleTrialSWAP']
    else:
        sabre_swap_count = sabre_results['TrivialLayout + SingleTrialSWAP']

    print(f"File: {file_path}")

    return file_path, poly_swap_count, more_excuted_swap_count, closure_swap_count, sabre_swap_count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run benchmark on Qiskit circuits using mapping and heuristics."
    )
    parser.add_argument("--benchmark", type=str, required=True,
                        help="Benchmark name (folder name) under benchmarks/polyhedral, e.g. 'queko-bss-20qbt'.")
    parser.add_argument("--initial_mapping", type=str, default="sabre",
                        choices=["trivial", "sabre"], help="Initial mapping method to use, either 'trivial' or 'sabre' (default: sabre).")
    args = parser.parse_args()
    initial_mapping_method = args.initial_mapping

    benchmark_name = args.benchmark
    benchmark_dir = os.path.join("benchmarks", "polyhedral", benchmark_name)
    if not os.path.isdir(benchmark_dir):
        raise FileNotFoundError(
            f"Benchmark folder '{benchmark_dir}' does not exist.")

    date_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file = f"experiment_results/results_{benchmark_name}_{initial_mapping_method}_{date_id}.csv"

    with open(csv_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["file_path", "decay", "more_executed",
                        "closure", "sabre_swap_count"])

        # Walk recursively through the benchmark directory.
        for root, dirs, files in os.walk(benchmark_dir):
            for file in files:
                if file.endswith(".json"):
                    file_path = os.path.join(root, file)
                    result = run_single_file(file_path, initial_mapping_method)
                    writer.writerow(result)
                    # Flush after each run so the result is saved immediately.
                    f.flush()
