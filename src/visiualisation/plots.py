import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import matplotlib.pyplot as plt
import os
import csv

def plot_performance(benchmark, results_swaps, results_depth, relative=False, baseline="Qlosure"):
    """
    Plot the performance of heuristic methods using Plotly.
    
    This function now offers an option to plot relative performance. When `relative=True`,
    the function computes for each method (including swap counts and circuit depths) the 
    relative difference with respect to the baseline method (default: "Qlosure"). 
    The formula used is: (method - baseline) / baseline.
    
    Parameters:
        benchmark (str): The label for the x-axis.
        results_swaps (dict): Dictionary where keys are method names and values are lists of swap counts.
        results_depth (dict): Dictionary where keys are method names and values are lists of circuit depths.
        relative (bool): If True, compute relative performance with respect to the baseline method.
        baseline (str): The method to use as baseline (default is "Qlosure").
            
    Returns:
        fig (plotly.graph_objects.Figure): Plotly figure with subplots and interactive buttons.
    """
    # Default colors for the methods
    colors = {
        "qmap": "#8c564b",     # blue
        "sabre": "#ff7f0e",    # orange
        "pytket": "#2ca02c",   # green 
        "cirq": "#9467bd",     # purple
        "Qlosure": "#d62728",  # red
        "no_read": "#1f77b4",  # brown

    }
    
    methods = list(results_swaps.keys())
    total_methods = len(methods)
    
    # If relative performance is requested, compute the relative differences
    if relative:
        relative_swaps = {}
        relative_depth = {}
        baseline_swaps = np.array(results_swaps[baseline])
        baseline_depth = np.array(results_depth[baseline])
        for method in methods:
            method_swaps = np.array(results_swaps[method])
            method_depth = np.array(results_depth[method])
            # For the baseline method, the relative difference is 0
            if method == baseline:
                relative_swaps[method] = [0] * len(method_swaps)
                relative_depth[method] = [0] * len(method_depth)
            else:
                relative_swaps[method] = ((method_swaps - baseline_swaps) / baseline_swaps).tolist()
                relative_depth[method] = ((method_depth - baseline_depth) / baseline_depth).tolist()
        plot_swaps = relative_swaps
        plot_depth = relative_depth
        yaxis_title_swaps = "Relative Swap Counts"
        yaxis_title_depth = "Relative Circuit Depth"
    else:
        plot_swaps = results_swaps
        plot_depth = results_depth
        yaxis_title_swaps = "Swap Counts"
        yaxis_title_depth = "Circuit Depth"
    
    # Create a subplot figure with 2 rows: swaps (row 1) and depths (row 2)
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        subplot_titles=("Swap Counts", "Circuit Depth")
    )
    
    # Add traces for swap counts in the first row
    for method in methods:
        x_vals = list(range(len(plot_swaps[method])))
        fig.add_trace(
            go.Scatter(
                x=x_vals, 
                y=plot_swaps[method],
                mode='lines+markers',
                name=method,
                legendgroup=method,
                marker=dict(color=colors.get(method, "#000000")),
                line=dict(color=colors.get(method, "#000000"))
            ),
            row=1, col=1
        )

    # Add traces for circuit depths in the second row
    for method in methods:
        x_vals = list(range(len(plot_depth[method])))
        fig.add_trace(
            go.Scatter(
                x=x_vals, 
                y=plot_depth[method],
                mode='lines+markers',
                name=method,
                legendgroup=method,
                showlegend=False,  # Avoid duplicate legend entries
                marker=dict(color=colors.get(method, "#000000")),
                line=dict(color=colors.get(method, "#000000"))
            ),
            row=2, col=1
        )

    # Total number of traces is twice the number of methods
    total_traces = total_methods * 2

    # Build interactive buttons
    buttons = [
        {
            "label": "Show All",
            "method": "update",
            "args": [{"visible": [True] * total_traces}]
        },
        {
            "label": "Hide All",
            "method": "update",
            "args": [{"visible": [False] * total_traces}]
        }
    ]

    # For each method, create a button to show its corresponding swap and depth traces only
    for i, method in enumerate(methods):
        visibility = [False] * total_traces
        visibility[i] = True                   # Swap trace in row 1
        visibility[i + total_methods] = True   # Depth trace in row 2
        buttons.append({
            "label": method,
            "method": "update",
            "args": [{"visible": visibility}]
        })

    # Update layout with interactive buttons and axis titles
    fig.update_layout(
        updatemenus=[{
            "buttons": buttons,
            "direction": "down",
            "showactive": True,
            "x": 1.15,
            "y": 0.5
        }],
        title="Performance of Heuristic Methods",
        xaxis_title=benchmark,
        yaxis_title=yaxis_title_swaps,
        yaxis2_title=yaxis_title_depth
    )
    
    return fig

