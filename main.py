import islpy as isl
from src.io_tools import *
from src.graph_tools import *
from src.swap_tools import *
import time 

def main():

    json_file_path = 'benchmarks/polyhedral/queko-bss-16qbt/16QBT_100CYC_QSE_7.json'
    data = json_file_to_isl(json_file_path)
    domain, read_dep, access = filter_multi_qubit_gates(data["domain"], data["read_dependencies"], data["schedule"])
    num_qubits = get_qubits_needed(read_dep)
    physical_qubits_domain = isl.Set(f"{{ [i] : 1 <= i <= {num_qubits} }}")
    backend_graph = generate_2d_grid()

    backend_disconnected_edges =  extract_edges_map(backend_graph)
    shortest_paths = extract_shortest_paths(backend_graph)


    mapping = isl.Map(f"{{ q[i] -> [i] : 1<=i<={num_qubits} }}")
    swap_count = 0

    iteration = 0

    access1 = access.lexmin()
    access2 = access.lexmax()

    global_start = time.time()
    while not access.is_empty():
        iteration += 1
        access_to_physical1 = access1.apply_range(mapping)
        access_to_physical2 = access2.apply_range(mapping)

        programme_access = access_to_physical1.range_product(access_to_physical2)
        disconnection_time = programme_access.intersect_range(backend_disconnected_edges).domain().lexmin()
        if disconnection_time.is_empty():
            break
            
        
        q1 = access_to_physical1.intersect_domain(disconnection_time).range().as_set().dim_max_val(0).to_python()
        q2 = access_to_physical2.intersect_domain(disconnection_time).range().as_set().dim_max_val(0).to_python()

        swap_count += shortest_paths[q1]['costs'][q2] -1
        new_domain = access.domain().as_set().lex_gt_set(disconnection_time.as_set()).domain()
        access1 = access1.intersect_domain(new_domain).coalesce()
        access2 = access2.intersect_domain(new_domain).coalesce()
        mapping = apply_swaps_to_logical_qubits_map(shortest_paths[q1]['isl_maps'][q2],mapping,physical_qubits_domain)

    print(f"Total time taken: {time.time() - global_start}")
    print(f"Total number of swaps: {swap_count}")


if __name__ == "__main__":
    main()


