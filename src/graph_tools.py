
from heapq import heappush, heappop
from collections import defaultdict
from src.swap_tools import swaps_to_isl_map
from src.io_tools import *
from src.circuit_tools import *
import re



def extract_coordinates(text):
    match = re.search(r'\[(.*?)\]', text)
    if match:
        return match.group(1)  
    
    raise ValueError("No content inside square brackets found")



def extract_shortest_paths(graph:defaultdict) -> dict:
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

def extract_edges_map(graph:defaultdict):
    edges = []
    for src in graph:
        for dst in graph[src]:
            edges.append((extract_coordinates(src),extract_coordinates(dst)))
    
    edges_str =  "{" + ";".join([f'[{src},{dst}]' for src,dst in edges]) + "}"
    print(edges_str)
    connected_edges_set = isl.Set(edges_str)
    
    all_connections = isl.Set(f"{{  [i,j] : 1 <= i,j <= {len(graph)} }}")

    disconnected_edges = all_connections.subtract(connected_edges_set)

    return isl.Map.from_domain_and_range(disconnected_edges, isl.Set("{[1]}"))
    

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

    print(extract_edges_map(graph))

    


