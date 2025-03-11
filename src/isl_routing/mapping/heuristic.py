from src.isl_routing.utils.python_to_isl import list_to_isl_set
from collections import deque
import random


def paths_poly_heuristic(front_layer, extended_layer, mapping, distance_matrix, access, swaps):

    W = 0.5
    front_layer_size = len(front_layer)
    extended_layer_size = len(extended_layer)

    f_distance = 0
    for gate in front_layer:
        q1, q2 = access[gate]
        Q1, Q2 = mapping[q1], mapping[q2]

        f_distance += distance_matrix[Q1][Q2]

    e_distance = 0
    for gate in extended_layer:
        q1, q2 = access[gate]
        Q1, Q2 = mapping[q1], mapping[q2]
        e_distance += distance_matrix[Q1][Q2]

    H = (f_distance / front_layer_size + W *
         ((e_distance / extended_layer_size) if extended_layer_size else 0)) + swaps

    return H


def decay_poly_heuristic(front_layer, extended_layer, mapping, distance_matrix, access, decay_parameter, gate):
    W = 0.5
    front_layer_size = len(front_layer)
    extended_layer_size = len(extended_layer)

    max_decay = max(decay_parameter[gate[0]], decay_parameter[gate[1]])

    f_distance = 0
    for gate in front_layer:
        q1, q2 = access[gate]
        Q1, Q2 = mapping[q1], mapping[q2]

        f_distance += distance_matrix[Q1][Q2]

    e_distance = 0
    for gate in extended_layer:
        q1, q2 = access[gate]
        Q1, Q2 = mapping[q1], mapping[q2]
        e_distance += distance_matrix[Q1][Q2]

    H = max_decay * (f_distance / front_layer_size + W *
                     ((e_distance / extended_layer_size) if extended_layer_size else 0))

    return H


def create_extended_successor_set(front_points, dag, extended_set_size=20):

    # front_points.sort()

    visited = []
    queue = deque(front_points)

    while queue and len(visited) < extended_set_size:
        current = queue.popleft()

        if current in dag:
            for succ in dag[current]:
                if succ not in visited:
                    visited.append(succ)
                    queue.append(succ)

                    if len(visited) >= extended_set_size:
                        break

    return list_to_isl_set(visited), visited


def find_min_score_swap_gate(heuristic_score, epsilon=1e-10):
    random.seed(21)
    min_score = float('inf')
    best_swaps = []

    for gate, score in heuristic_score.items():

        if score - min_score < -epsilon:
            min_score = score
            best_swaps = [gate]
        elif abs(score - min_score) <= epsilon:
            best_swaps.append(gate)

    best_swaps.sort()

    return random.choice(best_swaps)
