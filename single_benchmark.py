import time 
import csv
import os

import islpy as isl

from src.tools.io_tools import *
from src.tools.graph_tools import *
from src.tools.swap_tools import *
from src.tools.backend_generation import *
from src.swap_calc.simulation import *
from src.swap_calc.sabre import *


N, edges = generate_backend_edges(name="fake")
topology = edges_adjancy_list(N, edges)
print("Topology finished")
sc = SwapCalculator(topology)
print("Paths finished")

file_path = "benchmarks/polyhedral/queko-bss-20qbt/20QBT_100CYC_QSE_9.json"
data = json_file_to_isl(file_path)
domain, read_dep, access = filter_multi_qubit_gates(data["domain"], data["read_dependencies"], data["schedule"])

if domain is None:
    pass

num_qubits = get_qubits_needed(read_dep)+1
mapping = isl.Map(f"{{ q[i] -> [i] : 0<=i<={num_qubits} }}")

access = access.apply_range(mapping).coalesce()
access1 = access.lexmin().coalesce()
access2 = access.lexmax().coalesce()


print("Dot Product")
access = access1.range_product(access2).flatten().coalesce()
print(sc.backend_disconnected_edges)
# start = time.time()
# saber_swap_count = run_saber(edges,data['qasm_code'])
# saber_time = time.time()-start

# print(f"Sabber Swap Count {saber_swap_count}")
# print(f"Sabber Time {saber_time}")

start = time.time()
print("Starting Now")
simulation_swap_count = sc.run1(access1,access2,mapping)

simulation_time = time.time()-start
print(f"Simulation Swap Count {simulation_swap_count}")
print(f"Simulation Time {simulation_time}")



start = time.time()
print("Starting Now")
simulation_swap_count = sc.run(access,mapping)

simulation_time = time.time()-start
print(f"Simulation Swap Count {simulation_swap_count}")
print(f"Simulation Time {simulation_time}")
