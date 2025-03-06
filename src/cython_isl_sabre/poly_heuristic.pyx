# poly_heuristic.pyx
# cython: language_level=3, boundscheck=False, wraparound=False

import islpy as isl
from python_to_isl import list_to_isl_set
from isl_to_python import isl_set_to_python_list, isl_set_to_list_points


def paths_poly_heuristic(F, dag, mapping, distance_matrix, access, swaps):
    """
    Computes a heuristic cost by combining a lookahead value with a swap cost.
    """
    W = 0.5
    E = None
    lookahead_H = lookahead_heuristic(F,E, W, access, distance_matrix, mapping)
    H = lookahead_H + swaps
    return H

def decay_poly_heuristic(F, E, mapping, distance_matrix, access, decay_parameter, gate):
    """
    Computes a heuristic cost based on decay factors.
    """
    W = 0.5
    new_access = access.apply_range(mapping)
    max_decay = max(decay_parameter[gate[0]], decay_parameter[gate[1]])
    # Here we call lookahead_heuristic with 5 arguments (mapping defaults to None)
    lookahead_H = lookahead_heuristic(F, E, W, new_access, distance_matrix)
    H = max_decay * lookahead_H
    return H

def lookahead_heuristic(F, E, w, access, distance_matrix, mapping=None):
    """
    Computes a lookahead heuristic based on the average distance costs over two sets.
    An extra parameter 'mapping' is accepted (but not used here) so that callers
    with an extra argument do not cause an error.
    """
    size_F = isl_set_len(F)
    f_distance = isl_calc_distance(F, access, distance_matrix)
    f_distance = f_distance / size_F
    e_distance = 0

    if E is not None:
        size_E = isl_set_len(E)
        e_distance = isl_calc_distance(E, access, distance_matrix)
        if size_E:
            e_distance = w * e_distance / size_E


    return f_distance + e_distance

def isl_calc_distance(set_obj, access, distance_matrix):
    """
    Calculates the cumulative distance over all points in an ISL set.
    """
    points = isl_set_to_list_points(set_obj)
    # Sum the distances for each point (using calculate_distance below)
    return sum(calculate_distance(point, access, distance_matrix) for point in points)

def calculate_distance(gate_details, access, distance_matrix, mapping=None):
    """
    Computes the distance for a gate based on its qubit assignment.
    If a mapping is provided, it is passed to the 'apply' method.
    """
    if mapping is not None:
        qubits = gate_details.apply(access, mapping)
    else:
        qubits = gate_details.apply(access)
    if qubits.is_empty():
        return 0
    physical_q1 = qubits.lexmin().as_set()
    physical_q2 = qubits.lexmax().as_set()
    return distance_matrix[physical_q1][physical_q2]

def get_subset_of_unionset(uset, limit):
    """
    Returns a subset of the given union set, containing at most 'limit' points.
    """
    points_list = isl_set_to_python_list(uset)
    points_list.sort()
    subset_points_list = points_list[:limit]
    subset_isl_set = list_to_isl_set(subset_points_list)
    return subset_isl_set

def isl_set_len(S):
    """
    Returns the number of integer points in the given set S (if not empty).
    """
    if not S.is_empty():
        return S.as_set().count_val().to_python()
    return 0

def create_extended_successor_set(F, dag, extended_set_size=20):
    """
    Expands the successor set until it reaches at least 'extended_set_size' points
    or there are no more operations.
    """
    E = isl.UnionSet("{}")
    E_size = 0

    while E_size < extended_set_size and not F.is_empty():
        next_E = F.apply(dag).subtract(F)
        if next_E.is_empty():
            break
        
        next_E_size = isl_set_len(next_E)
        remaining_size = extended_set_size - E_size

        if next_E_size <= remaining_size:
            E = E.union(next_E)
            F = next_E  
        else:
            partial_next_E = get_subset_of_unionset(next_E, remaining_size)
            E = E.union(partial_next_E)
            F = next_E.subtract(partial_next_E)
        
        E_size = isl_set_len(E)
        
    return E
