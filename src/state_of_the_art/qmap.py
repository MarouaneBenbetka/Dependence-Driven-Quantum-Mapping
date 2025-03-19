from qiskit import QuantumCircuit
from mqt import qmap

def run_qmap(data,edges,initial_mapping=None):
    qc = QuantumCircuit.from_qasm_str(data["qasm_code"])
    edges_arch = set(tuple(edge) for edge in edges)
    arch = qmap.Architecture(127, edges_arch)
    
    

    # Map the circuit using QMAP (choose method: "exact" for optimal mapping or "heuristic" for faster results)
    
    if initial_mapping == "trivial": 
        qc_mapped, res = qmap.compile(qc, arch, method="heuristic",initial_layout=qmap.InitialLayout.identity, post_mapping_optimizations=False)
    else:
        qc_mapped, res = qmap.compile(qc, arch, method="heuristic", post_mapping_optimizations=False)


    return {
        "swaps":res.output.swaps,
        "depth":qc_mapped.depth()
    }