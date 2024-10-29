import json
from qiskit import QuantumCircuit, transpile
from qiskit.transpiler import CouplingMap, Layout,PassManager
from qiskit.transpiler.passes import SabreSwap
from src.graph_tools import generate_2d_grid
import time 


def read_qasm_code(file_path):
    with open(file_path, 'r') as json_file:
        data = json.load(json_file)
        qasm_code = data.get('qasm_code', '')
    return qasm_code

def create_coupling_map(graph):
    """Create a CouplingMap from the graph structure."""
    edges = [(i, j) for i, neighbors in enumerate(graph) for j in neighbors]
    return CouplingMap(edges)


graph = generate_2d_grid(10, 10)
coupling_map = create_coupling_map(graph)

def sabre_main(json_file_path):
    qasm_code = read_qasm_code(json_file_path)
    
    circuit = QuantumCircuit.from_qasm_str(qasm_code)

    num_qubits = circuit.num_qubits

    #print(circuit)

    # Create the initial layout directly from the circuit's qubits
    initial_layout_dict = {circuit.qubits[i]: i for i in range(num_qubits)}
    initial_layout = Layout(initial_layout_dict)
    start = time.time()
    #print(initial_layout_dict)
    #print(f"Number of qubits in circuit: {num_qubits}")
    #print(f"Initial layout: {initial_layout_dict}")
    pass_manager = PassManager()
    pass_manager.append(SabreSwap(coupling_map))

    # Transpile the circuit using the initial layout
    transpiled_circuit = transpile(
        circuit,
        coupling_map=coupling_map,
        initial_layout=initial_layout,
    )

    # Run the PassManager to apply the SABRE swap pass
    optimized_circuit = pass_manager.run(transpiled_circuit)

    # Count the number of SWAP gates in the optimized circuit
    swap_count = sum(1 for op in optimized_circuit.data if op.operation.name == 'swap')
    
    return time.time()-start, swap_count

# Example usage
if __name__ == "__main__":
    json_file_path = "benchmarks/polyhedral/cases/backward.json"  # Specify the path to your JSON file
    time,swaps = sabre_main(json_file_path)
    print(f"Number of SWAP gates: {swaps}")
