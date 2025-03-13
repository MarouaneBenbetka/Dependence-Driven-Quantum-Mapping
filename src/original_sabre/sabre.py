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


def run_sabre(data, edges):
    """
    Compare SWAP counts for:
    1) SabreLayout + single-trial SabreSwap
    2) SabreLayout + multi-trial SabreSwap
    3) TrivialLayout + single-trial SabreSwap
    4) TrivialLayout + multi-trial SabreSwap
    """
    # Build 16-qubit circuit from QASM
    circuit = QuantumCircuit.from_qasm_str(data["qasm_code"])

    # Get the number of physical qubits (27-qubit device)
    coupling_map = CouplingMap(edges)
    num_physical_qubits = coupling_map.size()

    # Get the number of qubits in the circuit
    num_circuit_qubits = circuit.num_qubits

    # ---------------------------------------------------------
    # A) SabreLayout
    # ---------------------------------------------------------
    # A1) First apply SabreLayout
    sabre_layout_pass = SabreLayout(coupling_map=coupling_map, seed=21)
    pm_sabre_layout = PassManager([sabre_layout_pass])
    circ_sabre_layout = pm_sabre_layout.run(circuit.copy())
    sabre_initial_layout = pm_sabre_layout.property_set["layout"]

    # Create layout that maps virtual to physical qubits
    sabre_layout = Layout()
    for virtual_bit, physical_bit in sabre_initial_layout.get_virtual_bits().items():
        sabre_layout[virtual_bit] = physical_bit

    # A2) Run SabreSwap directly on the layout-mapped circuit
    # Create a new circuit with enough qubits for the device
    qr = QuantumRegister(num_physical_qubits, 'q')
    mapped_circuit = QuantumCircuit(qr)

    # Apply the layout transform
    for gate, qargs, cargs in circuit.data:
        new_qargs = [qr[sabre_layout[qubit]] for qubit in qargs]
        mapped_circuit.append(gate, new_qargs, cargs)

    # A3) SabreSwap (single trial)
    pm_sabre_swap_single = PassManager([
        SabreSwap(coupling_map=coupling_map,
                  heuristic="decay", seed=21, trials=1)
    ])
    circ_sabre_single = pm_sabre_swap_single.run(mapped_circuit)
    sabre_swap_count_single = circ_sabre_single.count_ops().get("swap", 0)

    # A4) SabreSwap (multi trial)
    pm_sabre_swap_multi = PassManager([
        SabreSwap(coupling_map=coupling_map, heuristic="decay", seed=21)
    ])
    circ_sabre_multi = pm_sabre_swap_multi.run(mapped_circuit)
    sabre_swap_count_multi = circ_sabre_multi.count_ops().get("swap", 0)

    # ---------------------------------------------------------
    # B) TrivialLayout (logical i -> physical i)
    # ---------------------------------------------------------
    # B1) Create trivial layout mapping virtual qubits to first physical qubits
    trivial_layout = Layout()
    for i, qubit in enumerate(circuit.qubits):
        trivial_layout[qubit] = i

    # B2) Create new circuit with enough qubits for the device
    qr = QuantumRegister(num_physical_qubits, 'q')
    trivial_mapped_circuit = QuantumCircuit(qr)

    # Apply the trivial layout transform
    for gate, qargs, cargs in circuit.data:
        new_qargs = [qr[trivial_layout[qubit]] for qubit in qargs]
        trivial_mapped_circuit.append(gate, new_qargs, cargs)

    # B3) Single-trial SabreSwap
    circ_trivial_single = pm_sabre_swap_single.run(trivial_mapped_circuit)
    trivial_swap_count_single = circ_trivial_single.count_ops().get("swap", 0)

    # B4) Multi-trial SabreSwap
    circ_trivial_multi = pm_sabre_swap_multi.run(trivial_mapped_circuit)
    trivial_swap_count_multi = circ_trivial_multi.count_ops().get("swap", 0)

    # ---------------------------------------------------------
    # C) Return all four SWAP counts
    # ---------------------------------------------------------
    return {
        "SabreLayout + SingleTrialSWAP": sabre_swap_count_single,
        "SabreLayout + MultiTrialSWAP": sabre_swap_count_multi,
        "TrivialLayout + SingleTrialSWAP": trivial_swap_count_single,
        "TrivialLayout + MultiTrialSWAP": trivial_swap_count_multi,
    }
