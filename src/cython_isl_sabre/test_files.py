# test_functions.py

import islpy as isl
from dag import DAG
import isl_to_python
import python_to_isl
import poly_heuristic as ph
import poly_circuit_preprocess as pcp
import poly_circuit_utils as pcu
import poly_sabre as ps
import networkx as nx
import numpy as np
import time
from qiskit.providers.fake_provider import Fake27QPulseV1, Fake5QV1, Fake20QV1


def test_dag():
    print("=== Testing DAG ===")
    # Create a simple DAG:
    nodes_dict = {0: [0, 1], 1: [1, 2], 2: [0, 2]}
    write = {0: [1], 1: [2], 2: [2]}
    # Use no_read_dep=True for one branch of your logic.
    d = DAG(num_qubits=3, nodes_dict=nodes_dict, write=write, no_read_dep=True)

    sorted_nodes = d.top_sort()
    print("Topologically sorted nodes:", sorted_nodes)
    print("DAG structure:")
    d.print_dag()
    print()


def test_isl_to_python():
    print("=== Testing ISL to Python Functions ===")

    # Test isl_set_to_python_list, isl_set_to_list_points, and collect_points_from_set:
    s = isl.Set("{ [0]; [1]; [2] }")
    python_list = isl_to_python.isl_set_to_python_list(s)
    list_points = isl_to_python.isl_set_to_list_points(s)
    collected_points = isl_to_python.collect_points_from_set(s)

    print("isl_set_to_python_list output:", python_list)
    print("isl_set_to_list_points output:", list_points)
    print("collect_points_from_set output:", collected_points)
    print()

    # Create a finite map for testing.
    # This map has two points:
    # For i=0, j becomes 1; for i=1, j becomes 2.
    m = isl.Map("{ [i] -> [j] : (i = 0 or i = 1) and j = i + 1 }")

    python_dict = isl_to_python.isl_map_to_python_dict(m)
    dict_optimized = isl_to_python.isl_map_to_dict_optimized(m)
    dict_optimized2 = isl_to_python.isl_map_to_dict_optimized2(m)

    print("isl_map_to_python_dict output:", python_dict)
    print("isl_map_to_dict_optimized output:", dict_optimized)
    print("isl_map_to_dict_optimized2 output:", dict_optimized2)
    print()


def test_python_to_isl():
    print("=== Testing Python to ISL Functions ===")

    input_dict = {0: [1, 2], 1: [3]}
    isl_map = python_to_isl.dict_to_isl_map(input_dict)
    print("dict_to_isl_map output:")
    print(isl_map)
    print()

    input_list = [0, 1, 2]
    isl_set_from_list = python_to_isl.list_to_isl_set(input_list)
    print("list_to_isl_set output:")
    print(isl_set_from_list)
    print()

    isl_set_from_int = python_to_isl.int_to_isl_set(42)
    print("int_to_isl_set output:")
    print(isl_set_from_int)
    print()


def test_poly_heuristic():
    dummy_access = isl.Map("{[i] -> [i]}")
    dummy_dag = isl.Map("{[i] -> [i]}")
    dummy_mapping = isl.Map("{[i] -> [i]}")

    set0 = isl.Set("{[0]}")
    set1 = isl.Set("{[1]}")
    dummy_distance_matrix = {
        set0: {set0: 0, set1: 1},
        set1: {set0: 1, set1: 0},
    }

    F = isl.UnionSet("{[0]}")
    E = isl.UnionSet("{[1]}")

    # Dummy parameters for swaps and decay.
    swaps = 5
    decay_parameter = {"gate0": 0.5, "gate1": 0.7}
    gate = ("gate0", "gate1")
    print("=== Testing paths_poly_heuristic ===")
    result = ph.paths_poly_heuristic(F, dummy_dag, dummy_mapping,
                                     dummy_distance_matrix, dummy_access, swaps)
    print("paths_poly_heuristic result:", result)
    print()

    print("=== Testing decay_poly_heuristic ===")
    result = ph.decay_poly_heuristic(F, E, dummy_mapping,
                                     dummy_distance_matrix, dummy_access,
                                     decay_parameter, gate)
    print("decay_poly_heuristic result:", result)
    print()


