# isl_utils.pyx
# cython: language_level=3, boundscheck=False, wraparound=False

from .python_to_isl import dict_to_isl_map
from .dag import DAG
import islpy as isl
from collections import defaultdict

#
# This function uses no inner closure, so we mark it as cpdef.
#
cpdef dict isl_map_to_python_dict(object _map):
    cdef list domain_point = isl_set_to_python_list(_map.domain())
    cdef dict map_dict = {}
    cdef object point, qubits_list
    for point in domain_point:
        qubits_list = isl_set_to_python_list(
            _map.intersect_domain(isl.Set(f"{{[{point}]}}")).range().as_set())
        qubits_list.sort()
        map_dict[point] = qubits_list
    return map_dict


#
# This function has no closures.
#
cpdef dict isl_map_to_dict_optimized(object m):
    cdef object wrapped = m.wrap()
    cdef list points = collect_points_from_set(wrapped)
    cdef object result = defaultdict(list)
    cdef object p, domain_point, range_point
    for p in points:
        domain_point = p.get_coordinate_val(isl.dim_type.set, 0).to_python()
        range_point = p.get_coordinate_val(isl.dim_type.set, 1).to_python()
        result[domain_point].append(range_point)
    return dict(result)


#
# This function uses a callback (closure), so we declare it as a normal Python function.
#
def isl_map_to_dict_optimized2(object m):
    from collections import defaultdict
    cdef object result = defaultdict(list)
    cdef object dim_set = isl.dim_type.set
    cdef object to_py = isl.Val.to_python  # Cache method lookup

    def callback(p):
        domain = to_py(p.get_coordinate_val(dim_set, 0))
        range_val = to_py(p.get_coordinate_val(dim_set, 1))
        result[domain].append(range_val)
        return 0  # must return 0 to continue enumeration

    m.wrap().foreach_point(callback)
    return dict(result)


#
# Convert an ISL set to a list of integers.
# Uses an inner callback so defined as plain def.
#
def isl_set_to_python_list(object _set):
    cdef list points = []
    def point_to_int(point):
        # Append the minimal value of dimension 0 as an integer.
        points.append(point.to_set().dim_min_val(0).to_python())
        return 0
    _set.foreach_point(point_to_int)
    return points


#
# Convert an ISL set to a list of ISL Point objects.
# Uses a callback so defined as plain def.
#
def isl_set_to_list_points(object _set):
    cdef list points = []
    def point_to_int(point):
        points.append(point.to_set())
        return 0
    _set.foreach_point(point_to_int)
    return points


#
# Enumerate all integer points from the set S (if S is finite),
# and return them as a list of isl.Point objects.
#
def collect_points_from_set(object S):
    cdef list points_list = []
    def callback(p):
        points_list.append(p)
        return 0  # Return 0 to continue enumeration
    S.foreach_point(callback)
    return points_list
