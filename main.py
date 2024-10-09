import islpy as isl
from lib.graph_utils import *
from lib.swap_utils import *

def main():

    graph = defaultdict(list)
    
    graph['Q[1]'] = ['Q[2]', 'Q[4]']
    graph['Q[2]'] = ['Q[1]']
    graph['Q[3]'] = ['Q[4]']
    graph['Q[4]'] = ['Q[1]', 'Q[3]', 'Q[6]']
    graph['Q[5]'] = ['Q[6]', 'Q[7]']
    graph['Q[6]'] = ['Q[4]', 'Q[5]', 'Q[8]']
    graph['Q[7]'] = ['Q[5]']
    graph['Q[8]'] = ['Q[6]']

    logical_qubits_domain = isl.Set("{ q[i] : 1 <= i <  8 }")
    physical_qubits_domain = isl.Set("{ Q[i] : 0 <= i <  8 }")

    shortest_paths = extract_shortest_paths(graph)
    swap_map = swaps_to_isl_map(shortest_paths['Q[2]']['paths']['Q[3]'])

    initial_mapping = isl.Map("{ q[i] -> Q[8-i] : 1<=i<8}")
    new_mapping = apply_swaps_to_logical_qubits_map(swap_map,initial_mapping,physical_qubits_domain)

    print(new_mapping)


if __name__ == "__main__":
    main()


