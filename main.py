from qiskit.providers.fake_provider import Fake27QPulseV1, Fake5QV1, Fake20QV1
from qiskit_ibm_runtime import QiskitRuntimeService

from src.state_of_the_art.sabre import run_sabre, run_sabre2
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
    start = time()
    poly_mapper = POLY_QMAP(
        edges, data)
    print(f"Time to load: {time()-start}")

    start = time()
    closure_swap_count = poly_mapper.run(
        heuristic_method="closure", verbose=1, initial_mapping_method="sabre", num_iter=1)
    print(f"Time to run: {time()-start}")
    sabre_swap_count = run_sabre(data, edges)["swap_count"]

    print(f"File: {file_path}")
    print(f"Closure Swap Count: {closure_swap_count}")
    print(
        f"Saber Swap Count {sabre_swap_count}")
    print("-"*20)


if __name__ == "__main__":
    run_single_file(
        fr"benchmarks/polyhedral/queko-bss-16qbt/16QBT_600CYC_QSE_9.json")
