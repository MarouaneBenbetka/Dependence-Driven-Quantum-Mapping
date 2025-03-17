from src.isl_routing.utils.circuit_utils import *
from src.isl_routing.mapping.heuristic import *
from src.isl_routing.utils.isl_data_loader import *
from src.isl_routing.utils.isl_to_python import *
from src.isl_routing.utils.python_to_isl import *
from src.isl_routing.graph.graph import *
from src.isl_routing.mapping.mapping import *

import islpy as isl
import random
from tqdm import tqdm
from time import time

class POLY_QMAP():
    def __init__(self, edges, data) -> None:

        self.backend_connections = set(tuple(edge) for edge in edges)
        self.backend = build_backend_graph(edges)

        self.data = data

        self.distance_matrix = compute_distance_matrix(self.backend)
        self.num_qubits = len(self.distance_matrix) + 1

        self.disconnected_edges = extract_disconnected_edges_map(edges)

        self.nb_gates, self.isl_access, self.access, self.schedule, self.write_dep, self.write_dict = read_data(
            self.data)

        self.decay_parameter = [1 for _ in range(self.num_qubits)]
        self.qubit_depth = {q: 0 for q in range(self.num_qubits)}

        self.reset = 5
        self.isl_mapping = None
        self.mapping_dict = None
        self.reverse_mapping_dict = None
        self.isl_front_layer = None
        self.front_layer = None
        self.isl_extended_layer = None
        self.extended_layer = None
        
        self.circuit = QuantumCircuit(self.num_qubits - 1)
        self.results = {}

    def run(self, with_transitive_closure=False, heuristic_method=None, no_read_dep=False, transitive_reduction=True, initial_mapping_method="sabre",num_iter = 1, verbose=0):
        self.init_mapping(method=initial_mapping_method)
        self.results = {}
        min_swaps = float('inf')
        for i in range(num_iter):
            self.isl_dag, self.dag, self.dag_predecessors = generate_dag(
                self.access, self.write_dict, self.num_qubits, no_read_dep, transitive_reduction,i%2)

            self.dag_dependencies_count = compute_dependencies_length(self.dag)
            self.init_front_layer()

            
            self.qubit_depth = {q: 0 for q in range(self.num_qubits)}
            swap_count = self.execute_sabre_algorithm(
                with_transitive_closure, heuristic_method, verbose)
            min_swaps = min(min_swaps, swap_count)
            self.results[i] = {"swap_count": swap_count, "circuit_depth": self.get_circuit_depth()}
        return min_swaps

    def init_mapping(self, method="trivial"):
        if method == "random":
            self.isl_mapping, self.mapping_dict, self.reverse_mapping_dict = generate_random_initial_mapping(
                self.num_qubits)
        elif method == "trivial":
            self.isl_mapping, self.mapping_dict, self.reverse_mapping_dict = generate_trivial_initial_mapping(
                self.num_qubits)
        elif method == "sabre":
            self.isl_mapping, self.mapping_dict, self.reverse_mapping_dict = generate_sabre_initial_mapping(
                self.data["qasm_code"], self.backend_connections)
        elif method== "cirq":
            self.isl_mapping, self.mapping_dict, self.reverse_mapping_dict = generate_cirq_initial_mapping(
                self.data["qasm_code"])
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

        with tqdm(total=total_gates, desc="Executing Gates", mininterval=0.1, disable=(verbose == 0),leave=False) as pbar:
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
        if len(self.access[gate]) == 1:
            q = self.access[gate][0]
            phys_q = self.mapping_dict[q]
            new_depth = self.qubit_depth.get(phys_q, 0) + 1
            self.qubit_depth[phys_q] = new_depth
            self.circuit.h(phys_q)
            return True
        
        
        q1, q2 = self.access[gate]
        phys_q1, phys_q2 = self.mapping_dict[q1], self.mapping_dict[q2]

        if (phys_q1, phys_q2) in self.backend_connections or (phys_q2, phys_q1) in self.backend_connections:
            current_depth_q1 = self.qubit_depth.get(phys_q1, 0)
            current_depth_q2 = self.qubit_depth.get(phys_q2, 0)
            new_depth = max(current_depth_q1, current_depth_q2) + 1

            self.qubit_depth[phys_q1] = new_depth
            self.qubit_depth[phys_q2] = new_depth
            
            self.circuit.cx(phys_q1, phys_q2)

            return True
        return False

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
        if huristic_method not in ["decay", "single-decay", "lookahead", "max_focus", "more_excuted", "closure"]:
            raise ValueError("Invalid heuristic method provided")

        if huristic_method == "decay":
            return self._apply_decay_heuristic()

        if huristic_method == "single-decay":
            return self._apply_single_decay_heuristic(with_transitive)

        if huristic_method == "lookahead":
            return self._apply_lookahead_heuristic()

        if huristic_method == "max_focus":
            return self._apply_max_focus_heuristic()

        if huristic_method == "more_excuted":
            return self._apply_more_excuted_heuristic()

        if huristic_method == "closure":
            return self._apply_closure_score_heuristic()

    def _apply_decay_heuristic(self):
        

        logical_qubits = [
            q for gate in self.front_layer for q in self.access[gate]]
        physical_qubits = set(self.mapping_dict[q] for q in logical_qubits)

        self.isl_extended_layer, self.extended_layer = create_extended_successor_set(
            self.front_layer, self.dag,self.access, extended_set_size=len(physical_qubits)
        )
        
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
        
        phys_q1 , phys_q2 = self.mapping_dict[best_swap_gate[0]], self.mapping_dict[best_swap_gate[1]]
        
        self.update_depth(phys_q1, phys_q2)

        return 1

    def _apply_single_decay_heuristic(self, with_transitive):
        isl_best_node = self.find_best_node(with_transitive)
        best_node_list = isl_set_to_python_list(isl_best_node)

        logical_qubits = [
            q for gate in best_node_list for q in self.access[gate]]
        physical_qubits = set(self.mapping_dict[q] for q in logical_qubits)

        self.isl_extended_layer, self.extended_layer = create_extended_successor_set(
            self.front_layer, self.dag,self.access, extended_set_size=len(physical_qubits)
        )

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
        self.update_depth( best_swap_gate[0], best_swap_gate[1])

        return 1

    def _apply_lookahead_heuristic(self):

        lookahead_paths = create_lookahead_path_set(
            self.front_layer, self.dag, self.dag_predecessors
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
            for path in lookahead_paths:
                for node in self.front_layer:
                    score = lookahead_poly_heuristic(
                        node,
                        self.front_layer,
                        path,
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
        self.update_depth( best_swap_gate[0], best_swap_gate[1])

        return 1

    def _apply_max_focus_heuristic(self):
        

        logical_qubits = [
            q for gate in self.front_layer for q in self.access[gate]]
        physical_qubits = set(self.mapping_dict[q] for q in logical_qubits)

        self.isl_extended_layer, self.extended_layer = create_extended_successor_set(
            self.front_layer, self.dag,self.access,len(physical_qubits)
        )
        
        candidate_swaps = generate_swap_candidates(
            physical_qubits, self.backend)

        heuristic_score = {}
        for swap_gate in candidate_swaps:
            temp_mapping_dict = swap_logical_physical_mappings(
                self.mapping_dict, self.reverse_mapping_dict, swap_gate
            )
            score = max_focus_poly_heuristic(
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
        self.update_depth( best_swap_gate[0], best_swap_gate[1])

        return 1

    def _apply_more_excuted_heuristic(self):
        

        logical_qubits = [
            q for gate in self.front_layer for q in self.access[gate]]
        physical_qubits = set(self.mapping_dict[q] for q in logical_qubits)
        self.isl_extended_layer, self.extended_layer = create_extended_successor_set(
                    self.front_layer, self.dag,self.access,len(physical_qubits)
                )
        candidate_swaps = generate_swap_candidates(
            physical_qubits, self.backend)

        heuristic_score = {}
        for swap_gate in candidate_swaps:
            temp_mapping_dict = swap_logical_physical_mappings(
                self.mapping_dict, self.reverse_mapping_dict, swap_gate
            )
            score = more_excuted_heuristic(
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
        self.update_depth( best_swap_gate[0], best_swap_gate[1])

        return 1

    def _apply_closure_score_heuristic(self):

        logical_qubits = [
            q for gate in self.front_layer for q in self.access[gate]]
        physical_qubits = set(self.mapping_dict[q] for q in logical_qubits)

        self.isl_extended_layer, self.extended_layer, extended_layer_index = create_leveled_extended_successor_set(
            self.front_layer, self.dag,self.access,len(physical_qubits)   
        )
        
        candidate_swaps = generate_swap_candidates(
            physical_qubits, self.backend)

        heuristic_score = {}
        for swap_gate in candidate_swaps:
            temp_mapping_dict = swap_logical_physical_mappings(
                self.mapping_dict, self.reverse_mapping_dict, swap_gate
            )
            score = closure_poly_heuristic(self.front_layer, self.extended_layer, temp_mapping_dict,
                                           self.distance_matrix, self.access, self.decay_parameter, self.dag_dependencies_count, extended_layer_index, swap_gate)
            heuristic_score[swap_gate] = score

        best_swap_gate = find_min_score_swap_gate(heuristic_score)

        self.isl_mapping = swap_logical_physical_isl_mapping(
            self.isl_mapping, best_swap_gate)
        swap_logical_physical_mappings(
            self.mapping_dict, self.reverse_mapping_dict, best_swap_gate, inplace=True
        )

        self.decay_parameter[best_swap_gate[0]] += 0.001
        self.decay_parameter[best_swap_gate[1]] += 0.001
        self.update_depth( best_swap_gate[0], best_swap_gate[1])

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

    def update_depth(self,q1,q2):

        current_depth_q1 = self.qubit_depth.get(q1, 0)
        current_depth_q2 = self.qubit_depth.get(q2, 0)
        new_depth = max(current_depth_q1, current_depth_q2) + 1

        self.qubit_depth[q1] = new_depth
        self.qubit_depth[q2] = new_depth
        
        self.circuit.swap(q1, q2)
        
    def get_circuit_depth(self):
        return max(self.qubit_depth.values())
    