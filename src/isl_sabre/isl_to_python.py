from src.isl_sabre.python_to_isl import dict_to_isl_map
from src.isl_sabre.dag import DAG
import islpy as isl
from collections import defaultdict
import time


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
