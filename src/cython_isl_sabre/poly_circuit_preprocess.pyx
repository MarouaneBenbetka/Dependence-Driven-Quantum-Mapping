# poly_circuit_preprocess.pyx
# cython: language_level=3, boundscheck=False, wraparound=False

import random
import time
import itertools
import numpy as np
import islpy as isl
import networkx as nx

# Assuming your package structure compiles dag.pyx and python_to_isl.pyx as modules
from .dag import DAG
from .isl_to_python import isl_map_to_dict_optimized2, dict_to_isl_map

def get_poly_initial_mapping(int num_qubit) -> tuple:
    """
    Generates an initial mapping by shuffling physical qubits.
    Returns a tuple (mapping, elapsed_time).
    """
    physical_qubits = list(range(num_qubit+1))
    logical_qubits = list(range(num_qubit+1))
    random.shuffle(physical_qubits)
    start_time = time.time()
    map_str = ""
    for logical_qubit, physical_qubit in zip(logical_qubits, physical_qubits):
        map_str += f"q[{logical_qubit}] -> [{physical_qubit}];"
    mapping = isl.Map("{" + map_str + "}")
    return mapping, time.time() - start_time

def ploy_initial_mapping(layout) -> isl.Map:
    """
    Generates an initial mapping from a layout object.
    Expects layout._v2p to be a dictionary where each key v has attributes:
      - v._index : index of the logical qubit
      - v._register._name : register name (skipping if 'ancilla')
    """
    map_str = ""
    for v in layout._v2p:
        if v._register._name != "ancilla":
            map_str += f"q[{v._index}] -> [{layout._v2p[v]}];"
    return isl.Map("{" + map_str + "}")

def extract_disconnected_edges_map(edges):
    """
    Given a list of edge pairs, returns an ISL set of the disconnected edges.
    """
    edges_str = "{" + ";".join([f'[{src},{dst}]' for src, dst in edges]) + "}"
    connected_edges_set = isl.Set(edges_str)
    num_qubits = max(max(edge) for edge in edges)
    all_connections = isl.Set(f"{{ [i,j] : 0 <= i <= {num_qubits} and 0 <= j <= {num_qubits} }}")
    disconnected_edges = all_connections.subtract(connected_edges_set).coalesce()
    return disconnected_edges

def extract_neighbourss_map(edges):
    """
    Given a list of edges, returns an ISL map that contains both directions.
    """
    edges_str = "{" + ";".join([f'[{src}] -> [{dst}];[{dst}] -> [{src}]' for src, dst in edges]) + "}"
    return isl.Map(edges_str)

def generate_all_swaps_mapping(graph, physical_qubits_domain):
    """
    For every unordered pair of nodes in graph, generate swap mappings.
    """
    pathes = {}
    node_pairs = list(itertools.combinations(graph.nodes, 2))
    for node1, node2 in node_pairs:
        pathes[(node1, node2)] = generate_swap_mappings(graph, node1, node2, physical_qubits_domain)
        pathes[(node2, node1)] = generate_swap_mappings(graph, node2, node1, physical_qubits_domain)
    return pathes

def generate_all_neighbours_mapping(graph):
    """
    For every node in graph, generate a mapping of its neighbours.
    """
    neighbours_map = {}
    for node in graph.nodes:
        neighbours_map[node] = generate_neighbours_map(graph, node)
    return neighbours_map

def generate_neighbours_map(graph, node):
    """
    For a given node, generate a list of swap mappings with each neighbour.
    """
    neighbours = list(graph.neighbors(node))
    swaps = []
    for neighbour in neighbours:
        map_str = f"[{node}] -> [{neighbour}];[{neighbour}] -> [{node}]"
        swaps.append((isl.Map("{" + map_str + "}"), (node, neighbour)))
    return swaps

