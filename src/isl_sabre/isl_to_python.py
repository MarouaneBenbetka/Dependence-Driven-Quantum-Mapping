from src.isl_sabre.python_to_isl import dict_to_isl_map
from src.isl_sabre.dag import DAG
import islpy as isl
from collections import defaultdict
import time
import re
from collections import defaultdict
from itertools import product


def isl_map_to_python_dict(_map):
    domain_point = isl_set_to_python_list(_map.domain())

    map_dict = {}
    for point in domain_point:
        qubits_list = isl_set_to_python_list(
            _map.intersect_domain(isl.Set(f"{{[{point}]}}")).range().as_set())
        qubits_list.sort()

        map_dict[point] = qubits_list

    return map_dict


# def isl_map_to_dict_optimized(m: isl.Map):
#     wrapped = m.wrap()
#     points = collect_points_from_set(wrapped)

#     result = defaultdict(list)
#     for p in points:
#         domain_point = p.get_coordinate_val(isl.dim_type.set, 0).to_python()

#         range_point = p.get_coordinate_val(isl.dim_type.set, 1).to_python()

#         result[domain_point].append(range_point)

#     return result


def isl_map_to_dict_optimized(m: isl.Map):
    result = defaultdict(list)
    dim_set = isl.dim_type.set
    to_py = isl.Val.to_python  # Cache method lookup

    def callback(p: isl.Point) -> None:
        domain = to_py(p.get_coordinate_val(dim_set, 0))
        range_val = to_py(p.get_coordinate_val(dim_set, 1))
        result[domain].append(range_val)

    m.wrap().foreach_point(callback)

    return result


def isl_map_to_dict_optimized2(_map):
    result = defaultdict(list)

    def map_to_dict(b):
        dim_set = isl.dim_type.set
        to_py = isl.Val.to_python

        def callback(p) -> None:
            domain = to_py(p.get_coordinate_val(dim_set, 0))
            range_val = to_py(p.get_coordinate_val(dim_set, 1))
            result[domain].append(range_val)

        b.foreach_point(callback)

    for b in _map.wrap().get_basic_sets():
        map_to_dict(b)

    return result


