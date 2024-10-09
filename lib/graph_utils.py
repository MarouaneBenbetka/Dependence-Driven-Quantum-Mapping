
from heapq import heappush, heappop
from collections import defaultdict
from lib.swap_utils import swaps_to_isl_map

def extract_shortest_paths(graph:defaultdict) -> dict:
    """
    Extracts shortest paths from a graph.

    Args:
        graph: A graph.

    Returns:
        A dictionary of shortest paths.
    """
    all_shortest_paths = {}

    for src in graph:
        shortest = {}  
        paths = {src: [src]} 
        heap = [(0, src)]  
        
        while heap:
            cost, node = heappop(heap)
            if node in shortest: 
                continue
            shortest[node] = cost  

            for neighbor in graph[node]:
                new_cost = cost + 1
                if neighbor not in shortest or new_cost < shortest[neighbor]:
                    heappush(heap, (new_cost, neighbor))
                    paths[neighbor] = paths[node] + [neighbor]
        
        isl_maps = []
        for path in paths:
            isl_maps.append(swaps_to_isl_map(paths[path]))
        all_shortest_paths[src] = {'costs': shortest, 'paths': paths, 'isl_maps': isl_maps}  

    return all_shortest_paths


if __name__ == "__main__":

    graph = defaultdict(list)
    
    graph['Q[1]'] = ['Q[2]', 'Q[4]']
    graph['Q[2]'] = ['Q[1]']
    graph['Q[3]'] = ['Q[4]']
    graph['Q[4]'] = ['Q[1]', 'Q[3]', 'Q[6]']
    graph['Q[5]'] = ['Q[6]', 'Q[7]']
    graph['Q[6]'] = ['Q[4]', 'Q[5]', 'Q[8]']
    graph['Q[7]'] = ['Q[5]']
    graph['Q[8]'] = ['Q[6]']


    shortest_paths = extract_shortest_paths(graph)

    for src in shortest_paths:
        print(f"Shortest paths from {src}:")


        for target in shortest_paths[src]['costs']:
            print("To node:",target) 
            print(f"Cost: {shortest_paths[src]['costs'][target]}")
            print(f"Path: {shortest_paths[src]['paths'][target]}")
            print(f"Isl map: {shortest_paths[src]['isl_maps'][target]}")
        
        print("-" * 40)


