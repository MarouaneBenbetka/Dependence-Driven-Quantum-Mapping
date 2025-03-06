# python_to_isl.pyx
# cython: language_level=3, boundscheck=False, wraparound=False

import islpy as isl

cpdef object dict_to_isl_map(dict input_dict):
    """
    Convert a dictionary of {key: [values]} to an ISL Map string format.
    """
    cdef list entries = []
    cdef object key, values, val
    for key, values in input_dict.items():
        for val in values:
            entries.append(f"[{key}]->[{val}]")
    if not entries:
        return isl.UnionMap("{}")
    return isl.Map("{" + ";".join(entries) + "}").coalesce()


cpdef object list_to_isl_set(list input_list):
    if not input_list:
        return isl.UnionSet("{}")
    cdef list point_strings = []
    cdef object item
    for item in input_list:
        point_strings.append(f"[{item}]")
    cdef str set_str = "{" + ";".join(point_strings) + "}"
    return isl.Set(set_str)


cpdef object int_to_isl_set(input):
    return isl.Set("{" + f"[{input}]" + "}")
