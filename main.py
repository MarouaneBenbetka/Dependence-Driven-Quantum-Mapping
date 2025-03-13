from qiskit.providers.fake_provider import Fake27QPulseV1, Fake5QV1, Fake20QV1
from qiskit_ibm_runtime import QiskitRuntimeService

from src.original_sabre.sabre import run_sabre
from src.isl_routing.mapping.routing import POLY_QMAP
from src.isl_routing.utils.isl_data_loader import *
from src.isl_routing.utils.circuit_utils import *

from src.isl_routing.backend.load_backend import load_backend_edges
from time import time


def run_single_file(file_path):
    edges = load_backend_edges("ibm_sherbrooke")

    start = time()
    data = json_file_to_isl(file_path)
    print(f"Time to load data: {time()-start:.6f} seconds")
    start = time()
    poly_mapper = POLY_QMAP(
        edges, data)
    print(f"Time to create poly_sabre object: {time()-start:.6f} seconds")
    poly_swap_count = poly_mapper.run(
        heuristic_method="decay", verbose=1)

    print(f"Poly Swap Count: {poly_swap_count}")
    print(run_sabre(data, edges))


if __name__ == "__main__":
    run_single_file(
        fr"benchmarks/polyhedral/queko-bss-16qbt/16QBT_700CYC_QSE_9.json")
