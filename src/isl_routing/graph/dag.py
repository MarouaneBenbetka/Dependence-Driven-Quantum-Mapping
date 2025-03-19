from collections import defaultdict
from typing import Dict, List, Set, DefaultDict, Optional
from tqdm import tqdm


class DAG:
    def __init__(
        self,
        num_qubits: int,
        nodes_dict: Dict[int, List[int]],
        write: Dict[int, List[int]],
        no_read_dep: Optional[bool] = False,
        transitive_reduction: bool = False,
        backward: bool = False
    ) -> None:

        self.num_qubits = num_qubits
        self.nodes_dict = nodes_dict
        self.nodes_order = sorted(nodes_dict.keys(), reverse=backward)

        self.predecessors_full: DefaultDict[int, Set[int]] = defaultdict(set)
        self.successors_full: DefaultDict[int, Set[int]] = defaultdict(set)
        self.first_layer_full: List[int] = []

        self.predecessors_2q: DefaultDict[int, Set[int]] = defaultdict(set)
        self.successors_2q: DefaultDict[int, Set[int]] = defaultdict(set)
        self.first_layer_2q: List[int] = []

        self._build_edges_full()

        self._build_edges_2q()

        if transitive_reduction:
            self._transitive_reduction_2q()

    def _build_edges_full(self) -> None:

        qubit_pos = [None] * \
            self.num_qubits

        for node_key in self.nodes_order:
            qubits = self.nodes_dict[node_key]
            for q_idx in qubits:
                if q_idx >= self.num_qubits:
                    raise IndexError(f"Qubit index {q_idx} out of range.")
                prev_node = qubit_pos[q_idx]
                if prev_node is not None:
                    self.successors_full[prev_node].add(node_key)
                    self.predecessors_full[node_key].add(prev_node)

                qubit_pos[q_idx] = node_key

            if not self.predecessors_full[node_key]:
                self.first_layer_full.append(node_key)

    def _build_edges_2q(self) -> None:
        qubit_pos_2q = [None] * self.num_qubits

        for node_key in self.nodes_order:
            qubits = self.nodes_dict[node_key]

            if len(qubits) != 2:
                continue

            for q_idx in qubits:
                if q_idx >= self.num_qubits:
                    raise IndexError(f"Qubit index {q_idx} out of range.")
                prev_2q_node = qubit_pos_2q[q_idx]
                if prev_2q_node is not None:
                    self.successors_2q[prev_2q_node].add(node_key)
                    self.predecessors_2q[node_key].add(prev_2q_node)

                qubit_pos_2q[q_idx] = node_key

            if not self.predecessors_2q[node_key]:
                self.first_layer_2q.append(node_key)

    def _transitive_reduction_2q(self) -> None:
        order = self.nodes_order  # topological order
        reachable = {node: set() for node in order}

        for u in reversed(order):
            if u not in self.predecessors_2q and u not in self.successors_2q:
                continue

            new_succ = set()
            for v in self.successors_2q[u]:
                if v in reachable[u]:
                    continue
                else:
                    new_succ.add(v)
                    reachable[u].update(reachable[v])
                    reachable[u].add(v)

            self.successors_2q[u] = new_succ

        self.predecessors_2q = defaultdict(set)
        for u, sucs in self.successors_2q.items():
            for v in sucs:
                self.predecessors_2q[v].add(u)

    def print_dag_full(self) -> None:
        print("=== FULL DAG ===")
        for node in self.nodes_order:
            succ = self.successors_full[node]
            pred = self.predecessors_full[node]
            print(f"Node {node}: successors={succ}, predecessors={pred}")

    def print_dag_2q(self) -> None:
        print("=== 2Q DAG ===")
        all_2q_nodes = set(self.predecessors_2q.keys()) | set(
            self.successors_2q.keys())
        for node in self.nodes_order:
            if node not in all_2q_nodes:
                continue
            succ = self.successors_2q[node]
            pred = self.predecessors_2q[node]
            print(f"Node {node}: successors={succ}, predecessors={pred}")
