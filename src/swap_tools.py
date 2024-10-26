
import islpy as isl





def swaps_to_isl_map(path:list, physical_qubits_domain)  :
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

    partial_map = isl.Map("{"+map_str+"}")
    
    swap_domain = partial_map.domain()
    swap_complement_domain = physical_qubits_domain.subtract(swap_domain)

    return partial_map.union(isl.Map("{ [i]-> [i] }").intersect_domain(swap_complement_domain)).as_map().coalesce()




def apply_swaps_to_logical_qubits_map(swaps_map,logical_qubits_map) :
    return logical_qubits_map.apply_range(swaps_map)


# def first_disconnection(paths,logical_to_physical_mapping ):
#     programme_access.intersect_range(backend_disconnected_edges).domain().lexmin()