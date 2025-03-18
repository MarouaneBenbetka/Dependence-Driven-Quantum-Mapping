

from qiskit.providers.fake_provider import Fake27QPulseV1, Fake5QV1, Fake20QV1
from qiskit_ibm_runtime.fake_provider import FakeSherbrooke
#from state_of_the_art.sabre import run_sabre
#from state_of_the_art.cirq import run_cirq,from_backend_to_edges
from state_of_the_art.pytket import run_pyket
from state_of_the_art.qmap import run_qmap
#from isl_routing.mapping.routing import POLY_QMAP
from isl_routing.utils.isl_data_loader import *
#from isl_routing.utils.circuit_utils import *
#from visiualisation.plots import *
from time import time
from tqdm import tqdm


import csv

edges = FakeSherbrooke().configuration().coupling_map

def run_single_file(file_path,depth):

    data = load_qasm(file_path)
    
    qmap_trivial = run_pyket(data, edges,initial_mapping="trivial")
    qmap_default = run_pyket(data, edges)
    
    swaps_trivial = qmap_trivial["swaps"]
    depth_trivial = qmap_trivial["depth"]
    
    swaps_default = qmap_default["swaps"]
    depth_default = qmap_default["depth"]
    
    return file_path,depth,swaps_trivial,depth_trivial,swaps_default,depth_default
    
qpt = 53
csv_file = f"experiment_results/queko-bss-{qpt}qbt/pyket.csv"
os.makedirs(os.path.dirname(csv_file), exist_ok=True)

with open(csv_file, "a", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["file_path", "depth", "swaps_trivial","depth_trivial", "swaps_default","depth_default"])
    
    for i in range(500,1000,100):
        for j in tqdm(range(10), desc=f"Processing QSE {i}CYC"):
            try:
                file_path = f"benchmarks/polyhedral/queko-bss-{qpt}qbt/{qpt}QBT_{i}CYC_QSE_{j}.json"
                result = run_single_file(file_path,i)
                writer.writerow(result)
                f.flush()
            except:
                pass
            
qpt = 54
csv_file = f"experiment_results/queko-bss-{qpt}qbt/pyket.csv"
os.makedirs(os.path.dirname(csv_file), exist_ok=True)

with open(csv_file, "a", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["file_path", "depth", "swaps_trivial","depth_trivial", "swaps_default","depth_default"])
    
    for i in range(100,1000,100):
        for j in tqdm(range(10), desc=f"Processing QSE {i}CYC"):
            try:
                file_path = f"benchmarks/polyhedral/queko-bss-{qpt}qbt/{qpt}QBT_{i}CYC_QSE_{j}.json"
                result = run_single_file(file_path,i)
                writer.writerow(result)
                f.flush()
            except:
                pass
  
def run_single_file2(file_path,depth):

    data = load_qasm(file_path)
    
    qmap_trivial = run_qmap(data, edges,initial_mapping="trivial")
    qmap_default = run_qmap(data, edges)
    
    swaps_trivial = qmap_trivial["swaps"]
    depth_trivial = qmap_trivial["depth"]
    
    swaps_default = qmap_default["swaps"]
    depth_default = qmap_default["depth"]
    
    return file_path,depth,swaps_trivial,depth_trivial,swaps_default,depth_default
              
qpt = 54
csv_file = f"experiment_results/queko-bss-{qpt}qbt/qmap.csv"
os.makedirs(os.path.dirname(csv_file), exist_ok=True)

with open(csv_file, "a", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["file_path", "depth", "swaps_trivial","depth_trivial", "swaps_default","depth_default"])
    
    for i in range(900,1000,100):
        for j in tqdm(range(10), desc=f"Processing QSE {i}CYC"):
            try:
                file_path = f"benchmarks/polyhedral/queko-bss-{qpt}qbt/{qpt}QBT_{i}CYC_QSE_{j}.json"
                result = run_single_file(file_path,i)
                writer.writerow(result)
                f.flush()
            except:
                pass