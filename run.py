import argparse
from src.qlosure.utils.isl_data_loader import json_file_to_isl
from src.qlosure.mapping.routing import Qlosure
from hardware.src.load_backend import load_backend_edges

# Assuming competitor methods are defined and imported
from src.state_of_the_art.pytket import run_pytket
from src.state_of_the_art.sabre import run_sabre
from src.state_of_the_art.qmap import run_qmap
from src.state_of_the_art.cirq import run_cirq

# Argument parser setup
parser = argparse.ArgumentParser(description="Run Qlosure with optional parameters")
parser.add_argument("--circuit", type=str, default="benchmarks/polyhedral/queko-bss-54qbt/54QBT_100CYC_QSE_0.json", help="Path to circuit JSON file")
parser.add_argument("--backend", type=str, default="ibm_sherbrooke", help="Name of the backend")
parser.add_argument("--initial", type=str, default="trivial", help="Initial mapping method")
parser.add_argument("--verbose", type=int, default=1, help="Verbosity level")
parser.add_argument("--competitors", action="store_true", help="Run and compare with competitor mappers")

args = parser.parse_args()

# Load circuit data
print(f"Loading circuit from: {args.circuit}")
data = json_file_to_isl(args.circuit)
print("✅ Circuit loaded successfully.")

# Load backend edges
print(f"Loading backend: {args.backend}")
edges = load_backend_edges(args.backend)
print("✅ Backend topology loaded.")

# Run Qlosure
poly_mapper = Qlosure(edges, data)
qlosure_results = poly_mapper.run(initial_mapping_method=args.initial, verbose=args.verbose)

# Store results
results = {
    "qlosure": {"swaps": qlosure_results[0], "depth": qlosure_results[1]},
}

# Run competitors if requested
if args.competitors:
    print("Running Cirq...")
    cirq_results = run_cirq(data, edges, initial_mapping=args.initial)
    print("Running SABRE...")
    sabre_results = run_sabre(data, edges, layout=args.initial)
    print("Running QMAP...")
    qmap_results = run_qmap(data, edges, initial_mapping=args.initial)
    print("Running Pytket...")
    pytket_results = run_pytket(data, edges, initial_mapping=args.initial)
    

    results["sabre"] = {"swaps": sabre_results["swaps"], "depth": sabre_results["depth"]}
    results["qmap"] = {"swaps": qmap_results["swaps"], "depth": qmap_results["depth"]}
    results["tket"] = {"swaps": pytket_results["swaps"], "depth": pytket_results["depth"]}
    results["cirq"] = {"swaps": cirq_results["swaps"], "depth": cirq_results["depth"]}

# Print results in table format
print("\n📊 Mapping Results")
print("+-----------+--------+--------+")
print("| Method    | Swaps  | Depth  |")
print("+-----------+--------+--------+")
for method, res in results.items():
    print(f"| {method:<9} | {res['swaps']:<6} | {res['depth']:<6} |")
print("+-----------+--------+--------+")
