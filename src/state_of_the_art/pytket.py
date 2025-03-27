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


    routing_pass = RoutingPass(architecture)
    routing_pass.apply(circuit)
    
    
    swap_count = sum(1 for gate in circuit.get_commands() 
                    if gate.op.type == OpType.SWAP)

    return {
        "swaps": swap_count,
        "depth": circuit.depth()
    }