def compute_confusion_matrix(results):
    """
    Compute pairwise comparisons for a given metric (swap count or depth).
    
    Parameters:
        results (dict): Dictionary where keys are method names and values are lists of values.
        
    Returns:
        matrix (np.ndarray): A 2D array (percentage) where matrix[i,j] shows the percentage 
                             of times method i is better than method j.
        methods (list): List of method names (order corresponding to the matrix indices).
    """
    methods = list(results.keys())
    num_methods = len(methods)
    matrix = np.zeros((num_methods, num_methods))
    
    for i, method_i in enumerate(methods):
        for j, method_j in enumerate(methods):
            if i != j:
                # Compare each trial value: count how often method_i is better than method_j.
                count_better = sum(np.array(results[method_i]) <= np.array(results[method_j]))
                matrix[i, j] = (count_better / len(results[method_i])) * 100  # Percentage
    return matrix, methods

def plot_confusion_matrices(benchmark,results_swaps, results_depth):
    """
    Plot confusion matrices for swap counts and circuit depth using Matplotlib.
    
    Parameters:
        results_swaps (dict): Dictionary with swap count results for each method.
        results_depth (dict): Dictionary with circuit depth results for each method.
        
    Returns:
        fig (matplotlib.figure.Figure): Matplotlib figure containing the two confusion matrices.
    """
    # Compute confusion matrices and get the method order.
    conf_matrix_swaps, methods = compute_confusion_matrix(results_swaps)
    conf_matrix_depth, _ = compute_confusion_matrix(results_depth)
    num_methods = len(methods)
    
    # Create a figure with two subplots side by side.
    fig, axes = plt.subplots(1, 2, figsize=(16, 8))
    
    # Plot the confusion matrix for swap counts.
    im1 = axes[0].imshow(conf_matrix_swaps, cmap="Blues", vmin=0, vmax=100)
    axes[0].set_title("Confusion Matrix - Swap Counts")
    axes[0].set_xticks(np.arange(num_methods))
    axes[0].set_xticklabels(methods)
    axes[0].set_yticks(np.arange(num_methods))
    axes[0].set_yticklabels(methods)
    axes[0].set_xlabel("Compared Against")
    axes[0].set_ylabel("Method")
    
    # Add text annotations to the swap confusion matrix.
    for i in range(num_methods):
        for j in range(num_methods):
            if i != j:
                text_color = "black" if conf_matrix_swaps[i, j] < 50 else "white"
                axes[0].text(j, i, f"{conf_matrix_swaps[i, j]:.1f}%", ha="center", va="center", color=text_color)
    
    fig.colorbar(im1, ax=axes[0])
    
    # Plot the confusion matrix for circuit depths.
    im2 = axes[1].imshow(conf_matrix_depth, cmap="Reds", vmin=0, vmax=100)
    axes[1].set_title("Confusion Matrix - Circuit Depth")
    axes[1].set_xticks(np.arange(num_methods))
    axes[1].set_xticklabels(methods)
    axes[1].set_yticks(np.arange(num_methods))
    axes[1].set_yticklabels(methods)
    axes[1].set_xlabel("Compared Against")
    # The y-axis label is already on the left subplot.
    
    # Add text annotations to the depth confusion matrix.
    for i in range(num_methods):
        for j in range(num_methods):
            if i != j:
                text_color = "black" if conf_matrix_depth[i, j] < 50 else "white"
                axes[1].text(j, i, f"{conf_matrix_depth[i, j]:.1f}%", ha="center", va="center", color=text_color)
    
    fig.colorbar(im2, ax=axes[1])
    
    fig.suptitle(benchmark, fontsize=16)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    return fig

