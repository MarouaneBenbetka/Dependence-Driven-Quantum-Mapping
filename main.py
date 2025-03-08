from qiskit.providers.fake_provider import Fake27QPulseV1, Fake5QV1, Fake20QV1
from src.original_sabre.sabre import run_sabre
from src.isl_sabre.poly_sabre import POLY_SABRE
from src.isl_sabre.poly_circuit_utils import *
from src.isl_sabre.poly_circuit_preprocess import *
import sys
import os

# backends


# poly_sabre


# original sabre


def run_single_file(file_path):
    edges = Fake27QPulseV1().configuration().coupling_map
    data = json_file_to_isl(file_path)

    # poly sabre
    data = json_file_to_isl(file_path)
    poly_sabre = POLY_SABRE(edges, data)
    poly_swap_count = poly_sabre.run(heuristic_method="decay", verbose=1)

    # qiskit sabre
    single_trial_swap_count, multi_trial_swap_count = run_sabre(data, edges)
    print(
        f"poly_swap_count={poly_swap_count}, single_trial_swap_count={single_trial_swap_count}, multi_trial_swap_count={multi_trial_swap_count}")

    for name, elapsed in poly_sabre.instruction_times.items():
        print(f"{name}: {elapsed:.6f} seconds")
    return poly_swap_count, single_trial_swap_count, multi_trial_swap_count


if __name__ == "__main__":
    run_single_file(
        r"benchmarks/polyhedral/queko-bss-16qbt/16QBT_500CYC_QSE_1.json")
