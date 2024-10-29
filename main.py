import islpy as isl
from src.io_tools import *
from src.graph_tools import *
from src.swap_tools import *
import time 

def backend():
    physical_qubits_domain = isl.Set(f"{{ [i] : 0 <= i <= {100} }}")
    backend_graph = generate_2d_grid(num_rows=10, num_cols=10)

    backend_disconnected_edges =  extract_edges_map(backend_graph)
    shortest_paths = extract_shortest_paths(backend_graph, physical_qubits_domain)

    return backend_disconnected_edges, shortest_paths

backend_disconnected_edges , shortest_paths = backend()
def main(json_file_path):

    #json_file_path = 'benchmarks/polyhedral/queko-bss-20qbt/20QBT_100CYC_QSE_9.json'
    data = json_file_to_isl(json_file_path)
    domain, read_dep, access = filter_multi_qubit_gates(data["domain"], data["read_dependencies"], data["schedule"])
    if domain is None:
        return 0, 0, 0
    num_qubits = get_qubits_needed(read_dep)+1
    #physical_qubits_domain = isl.Set(f"{{ [i] : 0 <= i <= {num_qubits} }}")
    #backend_graph = generate_2d_grid(num_rows=10, num_cols=10)

    #backend_disconnected_edges =  extract_edges_map(backend_graph)
    #shortest_paths = extract_shortest_paths(backend_graph, physical_qubits_domain)


    mapping = isl.Map(f"{{ q[i] -> [i] : 0<=i<={num_qubits} }}")
    
    access = access.apply_range(mapping).coalesce()


    swap_count = 0

    iteration = 0
    
    access1 = access.lexmin().coalesce()
    access2 = access.lexmax().coalesce()
    transform_map = isl.Map(" { [[[a]->[b]] -> [c]] -> [[a] -> [[b]->[c]]]}").coalesce()

    global_start = time.time()

    #disconnection_time_global = 0
    #range_product_time = 0
    while not access1.is_empty():
        iteration += 1

        #start = time.time()

        # access1 , acces 2  => disconnection time

        # programme_access = access1.range_product(access2)
        programme_access = access1.domain_map().apply_range(access2).wrap().apply(transform_map).unwrap()
        
        #range_product_time += time.time() - start
        #print("range product time: ", time.time() - start)


        #start = time.time()
        disconnection_time = programme_access.intersect_range(backend_disconnected_edges).domain().lexmin()
        if disconnection_time.is_empty():
            break
        #disconnection_time_global += time.time() - start
        #print("disconnection time: ", time.time() - start)
            
        # start = time.time()
        q1 = access1.intersect_domain(disconnection_time).range().dim_max_val(0).to_python()
        q2 = access2.intersect_domain(disconnection_time).range().dim_max_val(0).to_python()
        # print("diconnected qubit finding ", time.time() - start)
        swap_count += shortest_paths[q1]['costs'][q2] -1
        # start = time.time()
        disconnection_time_point = disconnection_time.dim_max_val(0).to_python()
        new_domain = isl.Set(f"{{ [i] : i> {disconnection_time_point} }}") 

        # print("new domain time: ", time.time() - start)

        # start = time.time()
        access1 = access1.intersect_domain(new_domain)
        access2 = access2.intersect_domain(new_domain)
        # print("new access time: ", time.time() - start)

        # start = time.time()
        swap_map = shortest_paths[q1]['isl_maps'][q2]
        access1 = apply_swaps_to_logical_qubits_map(swap_map,access1)
        access2 = apply_swaps_to_logical_qubits_map(swap_map,access2)

        # print("find mapping time: ", time.time() - start)

        # print("+================================+")

    return time.time() - global_start, swap_count, iteration
    print(f"Total time taken: {time.time() - global_start}")
    print(f"Total number of swaps: {swap_count}")
    print(f"Total number of iterations: {iteration}")
    print(f"Total disconnection time: {disconnection_time_global}")
    print(f"Total range product time: {range_product_time}")

if __name__ == "__main__":
    json_file_path = 'benchmarks/polyhedral/queko-bss-20qbt/20QBT_100CYC_QSE_9.json'
    main(json_file_path)