def plots(benchmark, methods,layout,backend,our_method= "Qlosure"):

    
    results_swaps, results_depth = get_data(benchmark,methods,layout,backend)
    # Generate and display the Plotly performance plot
    performance_fig = plot_performance(benchmark,results_swaps, results_depth)
    performance_fig.show()
    
    performance_fig = plot_performance(benchmark,results_swaps, results_depth,relative=True)
    #performance_fig.show()
    
    # Generate and display the Matplotlib confusion matrices
    confusion_fig = plot_confusion_matrices(benchmark,results_swaps, results_depth)
     

    calculate_improvements(benchmark,results_swaps,"Swaps",our_method=our_method)
    calculate_improvements(benchmark,results_depth,"Depth",our_method=our_method)
    
    bars = plot_depth_ratios(benchmark, methods, layout,backend)
    plt.show()


    

def compute_average_depth_ratio(benchmark, methods, layout,backend):
    folder_path = "../experiment_results/" + benchmark 
    avg_ratios = {}
    
    for method in methods:
        file_path = os.path.join(folder_path, f"{method}.csv")
        ratios = []
        rows = []
        try:
            with open(file_path, newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                
                # Check if the required "depth" column is present.
                if "depth" not in reader.fieldnames:
                    return None
                
                for row in reader:
                    # Skip any row that is None or empty.
                    if not row:
                        continue
                    rows.append(row)
            
            if not rows:
                print(f"No valid data found in {file_path}.")
                avg_ratios[method] = None
                continue
            
            # First pass: determine the maximum value in depth_{layout} (ignoring "timeout" and invalid entries)
            numeric_values = []
            for row in rows:
                val_str = row.get(f"{backend}_depth_{layout}", "")
                if val_str != "timeout" and val_str != "error" and val_str != "":
                    try:
                        numeric_values.append(float(val_str))
                    except Exception as e:
                        print(f"Error converting value in {file_path} to float: {e}")
            
            max_val = max(numeric_values) if numeric_values else 0
            
            # Second pass: compute ratios, replacing "timeout" with max_val
            for row in rows:
                try:
                    baseline_str = row.get("depth", "")
                    if baseline_str in ["timeout", ""]:
                        continue  # skip if baseline is not valid
                    baseline = float(baseline_str)
                    if baseline == 0:
                        continue  # Avoid division by zero
                        
                    depth_str = row.get(f"depth_{layout}", "")
                    if depth_str == "timeout" or depth_str == "":
                        depth_val = max_val
                    else:
                        depth_val = float(depth_str)
                    
                    ratios.append(depth_val / baseline)
                except Exception as row_err:
                    print(f"Error processing row in {file_path}: {row_err}")
            
            avg_ratios[method] = sum(ratios) / len(ratios) if ratios else None
        except FileNotFoundError:
            print(f"File {file_path} not found.")
            avg_ratios[method] = None
        except Exception as e:
            print(f"An error occurred processing {file_path}: {e}")
            avg_ratios[method] = None
            
    return avg_ratios

def plot_depth_ratios(benchmark, methods, layout,backend):
    colors = {
        "qmap": "#8c564b",     # blue
        "sabre": "#ff7f0e",    # orange
        "pytket": "#2ca02c",   # green 
        "cirq": "#9467bd",     # purple
        "Qlosure": "#d62728",  # red
        "no_read": "#1f77b4",  # brown
    }
    
    
    avg_ratios = compute_average_depth_ratio(benchmark, methods, layout,backend)
    if not avg_ratios:
        return 
    methods = list(avg_ratios.keys())
    values = list(avg_ratios.values())
    bar_colors = [colors.get(method, "#000000") for method in methods]
    
    # Create a bar chart
    plt.figure(figsize=(10, 6))
    bars = plt.bar(methods, values, color=bar_colors)

    # Set labels and title
    plt.xlabel('Method')
    plt.ylabel('Average Depth Ratio')
    plt.title(f'Average Depth Ratio  {benchmark}')
    plt.ylim(0, max(values) + 1)

    # Annotate each bar with its value
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width() / 2, height + 0.05, f'{height:.2f}', 
                ha='center', va='bottom')
        
    return bars
    

  
