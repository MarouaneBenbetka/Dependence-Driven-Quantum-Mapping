from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit.providers.fake_provider import Fake27QPulseV1





def generate_backend_edges(name="ibm_sherbrooke",num_qubits=5):
    if name == "fake":
        backend_config = Fake27QPulseV1().configuration()
    else:
        service = QiskitRuntimeService()
        backend = service.backend(name)
        backend_config = backend.configuration()

    return backend_config.num_qubits, backend_config.coupling_map

def edges_adjancy_list(N,edges):
    
    graph = [[] for _ in range(N)]
    for q1, q2 in edges:
        graph[q1].append(q2)
        graph[q2].append(q1)
    
    return graph


