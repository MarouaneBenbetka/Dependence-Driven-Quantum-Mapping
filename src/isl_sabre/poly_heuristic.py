




def Poly_heuristic_function(F,dag,initial_mapping,distance_matrix,access,swaps):
    E = create_extended_successor_set(F, dag)

    size_E,size_F = 0,0
    if not E.is_empty():
        size_E = E.as_set().count_val().to_python()

    if not F.is_empty():
        size_F = F.as_set().count_val().to_python()

    W = 0.5


    f_distance = 0
    e_distance = 0

    def calc_f_distance(point):
        nonlocal f_distance
        f_distance += calculate_distance(point,access, distance_matrix, initial_mapping)

    F.foreach_point(lambda point: calc_f_distance(point))
    
    def calc_e_distance(point):
        nonlocal e_distance
        e_distance += calculate_distance(point,access, distance_matrix, initial_mapping)

    E.foreach_point(lambda point: calc_e_distance(point))
    
    
    f_distance = f_distance / size_F
    if size_E:
        e_distance = W * (e_distance ) / size_E
    H =  f_distance + e_distance + swaps

    return H

def Poly_heuristic_function_decay(F,dag,initial_mapping,distance_matrix,access,decay_parameter,gate):
    E = create_extended_successor_set(F, dag)

    size_F,size_E = 0,0
    if not E.is_empty():
        size_E = E.as_set().count_val().to_python()

    if not F.is_empty():
        size_F = F.as_set().count_val().to_python()


    W = 0.5

    max_decay = decay_parameter[gate[0]]+ decay_parameter[gate[1]]
    f_distance = 0
    e_distance = 0

    def calc_f_distance(point):
        nonlocal f_distance
        f_distance += calculate_distance(point,access, distance_matrix, initial_mapping)

    F.foreach_point(lambda point: calc_f_distance(point))
    
    def calc_e_distance(point):
        nonlocal e_distance
        e_distance += calculate_distance(point,access, distance_matrix, initial_mapping)

    E.foreach_point(lambda point: calc_e_distance(point))
    
    
    f_distance = f_distance / size_F
    if size_E:
        e_distance = W * (e_distance ) / size_E
    H =  max_decay * (f_distance + e_distance)

    return H

def calculate_distance(gate_details,access, distance_matrix, initial_mapping):
    qubits = gate_details.to_set().apply(access)
    if qubits.is_empty():
        return 0
    logical_q1,logical_q2 = qubits.lexmin(),qubits.lexmax()

    physical_q1 = logical_q1.apply(initial_mapping)
    physical_q2 = logical_q2.apply(initial_mapping)
    return distance_matrix[
        physical_q1.as_set().dim_max_val(0).to_python(),
        physical_q2.as_set().dim_max_val(0).to_python()
    ]

def create_extended_successor_set(F, dag):

    E = F.apply(dag) 
    new_dag = dag.subtract_range(F)
    E = E.subtract(new_dag.range())
    
    return E
   