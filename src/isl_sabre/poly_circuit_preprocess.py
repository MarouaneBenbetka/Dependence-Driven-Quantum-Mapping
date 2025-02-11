from networkx import Graph
import random
import islpy as isl
import networkx as nx
import itertools
import numpy as np
from .dag import DAG
from .isl_to_python import isl_map_to_dict_optimized2, dict_to_isl_map


def get_poly_initial_mapping(coupling_graph: Graph) -> dict:

    physical_qubits = list(coupling_graph.nodes())
    num_qubit = max(physical_qubits)
    logical_qubits = list(range(num_qubit+1))
    random.shuffle(physical_qubits)
    map_str = ""
    for logical_qubit, physical_qubit in zip(logical_qubits, physical_qubits):
        map_str += f"q[{logical_qubit}] -> [{physical_qubit}];"
    return isl.Map("{"+map_str+"}")


def ploy_initial_mapping(layout) -> dict:
    map_str = ""
    for v in layout._v2p:
        if v._register._name != "ancilla":
            map_str += f"q[{v._index}] -> [{layout._v2p[v]}];"

    return isl.Map("{"+map_str+"}")


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
    paths = list(nx.all_simple_paths(graph, source, target))
    swap_mappings = []
    for path in paths:
        for connect in range(len(path)-1):
            swap_mappings.append(
                (swaps_to_isl_map(path, connect, physical_qubits_domain), len(path)-2, path))
    return swap_mappings


def get_distance_matrix(graph):

    nodes = list(graph.nodes)
    num_nodes = len(nodes)
    distance_matrix = np.zeros((num_nodes, num_nodes))

    for i, node_i in enumerate(nodes):
        for j, node_j in enumerate(nodes):
            if i != j:
                try:
                    distance_matrix[i, j] = nx.shortest_path_length(
                        graph, source=i, target=j)
                except nx.NetworkXNoPath:
                    distance_matrix[i, j] = float(
                        'inf')  # No path between nodes
    return distance_matrix


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

    return front_layer.union(single_nodes)


def distance_map(distance_matrix):
    n = len(distance_matrix)
    map_str = ""
    for i in range(n):
        for j in range(i+1, n):
            map_str += f"[{i},{j}]->[{int(distance_matrix[i,j])}];"
    return isl.Map("{"+map_str+"}")


def generate_dag(access,write):
    _map = isl_map_to_dict_optimized2(access)
    _write = isl_map_to_dict_optimized2(write)

    dag = DAG(num_qubits=access.range().dim_max_val(
        0).to_python() + 1, nodes_dict=_map,write=_write)
    return dict_to_isl_map(dag.successors)
