from collections import defaultdict
from typing import Dict, List, Set, DefaultDict, Optional


class DAG:
    def __init__(self, num_qubits: int, nodes_dict: Dict[int, List[int]], write: Dict[int, List[int]], no_read_dep: Optional[bool] = False, transitive_reduction: Optional[bool] = False, backward: Optional[bool] = False) -> None:

        self.num_qubits = num_qubits
        self.nodes_dict = nodes_dict
        self.nodes_order = sorted(list(nodes_dict.keys()), reverse=backward)

        self.predecessors: DefaultDict[int, Set[int]] = defaultdict(set)
        self.successors: DefaultDict[int, Set[int]] = defaultdict(set)
        self.first_layer: List[int] = []

        if no_read_dep:
            self.write_order = sorted(write.keys(), reverse=backward)
            read_lists = {qubit: [] for qubit in range(num_qubits)}
            last_write = {}

            for gate in self.write_order:
                read_to_write = not backward
                current_writes = write.get(gate, [])
                writes_set = set(current_writes)

                # Process RAW dependencies for qubits not written by this gate
                for qubit in self.nodes_dict.get(gate, []):
                    if qubit in last_write and qubit not in writes_set:
                        if read_to_write:
                            self._add_edge(last_write[qubit], gate)
                        else:
                            self._add_edge(gate, last_write[qubit])

                # Process WAR and WAW for qubits written by this gate
                for qubit in current_writes:
                    # WAR: Add edges from previous reads to this write
                    for read_gate in read_lists[qubit]:
                        if read_to_write:
                            self._add_edge(read_gate, gate)
                        else:
                            self._add_edge(gate, read_gate)
                    read_lists[qubit].clear()

                    # WAW: Add edge from last write to this write
                    if qubit in last_write:
                        prev_write = last_write[qubit]
                        if read_to_write:
                            self._add_edge(prev_write, gate)
                        else:
                            self._add_edge(gate, prev_write)
                    last_write[qubit] = gate

                # Add this gate to read lists for qubits it reads but doesn't write
                read_qubits = [q for q in self.nodes_dict.get(gate, []) if q not in writes_set]
                for qubit in read_qubits:
                    read_lists[qubit].append(gate)

            # Determine first layer (gates with no predecessors)
            self.first_layer = [gate for gate in self.write_order if not self.predecessors[gate]]


        else:
            qubit_pos: List[Optional[int]] = [None] * num_qubits
            for node_key in self.nodes_order:
                qubits = self.nodes_dict[node_key]
                for q_idx in qubits:
                    if q_idx >= num_qubits:
                        raise IndexError(
                            f"Qubit index {q_idx} is out of range for {num_qubits} qubits.")
                    prev_node = qubit_pos[q_idx]
                    if prev_node is not None:
                        self._add_edge(prev_node, node_key)
                    qubit_pos[q_idx] = node_key

                if not self.predecessors[node_key]:
                    self.first_layer.append(node_key)

        if transitive_reduction:
            self._transitive_reduction()

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
            print(
                f"Node {node}: successors {self.successors[node]}, predecessors {self.predecessors[node]}")

    def _transitive_reduction(self):
        """
        Removes edges in self.successors/self.predecessors that are
        transitively implied by other paths in the DAG.
        """
        # Collect all edges so we can iterate over a stable list
        all_edges = []
        for u in self.nodes_order:
            for v in self.successors[u]:
                all_edges.append((u, v))

        for u, v in all_edges:
            # Temporarily remove (u, v)
            self.successors[u].remove(v)
            self.predecessors[v].remove(u)

            # If there's still a path from u to v, the edge was redundant
            if not self._path_exists(u, v):
                # No path found: we do need this edge. Re-add it.
                self.successors[u].add(v)
                self.predecessors[v].add(u)

    def _path_exists(self, start, end):
        """
        Returns True if there is a path from start to end in self.successors.
        """
        visited = set()
        stack = [start]
        while stack:
            node = stack.pop()
            if node == end:
                return True
            for nxt in self.successors[node]:
                if nxt not in visited:
                    visited.add(nxt)
                    stack.append(nxt)
        return False
