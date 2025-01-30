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

import time
# qiskit


file_path = r"benchmarks/polyhedral/queko-bss-16qbt/16QBT_900CYC_QSE_9.json"
data = json_file_to_isl(file_path)

_, read_dep, access = filter_multi_qubit_gates(
    data["domain"], data["read_dependencies"], data["schedule"])

print("Starting now")

start = time.time()
_map = isl_map_to_dict_optimized2(access)
print(time.time() - start)

start2 = time.time()

dag = DAG(num_qubits=access.range().dim_max_val(
    0).to_python() + 1, nodes_dict=_map)
print(time.time() - start2)

start3 = time.time()
xx = dict_to_isl_map(dag.successors)

print(time.time() - start3)

print("Total ", time.time() - start)


# edges = FakeGuadalupeV2().configuration().coupling_map


# poly_sabre = POLY_SABRE(edges, data)


# # with cProfile.Profile() as pr:
# initial_mapping = poly_sabre.get_initial_mapping()
# swaps = poly_sabre.run(initial_mapping, num_iter=3,
#                        verbose=True, huristic_method="decay")
# print(swaps)


# circuit = QuantumCircuit.from_qasm_str(data["qasm_code"])
# transpiled_circuit = transpile(
#     circuit, coupling_map=edges, optimization_level=1)
# sabre_swap_count = transpiled_circuit.count_ops().get('swap')
# print(sabre_swap_count)
