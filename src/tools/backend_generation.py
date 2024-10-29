from qiskit_ibm_runtime import QiskitRuntimeService






def generate_backend_edges(name="ibm_sherbrooke"):
    service = QiskitRuntimeService()
    backend = service.backend(name)

    return backend.configuration().num_qubits, backend.configuration().coupling_map

def edges_adjancy_list(N,edges):
    
    graph = [[] for _ in range(N)]
    for q1, q2 in edges:
        graph[q1].append(q2)
        graph[q2].append(q1)
    
    return graph


