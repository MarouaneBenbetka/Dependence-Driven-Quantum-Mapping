import islpy as isl
from src.graph_tools import *
from src.swap_tools import *

def main():

    logical_qubits_domain = isl.Set("{ q[i] : 1 <= i <  8 }")
    physical_qubits_domain = isl.Set("{ Q[i] : 0 <= i <  8 }")

    graph = defaultdict(list)
    
    graph['Q[1]'] = ['Q[2]', 'Q[4]']
    graph['Q[2]'] = ['Q[1]']
    graph['Q[3]'] = ['Q[4]']
    graph['Q[4]'] = ['Q[1]', 'Q[3]', 'Q[6]']
    graph['Q[5]'] = ['Q[6]', 'Q[7]']
    graph['Q[6]'] = ['Q[4]', 'Q[5]', 'Q[8]']
    graph['Q[7]'] = ['Q[5]']
    graph['Q[8]'] = ['Q[6]']
    
    print(extract_edges_map(graph))
    return

    shortest_paths = extract_shortest_paths(graph)
    swap_map = swaps_to_isl_map(shortest_paths['Q[2]']['paths']['Q[3]'])

    initial_mapping = isl.Map("{ q[i] -> Q[8-i] : 1<=i<8}")
    new_mapping = apply_swaps_to_logical_qubits_map(swap_map,initial_mapping,physical_qubits_domain)


    circuit_polyhedral_representation = json_file_to_isl("benchmarks/polyhedral/test.json")
    domain = circuit_polyhedral_representation['domain']
    schedule = circuit_polyhedral_representation['schedule']
    read_dependencies = circuit_polyhedral_representation['read_dependencies']
    
    domain_with_multi_qubits_gates = extract_multi_qubit_gates(read_dependencies)
    schedule_with_multi_qubits_gates = access_to_gates(read_dependencies,schedule.intersect_domain(domain_with_multi_qubits_gates))
    read_dependencies_with_multi_qubits_ = read_dependencies.intersect_domain(domain_with_multi_qubits_gates)


    access_to_gates_mapping = access_to_gates(read_dependencies,schedule.intersect_domain(domain_with_multi_qubits_gates))
    print(schedule.intersect_domain(domain_with_multi_qubits_gates))

if __name__ == "__main__":
    main()


