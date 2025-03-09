from networkx import Graph
import random
import islpy as isl
import networkx as nx
import itertools
import numpy as np
from .dag import DAG
from .isl_to_python import isl_map_to_dict_optimized, dict_to_isl_map, isl_set_to_python_list, isl_set_to_python_set, parse_mapping
import time


def get_poly_initial_mapping(num_qubit: Graph) -> dict:
    mapping_dict = {}
    physical_qubits = list(range(num_qubit+1))
    logical_qubits = list(range(num_qubit+1))
    random.shuffle(physical_qubits)
    map_str = ""
    for logical_qubit, physical_qubit in zip(logical_qubits, physical_qubits):
        map_str += f"q[{logical_qubit}] -> [{physical_qubit}];"
        mapping_dict[logical_qubit] = physical_qubit
    mapping = isl.Map("{"+map_str+"}")

    return mapping, mapping_dict


def ploy_initial_mapping(layout, num_qubits) -> dict:
    mapping_dict = {}
    map_str = ""
    for v in layout._v2p:
        if v._register._name != "ancilla":
            map_str += f"q[{v._index}] -> [{layout._v2p[v]}];"
            mapping_dict[v._index] = layout._v2p[v]

    return isl.Map("{"+map_str+"}"), mapping_dict


def extract_disconnected_edges_map(edges):

    edges_str = "{" + ";".join([f'[{src},{dst}]' for src, dst in edges]) + "}"
    connected_edges_set = isl.Set(edges_str)
    num_qubits = max(max(edge) for edge in edges)

    all_connections = isl.Set(
        f"{{ [i,j] : 0 <= i <= {num_qubits} and 0 <= j <= {num_qubits} }}")

    disconnected_edges = all_connections.subtract(
        connected_edges_set).coalesce()

    return disconnected_edges


def extract_neighbourss_map(edges):
    edges_str = "{" + \
        ";".join(
            [f'[{src}] -> [{dst}];[{dst}] -> [{src}]' for src, dst in edges]) + "}"
    return isl.Map(edges_str)


def generate_all_swaps_mapping(graph, physical_qubits_domain):
    pathes = {}
    node_pairs = list(itertools.combinations(graph.nodes, 2))
    for node1, node2 in node_pairs:
        pathes[(node1, node2)] = generate_swap_mappings(
            graph, node1, node2, physical_qubits_domain)
        pathes[(node2, node1)] = generate_swap_mappings(
            graph, node2, node1, physical_qubits_domain)
    return pathes


def generate_all_neighbours_mapping(graph):
    neighbours_map = {}
    for node in graph.nodes:
        neighbours_map[node] = generate_neighbours_map(graph, node)
    return neighbours_map


def generate_neighbours_map(graph, node):
    neighbours = list(graph.neighbors(node))
    swaps = []
    for neighbour in neighbours:
        map_str = f"[{node}] -> [{neighbour}];[{neighbour}] -> [{node}]"
        swaps.append((isl.Map("{"+map_str+"}"), (node, neighbour)))

    return swaps


def swaps_to_isl_map(path: list, connect, physical_qubits_domain):

    if len(path) <= 2:
        return isl.UnionMap("{}")

    n = len(path)

    map_str = f"[{path[0]}]->[{path[connect]}]"
    map_str += f";[{path[n-1]}]->[{path[connect+1]}]"

    for i in range(1, connect + 1):
        map_str += f";[{path[i]}]->[{path[i-1]}]"

    for i in range(connect + 1, n-1):
        map_str += f";[{path[i]}]->[{path[i+1]}]"

    partial_map = isl.Map("{"+map_str+"}")

    swap_domain = partial_map.domain()
    swap_complement_domain = physical_qubits_domain.subtract(swap_domain)

    physical_map = partial_map.union(isl.Map(
        "{ [i]-> [i] }").intersect_domain(swap_complement_domain)).as_map().coalesce()
    return physical_map


def generate_swap_mappings(graph, source, target, physical_qubits_domain):
    path_generator = nx.shortest_simple_paths(graph, source, target)

    swap_mappings = []
    # Limit to only the first k shortest paths.
    k = 1
    for path in itertools.islice(path_generator, k):
        for connect in range(len(path)-1):
            swap_mappings.append(
                (swaps_to_isl_map(path, connect, physical_qubits_domain), len(path)-2, path))
    return swap_mappings


def get_distance_matrix(graph):

    distance_dict = [[0] * len(graph.nodes())
                     for _ in range(len(graph.nodes()))]
    for i in graph.nodes():
        for j in graph.nodes():
            if i != j:
                try:
                    distance = nx.shortest_path_length(
                        graph, source=i, target=j)
                except nx.NetworkXNoPath:
                    distance = float('inf')  # No path between nodes
                distance_dict[i][j] = distance
    return distance_dict


def get_dag(read_dep, schedule):
    scheduled_dep = read_dep.apply_domain(schedule)
    composed_dep = scheduled_dep.apply_range(scheduled_dep.reverse())
    dag = composed_dep.intersect(isl.Map("{ [i] -> [j] : i < j }"))

    return dag


def get_front_layer(dependencies, schedule):
    domain = dependencies.domain()
    range = dependencies.range()
    front_layer = domain.subtract(range)

    single_nodes = schedule.range().subtract(domain.union(range))

    isl_front_layer = front_layer.union(single_nodes)

    return isl_front_layer, isl_set_to_python_set(isl_front_layer)


def compute_circuit_depth(dependencies):
    current_depth = 1
    remaining_dependencies = dependencies
    while not remaining_dependencies.is_empty():
        front_layer = remaining_dependencies.domain().subtract(
            remaining_dependencies.range())
        remaining_dependencies = remaining_dependencies.subtract_domain(
            front_layer)
        current_depth += 1
    return current_depth


def distance_map(distance_matrix):
    n = len(distance_matrix)
    map_str = ""
    for i in range(n):
        for j in range(i+1, n):
            map_str += f"[{i},{j}]->[{int(distance_matrix[i,j])}];"
    return isl.Map("{"+map_str+"}")


def generate_dag(read, write, no_read_dep, transitive_reduction=False):
    _map = isl_map_to_dict_optimized(read)
    if no_read_dep:
        _write = parse_mapping(write.as_map().to_str())
    else:
        _write = None
    dag = DAG(num_qubits=read.range().dim_max_val(0).to_python() + 1,
              nodes_dict=_map, write=_write, no_read_dep=no_read_dep, transitive_reduction=transitive_reduction)
    isl_dag = dict_to_isl_map(dag.successors)
    return isl_dag, dag.successors, dag.predecessors
