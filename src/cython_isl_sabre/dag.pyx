# dag.pyx
# cython: language_level=3, boundscheck=False, wraparound=False

from collections import defaultdict

cdef class DAG:
    cdef public int num_qubits
    cdef dict nodes_dict
    cdef dict write
    cdef list nodes_order
    cdef public object predecessors      # Changed from dict to object to allow defaultdict
    cdef public object successors        # Changed from dict to object
    cdef public list first_layer

    def __init__(self, int num_qubits,
                 dict nodes_dict,
                 dict write,
                 bint no_read_dep=False):

        self.num_qubits = num_qubits
        self.nodes_dict = nodes_dict
        self.write = write
        self.nodes_order = sorted(nodes_dict.keys())

        # Use defaultdict for predecessors and successors.
        self.predecessors = defaultdict(set)
        self.successors = defaultdict(set)
        self.first_layer = []

        
        cdef list qubit_pos = [None] * num_qubits
        cdef object node_key
        cdef list qubits
        cdef int q_idx
        for node_key in self.nodes_order:
            qubits = self.nodes_dict[node_key]
            if len(qubits) == 2:
                for q_idx in qubits:
                    if q_idx >= num_qubits:
                        raise IndexError(
                            f"Qubit index {q_idx} is out of range for {num_qubits} qubits."
                        )
                    if qubit_pos[q_idx] is not None:
                        self._add_edge(qubit_pos[q_idx], node_key)
                    qubit_pos[q_idx] = node_key

                if not self.predecessors[node_key]:
                    self.first_layer.append(node_key)

    cdef void _add_edge(self, from_node, to_node):
        self.successors[from_node].add(to_node)
        self.predecessors[to_node].add(from_node)

    cpdef list top_sort(self):
        cdef dict visited = {node: False for node in self.nodes_order}
        cdef list top_order = []
        cdef int node

        for node in self.first_layer:
            if not visited[node]:
                self._dfs(node, visited, top_order)
        return top_order[::-1]

    cdef void _dfs(self, int node, dict visited, list top_order):
        visited[node] = True
        for succ in self.successors[node]:
            if not visited[succ]:
                self._dfs(succ, visited, top_order)
        top_order.append(node)

    cpdef void print_dag(self):
        for node in self.nodes_order:
            print(
                f"Node {node}: successors {self.successors[node]}, "
                f"predecessors {self.predecessors[node]}"
            )
