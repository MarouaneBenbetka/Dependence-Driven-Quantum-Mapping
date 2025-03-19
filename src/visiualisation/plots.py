import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import matplotlib.pyplot as plt

def plot_performance(results_swaps, results_depth, colors=None):
    """
    Plot the performance of heuristic methods using Plotly.

    Parameters:
        results_swaps (dict): Dictionary where keys are method names and values are lists of swap counts.
        results_depth (dict): Dictionary where keys are method names and values are lists of circuit depths.
        methods (list): List of method names to plot.
        colors (dict, optional): Dictionary mapping method names to color hex codes. 
            Defaults to preset colors if not provided.
            
    Returns:
        fig (plotly.graph_objects.Figure): Plotly figure with subplots and interactive buttons.
    """
    # Use default colors if not provided
    if colors is None:
        colors = {
            "qmap": "#1f77b4",     # blue
            "sabre": "#ff7f0e",    # orange
            "pytket": "#2ca02c",     # green 
            "cirq" : "#9467bd",     #purple
            "closure": "#d62728",  # red
        }

    # Create a subplot figure with 2 rows: swaps (row 1) and depths (row 2)
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        subplot_titles=("Swap Counts", "Circuit Depth")
    )
    methods = list(results_swaps.keys())

    total_methods = len(methods)

    # Add traces for swap counts in the first row
    for method in methods:
        x_vals = list(range(len(results_swaps[method])))
        fig.add_trace(
            go.Scatter(
                x=x_vals, 
                y=results_swaps[method],
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
        x_vals = list(range(len(results_depth[method])))
        fig.add_trace(
            go.Scatter(
                x=x_vals, 
                y=results_depth[method],
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

    # For each method, show its two traces (one for swaps and one for depths)
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
        xaxis_title="Trial Index",
        yaxis_title="Swap Counts",
        yaxis2_title="Circuit Depth"
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
                count_better = sum(np.array(results[method_i]) < np.array(results[method_j]))
                matrix[i, j] = (count_better / len(results[method_i])) * 100  # Percentage
    return matrix, methods

def plot_confusion_matrices(results_swaps, results_depth):
    """
    Plot confusion matrices for swap counts and circuit depth using Matplotlib.
    
    Parameters:
        results_swaps (dict): Dictionary with swap count results for each method.
        results_depth (dict): Dictionary with circuit depth results for each method.
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
    
    fig.suptitle("Confusion Matrices: Method Performance Comparison", fontsize=16)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.show()