def swaps_to_isl_map(list path, int connect, physical_qubits_domain):
    """
    Given a path (list of nodes) and a connection index, generates a swap mapping.
    """
    if len(path) <= 2:
        return isl.UnionMap("{}")
    cdef int n = len(path)
    cdef str map_str = f"[{path[0]}]->[{path[connect]}]"
    map_str += f";[{path[n-1]}]->[{path[connect+1]}]"
    for i in range(1, connect + 1):
        map_str += f";[{path[i]}]->[{path[i-1]}]"
    for i in range(connect + 1, n-1):
        map_str += f";[{path[i]}]->[{path[i+1]}]"
    cdef object partial_map = isl.Map("{" + map_str + "}")
    cdef object swap_domain = partial_map.domain()
    cdef object swap_complement_domain = physical_qubits_domain.subtract(swap_domain)
    cdef object identity = isl.Map("{ [i]-> [i] }")
    cdef object physical_map = partial_map.union(identity.intersect_domain(swap_complement_domain)).as_map().coalesce()
    return physical_map

def generate_swap_mappings(graph, source, target, physical_qubits_domain):
    """
    Generate swap mappings for the first k shortest simple paths between source and target.
    """
    cdef object path_generator = nx.shortest_simple_paths(graph, source, target)
    swap_mappings = []
    cdef int k = 1
    for path in itertools.islice(path_generator, k):
        for connect in range(len(path)-1):
            swap_mappings.append((swaps_to_isl_map(path, connect, physical_qubits_domain), len(path)-2, path))
    return swap_mappings

def get_distance_matrix(graph):
    """
    Constructs a distance matrix as a dictionary indexed by ISL sets (points) for each node.
    """
    distance_dict = {}
    for i in graph.nodes():
        point_i = isl.Set("{[" + str(i) + "]}")
        distance_dict[point_i] = {}
        for j in graph.nodes():
            point_j = isl.Set("{[" + str(j) + "]}")
            if i != j:
                try:
                    distance = nx.shortest_path_length(graph, source=i, target=j)
                except nx.NetworkXNoPath:
                    distance = float('inf')
                distance_dict[point_i][point_j] = distance
    return distance_dict

def get_dag(read_dep, schedule):
    """
    Computes a DAG from dependency maps.
    """
    scheduled_dep = read_dep.apply_domain(schedule)
    composed_dep = scheduled_dep.apply_range(scheduled_dep.reverse())
    dag = composed_dep.intersect(isl.Map("{ [i] -> [j] : i < j }"))
    return dag

def get_front_layer(dependencies, schedule):
    """
    Returns the front layer of operations given dependencies and schedule maps.
    """
    cdef object domain = dependencies.domain()
    cdef object rnge = dependencies.range()
    cdef object front_layer = domain.subtract(rnge)
    cdef object single_nodes = schedule.range().subtract(domain.union(rnge))
    return front_layer.union(single_nodes)

def compute_circuit_depth(dependencies):
    """
    Computes the circuit depth by iteratively peeling off front layers.
    """
    cdef int current_depth = 1
    cdef object remaining_dependencies = dependencies
    while not remaining_dependencies.is_empty():
        front_layer = remaining_dependencies.domain().subtract(remaining_dependencies.range())
        remaining_dependencies = remaining_dependencies.subtract_domain(front_layer)
        current_depth += 1
    return current_depth

def distance_map(distance_matrix):
    """
    Constructs an ISL map from a distance matrix (e.g. a numpy array).
    """
    cdef int n = len(distance_matrix)
    cdef str map_str = ""
    for i in range(n):
        for j in range(i+1, n):
            map_str += f"[{i},{j}]->[{int(distance_matrix[i,j])}];"
    return isl.Map("{" + map_str + "}")

def generate_dag(read, write, bint no_read_dep):
    """
    Generates a DAG by converting dependency maps using helper functions.
    """
    cdef dict _map = isl_map_to_dict_optimized2(read)
    cdef dict _write = isl_map_to_dict_optimized2(write)
    cdef int num_qubits = read.range().dim_max_val(0).to_python() + 1
    dag_obj = DAG(num_qubits=num_qubits, nodes_dict=_map, write=_write, no_read_dep=no_read_dep)
    return dict_to_isl_map(dict(dag_obj.successors))
