# qiskit
from qiskit import QuantumCircuit, transpile
from qiskit.transpiler.passes import SabreLayout, SabreSwap
from qiskit.transpiler import PassManager,CouplingMap
from qiskit.converters import circuit_to_dag
from qiskit.transpiler.layout import Layout
from qiskit.transpiler.passes import SetLayout, ApplyLayout, SabreSwap


def get_layout(coupling_map,circuit):
    sabre_layout = SabreLayout(coupling_map, seed=21)
    layout_pass_manager = PassManager(sabre_layout)
    layout_applied_circuit = layout_pass_manager.run(circuit)
    return sabre_layout.property_set["layout"]
    

    
def run_sabre(data,edges):
    circuit = QuantumCircuit.from_qasm_str(data["qasm_code"])    
    # Create coupling map
    coupling_map = CouplingMap(edges)
    
    layout = get_layout(coupling_map,circuit)
    # Step 1: Apply the given layout to the circuit
    layout_pass = PassManager([
        SetLayout(layout),      # Set the predetermined layout
        ApplyLayout()           # Apply the layout to modify qubit indices
    ])
    mapped_circuit = layout_pass.run(circuit)

    # Step 2: Run SabreSwap for routing
    sabre_swap = SabreSwap(
        coupling_map,
        seed=21,
        heuristic="decay",
        trials=1
    )
    
    swap_pass = PassManager(sabre_swap)
    optimized_circuit = swap_pass.run(mapped_circuit)

    # Count the number of swap gates
    swap_count = optimized_circuit.count_ops().get("swap", 0)
    
    multi_sabre_swap = SabreSwap(
        coupling_map,
        seed=21,
        heuristic="decay",
    )
    
    multi_swap_pass = PassManager(multi_sabre_swap)
    multi_optimized_circuit = multi_swap_pass.run(mapped_circuit)

    # Count the number of swap gates
    multi_swap_count = multi_optimized_circuit.count_ops().get("swap", 0)
    return swap_count,multi_swap_count
