import cirq
import cirq_google as cg
from cirq.contrib.qasm_import import circuit_from_qasm
import networkx as nx


def from_backend_to_edges():
    sycamore_device = cg.Sycamore
    device_graph = sycamore_device.metadata.nx_graph

    edges = list(device_graph.edges())

    all_qubits = sorted({q for edge in edges for q in edge}, key=lambda q: (q.row, q.col))

    qubit_to_index = {qubit: idx for idx, qubit in enumerate(all_qubits)}

    integer_edges = [[qubit_to_index[q1], qubit_to_index[q2]] for q1, q2 in edges]

    return integer_edges



def run_cirq(qasm_str,edges=None,initial_mapping="abstract"):
    
    circuit = circuit_from_qasm(qasm_str)

    if edges:
        device_graph = edges_to_device(edges)
    else:
        sycamore_device = cg.Sycamore
        device_graph = sycamore_device.metadata.nx_graph

    router = cirq.RouteCQC(device_graph)

    if initial_mapping == "trivial":
        initial_mapper = get_trivial_mapping(circuit,device_graph)
        routed_circuit, _, _ = router.route_circuit(
            circuit,initial_mapper=initial_mapper, tag_inserted_swaps=True
        )
    else:
        routed_circuit, _, _ = router.route_circuit(
            circuit, tag_inserted_swaps=True
        )
    
    swap_count = sum(
    1 for op in routed_circuit.all_operations()
        if isinstance(op, cirq.TaggedOperation) and cirq.RoutingSwapTag() in op.tags
    )

    depth = len(routed_circuit)

    return {
        "swaps": swap_count,
        "depth": depth,
    }
    
    
def get_trivial_mapping(circuit,device_graph):
    class TrivialInitialMapper:
        def __init__(self, mapping):
            self._mapping = mapping

        def initial_mapping(self, circuit):
            return self._mapping

    # Now create your trivial mapping dictionary as before.
    logical_qubits_sorted = sorted(circuit.all_qubits(), key=lambda q: q.name)
    physical_qubits_sorted = sorted(device_graph.nodes(), key=lambda q: (q.row, q.col))
    trivial_mapping = {lq: pq for lq, pq in zip(logical_qubits_sorted, physical_qubits_sorted)}

    # Wrap the mapping in the helper class.
    initial_mapper = TrivialInitialMapper(trivial_mapping)
    
    return initial_mapper
    
    
def edges_to_device(edge_list):

    g = nx.Graph()

    nodes = set()
    for edge in edge_list:
        nodes.update(edge)
    
    qubit_map = {node: cirq.NamedQubit(str(node)) for node in nodes}
    
    for q in qubit_map.values():
        g.add_node(q)
    
    for edge in edge_list:
        q1 = qubit_map[edge[0]]
        q2 = qubit_map[edge[1]]
        g.add_edge(q1, q2)
    
    return g