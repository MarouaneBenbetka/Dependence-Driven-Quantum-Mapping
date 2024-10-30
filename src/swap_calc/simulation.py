import islpy as isl

from src.tools.circuit_tools import *
from src.tools.graph_tools import *
from src.tools.io_tools import *
from src.tools.swap_tools import *



class SwapCalculator():

    def __init__(self, backend):
        self.Q = len(backend)
        self.backend_topology = backend
        self.backend_disconnected_edges = extract_edges_map(backend)
        self.physical_qubits_domain = isl.Set(f"{{ [i] : 0 <= i <= {self.Q} }}")
        self.backend_infos = extract_shortest_paths(backend, self.physical_qubits_domain)
        self.transform_to_gate_map = isl.Map(" { [[[a]->[b]] -> [c]] -> [[a] -> [[b]->[c]]]}")

    

    def run(self, access1, access2, mapping):
        swap_count = 0
        iteration = 0
        disconnection_time_point = 0
        new_domain = isl.Set(f"{{ [i] : i <= {disconnection_time_point+100} }}")
        while not access1.is_empty():
            iteration += 1
            # print(f"Iteration {iteration}")
            # programme_access = access1.range_product(access2)
            compress_domain = isl.Set(f"{{ [i] : i <= {disconnection_time_point+100} }}")
            access1_compress = access1.intersect_domain(compress_domain)
            access2_compress = access2.intersect_domain(compress_domain)
            programme_access = access1_compress.domain_map().apply_range(access2_compress).wrap().apply(self.transform_to_gate_map).unwrap()
            disconnection_time = programme_access.intersect_range(self.backend_disconnected_edges).domain().lexmin()
            if disconnection_time.is_empty():
                disconnection_time_point += 100
                new_domain = isl.Set(f"{{ [i] : i> {disconnection_time_point} }}")
                access1 = access1.intersect_domain(new_domain)
                access2 = access2.intersect_domain(new_domain)
                continue

            q1 = access1.intersect_domain(disconnection_time).range().dim_max_val(0).to_python()
            q2 = access2.intersect_domain(disconnection_time).range().dim_max_val(0).to_python()

            swap_count += self.backend_infos[q1]['costs'][q2] -1

            disconnection_time_point = disconnection_time.dim_max_val(0).to_python()
            new_domain = isl.Set(f"{{ [i] : i> {disconnection_time_point} }}") 

            access1 = access1.intersect_domain(new_domain)
            access2 = access2.intersect_domain(new_domain)

            swap_map = self.backend_infos[q1]['isl_maps'][q2]
            access1 = apply_swaps_to_logical_qubits_map(swap_map,access1)
            access2 = apply_swaps_to_logical_qubits_map(swap_map,access2)

        
        return swap_count


        