from qiskit.providers.fake_provider import Fake27QPulseV1, Fake5QV1, Fake20QV1
from src.original_sabre.sabre import run_sabre
from src.isl_routing.mapping.routing import POLY_QMAP
from src.isl_routing.utils.isl_data_loader import *
from src.isl_routing.utils.circuit_utils import *
from time import time


def run_single_file(file_path):
    edges = Fake27QPulseV1().configuration().coupling_map

    start = time()
    data = json_file_to_isl(file_path)
    print(f"Time to load data: {time()-start:.6f} seconds")
    start = time()
    poly_mapper = POLY_QMAP(
        edges, data)
    print(f"Time to create poly_sabre object: {time()-start:.6f} seconds")
    poly_swap_count = poly_mapper.run(
        heuristic_method="decay", verbose=1)

    single_trial_swap_count, multi_trial_swap_count = run_sabre(data, edges)
    print(
        f" poly_swap_with_transitive={poly_swap_count} ,single_trial_swap_count={single_trial_swap_count}, multi_trial_swap_count={multi_trial_swap_count}")

    return poly_swap_count, single_trial_swap_count, multi_trial_swap_count


if __name__ == "__main__":
    run_single_file(
        fr"benchmarks/polyhedral/queko-bss-20qbt/20QBT_900CYC_QSE_9.json")
