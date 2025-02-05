

def paths_poly_heuristic(F, dag, initial_mapping, distance_matrix, access, swaps):
    E = create_extended_successor_set(F, dag)

    size_E, size_F = 0, 0
    if not E.is_empty():
        size_E = E.as_set().count_val().to_python()

    if not F.is_empty():
        size_F = F.as_set().count_val().to_python()

    W = 0.5

    f_distance = 0
    e_distance = 0

    def calc_f_distance(point):
        nonlocal f_distance
        f_distance += calculate_distance(point,
                                         access, distance_matrix, initial_mapping)

    F.foreach_point(lambda point: calc_f_distance(point))

    def calc_e_distance(point):
        nonlocal e_distance
        e_distance += calculate_distance(point,
                                         access, distance_matrix, initial_mapping)

    E.foreach_point(lambda point: calc_e_distance(point))

    f_distance = f_distance / size_F
    if size_E:
        e_distance = W * (e_distance) / size_E
    H = f_distance + e_distance + swaps

    return H


def decay_poly_heuristic(F, dag, initial_mapping, distance_matrix, access, decay_parameter, gate):
    E = create_extended_successor_set(F, dag)

    size_F, size_E = 0, 0
    if not E.is_empty():
        size_E = E.as_set().count_val().to_python()

    if not F.is_empty():
        size_F = F.as_set().count_val().to_python()

    W = 0.5

    max_decay = decay_parameter[gate[0]] + decay_parameter[gate[1]]
    f_distance = 0
    e_distance = 0

    def calc_f_distance(point):
        nonlocal f_distance
        f_distance += calculate_distance(point,
                                         access, distance_matrix, initial_mapping)

    F.foreach_point(lambda point: calc_f_distance(point))

    def calc_e_distance(point):
        nonlocal e_distance
        e_distance += calculate_distance(point,
                                         access, distance_matrix, initial_mapping)

    E.foreach_point(lambda point: calc_e_distance(point))

    f_distance = f_distance / size_F
    if size_E:
        e_distance = W * (e_distance) / size_E
    H = max_decay * (f_distance + e_distance)

    return H


def multi_layer_poly_heuristic(F, dag, initial_mapping, distance_matrix, access,
                               decay_parameter, gate,
                               lookahead_layers=5,
                               initial_layer_weight=1.0,
                               weight_decay=0.8):
    """
    A dynamic decay heuristic that looks ahead a specified number of layers in the DAG.

    At each layer, we compute the average distance cost for the gates in the current front.
    The contribution of each layer is weighted by a factor that decays as we move deeper.
    The final heuristic value is also scaled by a decay factor (derived from the two gate keys).

    Parameters:
      F                : The initial front set of gates.
      dag              : The DAG representing the circuit dependencies.
      initial_mapping  : A mapping from logical qubits to physical qubits.
      distance_matrix  : A matrix where each entry represents the distance between physical qubits.
      access           : A function to extract qubit(s) from a gate.
      decay_parameter  : A dictionary (or similar) that maps gate keys to decay parameters.
      gate             : A tuple (or list) containing two gate keys used to look up decay parameters.
      lookahead_layers : Number of layers to look ahead in the DAG (default is 5).
      initial_layer_weight:
                       The weight assigned to the immediate layer (layer 0) (default 1.0).
      weight_decay     : Multiplicative decay factor for the weight when moving to the next layer
                         (default 0.8). For example, layer i will have weight:
                             initial_layer_weight * (weight_decay ** i)

    Returns:
      heuristic_value  : A cost value that represents the “badness” of the current mapping.
    """
    total_cost = 0.0
    current_front = F  # Start with the immediate front (layer 0)
    current_dag = dag  # The current working copy of the DAG

    # Look ahead for the specified number of layers
    for layer in range(lookahead_layers):
        # If there are no more operations in the current front, break out.
        if current_front.is_empty():
            break

        # Compute the average distance cost for the current layer.
        layer_total_distance = 0.0
        layer_count = 0

        def accumulate_distance(point):
            nonlocal layer_total_distance, layer_count
            d = calculate_distance(
                point, access, distance_matrix, initial_mapping)
            layer_total_distance += d
            layer_count += 1

        current_front.foreach_point(lambda point: accumulate_distance(point))
        avg_distance = layer_total_distance / layer_count if layer_count > 0 else 0

        # Compute the dynamic weight for this layer.
        current_layer_weight = initial_layer_weight * (weight_decay ** layer)
        total_cost += current_layer_weight * avg_distance

        # Prepare for the next layer:
        #   - Update the DAG by subtracting the operations in the current front.
        #   - The next front is derived from the successors of the current front,
        #     excluding any nodes already removed.
        new_dag = current_dag.subtract_range(current_front)
        next_front = current_front.apply(current_dag)
        next_front = next_front.subtract(new_dag.range())

        # Update for the next iteration
        current_front = next_front
        current_dag = new_dag

    # Compute a decay factor based on the two gate keys.
    decay_factor = decay_parameter[gate[0]] + decay_parameter[gate[1]]
    heuristic_value = decay_factor * total_cost

    return heuristic_value


def calculate_distance(gate_details, access, distance_matrix, initial_mapping):
    qubits = gate_details.to_set().apply(access)
    if qubits.is_empty():
        return 0
    logical_q1, logical_q2 = qubits.lexmin(), qubits.lexmax()

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
