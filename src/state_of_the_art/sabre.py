# qiskit
from qiskit import QuantumCircuit, transpile, QuantumRegister
from qiskit.transpiler.passes import SabreLayout, SabreSwap
from qiskit.transpiler import PassManager, CouplingMap
from qiskit.converters import circuit_to_dag
from qiskit.transpiler.layout import Layout
from qiskit.transpiler.passes import SetLayout, ApplyLayout, SabreSwap
from qiskit.transpiler.passes import (
    SabreLayout,
    SabreSwap,
    SetLayout,
    ApplyLayout,
    FullAncillaAllocation,
    EnlargeWithAncilla,
    TrivialLayout
)


def get_layout(coupling_map, circuit):
    sabre_layout = SabreLayout(coupling_map, seed=21)
    layout_pass_manager = PassManager(sabre_layout)
    layout_applied_circuit = layout_pass_manager.run(circuit)
    return sabre_layout.property_set["layout"]


def run_sabre(data, edges, layout="sabre", trial="single"):
    """
    Run SabreSwap mapping with the specified layout and trial options,
    and return the SWAP count and circuit depth.

    Args:
        data (dict): Dictionary containing the QASM code under the key "qasm_code".
        edges (list): List of edges defining the coupling map of the device.
        layout (str): The layout to use. Options are "trivial" and "sabre". Default is "trivial".
        trial (str): The trial mode for SabreSwap. Options are "single" and "multi". Default is "single".

    Returns:
        dict: A dictionary with keys "swap_count" and "circuit_depth".
    """

    # Build circuit from QASM code
    circuit = QuantumCircuit.from_qasm_str(data["qasm_code"])

    # Get the coupling map and number of physical qubits
    coupling_map = CouplingMap(edges)
    num_physical_qubits = coupling_map.size()

    # Create a QuantumRegister for the device and an empty circuit
    qr = QuantumRegister(num_physical_qubits, 'q')
    mapped_circuit = QuantumCircuit(qr)

    # Apply the chosen layout
    if layout.lower() == "sabre":
        # Use SabreLayout pass to compute an initial layout
        sabre_layout_pass = SabreLayout(coupling_map=coupling_map, seed=21)
        pm_sabre_layout = PassManager([sabre_layout_pass])
        _ = pm_sabre_layout.run(circuit.copy())
        sabre_initial_layout = pm_sabre_layout.property_set["layout"]

        # Build a mapping from virtual to physical qubits
        computed_layout = Layout()
        for virtual_qubit, physical_qubit in sabre_initial_layout.get_virtual_bits().items():
            computed_layout[virtual_qubit] = physical_qubit

    else:  # default is trivial layout
        computed_layout = Layout()
        for i, qubit in enumerate(circuit.qubits):
            computed_layout[qubit] = i

    # Apply the layout transform to map the circuit to the device qubits
    for gate, qargs, cargs in circuit.data:
        new_qargs = [qr[computed_layout[qubit]] for qubit in qargs]
        mapped_circuit.append(gate, new_qargs, cargs)

    # Set up SabreSwap pass based on the trial option
    if trial.lower() == "single":
        sabre_swap_pass = SabreSwap(
            coupling_map=coupling_map, heuristic="decay", seed=21, trials=1)
    else:  # multi trial
        sabre_swap_pass = SabreSwap(
            coupling_map=coupling_map, heuristic="decay", seed=21)

    pm_sabre_swap = PassManager([sabre_swap_pass])

    # Run the SabreSwap pass
    swapped_circuit = pm_sabre_swap.run(mapped_circuit)

    # Count the number of SWAP operations and determine the circuit depth
    swap_count = swapped_circuit.count_ops().get("swap", 0)
    circuit_depth = swapped_circuit.depth()

    return {"swap_count": swap_count, "circuit_depth": circuit_depth}


def run_sabre2(data, edges):
    circuit = QuantumCircuit.from_qasm_str(data["qasm_code"])
    # Create coupling map
    coupling_map = CouplingMap(edges)

    layout = get_layout(coupling_map, circuit)
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
    return swap_count, multi_swap_count