def test_poly_circuit_preprocess():
    print("=== Testing poly_circuit_preprocess functions ===")

    # 1. Test get_poly_initial_mapping with an integer number of qubits.
    print("-- Testing get_poly_initial_mapping --")
    mapping, elapsed = pcp.get_poly_initial_mapping(4)
    print("Mapping:", mapping)
    print("Elapsed time:", elapsed)
    print()

    # 2. Test ploy_initial_mapping with a dummy layout.
    # print("-- Testing ploy_initial_mapping --")

    # 3. Test extract_disconnected_edges_map and extract_neighbourss_map.
    print("-- Testing extract_disconnected_edges_map and extract_neighbourss_map --")
    edges = [(0, 1), (1, 2)]
    disc_edges = pcp.extract_disconnected_edges_map(edges)
    neigh_map = pcp.extract_neighbourss_map(edges)
    print("Disconnected edges set:", disc_edges)
    print("Neighbours map:", neigh_map)
    print()

    # 4. Create a sample graph using networkx.
    G = nx.Graph()
    G.add_nodes_from([0, 1, 2, 3])
    G.add_edges_from([(0, 1), (1, 2), (2, 3)])
    # Create a dummy physical_qubits_domain as an ISL set.
    physical_qubits_domain = isl.Set("{[0:4]}")

    # 5. Test generate_all_swaps_mapping and generate_all_neighbours_mapping.
    print("-- Testing generate_all_swaps_mapping and generate_all_neighbours_mapping --")
    swaps_mapping = pcp.generate_all_swaps_mapping(G, physical_qubits_domain)
    neighbours_mapping = pcp.generate_all_neighbours_mapping(G)
    print("All swaps mapping:", swaps_mapping)
    print("All neighbours mapping:", neighbours_mapping)
    print()

    # 6. Test generate_neighbours_map for a specific node.
    print("-- Testing generate_neighbours_map for node 1 --")
    neigh_map_node = pcp.generate_neighbours_map(G, 1)
    print("Neighbours map for node 1:", neigh_map_node)
    print()

    # 7. Test swaps_to_isl_map with a sample path.
    print("-- Testing swaps_to_isl_map with sample path --")
    sample_path = [0, 1, 2, 3]
    swap_map = pcp.swaps_to_isl_map(sample_path, 1, physical_qubits_domain)
    print("Swaps to ISL map result:", swap_map)
    print()

    # 8. Test generate_swap_mappings for a pair of nodes.
    print("-- Testing generate_swap_mappings for nodes 0 and 3 --")
    swap_mappings = pcp.generate_swap_mappings(G, 0, 3, physical_qubits_domain)
    print("Swap mappings:", swap_mappings)
    print()

    # 9. Test get_distance_matrix on graph G.
    print("-- Testing get_distance_matrix on graph --")
    dist_matrix = pcp.get_distance_matrix(G)
    print("Distance matrix:", dist_matrix)
    print()

    # 10. Test get_dag, get_front_layer, compute_circuit_depth using dummy ISL maps.
    print("-- Testing get_dag, get_front_layer, compute_circuit_depth --")
    dummy_read_dep = isl.Map("{[0]->[1];[1]->[2]}")
    dummy_schedule = isl.Map("{[0]->[1];[1]->[2]}")
    dag_map = pcp.get_dag(dummy_read_dep, dummy_schedule)
    front_layer = pcp.get_front_layer(dag_map, dummy_schedule)
    depth = pcp.compute_circuit_depth(dag_map)
    print("DAG:", dag_map)
    print("Front layer:", front_layer)
    print("Circuit depth:", depth)
    print()

    # 11. Test distance_map using a numpy array.
    print("-- Testing distance_map using numpy array --")
    np_matrix = np.array([[0, 1, 2],
                          [1, 0, 1],
                          [2, 1, 0]])
    dist_map = pcp.distance_map(np_matrix)
    print("Distance map:", dist_map)
    print()

    # 12. Test generate_dag with dummy read and write maps.
    print("-- Testing generate_dag with dummy read and write maps --")
    nodes_dict = {0: [0, 1], 1: [1, 2], 2: [0, 2]}
    write = {0: [1], 1: [2], 2: [2]}

    nodes_dict_map = python_to_isl.dict_to_isl_map(nodes_dict)
    write_map = python_to_isl.dict_to_isl_map(write)

    generated_dag, _ = pcp.generate_dag(nodes_dict_map, write_map, False)
    print("Generated DAG:", generated_dag)
    print()


def test_poly_circuit_utils():
    json_file_path = "../../benchmarks/polyhedral/cases/backward.json"
    print("Reading JSON file from:", json_file_path)

    # Convert JSON data into ISL objects and additional info.
    data = pcu.json_file_to_isl(json_file_path)
    print("\nOutput of json_file_to_isl:")
    for key, value in data.items():
        print(f"{key}: {value}")

    # Process the data with read_data.
    result = pcu.read_data(data)
    print("\nOutput of read_data:")
    print(result)


def test_poly_sabre():
    edges = Fake27QPulseV1().configuration().coupling_map
    json_file_path = "../../benchmarks/polyhedral/queko-bss-16qbt/16QBT_500CYC_QSE_0.json"
    data = pcu.json_file_to_isl(json_file_path)
    poly_sabre = ps.POLY_SABRE(edges, data)
    start_time = time.time()
    swap_count = poly_sabre.run(heuristic_method="decay", verbose=1)
    total_time = time.time()-start_time
    print("Swap count :", swap_count)
    print("Total time :", total_time)


if __name__ == "__main__":
    # test_dag()
    # test_isl_to_python()
    # test_python_to_isl()
    # test_poly_heuristic()
    # test_poly_circuit_preprocess()
    # test_poly_circuit_utils()
    test_poly_sabre()
