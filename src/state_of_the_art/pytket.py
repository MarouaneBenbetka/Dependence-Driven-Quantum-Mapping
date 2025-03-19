from pytket import OpType
from pytket.qasm import circuit_from_qasm_str
from pytket.architecture import Architecture
from pytket.placement import place_with_map
from pytket.passes import RoutingPass
from pytket._tket.unit_id import Node 



def run_pyket(data,edges,initial_mapping=None):
    circuit = circuit_from_qasm_str(data["qasm_code"])
    architecture = Architecture(edges)

    if initial_mapping == "trivial":
        mapping = {q: Node(i) for i, q in enumerate(circuit.qubits)}
        place_with_map(circuit, mapping)

    original_circuit = circuit.copy()

    routing_pass = RoutingPass(architecture)

    pre_decompose_circuit = original_circuit.copy()
    routing_pass.apply(pre_decompose_circuit)
    swap_count = sum(1 for gate in pre_decompose_circuit.get_commands() 
                    if gate.op.type == OpType.SWAP)

    return {
        "swaps": swap_count,
        "depth": pre_decompose_circuit.depth()
    }