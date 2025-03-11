from qiskit.providers.fake_provider import Fake27QPulseV1, Fake5QV1, Fake20QV1
from src.original_sabre.sabre import run_sabre
from src.isl_sabre.poly_sabre import POLY_SABRE
from src.isl_sabre.poly_circuit_utils import *
from src.isl_sabre.poly_circuit_preprocess import *
import sys
import os
from time import time

# backends


# poly_sabre


# original sabre


def run_single_file(file_path):
    edges = Fake27QPulseV1().configuration().coupling_map

    start = time()
    data = json_file_to_isl(file_path)
    print(f"Time to load data: {time()-start:.6f} seconds")
    start = time()
    poly_sabre = POLY_SABRE(
        edges, data)
    print(f"Time to create poly_sabre object: {time()-start:.6f} seconds")
    poly_swap_count = poly_sabre.run(
        heuristic_method="decay", verbose=1, with_transitive_closure=True)

    single_trial_swap_count, multi_trial_swap_count = run_sabre(data, edges)
    print(
        f" poly_swap_with_transitive={poly_swap_count} ,single_trial_swap_count={single_trial_swap_count}, multi_trial_swap_count={multi_trial_swap_count}")

    return poly_swap_count, single_trial_swap_count, multi_trial_swap_count


if __name__ == "__main__":
    run_single_file(
        fr"benchmarks/polyhedral/queko-bss-16qbt/16QBT_200CYC_QSE_4.json")
