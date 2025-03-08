from src.isl_sabre.poly_circuit_preprocess import *
from src.isl_sabre.poly_heuristic import *
from src.isl_sabre.poly_circuit_utils import *


import islpy as isl
import networkx as nx
from tqdm import tqdm

from qiskit import QuantumCircuit
from qiskit.transpiler import CouplingMap
from qiskit.transpiler.passes import SabreLayout
from qiskit.converters import circuit_to_dag
from collections import defaultdict
import time
import random


class POLY_SABRE():
    def __init__(self, edges, data, no_read_dep=False, poly_path=False) -> None:

        self.backend_connections = set(tuple(edge) for edge in edges)
        self.data = data
        self.coupling_graph = nx.Graph()
        self.coupling_graph.add_edges_from(edges)
        self.distance_matrix = get_distance_matrix(self.coupling_graph)
        self.num_qubit = len(self.distance_matrix) + 1
        self.disconnected_edges = extract_disconnected_edges_map(edges)
        self.neighbours = extract_neighbourss_map(edges)
        self.physical_qubits_domain = isl.Set(
            "{ [i]:  0 <= i <  %d }" % self.num_qubit)
        if poly_path:
            self.all_swap_mappings = generate_all_swaps_mapping(
                self.coupling_graph, self.physical_qubits_domain)

        self.swap_mapping = generate_all_neighbours_mapping(
            self.coupling_graph)
        self.nb_gates, self.read_dep, self.access, self.reverse_access, self.schedule, self.reverse_schedule, self.write_dep = read_data(
            self.data)

        self.access_dict = isl_map_to_dict_optimized2(self.access)
        self.decay_parameter = [1 for _ in range(self.num_qubit)]
        self.dag, self.dag_graph = generate_dag(
            self.read_dep, self.write_dep, no_read_dep)
        map_str = f"{{ [i] -> [{self.nb_gates}-i - 1] : 0 <= i < {self.nb_gates} }}"
        self.reverse_dag = self.dag.apply_range(
            isl.Map(map_str)).apply_domain(isl.Map(map_str))
        self.reset = 5
        self.instruction_times = defaultdict(float)
        self.mapping_dict = None
        self.reverse_mapping_dict = None
        self.isl_front_layer = None
        self.front_layer = None
        self.isl_extended_layer = None
        self.extended_layer = None

    def execute_sabre_algorithm(self, access, mapping, dag, with_transitive, huristic_method, verbose):
        nb_swaps = 0
        total_executed_gates = 0
        total_gates = self.count_number_gates(dag, self.isl_front_layer)
        self.decay_parameter = [1 for _ in range(self.num_qubit)]

        with tqdm(total=total_gates, desc="Executing Gates", mininterval=0.1, disable=(verbose == 0)) as pbar:
            while not self.isl_front_layer.is_empty():

                isl_ready_to_execute_gates, ready_to_execute_gates = self.track_time(
                    "extract_gate_time",
                    lambda: self.extract_ready_to_execute_gate_list(
                        access, mapping)
                )

                if len(ready_to_execute_gates) > 0:

                    original_dag = dag
                    dag = self.track_time(
                        "remove_execute_gate_time",
                        lambda: self.remove_excuted_gate(
                            original_dag, isl_ready_to_execute_gates)
                    )
                    waiting_nodes = self.track_time(
                        "waiting_nodes_time",
                        lambda: isl_ready_to_execute_gates.apply(
                            original_dag).subtract(dag.range())
                    )

                    self.isl_front_layer = self.track_time(
                        "front_layer_gates_time",
                        lambda: self.isl_front_layer.subtract(
                            isl_ready_to_execute_gates).union(waiting_nodes)
                    )
                    self.front_layer = isl_set_to_python_list(
                        self.isl_front_layer)

                    self.decay_parameter = [1 for _ in range(self.num_qubit)]
                    executed_gates_count = isl_ready_to_execute_gates.as_set().count_val().to_python()
                    total_executed_gates += executed_gates_count
                    pbar.update(executed_gates_count)

                else:

                    best_node = self.track_time(
                        "find_best_node_time",
                        lambda: self.find_best_node(dag, with_transitive)
                    )

                    local_swap, mapping = self.track_time(
                        "heuristic_time",
                        lambda: self.apply_heuristic(
                            access, mapping, dag, best_node, huristic_method, verbose=verbose)
                    )

                    nb_swaps += local_swap

        return nb_swaps, mapping

    def count_number_gates(self, dag, front_layer_gates):
        try:
            return dag.domain().union(dag.range()).union(front_layer_gates).as_set().count_val().to_python()
        except:
            return 0

    def remove_excuted_gate(self, dag, ready_to_execute_gates):
        complement_set = ready_to_execute_gates.as_set().complement()
        return dag.intersect_domain(complement_set)

    def track_time(self, label, func):
        start = time.time()
        result = func()
        elapsed = time.time() - start
        if label in self.instruction_times:
            self.instruction_times[label] += elapsed
        else:
            self.instruction_times[label] = elapsed
        return result

    def apply_heuristic(self, access, mapping, dag, best_node, huristic_method, verbose=0):

        if huristic_method not in ["decay", "multi-layer-decay", "single-decay", "poly-paths"]:
            raise ValueError("Invalid heuristic method provided")

        if huristic_method == "decay":
            heuristic_score = dict()

            self.isl_extended_layer, self.extended_layer = self.track_time(
                "Extended_layer", lambda: create_extended_successor_set2(self.front_layer, self.dag_graph))

            mapping = self.track_time("mapping", lambda: mapping.coalesce())

            logical_qubits = self.track_time(
                "logical_qubits", lambda: self.isl_front_layer.apply(access))
            physical_qubits = self.track_time(
                "physical_qubits", lambda: logical_qubits.apply(mapping))
            physical_qubits_int = self.track_time(
                "physical_qubits_int", lambda: isl_set_to_python_list(physical_qubits))
            swap_candidate_list = self.track_time(
                "swap_candidate_list", lambda: self.candidate_swaps(physical_qubits_int))

            total = 0
            for swap_gate in swap_candidate_list:
                temp_mapping = self.update_mapping(
                    swap_gate[0], mapping)
                temp_mapping_dict = {k: v for k,
                                     v in self.mapping_dict.items()}
                Q1, Q2 = swap_gate[1]
                q1 = self.reverse_mapping_dict.get(Q1, None)
                q2 = self.reverse_mapping_dict.get(Q2, None)
                if q1:
                    temp_mapping_dict[q1] = Q2
                if q2:
                    temp_mapping_dict[q2] = Q1

                start = time.time()
                swap_gate_score = decay_poly_heuristic2(
                    self.front_layer, self.extended_layer, temp_mapping_dict, self.distance_matrix, self.access_dict, self.decay_parameter, (swap_gate[1][0], swap_gate[1][1]))
                total += time.time() - start

                heuristic_score.update(
                    {swap_gate[0]: (swap_gate_score, swap_gate[1])})

            self.instruction_times["for_inside_apply_heuristic"] += total
            min_score_swap_gate, min_gate = self.find_min_score_swap_gate(
                heuristic_score, verbose=verbose)

            mapping = self.update_mapping(
                min_score_swap_gate, mapping)

            Q1, Q2 = min_gate[0], min_gate[1]
            q1 = self.reverse_mapping_dict.get(Q1, None)
            q2 = self.reverse_mapping_dict.get(Q2, None)
            if q1:
                self.mapping_dict[q1] = Q2
            self.reverse_mapping_dict[Q2] = q1
            if q2:
                self.mapping_dict[q2] = Q1
            self.reverse_mapping_dict[Q1] = q2

            if verbose > 2:
                print("     chosen swap gate :", min_score_swap_gate)
                print("*"*50)

            # newH = lookahead_heuristic(front_layer_gates,dag,0.5,access,self.distance_matrix,mapping)
            # print("the improvment : ",H0 -newH)
            self.decay_parameter[min_gate[0]] += 0.001
            self.decay_parameter[min_gate[1]] += 0.001

            number_swap = 1
            return number_swap, mapping

        heuristic_score = dict()
        qubits = best_node.apply(access)
        logical_q1, logical_q2 = qubits.lexmin(), qubits.lexmax()

        physical_q1, physical_q2 = logical_q1.apply(mapping).as_set().dim_max_val(
            0).to_python(), logical_q2.apply(mapping).as_set().dim_max_val(0).to_python()

        if huristic_method == "single-decay":
            swap_candidate_list = self.swap_mapping[physical_q1] + \
                self.swap_mapping[physical_q2]
            for swap_gate in swap_candidate_list:
                temp_mapping = self.update_mapping(
                    swap_gate[0], mapping)
                swap_gate_score = decay_poly_heuristic(
                    self.isl_front_layer, dag, temp_mapping, self.distance_matrix, access, self.decay_parameter, (swap_gate[1][0], swap_gate[1][1]))
                heuristic_score.update(
                    {swap_gate[0]: (swap_gate_score, swap_gate[1])})

            min_score_swap_gate, min_gate = self.find_min_score_swap_gate(
                heuristic_score)
            mapping = self.update_mapping(
                min_score_swap_gate, mapping)
            self.decay_parameter[min_gate[0]] += 0.01
            self.decay_parameter[min_gate[1]] += 0.01

            number_swap = 1
            return number_swap, mapping

        if huristic_method == "multi-layer-decay":
            swap_candidate_list = self.swap_mapping[physical_q1] + \
                self.swap_mapping[physical_q2]
            for swap_gate in swap_candidate_list:
                temp_mapping = self.update_mapping(
                    swap_gate[0], mapping)
                swap_gate_score = multi_layer_poly_heuristic(
                    self.isl_front_layer, dag, temp_mapping, self.distance_matrix, access, self.decay_parameter, (swap_gate[1][0], swap_gate[1][1]))
                heuristic_score.update(
                    {swap_gate[0]: (swap_gate_score, swap_gate[1])})

            min_score_swap_gate, min_gate = self.find_min_score_swap_gate(
                heuristic_score)
            mapping = self.update_mapping(
                min_score_swap_gate, mapping)
            number_swap = 1
            self.decay_parameter[min_gate[0]] += 0.01
            self.decay_parameter[min_gate[1]] += 0.01

            return number_swap, mapping

        if huristic_method == "poly-paths":
            swap_candidate_list = self.all_swap_mappings[(
                physical_q1, physical_q2)]
            for swap_gate in swap_candidate_list:
                temp_mapping = self.update_mapping(
                    swap_gate[0], mapping)
                swap_gate_score = paths_poly_heuristic(
                    self.isl_front_layer, dag, temp_mapping, self.distance_matrix, access, swap_gate[1])
                heuristic_score.update({swap_gate[0]: swap_gate_score})

            min_score_swap_gate, _ = self.find_min_score_swap_gate(
                heuristic_score, swap_candidate_list)
            mapping = self.update_mapping(
                min_score_swap_gate[0], mapping)
            number_swap = min_score_swap_gate[1]

            return number_swap, mapping

    def candidate_swaps(self, active_qubits):

        candidates = []
        active_set = set(active_qubits)

        for u, v in self.coupling_graph.edges():
            if u in active_set or v in active_set:

                candidate = None
                if u in active_set:
                    candidate = (u, v)
                else:
                    candidate = (v, u)
                map_str = f"[{u}] -> [{v}];[{v}] -> [{u}]"
                candidates.append((isl.Map("{"+map_str+"}"), candidate))

        return candidates

    def extract_ready_to_execute_gate_list(self, access, mapping):
        ready_to_execute_gates_list = []

        front_layer_gates_list = self.front_layer
        for gate in front_layer_gates_list:
            q1, q2 = self.access_dict[gate]
            Q1, Q2 = self.mapping_dict[q1], self.mapping_dict[q2]

            if (Q1, Q2) in self.backend_connections or (Q2, Q1) in self.backend_connections:
                ready_to_execute_gates_list.append(gate)

        isl_ready_to_execute_gates = list_to_isl_set(
            ready_to_execute_gates_list)
        return isl_ready_to_execute_gates, ready_to_execute_gates_list

    def find_best_node(self, dag, with_transitive):

        if with_transitive and self.isl_front_layer.as_set().count_val().to_python() != 1:
            best_val, best_node = -1, None
            transitive_closure = dag.transitive_closure(
            )[0].intersect_domain(self.isl_front_layer)

            def evaluate_gate(point):
                nonlocal best_val, best_node
                gate = point.to_set()
                try:
                    dep = gate.apply(
                        transitive_closure).as_set().count_val().to_python()
                except:
                    dep = 0
                if dep > best_val:
                    best_val = dep
                    best_node = gate

            self.isl_front_layer.foreach_point(
                lambda point: evaluate_gate(point))

        else:
            best_node = self.isl_front_layer.sample()

        return best_node

    def find_min_score_swap_gate(self, heuristic_score, swap_candidate_list=None, verbose=0, epsilon=1e-10):
        if swap_candidate_list:
            all_scores = list(heuristic_score.values())

            min_score = min(all_scores)
            min_score_swap_gate = swap_candidate_list[all_scores.index(
                min_score)]
            return min_score_swap_gate, None
        else:
            random.seed(21)
            min_score = float('inf')
            best_swaps = []

            for swap, (score, gate) in heuristic_score.items():
                if verbose > 2:
                    print("     swap gate :", swap)
                    print("     score :", score)
                    print("-"*50)
                if score - min_score < -epsilon:
                    # Found a significantly lower score: update min_score and reset best_swaps
                    min_score = score
                    best_swaps = [(swap, (score, gate))]
                elif abs(score - min_score) <= epsilon:
                    # Score is within epsilon of the min_score: add it to the list
                    best_swaps.append((swap, (score, gate)))

            best_swaps.sort()
            selected_swap, (_, selected_gate) = random.choice(best_swaps)
            # print([(bs[1], bs[0]) for _, bs in heuristic_score.items()], '--> ', selected_gate)
            return selected_swap, selected_gate

    def update_mapping(self, swap_gate, mapping):
        if swap_gate.is_empty():
            return mapping
        other_mapping = mapping.subtract_range(swap_gate.domain())
        return mapping.apply_range(swap_gate).union(other_mapping)

    def is_gate_executable(self, gate, access, mapping) -> bool:

        logical_qubits = gate.apply(access)
        physical_qubits = logical_qubits.apply(mapping)

        q1, q2 = isl_set_to_python_list(physical_qubits)
        return (q1, q2) in self.backend_connections or (q2, q1) in self.backend_connections

    def get_initial_mapping(self, method="sabre"):
        if method == "random":
            return get_poly_initial_mapping(self.coupling_graph)
        elif method == "sabre":
            circuit = QuantumCircuit.from_qasm_str(self.data["qasm_code"])
            dag_circuit = circuit_to_dag(circuit)
            coupling_map = CouplingMap(self.backend_connections)
            sabre_layout = SabreLayout(coupling_map, seed=21)
            sabre_layout.run(dag_circuit)

            layout = sabre_layout.property_set["layout"]

            return ploy_initial_mapping(layout, self.num_qubit)

    def run(self, num_iter=1, chunk_size=None, with_transitive=False, heuristic_method="single-decay", verbose=0):
        min_swap = float('inf')
        mapping, self.mapping_dict = self.get_initial_mapping()
        self.reverse_mapping_dict = {
            v: k for k, v in self.mapping_dict.items()}

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
                filter_domain = isl.Set(
                    f"{{ [i] : {chunk}<= i < {chunk + chunk_size} }}")
                new_access = temp_access.intersect_domain(filter_domain)
                new_schedule = temp_schedule.intersect_range(filter_domain)
                new_dag = dag.intersect_domain(
                    filter_domain).intersect_range(filter_domain)

                self.isl_front_layer, self.front_layer = get_front_layer(
                    new_dag, new_schedule)

                swap_count, mapping = self.execute_sabre_algorithm(
                    new_access, mapping, new_dag, with_transitive, heuristic_method, verbose)

                total_swaps += swap_count
                chunk += chunk_size

                if verbose == 2:
                    print(f"total swaps in chunk {chunk} is ", total_swaps)

            if verbose == 2:
                print("*"*50)
                print(f"total swaps in iteration {i} is ", total_swaps)
                print("*"*50)

            min_swap = min(min_swap, total_swaps)
        return min_swap
