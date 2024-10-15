import islpy as isl
from src.io_tools import *
from src.graph_tools import *
from src.swap_tools import *
import time 

def main():

    json_file_path = 'benchmarks/polyhedral/cases/bigd.json'

    data = json_file_to_isl(json_file_path)
    Qops = data["Qops"]
    domain, _ ,access  = filter_multi_qubit_gates(data["domain"], data["read_dependencies"], data["schedule"])

    graph = [
        [1, 5],           # Q[1] is connected to Q[2] and Q[6]
        [0, 2, 6],        # Q[2] is connected to Q[1], Q[3], and Q[7]
        [1, 3, 7],        # Q[3] is connected to Q[2], Q[4], and Q[8]
        [2, 4, 8],        # Q[4] is connected to Q[3], Q[5], and Q[9]
        [3, 9],           # Q[5] is connected to Q[4] and Q[10]
        [0, 6, 10],       # Q[6] is connected to Q[1], Q[7], and Q[11]
        [1, 5, 7, 11],    # Q[7] is connected to Q[2], Q[6], Q[8], and Q[12]
        [2, 6, 8, 12],    # Q[8] is connected to Q[3], Q[7], Q[9], and Q[13]
        [3, 7, 9, 13],    # Q[9] is connected to Q[4], Q[8], Q[10], and Q[14]
        [4, 8, 14],       # Q[10] is connected to Q[5], Q[9], and Q[15]
        [5, 11, 15],      # Q[11] is connected to Q[6], Q[12], and Q[16]
        [6, 10, 12, 16],  # Q[12] is connected to Q[7], Q[11], Q[13], and Q[17]
        [7, 11, 13, 17],  # Q[13] is connected to Q[8], Q[12], Q[14], and Q[18]
        [8, 12, 14, 18],  # Q[14] is connected to Q[9], Q[13], Q[15], and Q[19]
        [9, 13, 19],      # Q[15] is connected to Q[10], Q[14], and Q[20]
        [10, 16],         # Q[16] is connected to Q[11] and Q[17]
        [11, 15, 17],     # Q[17] is connected to Q[12], Q[16], and Q[18]
        [12, 16, 18],     # Q[18] is connected to Q[13], Q[17], and Q[19]
        [13, 17, 19],     # Q[19] is connected to Q[14], Q[18], and Q[20]
        [14, 18]          # Q[20] is connected to Q[15] and Q[19]
    ]
    backend_disconnected_edges =  extract_edges_map(graph)
    shortest_paths = extract_shortest_paths(graph)
    physical_qubits_domain = isl.Set(f"{{ [i] : 1 <= i <= {Qops} }}")
    mapping = isl.Map(f"{{ q[i] -> [i] : 1<=i<={Qops} }}")
    swap_count = 0

    start = time.time()
    while not access.is_empty():
        physical_access = access.apply_range(mapping)
        gates_acces = physical_access.flat_range_product(physical_access).intersect_range(isl.Set("{ [i, j] : i > j }"))
        first_disconnected_edge = gates_acces.intersect_range(backend_disconnected_edges).domain().lexmin()
        if first_disconnected_edge.is_empty():
            break

        disconected_qubits = physical_access.intersect_domain(first_disconnected_edge).range().as_set()
        q1 , q2 = eval(disconected_qubits.to_str().replace('[','').replace(']','').replace(';',','))
        swap_count += shortest_paths[q1]['costs'][q2] -1
        new_domain = access.domain().as_set().lex_gt_set(first_disconnected_edge.as_set()).domain()
        access = access.intersect_domain(new_domain).coalesce()
        mapping = apply_swaps_to_logical_qubits_map(swaps_to_isl_map(shortest_paths[q1]['paths'][q2]),mapping,physical_qubits_domain)
    
    print(f"Time taken: {time.time() - start}")
    print(f"Total number of swaps: {swap_count}")


if __name__ == "__main__":
    main()


