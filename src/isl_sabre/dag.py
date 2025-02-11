from collections import defaultdict
from typing import Dict, List, Set, DefaultDict, Optional

class DAG:
    def __init__(self, num_qubits: int, nodes_dict: Dict[int, List[int]], write: Dict[int, List[int]]):


        self.num_qubits = num_qubits
        self.nodes_dict = nodes_dict
        self.write = write
        self.nodes_order = sorted(list(nodes_dict.keys()))


        self.predecessors: DefaultDict[int, Set[int]] = defaultdict(set)
        self.successors: DefaultDict[int, Set[int]] = defaultdict(set)
        self.first_layer: List[int] = []


        qubit_history: List[List[int]] = [[] for _ in range(num_qubits)]


        for node in self.nodes_order:

            for q in self.nodes_dict[node]:


                if q in self.write[node]:
                    for prev_node in qubit_history[q]:
                        self._add_edge(prev_node, node)
                    qubit_history[q] = [node]
                else:
                    
                    for prev_node in qubit_history[q]:
                        if q in self.write[prev_node]:
                            self._add_edge(prev_node, node)
                    qubit_history[q].append(node)

            if not self.predecessors[node]:
                self.first_layer.append(node)


    def _add_edge(self, from_node: int, to_node: int) -> None:
        """Adds an edge in the dependency graph from 'from_node' to 'to_node'."""
        self.successors[from_node].add(to_node)
        self.predecessors[to_node].add(from_node)

    def top_sort(self) -> List[int]:
        """Returns a topologically sorted list of nodes."""
        visited = {node: False for node in self.nodes_order}
        top_order = []

        def dfs(node: int) -> None:
            visited[node] = True
            for succ in self.successors[node]:
                if not visited[succ]:
                    dfs(succ)
            top_order.append(node)

        # Start DFS from nodes that have no dependencies.
        for node in self.first_layer:
            if not visited[node]:
                dfs(node)

        return top_order[::-1]

    def print_dag(self) -> None:
        """Prints each node along with its successors and predecessors."""
        for node in self.nodes_order:
            print(f"Node {node}: successors {self.successors[node]}, predecessors {self.predecessors[node]}")



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