def parse_mapping(s):

    # Remove curly braces and split into entries
    s = s.strip('{}').strip()
    entries = s.split(';')
    dag = defaultdict(list)

    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue

        # Determine if it's the existing format or new format
        if '->' in entry:
            # Existing format: [key] -> q[expr] : conditions
            left, right = entry.split('->', 1)
            key_part = re.search(r'\[(.*?)\]', left)
            if not key_part:
                continue
            key_str = key_part.group(1).strip()
            if key_str.isdigit():
                key = int(key_str)
                key_var = None
            else:
                key_var = key_str
                key = None
            right = right.strip()
        else:
            # New format: q[expr] : conditions, implicit key is 'i0'
            right = entry
            key_var = 'i0'
            key = None

        # Extract expression and conditions
        if ':' in right:
            value_part, condition_part = right.split(':', 1)
            value_part = value_part.strip()
            condition_part = condition_part.strip()
        else:
            value_part = right.strip()
            condition_part = None

        expr_match = re.search(r'q\[(.*?)\]', value_part)
        if not expr_match:
            continue
        expr = expr_match.group(1).strip()
        # Add explicit multiplication, e.g., '10i0' -> '10*i0'
        expr = re.sub(r'(\d+)([a-zA-Z_]\w*)', r'\1*\2', expr)

        # Parse conditions
        var_ranges = {}
        if condition_part:
            # Add explicit multiplication in conditions
            condition_part = re.sub(
                r'(\d+)([a-zA-Z_]\w*)', r'\1*\2', condition_part)
            # Split conditions by 'and' to find range constraints
            condition_parts = re.split(r'\s+and\s+', condition_part)
            for part in condition_parts:
                part = part.strip()
                match = re.match(
                    r'^\s*(.*?)\s*<=\s*([a-zA-Z0-9_]+)\s*<=\s*(.*?)\s*$', part)
                if match:
                    lower_expr = match.group(1).strip()
                    var_name = match.group(2).strip()
                    upper_expr = match.group(3).strip()
                    var_ranges[var_name] = {
                        'lower': lower_expr, 'upper': upper_expr}

        # Process based on key type
        if key is not None:  # Fixed integer key
            if not condition_part:
                # No conditions, evaluate expression directly
                try:
                    value = eval(expr, {})
                    dag[key].append(value)
                except:
                    pass
            else:
                # Generate combinations for variables
                var_names = sorted(var_ranges.keys())
                if not var_names:
                    # Conditions exist but no range variables, evaluate condition
                    try:
                        if eval(condition_part, {}):
                            value = eval(expr, {})
                            dag[key].append(value)
                    except:
                        pass
                else:
                    # Compute ranges and generate combinations
                    var_values = {}
                    try:
                        for var in var_names:
                            lower = eval(var_ranges[var]['lower'], {})
                            upper = eval(var_ranges[var]['upper'], {})
                            var_values[var] = range(int(lower), int(upper) + 1)
                        for combo in product(*var_values.values()):
                            context = dict(zip(var_names, combo))
                            if eval(condition_part, {}, context):
                                value = eval(expr, {}, context)
                                dag[key].append(value)
                    except:
                        pass

        else:  # Variable key (key_var)
            if not condition_part or key_var not in var_ranges:
                continue
            try:
                # Determine range for key variable
                lower_key = eval(var_ranges[key_var]['lower'], {})
                upper_key = eval(var_ranges[key_var]['upper'], {})
                for key_value in range(int(lower_key), int(upper_key) + 1):
                    context = {key_var: key_value}
                    other_vars = {v: var_ranges[v]
                                  for v in var_ranges if v != key_var}
                    if not other_vars:
                        # No other variables, check full condition
                        if eval(condition_part, {}, context):
                            try:
                                value = eval(expr, {}, context)
                                dag[key_value].append(value)
                            except:
                                pass
                    else:
                        # Generate combinations for other variables
                        var_values = {}
                        for var in other_vars:
                            try:
                                lower = eval(other_vars[var]['lower'], context)
                                upper = eval(other_vars[var]['upper'], context)
                                var_values[var] = range(
                                    int(lower), int(upper) + 1)
                            except:
                                continue
                        if var_values:
                            keys = var_values.keys()
                            for combo in product(*var_values.values()):
                                full_context = context.copy()
                                full_context.update(zip(keys, combo))
                                if eval(condition_part, {}, full_context):
                                    try:
                                        value = eval(expr, {}, full_context)
                                        dag[key_value].append(value)
                                    except:
                                        pass
                        else:
                            # No valid ranges for other vars, evaluate with key only
                            if eval(condition_part, {}, context):
                                try:
                                    value = eval(expr, {}, context)
                                    dag[key_value].append(value)
                                except:
                                    pass
            except:
                pass

    return dict(dag)


def isl_set_to_python_list(_set):
    points = []

    def point_to_int(point):
        points.append(point.to_set().dim_min_val(0).to_python())

    _set.foreach_point(point_to_int)

    return points


def isl_set_to_python_set(_set):
    points = set()

    def point_to_int(point):
        points.add(point.to_set().dim_min_val(0).to_python())

    _set.foreach_point(point_to_int)
    return points


def isl_set_to_list_points(_set):
    points = []

    def point_to_int(point):
        points.append(point.to_set())

    _set.foreach_point(point_to_int)

    return points


def collect_points_from_set(S: isl.Set):
    """
    Enumerate all integer points from the set S (if S is finite),
    and return them as a list of isl.Point objects.
    """
    points_list = []

    # Callback that appends the point to our Python list
    def callback(p: isl.Point):
        points_list.append(p)
        # Must return 0 to continue enumeration, nonzero ends it
        return 0

    # This will invoke 'callback' for every integer point in S
    S.foreach_point(callback)

    return points_list
