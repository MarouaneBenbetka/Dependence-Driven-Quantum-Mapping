from collections import defaultdict, deque
from typing import DefaultDict, Set, List, Tuple, TypeVar


def build_backend_graph(edges: List[Tuple[int, int]]):
    graph = defaultdict(set)
    for node1, node2 in edges:
        graph[node1].add(node2)
        graph[node2].add(node1)

    return graph


def compute_distance_matrix(graph: DefaultDict[int, Set[int]]):

    nodes = sorted(graph.keys())
    n = nodes[-1] + 1

    dist_matrix = [[float('inf')] * n for _ in range(n)]

    # For each node, run a BFS to compute distances to all other nodes.
    for start_node in nodes:
        dist_matrix[start_node][start_node] = 0
        queue = deque([start_node])

        while queue:
            current = queue.popleft()
            current_idx = current
            current_dist = dist_matrix[start_node][current_idx]

            for neighbor in graph[current]:
                neighbor_idx = neighbor
                # If we haven't visited this neighbor yet, update distance and queue it.
                if dist_matrix[start_node][neighbor_idx] == float('inf'):
                    dist_matrix[start_node][neighbor_idx] = current_dist + 1
                    queue.append(neighbor)

    return dist_matrix


# generate swap candidates based on the active qubits

def generate_swap_candidates(active_qubits, backend):
    candidates = []

    for qubit in active_qubits:
        for neighbor in backend[qubit]:
            candidates.append((qubit, neighbor))

    return candidates
