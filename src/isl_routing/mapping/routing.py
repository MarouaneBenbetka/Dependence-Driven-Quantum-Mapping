from src.isl_routing.utils.circuit_utils import *
from src.isl_routing.mapping.heuristic import *
from src.isl_routing.utils.isl_data_loader import *
from src.isl_routing.utils.isl_to_python import *
from src.isl_routing.graph.graph import *
from src.isl_routing.mapping.mapping import *

import islpy as isl
import random
from tqdm import tqdm


class POLY_QMAP():
    def __init__(self, edges, data) -> None:

        self.backend_connections = set(tuple(edge) for edge in edges)
        self.backend = build_backend_graph(edges)

        self.data = data

        self.distance_matrix = compute_distance_matrix(self.backend)
        self.num_qubits = len(self.distance_matrix) + 1

        self.disconnected_edges = extract_disconnected_edges_map(edges)

        self.nb_gates, self.isl_access, self.access, self.schedule, self.write_dep = read_data(
            self.data)

        self.decay_parameter = [1 for _ in range(self.num_qubits)]

        self.reset = 5
        self.isl_mapping = None
        self.mapping_dict = None
        self.reverse_mapping_dict = None
        self.isl_front_layer = None
        self.front_layer = None
        self.isl_extended_layer = None
        self.extended_layer = None

    def run(self, with_transitive_closure=False, heuristic_method="decay", no_read_dep=False, transitive_reduction=True, verbose=0):
        self.isl_dag, self.dag, self.dag_predecessors = generate_dag(
            self.access, None, self.num_qubits, no_read_dep, transitive_reduction)

        self.init_mapping(method="sabre")
        self.init_front_layer()

        if with_transitive_closure:
            self.dag_dependencies = count_dependencies(self.dag)

        swap_count = self.execute_sabre_algorithm(
            with_transitive_closure, heuristic_method, verbose)

        return swap_count

    def init_mapping(self, method="sabre"):
        if method == "random":
            self.isl_mapping, self.mapping_dict, self.reverse_mapping_dict = generate_random_initial_mapping(
                self.num_qubits)
        elif method == "sabre":
            self.isl_mapping, self.mapping_dict, self.reverse_mapping_dict = generate_sabre_initial_mapping(
                self.data["qasm_code"], self.backend_connections)
        else:
            raise ValueError(
                f"Unknown mapping initialization method: {method}")

    def init_front_layer(self):
        self.front_layer = set()
        for gate in self.dag:
            if len(self.dag_predecessors[gate]) == 0:
                self.front_layer.add(gate)

        self.isl_front_layer = list_to_isl_set(self.front_layer)

    def execute_sabre_algorithm(self, with_transitive, huristic_method, verbose):
        swap_count = 0
        total_gates = len(self.access)
        self.decay_parameter = [1 for _ in range(self.num_qubits)]

        with tqdm(total=total_gates, desc="Executing Gates", mininterval=0.1, disable=(verbose == 0)) as pbar:
            while not self.isl_front_layer.is_empty():
                isl_ready_to_execute_gates, ready_to_execute_gates = self.extract_ready_to_execute_gate_list()

                if len(ready_to_execute_gates) > 0:

                    self.update_front_layer(
                        ready_to_execute_gates, isl_ready_to_execute_gates)

                    self.decay_parameter = [1 for _ in range(self.num_qubits)]
                    pbar.update(len(ready_to_execute_gates))

                else:

                    local_swap_count = self.apply_heuristic(
                        huristic_method, with_transitive=with_transitive, verbose=verbose)

                    swap_count += local_swap_count

        return swap_count

    def extract_ready_to_execute_gate_list(self,):
        ready_to_execute_gates_list = []

        for gate in self.front_layer:
            if self.is_gate_executable(gate):
                ready_to_execute_gates_list.append(gate)

        isl_ready_to_execute_gates = list_to_isl_set(
            ready_to_execute_gates_list)
        return isl_ready_to_execute_gates, ready_to_execute_gates_list

    def is_gate_executable(self, gate) -> bool:

        q1, q2 = self.access[gate]
        phys_q1, phys_q2 = self.mapping_dict[q1], self.mapping_dict[q2]

        return (phys_q1, phys_q2) in self.backend_connections or (phys_q2, phys_q1) in self.backend_connections

    def update_front_layer(self, executable_gates, isl_executable_gates):
        for gate in executable_gates:
            for successor_gate in self.dag[gate]:
                self.dag_predecessors[successor_gate].discard(gate)
                if len(self.dag_predecessors[successor_gate]) == 0:
                    self.front_layer.add(successor_gate)
                    self.isl_front_layer = self.isl_front_layer.union(
                        isl.Set(f"{{[{successor_gate}]}}"))

            self.front_layer.discard(gate)

        self.isl_front_layer = self.isl_front_layer.subtract(
            isl_executable_gates)

    def apply_heuristic(self, huristic_method, with_transitive=False, verbose=0):
        if huristic_method not in ["decay", "single-decay"]:
            raise ValueError("Invalid heuristic method provided")

        if huristic_method == "decay":
            return self._apply_decay_heuristic()

        if huristic_method == "single-decay":
            return self._apply_single_decay_heuristic(with_transitive)

    def _apply_decay_heuristic(self):
        self.isl_extended_layer, self.extended_layer = create_extended_successor_set(
            self.front_layer, self.dag
        )

        logical_qubits = [
            q for gate in self.front_layer for q in self.access[gate]]
        physical_qubits = set(self.mapping_dict[q] for q in logical_qubits)

        candidate_swaps = generate_swap_candidates(
            physical_qubits, self.backend)

        heuristic_score = {}
        for swap_gate in candidate_swaps:
            temp_mapping_dict = swap_logical_physical_mappings(
                self.mapping_dict, self.reverse_mapping_dict, swap_gate
            )
            score = decay_poly_heuristic(
                self.front_layer,
                self.extended_layer,
                temp_mapping_dict,
                self.distance_matrix,
                self.access,
                self.decay_parameter,
                swap_gate
            )
            heuristic_score[swap_gate] = score

        best_swap_gate = find_min_score_swap_gate(heuristic_score)

        self.isl_mapping = swap_logical_physical_isl_mapping(
            self.isl_mapping, best_swap_gate)
        swap_logical_physical_mappings(
            self.mapping_dict, self.reverse_mapping_dict, best_swap_gate, inplace=True
        )

        self.decay_parameter[best_swap_gate[0]] += 0.001
        self.decay_parameter[best_swap_gate[1]] += 0.001

        return 1

    def _apply_single_decay_heuristic(self, with_transitive):
        isl_best_node = self.find_best_node(with_transitive)
        best_node_list = isl_set_to_python_list(isl_best_node)

        self.isl_extended_layer, self.extended_layer = create_extended_successor_set(
            best_node_list, self.dag
        )

        logical_qubits = [
            q for gate in best_node_list for q in self.access[gate]]
        physical_qubits = set(self.mapping_dict[q] for q in logical_qubits)

        candidate_swaps = generate_swap_candidates(
            physical_qubits, self.backend)

        heuristic_score = {}
        for swap_gate in candidate_swaps:
            temp_mapping_dict = swap_logical_physical_mappings(
                self.mapping_dict, self.reverse_mapping_dict, swap_gate
            )
            score = decay_poly_heuristic(
                self.front_layer,
                self.extended_layer,
                temp_mapping_dict,
                self.distance_matrix,
                self.access,
                self.decay_parameter,
                swap_gate
            )
            heuristic_score[swap_gate] = score

        best_swap_gate = find_min_score_swap_gate(heuristic_score)

        swap_logical_physical_mappings(
            self.mapping_dict, self.reverse_mapping_dict, best_swap_gate, inplace=True
        )

        self.decay_parameter[best_swap_gate[0]] += 0.001
        self.decay_parameter[best_swap_gate[1]] += 0.001

        return 1

    def find_best_node(self, with_transitive):

        if with_transitive and self.isl_front_layer.as_set().count_val().to_python() != 1 and self.dag_dependencies:
            min_key = min(self.dag_dependencies, key=self.dag_dependencies.get)
            best_node = int_to_isl_set(min_key)
            del self.dag_dependencies[min_key]
        else:

            best_node = random.choice(list(self.front_layer))
            best_node = int_to_isl_set(best_node)

        return best_node
