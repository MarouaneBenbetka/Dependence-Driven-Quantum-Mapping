
import islpy as isl





def swaps_to_isl_map(path:list)  :
    """
    args:
        path: a list of nodes that will be swaped so that the src an target will be 
    """
    if len(path) <= 2:
        return isl.UnionMap("{}") 
    
    n = len(path) - 1
    map_str = f"[{path[0]}]->[{path[n-1]}]"
    for i in range(1,n):
        map_str += f";[{path[i]}]->[{path[i-1]}]"

    
    return isl.Map("{"+map_str+"}")


def apply_swaps_to_logical_qubits_map(swaps_map,logical_qubits_map,physical_qubits_domain) :
    swap_domain = swaps_map.domain()
    swap_complement_domain = physical_qubits_domain.subtract(swap_domain)

    return logical_qubits_map.apply_range(swaps_map).union(logical_qubits_map.intersect_range(swap_complement_domain)).coalesce()


# def first_disconnection(paths,logical_to_physical_mapping ):
#     programme_access.intersect_range(backend_disconnected_edges).domain().lexmin()