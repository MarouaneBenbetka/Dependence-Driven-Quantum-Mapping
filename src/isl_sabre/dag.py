from typing import Dict, List, Set, Optional, DefaultDict
from collections import defaultdict


class DAG:
    def __init__(self, num_qubits: int, nodes_dict: Dict[int, List[int]]):
        self.num_qubits = num_qubits
        self.nodes_dict = nodes_dict
        self.nodes_order = list(nodes_dict.keys())

        self.predecessors: DefaultDict[Set[int]] = defaultdict(set)
        self.successors: DefaultDict[Set[int]] = defaultdict(set)
        self.first_layer: List[int] = []

        qubit_pos: List[Optional[int]] = [None] * num_qubits

        for current_idx, node_key in enumerate(self.nodes_order):
            qubits = self.nodes_dict[node_key]
            for q_idx in qubits:
                if q_idx >= num_qubits:
                    raise IndexError(
                        f"Qubit index {q_idx} is out of range for {num_qubits} qubits."
                    )
                prev_node = qubit_pos[q_idx]
                if prev_node is not None:
                    self._add_edge(prev_node, node_key)
                qubit_pos[q_idx] = node_key

            if not self.predecessors[node_key]:
                self.first_layer.append(node_key)

    def _add_edge(self, from_node: int, to_node: int) -> None:
        self.successors[from_node].add(to_node)
        self.predecessors[to_node].add(from_node)

    def top_sort(self) -> List[int]:
        visited = [False] * len(self.nodes_order)
        top_order = []

        def dfs(node: int) -> None:
            visited[node] = True
            for succ in self.successors[node]:
                if not visited[succ]:
                    dfs(succ)
            top_order.append(node)

        for node in self.first_layer:
            if not visited[node]:
                dfs(node)

        return top_order[::-1]

    def print_dag(self) -> None:
        for node_key in self.nodes_order:
            print(f"Node {node_key}:", end=" ")
            print("successors", self.successors[node_key],
                  "predecessors", self.predecessors[node_key])


if __name__ == "__main__":
    # Create nodes dictionary for the DAG (3-qubit circuit)
    nodes_dict = {
        0: [0, 1],  # CX gate (qubits 0 and 1)
        1: [0],      # RX gate (qubit 0)
        2: [1],      # RZ gate (qubit 1)
        3: [0, 2],   # H gate (qubit 2)
    }

    # Instantiate the DAG
    dag = DAG(num_qubits=3, nodes_dict=nodes_dict)

    # Inspect the structure
    print("First layer nodes:", dag.first_layer)  # Should show [0]
    print("Node 0", "successors",
          dag.successors[0], "predecessors", dag.predecessors[0])
    print("Node 1", "successors",
          dag.successors[1], "predecessors", dag.predecessors[1])
    print("Node 2", "successors",
          dag.successors[2], "predecessors", dag.predecessors[2])
    print("Node 3", "successors",
          dag.successors[3], "predecessors", dag.predecessors[3])