def get_data(benchmark,methods,layout,beckend):
    
    folder_path = "../experiment_results/"+benchmark 

    # Initialize result dictionaries for trivial swaps and depth
    raw_swaps = {method: [] for method in methods}
    raw_depth = {method: [] for method in methods}

    # Process each method's CSV file in the specified folder
    for method in methods:
        file_path = os.path.join(folder_path, f"{method}.csv")
        try:
            with open(file_path, newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    raw_swaps[method].append(row[beckend+"_swaps_"+layout])
                    raw_depth[method].append(row[beckend+"_depth_"+layout])
                    
            
        except FileNotFoundError:
            print(f"File {file_path} not found.")
        except Exception as e:
            print(f"An error occurred processing {file_path}: {e}")
            
    results_swaps = {}
    results_depth = {}
    for method in methods:
        # Process swaps.
        # Collect non-timeout entries as integers.
        numeric_swaps = [int(val) for val in raw_swaps[method] if val != "timeout" and val != "error"]
        # Determine maximum value; if all entries were "timeout", you can set a default (e.g., 0).
        max_swaps = max(numeric_swaps) if numeric_swaps else 0
        # Replace "timeout" with the maximum value.
        results_swaps[method] = [max_swaps if val == "timeout" or val == "error" else int(val) for val in raw_swaps[method]]
        
        # Process depth.
        
        numeric_depth = [int(val) for val in raw_depth[method] if val != "timeout" and val != "error"]
        max_depth = max(numeric_depth) if numeric_depth else 0
        results_depth[method] = [max_depth if val == "timeout" or val == "error" else int(val) for val in raw_depth[method]]
    return results_swaps, results_depth






def calculate_improvements(benchmark,results_swaps,metric, our_method="Qlosure"):
    # Calculate our average value
    our_values = results_swaps[our_method]
    our_avg = sum(our_values) / len(our_values)
    
    improvements = {}
    for method, values in results_swaps.items():
        if not values:
            continue  
        method_avg = sum(values) / len(values)
        if method == our_method:
            continue  
        improvement = ((method_avg - our_avg) / method_avg) * 100
        improvements[method] = improvement

    # Prepare data for the bar chart
    methods = list(improvements.keys())
    improvement_values = list(improvements.values())
    colors = {
            "qmap": "#8c564b",     # blue
            "sabre": "#ff7f0e",    # orange
            "pytket": "#2ca02c",   # green 
            "cirq": "#9467bd",     # purple
            "Qlosure": "#d62728",  # red
            "no_read": "#1f77b4",  # brown

        }
    # Create the bar chart
    plt.figure(figsize=(8, 6))
    bar_colors = [colors.get(method, "#000000") for method in methods]
    bars = plt.bar(methods, improvement_values, color=bar_colors)
    plt.xlabel("Method")
    plt.ylabel("Improvement (%)")
    plt.title(f"{metric} improvement Comparison ('{benchmark}')")
    plt.axhline(0, color='gray', linewidth=0.8)  # horizontal line at zero
    plt.grid(axis='y', linestyle='--', alpha=0.7)

    # Annotate each bar with its improvement value
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval,
                 f"{yval:.2f}", ha='center', va='bottom')
    
    plt.show()
