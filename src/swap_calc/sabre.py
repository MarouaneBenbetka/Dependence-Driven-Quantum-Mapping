import json
from qiskit import QuantumCircuit, transpile
from qiskit.transpiler import CouplingMap, Layout,PassManager
from qiskit.transpiler.passes import SabreSwap
from src.tools.graph_tools import generate_2d_grid
import time 




def run_saber(edges, qasm_code):

    circuit = QuantumCircuit.from_qasm_str(qasm_code)
    coupling_map = CouplingMap(edges)
    num_qubits = circuit.num_qubits

    initial_layout_dict = {circuit.qubits[i]: i for i in range(num_qubits)}
    initial_layout = Layout(initial_layout_dict)
 
    pass_manager = PassManager()

    pass_manager.append(SabreSwap(coupling_map,seed=42))

    transpiled_circuit = transpile(
        circuit,
        coupling_map=coupling_map,
        initial_layout=initial_layout,
    )

    optimized_circuit = pass_manager.run(transpiled_circuit)

    swap_count = sum(op.operation.name == 'swap' for op in optimized_circuit.data  )
    
    return swap_count

