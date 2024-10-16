
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
    for src in range(len(graph)):
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
        
        isl_maps = {}
        for path in paths:
            isl_maps[path] =  swaps_to_isl_map(paths[path])

        all_shortest_paths[src] = {'costs': shortest, 'paths': paths, 'isl_maps': isl_maps}  

    return all_shortest_paths

def extract_edges_map(graph:list[list]):
    edges = []
    for src in range(len(graph)):
        for dst in graph[src]:
            edges.append((src,dst))
    
    edges_str =  "{" + ";".join([f'[[{src}] -> [{dst}]]' for src,dst in edges if src < dst]) + "}"
    connected_edges_set = isl.Set(edges_str)
    
    all_connections = isl.Set(f"{{  [[i] -> [j]] : 1 <= i < j <= {len(graph)} }}")

    disconnected_edges = all_connections.subtract(connected_edges_set)

    return disconnected_edges
    

def generate_2d_grid(num_rows = 4, num_cols = 4):
    num_qubits = num_rows * num_cols
    graph = [[] for _ in range(num_qubits)]
    
    for i in range(num_rows):
        for j in range(num_cols):
            index = i * num_cols + j
            if j > 0:
                graph[index].append(index - 1)
            if j + 1 < num_cols:
                graph[index].append(index + 1)
            if i > 0:
                graph[index].append(index - num_cols)
            if i + 1 < num_rows:
                graph[index].append(index + num_cols)
    
    return graph

