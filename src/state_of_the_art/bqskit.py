import tempfile
from bqskit import Circuit, compile, MachineModel
from bqskit.ir.gates import SwapGate,CNOTGate, CNOTGate, U3Gate, SwapGate
from bqskit.compiler import GateSet


def run_bqskit(data, edges, num_qubits,op_level=1):
    qasm_str = data["qasm_code"]
    with tempfile.NamedTemporaryFile(mode='w', suffix='.qasm', delete=True) as tmp:
        tmp.write(qasm_str)
        tmp.flush()  
        circuit = Circuit.from_file(tmp.name)

    edges = [tuple(edge) for edge in edges]  
    gate_set = GateSet([CNOTGate(), U3Gate(), SwapGate()])
    machine = MachineModel(num_qubits, coupling_graph=edges, gate_set=gate_set)
    
    compiled_circuit = compile(
        circuit,
        machine,
        seed=42,
        optimization_level=op_level,
    )
    
    circuit_depth = compiled_circuit.depth
    cx_count = sum(1 for op in compiled_circuit if op.gate.name == "CNOTGate")
    swap_count = sum(1 for op in compiled_circuit if op.gate.name == "SwapGate")
    
    return {
        "swap_count": swap_count,
        "depth": circuit_depth,
        "cx_count": cx_count,
    }


