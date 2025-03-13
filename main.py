from qiskit.providers.fake_provider import Fake27QPulseV1, Fake5QV1, Fake20QV1
from qiskit_ibm_runtime import QiskitRuntimeService

from src.original_sabre.sabre import run_sabre
from src.isl_routing.mapping.routing import POLY_QMAP
from src.isl_routing.utils.isl_data_loader import *
from src.isl_routing.utils.circuit_utils import *

from src.isl_routing.backend.load_backend import load_backend_edges
from time import time
better_sabre = 0
better_decay = 0
tries = 0


def run_single_file(file_path):
    edges = load_backend_edges("ibm_sherbrooke")

    data = json_file_to_isl(file_path)
    poly_mapper = POLY_QMAP(
        edges, data)
    poly_swap_count = poly_mapper.run(
        heuristic_method="decay", verbose=0, initial_mapping_method="sabre")

    closure_swap_count = poly_mapper.run(
        heuristic_method="closure", verbose=0, initial_mapping_method="sabre")
    sabre_swap_count = run_sabre(data, edges)['SabreLayout + SingleTrialSWAP']
    print(f"File: {file_path}")
    print(f"Poly Swap Count: {poly_swap_count}")
    print(f"Closure Swap Count: {closure_swap_count}")
    print(
        f"Saber Swap Count {sabre_swap_count}")
    print("-"*20)


if __name__ == "__main__":
    for cycle in range(1, 5):
        for i in range(10):
            run_single_file(
                fr"benchmarks/polyhedral/queko-bss-20qbt/20QBT_{cycle}00CYC_QSE_{i}.json")
