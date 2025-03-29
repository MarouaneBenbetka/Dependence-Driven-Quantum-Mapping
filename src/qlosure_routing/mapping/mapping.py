
import random
import islpy as isl
import cirq
import cirq_google as cg
import networkx as nx
from cirq.contrib.qasm_import import circuit_from_qasm

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


def generate_cirq_initial_mapping(qasm_code):
    def get_physical_qubit_to_index():
        """
        Constructs a mapping from physical qubits (GridQubits) on the Sycamore device
        to integer indices based on sorted order (by row, then column).
        """
        sycamore_device = cg.Sycamore
        device_graph = sycamore_device.metadata.nx_graph
        edges = list(device_graph.edges())
        all_qubits = sorted({q for edge in edges for q in edge}, key=lambda q: (q.row, q.col))
        qubit_to_index = {qubit: idx for idx, qubit in enumerate(all_qubits)}
        return qubit_to_index
    
    circuit = circuit_from_qasm(qasm_code)

    # Use the Sycamore device connectivity for routing.
    sycamore_device = cg.Sycamore
    device_graph = sycamore_device.metadata.nx_graph
    router = cirq.RouteCQC(device_graph)

    # Route the circuit; this produces an initial mapping from logical qubits to physical qubits.
    routed_circuit, initial_mapping, final_mapping = router.route_circuit(circuit)
    
    
    logical_qubits_sorted = sorted(initial_mapping.keys(), key=lambda q: q.name)
    logical_to_int = {q: i for i, q in enumerate(logical_qubits_sorted)}

    # 2. Get the physical qubit to integer mapping from the device.
    physical_qubit_to_int = get_physical_qubit_to_index()

    # 3. Build the ISL mapping string and Python dictionaries.
    isl_mapping_str = ""
    mapping = {}         # logical (int) -> physical (int)
    reverse_mapping = {} # physical (int) -> logical (int)
    for logical_qubit, physical_qubit in initial_mapping.items():
        logical_index = logical_to_int[logical_qubit]
        physical_index = physical_qubit_to_int[physical_qubit]
        isl_mapping_str += f"q[{logical_index}] -> [{physical_index}];"
        mapping[logical_index] = physical_index
        reverse_mapping[physical_index] = logical_index
        
    isl_mapping_str = "{" + isl_mapping_str + "}"
    isl_mapping = isl.Map(isl_mapping_str)  
    
    return isl_mapping,mapping,reverse_mapping
    
    

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



