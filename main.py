# backends
import pstats
import cProfile
from qiskit import QuantumCircuit, transpile
from qiskit.providers.fake_provider import Fake27QPulseV1, Fake5QV1, Fake20QV1
from qiskit_ibm_runtime.fake_provider import FakeGuadalupeV2


# poly_sabre
from src.isl_sabre.poly_circuit_preprocess import *
from src.isl_sabre.poly_circuit_utils import *
from src.isl_sabre.poly_sabre import POLY_SABRE
from src.isl_sabre.dag import DAG
from src.isl_sabre.isl_to_python import *

from qiskit import QuantumCircuit, transpile
from qiskit.transpiler.passes import SabreLayout, SabreSwap
from qiskit.transpiler import PassManager
from qiskit.transpiler import CouplingMap

import time
# qiskit


start_time = time.time()
file_path = r"benchmarks/polyhedral/queko-bss-16qbt/16QBT_200CYC_QSE_0.json"
data = json_file_to_isl(file_path)
print(f"Data loaded in {time.time() - start_time:.2f} seconds")

start_time = time.time()
edges = Fake20QV1().configuration().coupling_map
print(f"Edges loaded in {time.time() - start_time:.2f} seconds")

start_time = time.time()
poly_sabre = POLY_SABRE(edges, data)
print(f"POLY_SABRE initialized in {time.time() - start_time:.2f} seconds")

start_time = time.time()
initial_mapping = poly_sabre.get_initial_mapping()
print(f"Initial mapping obtained in {time.time() - start_time:.2f} seconds")

print("RUNNING ALGORITHMS:\n--\n\n")
min_swaps = poly_sabre.run(initial_mapping, num_iter=1,
                           chunk_size=80, huristic_method="poly-paths")
print(f"Min swaps: {min_swaps} [poly-paths method]")
start_time = time.time()
min_swaps = poly_sabre.run(initial_mapping, num_iter=1,
                           chunk_size=80, huristic_method="multi-layer-decay")
print(f"Min swaps: {min_swaps} [multi-layer-decay method]")

min_swaps = poly_sabre.run(initial_mapping, num_iter=1,
                           chunk_size=80, huristic_method="decay")
print(f"Min swaps: {min_swaps} [decay method]")
# poly_sabre = POLY_SABRE(edges, data)


# # with cProfile.Profile() as pr:
# initial_mapping = poly_sabre.get_initial_mapping()
# swaps = poly_sabre.run(initial_mapping, num_iter=3,
#                        verbose=True, huristic_method="decay")
# print(swaps)


def run_sabre(data):
    circuit = QuantumCircuit.from_qasm_str(data["qasm_code"])
    coupling_map = CouplingMap(edges)

    sabre_layout = SabreLayout(coupling_map, seed=21)
    pm_initial_layout = PassManager(sabre_layout)
    mapped_circuit = pm_initial_layout.run(circuit)

    sabre_swap = SabreSwap(coupling_map, seed=21)
    pm_swap = PassManager(sabre_swap)
    routed_circuit = pm_swap.run(mapped_circuit)

    swap_count = routed_circuit.count_ops().get('swap', 0)
    return swap_count


circuit = QuantumCircuit.from_qasm_str(data["qasm_code"])
transpiled_circuit = transpile(
    circuit, coupling_map=edges, optimization_level=1)
sabre_swap_count = transpiled_circuit.count_ops().get('swap')
print(f"SABRE transpile lvl1: {sabre_swap_count}")

transpiled_circuit = transpile(
    circuit, coupling_map=edges, optimization_level=2)
sabre_swap_count = transpiled_circuit.count_ops().get('swap')
print(f"SABRE transpile lvl2: {sabre_swap_count}")

transpiled_circuit = transpile(
    circuit, coupling_map=edges, optimization_level=3)
sabre_swap_count = transpiled_circuit.count_ops().get('swap')
print(f"SABRE transpile lvl3: {sabre_swap_count}")


print(f"SABRE 7arfi : {run_sabre(data)}")
