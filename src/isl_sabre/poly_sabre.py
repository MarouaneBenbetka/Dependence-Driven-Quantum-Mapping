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


class POLY_SABRE():
    def __init__(self, edges, data) -> None:

        self.edges = edges
        self.data = data
        self.coupling_graph = nx.Graph()
        self.coupling_graph.add_edges_from(edges)
        self.distance_matrix = get_distance_matrix(self.coupling_graph)
        self.num_qubit = len(self.distance_matrix[0])
        self.disconnected_edges = extract_disconnected_edges_map(edges)
        self.neighbours = extract_neighbourss_map(edges)
        self.physical_qubits_domain = isl.Set(
            "{ [i]:  0 <= i <  %d }" % self.num_qubit)
        self.all_swap_mappings = generate_all_swaps_mapping(
            self.coupling_graph, self.physical_qubits_domain)
        self.swap_mapping = generate_all_neighbours_mapping(
            self.coupling_graph)
        self.qops, self.read_dep, self.access, self.reverse_access, self.schedule, self.reverse_schedule = read_data(
            self.data)
        self.decay_parameter = [0.01 for _ in range(self.num_qubit)]
        self.distance_map = distance_map(self.distance_matrix)

    def execute_sabre_algorithm(self, front_layer_gates, access, initial_mapping, dag, with_transitive, huristic_method):
        number_swap = 0
        total_executed_gates = 0
        total_gates = self.count_number_gates(dag)

        with tqdm(total=total_gates, desc="Executing Gates", mininterval=0.1) as pbar:
            while not front_layer_gates.is_empty():

                execute_gate_list = self.check_excute_gate(
                    front_layer_gates, access, initial_mapping)

                if not execute_gate_list.is_empty():
                    front_layer_gates = front_layer_gates.subtract(
                        execute_gate_list)
                    waiting_nodes = execute_gate_list.apply(dag)
                    dag = dag.subtract_domain(execute_gate_list)
                    waiting_nodes = waiting_nodes.subtract(dag.range())
                    front_layer_gates = front_layer_gates.union(waiting_nodes)

                    self.decay_parameter = [
                        0.01 for _ in range(self.num_qubit)]
                    executed_gates_count = execute_gate_list.as_set().count_val().to_python()
                    total_executed_gates += executed_gates_count
                    pbar.update(executed_gates_count)

                else:
                    best_node = self.find_best_node(
                        front_layer_gates, dag, with_transitive)
                    local_swap, initial_mapping = self.apply_heuristic(
                        front_layer_gates, access, initial_mapping, dag, best_node, huristic_method)
                    number_swap += local_swap

        return number_swap, initial_mapping

    def count_number_gates(self, dag):
        return dag.domain().union(dag.range()).as_set().count_val().to_python()

    def apply_heuristic(self, front_layer_gates, access, initial_mapping, dag, best_node, huristic_method):
        heuristic_score = dict()
        qubits = best_node.apply(access)
        logical_q1, logical_q2 = qubits.lexmin(), qubits.lexmax()

        physical_q1, physical_q2 = logical_q1.apply(initial_mapping).as_set().dim_max_val(
            0).to_python(), logical_q2.apply(initial_mapping).as_set().dim_max_val(0).to_python()

        if huristic_method == "decay":
            swap_candidate_list = self.swap_mapping[physical_q1] + \
                self.swap_mapping[physical_q2]
            for swap_gate in swap_candidate_list:
                temp_mapping = self.update_mapping(
                    swap_gate[0], initial_mapping)
                swap_gate_score = Poly_heuristic_function_decay(
                    front_layer_gates, dag, temp_mapping, self.distance_matrix, access, self.decay_parameter, (swap_gate[1][0], swap_gate[1][1]))
                heuristic_score.update(
                    {swap_gate[0]: (swap_gate_score, swap_gate[1])})

            min_score_swap_gate, min_gate = self.find_min_score_swap_gate(
                heuristic_score)
            initial_mapping = self.update_mapping(
                min_score_swap_gate, initial_mapping)
            number_swap = 1
            self.decay_parameter[min_gate[0]] += 0.01
            self.decay_parameter[min_gate[1]] += 0.01

            return number_swap, initial_mapping

        else:

            swap_candidate_list = self.all_swap_mappings[(
                physical_q1, physical_q2)]
            for swap_gate in swap_candidate_list:
                temp_mapping = self.update_mapping(
                    swap_gate[0], initial_mapping)
                swap_gate_score = Poly_heuristic_function(
                    front_layer_gates, dag, temp_mapping, self.distance_matrix, access, swap_gate[1])
                heuristic_score.update({swap_gate[0]: swap_gate_score})

            min_score_swap_gate, _ = self.find_min_score_swap_gate(
                heuristic_score, swap_candidate_list)
            initial_mapping = self.update_mapping(
                min_score_swap_gate[0], initial_mapping)
            number_swap = min_score_swap_gate[1]

            return number_swap, initial_mapping

    def check_excute_gate(self, front_layer_gates, access, initial_mapping):
        execute_gate_list = isl.UnionSet("{}")

        def process_gate(gate):
            if self.is_gate_executable(gate, access, initial_mapping):
                nonlocal execute_gate_list
                execute_gate_list = execute_gate_list.union(gate)

        front_layer_gates.foreach_point(
            lambda point: process_gate(point.to_set()))

        return execute_gate_list

    def find_best_node(self, front_layer_gates, dag, with_transitive):

        if with_transitive and front_layer_gates.as_set().count_val().to_python() != 1:
            best_val, best_node = -1, None
            transitive_closure = dag.transitive_closure(
            )[0].intersect_domain(front_layer_gates)

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

            front_layer_gates.foreach_point(lambda point: evaluate_gate(point))

        else:
            best_node = front_layer_gates.sample()

        return best_node

    def find_min_score_swap_gate(self, heuristic_score, swap_candidate_list=None):
        if swap_candidate_list:
            all_scores = list(heuristic_score.values())

            min_score = min(all_scores)
            min_score_swap_gate = swap_candidate_list[all_scores.index(
                min_score)]
            return min_score_swap_gate, None
        else:
            min_score = float('inf')
            min_score_swap_gate = None
            min_gate = None
            for swap_gate, (score, gate) in heuristic_score.items():
                if score < min_score:
                    min_score = score
                    min_score_swap_gate = swap_gate
                    min_gate = gate
            return min_score_swap_gate, min_gate

    def update_mapping(self, swap_gate, initial_mapping):
        if swap_gate.is_empty():
            return initial_mapping
        other_mapping = initial_mapping.subtract_range(swap_gate.domain())
        return initial_mapping.apply_range(swap_gate).union(other_mapping)

    def is_gate_executable(self, gate, access, initial_mapping) -> bool:

        logical_qubits = gate.apply(access)
        physical_qubits = logical_qubits.apply(initial_mapping)
        q1, q2 = physical_qubits.lexmin().as_set(), physical_qubits.lexmax().as_set()
        return q1.flat_product(q2).intersect(self.disconnected_edges).is_empty()

    def get_initial_mapping(self, method="sabre"):
        if method == "random":
            return get_poly_initial_mapping(self.coupling_graph)
        elif method == "sabre":
            circuit = QuantumCircuit.from_qasm_str(self.data["qasm_code"])
            dag_circuit = circuit_to_dag(circuit)
            coupling_map = CouplingMap(self.edges)
            sabre_layout = SabreLayout(coupling_map)
            sabre_layout.run(dag_circuit)

            layout = sabre_layout.property_set["layout"]

            return ploy_initial_mapping(layout)

    def run(self, initial_mapping, num_iter=3, chunks=None, with_transitive=True, huristic_method=None, verbose=False):
        min_swap = float('inf')
        temp_mapping = initial_mapping
        if chunks is None:
            chunks = self.qops
        for i in range(num_iter):
            total_swaps = 0
            transh = 0
            if i % 2 == 0:
                temp_schedule = self.schedule
                temp_access = self.access
            else:
                temp_schedule = self.reverse_schedule
                temp_access = self.reverse_access

            while transh < self.qops:
                filter_domain = isl.Map(
                    f"{{ [i] -> [i] : {transh}<= i < {transh + chunks} }}")
                new_access = temp_access.apply_domain(filter_domain)
                news_schedule = temp_schedule.apply_range(filter_domain)
                dag, front_layer = generate_dag_front_layer(
                    self.read_dep, news_schedule)
                swap_count, temp_mapping = self.execute_sabre_algorithm(
                    front_layer, new_access, temp_mapping, dag, with_transitive, huristic_method)
                total_swaps += swap_count
                transh += chunks
                if verbose:
                    print(f"total swaps in transh {transh} is ", total_swaps)

            if verbose or True:
                print("*"*50)
                print(f"total swaps in iteration {i} is ", total_swaps)
                print("*"*50)

            min_swap = min(min_swap, total_swaps)
        return min_swap
