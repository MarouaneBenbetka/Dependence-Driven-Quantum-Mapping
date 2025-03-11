
import random
import islpy as isl

from qiskit import QuantumCircuit
from qiskit.transpiler import CouplingMap
from qiskit.transpiler.passes import SabreLayout
from qiskit.converters import circuit_to_dag


def generate_random_initial_mapping(num_qubits: int):
    """
    Generate a random mapping from logical qubits to physical qubits.
    """
    logical_qubits = list(range(num_qubits))
    physical_qubits = list(range(num_qubits))
    random.shuffle(physical_qubits)
    isl_mapping_str = ""
    mapping = {}
    reverse_mapping = {}
    for logical_qubit, physical_qubit in zip(logical_qubits, physical_qubits):
        isl_mapping_str += f"q[{logical_qubit}] -> [{physical_qubit}];"
        mapping[logical_qubit] = physical_qubit
        reverse_mapping[physical_qubit] = logical_qubit
    isl_mapping = isl.Map("{"+isl_mapping_str+"}")

    return isl_mapping, mapping, reverse_mapping


def generate_trivial_initial_mapping(num_qubits: int):
    """
    Generate a trivial mapping from logical qubits to physical qubits.
    """
    logical_qubits = list(range(num_qubits))
    physical_qubits = list(range(num_qubits))
    isl_mapping_str = ""
    mapping = {}
    reverse_mapping = {}
    for logical_qubit, physical_qubit in zip(logical_qubits, physical_qubits):
        isl_mapping_str += f"q[{logical_qubit}] -> [{physical_qubit}];"
        mapping[logical_qubit] = physical_qubit
        reverse_mapping[physical_qubit] = logical_qubit
    isl_mapping = isl.Map("{"+isl_mapping_str+"}")

    return isl_mapping, mapping, reverse_mapping

def generate_sabre_initial_mapping(qasm_code, backned_edges):
    circuit = QuantumCircuit.from_qasm_str(qasm_code)
    dag_circuit = circuit_to_dag(circuit)
    coupling_map = CouplingMap(backned_edges)
    sabre_layout = SabreLayout(coupling_map, seed=21)
    sabre_layout.run(dag_circuit)

    layout = sabre_layout.property_set["layout"]

    mapping = {}
    reverse_mapping = {}
    map_str = ""
    for v in layout._v2p:
        if v._register._name != "ancilla":
            map_str += f"q[{v._index}] -> [{layout._v2p[v]}];"
            mapping[v._index] = layout._v2p[v]
            reverse_mapping[layout._v2p[v]] = v._index

    return isl.Map("{"+map_str+"}"), mapping, reverse_mapping


def swap_logical_physical_mappings(logical_to_physical, physical_to_logical, swap_pair, inplace=False):

    updated_mapping = logical_to_physical if inplace else logical_to_physical.copy()
    physical_1, physical_2 = swap_pair

    logical_1 = physical_to_logical.get(physical_1, None)
    logical_2 = physical_to_logical.get(physical_2, None)

    if logical_1 is not None:
        updated_mapping[logical_1] = physical_2

    if logical_2 is not None:
        updated_mapping[logical_2] = physical_1

    if inplace:
        physical_to_logical[physical_1] = logical_2
        physical_to_logical[physical_2] = logical_1

    return updated_mapping


def swap_logical_physical_isl_mapping(isl_mapping, swap_pair):
    q1, q2 = swap_pair

    swap_domain = isl.Set(f"{{[{q1}];[{q2}]}}")
    swap_map = isl.Map(f"{{[{q1}] -> [{q2}]; [{q2}] -> [{q1}]}}")

    other_mapping = isl_mapping.subtract_range(swap_domain)
    return isl_mapping.apply_range(swap_map).union(other_mapping)


def swap_logical_physical_isl_mapping_path(isl_mapping, swap_path_map):
    if swap_path_map.is_empty():
        return isl_mapping
    other_mapping = isl_mapping.subtract_range(swap_path_map.domain())
    return isl_mapping.apply_range(swap_path_map).union(other_mapping)
