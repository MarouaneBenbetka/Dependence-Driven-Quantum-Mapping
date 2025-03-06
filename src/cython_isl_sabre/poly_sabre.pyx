# poly_sabre.pyx
# cython: language_level=3

from .poly_circuit_preprocess import *
from .poly_heuristic import *
from .poly_circuit_utils import *

import islpy as isl
import networkx as nx
from tqdm import tqdm

from qiskit import QuantumCircuit
from qiskit.transpiler import CouplingMap
from qiskit.transpiler.passes import SabreLayout
from qiskit.converters import circuit_to_dag
import time
import random

cdef class POLY_SABRE:
    # Declare instance attributes (public if accessed externally)
    cdef public object edges
    cdef public object data
    cdef public object coupling_graph
    cdef public object distance_matrix
    cdef public int num_qubit
    cdef public object disconnected_edges
    cdef public object neighbours
    cdef public object physical_qubits_domain
    cdef public object all_swap_mappings
    cdef public object swap_mapping
    cdef public int nb_gates
    cdef public object read_dep
    cdef public object access
    cdef public object reverse_access
    cdef public object schedule
    cdef public object reverse_schedule
    cdef public object write_dep
    cdef public object decay_parameter
    cdef public object dag
    cdef public object reverse_dag
    cdef public int reset
    cdef public object instruction_times

    def __init__(self, edges, data, bint no_read_dep=False, bint poly_path=False):
        self.edges = edges
        self.data = data
        self.coupling_graph = nx.Graph()
        self.coupling_graph.add_edges_from(edges)
        self.distance_matrix = get_distance_matrix(self.coupling_graph)
        self.num_qubit = len(self.distance_matrix) + 1
        self.disconnected_edges = extract_disconnected_edges_map(edges)
        self.neighbours = extract_neighbourss_map(edges)
        self.physical_qubits_domain = isl.Set("{ [i]:  0 <= i < %d }" % self.num_qubit)
        if poly_path:
            self.all_swap_mappings = generate_all_swaps_mapping(self.coupling_graph, self.physical_qubits_domain)
        else:
            self.all_swap_mappings = None
        self.swap_mapping = generate_all_neighbours_mapping(self.coupling_graph)
        # read_data returns a tuple: (nb_gates, read_dep, access, reverse_access, schedule, reverse_schedule, write_dep)
        self.nb_gates, self.read_dep, self.access, self.reverse_access, self.schedule, self.reverse_schedule, self.write_dep = read_data(self.data)
        self.decay_parameter = [1 for _ in range(self.num_qubit)]
        self.dag = generate_dag(self.read_dep, self.write_dep, no_read_dep)
        cdef str map_str = f"{{ [i] -> [{self.nb_gates}-i - 1] : 0 <= i < {self.nb_gates} }}"
        self.reverse_dag = self.dag.apply_range(isl.Map(map_str)).apply_domain(isl.Map(map_str))
        self.reset = 5
        self.instruction_times = {}

    def execute_sabre_algorithm(self, front_layer_gates, access, mapping, dag, with_transitive, huristic_method, verbose):
        cdef int nb_swaps = 0
        cdef int total_executed_gates = 0
        cdef int total_gates = self.count_number_gates(dag, front_layer_gates)
        self.decay_parameter = [1 for _ in range(self.num_qubit)]
        
        with tqdm(total=total_gates, desc="Executing Gates", mininterval=0.1, disable=(verbose==0)) as pbar:
            while not front_layer_gates.is_empty():
                ready_to_execute_gates = self.track_time(
                    "extract_gate_time",
                    lambda: self.extract_ready_to_execute_gate_list(front_layer_gates, access, mapping)
                )
                if not ready_to_execute_gates.is_empty():
                    original_dag = dag
                    dag = self.track_time(
                        "remove_execute_gate_time",
                        lambda: self.remove_excuted_gate(original_dag, ready_to_execute_gates)
                    )
                    waiting_nodes = self.track_time(
                        "waiting_nodes_time",
                        lambda: ready_to_execute_gates.apply(original_dag).subtract(dag.range())
                    )
                    front_layer_gates = self.track_time(
                        "front_layer_gates_time",
                        lambda: front_layer_gates.subtract(ready_to_execute_gates).union(waiting_nodes)
                    )
                    self.decay_parameter = [1 for _ in range(self.num_qubit)]
                    executed_gates_count = ready_to_execute_gates.as_set().count_val().to_python()
                    total_executed_gates += executed_gates_count
                    pbar.update(executed_gates_count)
                else:
                    best_node = self.track_time(
                        "find_best_node_time",
                        lambda: self.find_best_node(front_layer_gates, dag, with_transitive)
                    )
                    local_swap, mapping = self.track_time(
                        "heuristic_time",
                        lambda: self.apply_heuristic(front_layer_gates, access, mapping, dag, best_node, huristic_method, verbose=verbose)
                    )
                    nb_swaps += local_swap
        return nb_swaps, mapping

    def count_number_gates(self, dag, front_layer_gates):
        try:
            return dag.domain().union(dag.range()).union(front_layer_gates).as_set().count_val().to_python()
        except Exception:
            return 0

    def remove_excuted_gate(self, dag, ready_to_execute_gates):
        cdef object complement_set = ready_to_execute_gates.as_set().complement()
        return dag.intersect_domain(complement_set)
    
    def track_time(self, label, func):
        cdef double start = time.time()
        cdef object result = func()
        cdef double elapsed = time.time() - start
        if label in self.instruction_times:
            self.instruction_times[label] += elapsed
        else:
            self.instruction_times[label] = elapsed
        return result

    def apply_heuristic(self, front_layer_gates, access, mapping, dag, best_node, huristic_method, verbose=0):
        if huristic_method not in ["decay", "multi-layer-decay", "single-decay", "poly-paths"]:
            raise ValueError("Invalid heuristic method provided")

        cdef dict heuristic_score = {}
        if huristic_method == "decay":
            Extended_layer = self.track_time("Extended_layer", lambda: create_extended_successor_set(front_layer_gates, dag))
            combined_domain = self.track_time("combined_domain", lambda: front_layer_gates.union(Extended_layer).coalesce())
            mapping = self.track_time("mapping", lambda: mapping.coalesce())
            simplified_access = self.track_time("simplified_access", lambda: access.gist_domain(combined_domain))
            new_access = self.track_time("new_access", lambda: simplified_access.intersect_domain(combined_domain))
            logical_qubits = self.track_time("logical_qubits", lambda: front_layer_gates.apply(access))
            physical_qubits = self.track_time("physical_qubits", lambda: logical_qubits.apply(mapping))
            physical_qubits_int = self.track_time("physical_qubits_int", lambda: isl_set_to_python_list(physical_qubits))
            swap_candidate_list = self.track_time("swap_candidate_list", lambda: self.candidate_swaps(physical_qubits_int))
            for swap_gate in swap_candidate_list:
                temp_mapping = self.update_mapping(swap_gate[0], mapping)
                swap_gate_score = decay_poly_heuristic(
                    front_layer_gates, Extended_layer, temp_mapping, self.distance_matrix, new_access, self.decay_parameter, (swap_gate[1][0], swap_gate[1][1])
                )
                heuristic_score.update({swap_gate[0]: (swap_gate_score, swap_gate[1])})
            min_score_swap_gate, min_gate = self.find_min_score_swap_gate(heuristic_score, verbose=verbose)
            mapping = self.update_mapping(min_score_swap_gate, mapping)
            if verbose > 2:
                print("     chosen swap gate :", min_score_swap_gate)
                print("*" * 50)
            self.decay_parameter[min_gate[0]] += 0.001
            self.decay_parameter[min_gate[1]] += 0.001
            return 1, mapping

        
        cdef object qubits = best_node.apply(access)
        cdef object logical_q1 = qubits.lexmin()
        cdef object logical_q2 = qubits.lexmax()
        cdef int physical_q1 = logical_q1.apply(mapping).as_set().dim_max_val(0).to_python()
        cdef int physical_q2 = logical_q2.apply(mapping).as_set().dim_max_val(0).to_python()

        if huristic_method == "single-decay":
            swap_candidate_list = self.swap_mapping[physical_q1] + self.swap_mapping[physical_q2]
            for swap_gate in swap_candidate_list:
                temp_mapping = self.update_mapping(swap_gate[0], mapping)
                swap_gate_score = decay_poly_heuristic(
                    front_layer_gates, dag, temp_mapping, self.distance_matrix, access, self.decay_parameter, (swap_gate[1][0], swap_gate[1][1])
                )
                heuristic_score.update({swap_gate[0]: (swap_gate_score, swap_gate[1])})
            min_score_swap_gate, min_gate = self.find_min_score_swap_gate(heuristic_score)
            mapping = self.update_mapping(min_score_swap_gate, mapping)
            self.decay_parameter[min_gate[0]] += 0.01
            self.decay_parameter[min_gate[1]] += 0.01
            return 1, mapping

        if huristic_method == "multi-layer-decay":
            swap_candidate_list = self.swap_mapping[physical_q1] + self.swap_mapping[physical_q2]
            for swap_gate in swap_candidate_list:
                temp_mapping = self.update_mapping(swap_gate[0], mapping)
                swap_gate_score = multi_layer_poly_heuristic(
                    front_layer_gates, dag, temp_mapping, self.distance_matrix, access, self.decay_parameter, (swap_gate[1][0], swap_gate[1][1])
                )
                heuristic_score.update({swap_gate[0]: (swap_gate_score, swap_gate[1])})
            min_score_swap_gate, min_gate = self.find_min_score_swap_gate(heuristic_score)
            mapping = self.update_mapping(min_score_swap_gate, mapping)
            self.decay_parameter[min_gate[0]] += 0.01
            self.decay_parameter[min_gate[1]] += 0.01
            return 1, mapping

        if huristic_method == "poly-paths":
            swap_candidate_list = self.all_swap_mappings[(physical_q1, physical_q2)]
            for swap_gate in swap_candidate_list:
                temp_mapping = self.update_mapping(swap_gate[0], mapping)
                swap_gate_score = paths_poly_heuristic(
                    front_layer_gates, dag, temp_mapping, self.distance_matrix, access, swap_gate[1]
                )
                heuristic_score.update({swap_gate[0]: swap_gate_score})
            min_score_swap_gate, _ = self.find_min_score_swap_gate(heuristic_score, swap_candidate_list)
            mapping = self.update_mapping(min_score_swap_gate[0], mapping)
            return min_score_swap_gate[1], mapping

    def candidate_swaps(self, active_qubits):
        cdef list candidates = []
        cdef set active_set = set(active_qubits)
        for u, v in self.coupling_graph.edges():
            if u in active_set or v in active_set:
                if u in active_set:
                    candidate = (u, v)
                else:
                    candidate = (v, u)
                map_str = f"[{u}] -> [{v}];[{v}] -> [{u}]"
                candidates.append((isl.Map("{" + map_str + "}"), candidate))
        return candidates

    def extract_ready_to_execute_gate_list(self, front_layer_gates, access, mapping):
        cdef object ready_to_execute_gates = isl.UnionSet("{}")
        def process_gate(gate):
            if self.is_gate_executable(gate, access, mapping):
                nonlocal ready_to_execute_gates
                ready_to_execute_gates = ready_to_execute_gates.union(gate)
        front_layer_gates.foreach_point(lambda point: process_gate(point.to_set()))
        return ready_to_execute_gates

    def find_best_node(self, front_layer_gates, dag, with_transitive):
        cdef object best_node
        if with_transitive and front_layer_gates.as_set().count_val().to_python() != 1:
            best_val = -1
            best_node = None
            transitive_closure = dag.transitive_closure()[0].intersect_domain(front_layer_gates)
            def evaluate_gate(point):
                nonlocal best_val, best_node
                gate = point.to_set()
                try:
                    dep = gate.apply(transitive_closure).as_set().count_val().to_python()
                except Exception:
                    dep = 0
                if dep > best_val:
                    best_val = dep
                    best_node = gate
            front_layer_gates.foreach_point(lambda point: evaluate_gate(point))
        else:
            best_node = front_layer_gates.sample()
        return best_node

    def find_min_score_swap_gate(self, heuristic_score, swap_candidate_list=None, verbose=0, double epsilon=1e-10):
        if swap_candidate_list:
            all_scores = list(heuristic_score.values())
            min_score = min(all_scores)
            min_score_swap_gate = swap_candidate_list[all_scores.index(min_score)]
            return min_score_swap_gate, None
        else:
            random.seed(21)
            min_score = float('inf')
            best_swaps = []
            for swap, (score, gate) in heuristic_score.items():
                if verbose > 2:
                    print("     swap gate :", swap)
                    print("     score :", score)
                    print("-" * 50)
                if score - min_score < -epsilon:
                    min_score = score
                    best_swaps = [(swap, (score, gate))]
                elif abs(score - min_score) <= epsilon:
                    best_swaps.append((swap, (score, gate)))
            best_swaps.sort()
            selected = random.choice(best_swaps)
            return selected[0], selected[1][1]

    def update_mapping(self, swap_gate, mapping):
        if swap_gate.is_empty():
            return mapping
        cdef object other_mapping = mapping.subtract_range(swap_gate.domain())
        return mapping.apply_range(swap_gate).union(other_mapping)

    def is_gate_executable(self, gate, access, mapping) -> bint:
        cdef object logical_qubits = gate.apply(access)
        cdef object physical_qubits = logical_qubits.apply(mapping)
        cdef object q1 = physical_qubits.lexmin().as_set()
        cdef object q2 = physical_qubits.lexmax().as_set()
        return q1.flat_product(q2).intersect(self.disconnected_edges).is_empty()

    def get_initial_mapping(self, method="sabre"):
        if method == "random":
            return get_poly_initial_mapping(self.coupling_graph)
        elif method == "sabre":
            circuit = QuantumCircuit.from_qasm_str(self.data["qasm_code"])
            dag_circuit = circuit_to_dag(circuit)
            coupling_map = CouplingMap(self.edges)
            sabre_layout = SabreLayout(coupling_map, seed=21)
            sabre_layout.run(dag_circuit)
            layout = sabre_layout.property_set["layout"]
            return ploy_initial_mapping(layout)

    def run(self, int num_iter=1, chunk_size=None, bint with_transitive=False, heuristic_method="single-decay", verbose=0):
        cdef double min_swap = float('inf')
        cdef object temp_mapping = self.get_initial_mapping()
        if chunk_size is None:
            chunk_size = self.nb_gates + 1
        for i in range(num_iter):
            total_swaps = 0
            chunk = 0

            if i % 2 == 0:
                temp_schedule = self.schedule
                temp_access = self.access
                dag = self.dag
            else:
                temp_schedule = self.reverse_schedule
                temp_access = self.reverse_access
                dag = self.reverse_dag
            while chunk <= self.nb_gates:
                filter_domain = isl.Set(f"{{ [i] : {chunk}<= i < {chunk + chunk_size} }}")
                new_access = temp_access.intersect_domain(filter_domain)
                new_schedule = temp_schedule.intersect_range(filter_domain)
                new_dag = dag.intersect_domain(filter_domain).intersect_range(filter_domain)
                front_layer = get_front_layer(new_dag, new_schedule)
                swap_res = self.execute_sabre_algorithm(front_layer, new_access, temp_mapping, new_dag, with_transitive, heuristic_method, verbose)
                total_swaps += swap_res[0]
                temp_mapping = swap_res[1]
                chunk += chunk_size
                if verbose == 2:
                    print(f"total swaps in chunk {chunk} is ", total_swaps)
            if verbose == 2:
                print("*" * 50)
                print(f"total swaps in iteration {i} is ", total_swaps)
                print("*" * 50)
            if total_swaps < min_swap:
                min_swap = total_swaps
        return min_swap
