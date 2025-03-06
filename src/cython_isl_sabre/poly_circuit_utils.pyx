# poly_circuit_utils.pyx
# cython: language_level=3

import json
import islpy as isl

cpdef object json_file_to_isl(str path):
    """
    Reads a JSON file at 'path' and converts its content into a dictionary
    of ISL objects and other values.
    """
    with open(path) as f:
        data = json.load(f)
    return {
        "domain": isl.UnionSet(data["Domain"]),
        "read_dependencies": isl.UnionMap(data["Read"]),
        "write_dependencies": isl.UnionMap(data["Write"]),
        "call": isl.UnionMap(data["Call"]),
        "schedule": isl.UnionMap(data["RecoveredSchedule"]),
        "Qops": data["Stats"]["Qops"],
        "qasm_code": data["qasm_code"]
    }

cpdef object extract_multi_qubit_gates(object access_map):
    """
    Extracts multi-qubit gates from an access map.
    """
    return access_map.subtract(access_map.lexmin().intersect(access_map.lexmax())).domain()

cpdef object access_to_gates(object read_dependencies_map, object schedule_map):
    """
    Returns the gate access map given the read dependencies and schedule.
    """
    if schedule_map.is_empty():
        return None
    return schedule_map.reverse().apply_range(read_dependencies_map).as_map()

cpdef tuple filter_multi_qubit_gates(object domain, object read_dependencies, object schedule):
    """
    Filters the multi-qubit gates from the given domain, read dependencies,
    and schedule maps.
    Returns a tuple: (new_domain, new_read_dependencies, new_schedule)
    """
    cdef object new_domain = extract_multi_qubit_gates(read_dependencies).coalesce()
    cdef object filtered_schedule = schedule.intersect_domain(new_domain)
    if filtered_schedule is None:
        return None, None, None
    cdef object new_read_dependencies = read_dependencies.intersect_domain(new_domain).coalesce()
    # Uncomment the following line if you have a rescheduling function.
    # new_schedule = rescheduling(filtered_schedule)
    cdef object new_schedule = filtered_schedule
    return new_domain, new_read_dependencies, new_schedule

cpdef tuple read_data(object data):
    """
    Reads the data dictionary and returns a tuple containing:
      qops, read_dependencies, access, reverse_access, schedule, reverse_schedule, write_dependencies
    """
    cdef tuple filt = filter_multi_qubit_gates(data["domain"], data["read_dependencies"], data["schedule"])
    if filt[0] is None:
        return None
    
    domain = filt[0]
    read_dep = filt[1]
    schedule = filt[2]

    cdef object access = access_to_gates(read_dep, schedule)
    # You can choose between count_val() or dim_max_val(0) depending on your needs.
    cdef int qops = access.domain().dim_max_val(0).to_python()
    cdef object write_dep = data["write_dependencies"]
    write_dep = schedule.reverse().apply_range(write_dep).as_map()
    read_dep = access_to_gates(data["read_dependencies"], data["schedule"])
    cdef str map_str = f"{{ [i] -> [{qops}-i - 1] : 0 <= i <= {qops} }}"
    cdef reverse_map = isl.Map(map_str)
    cdef object reverse_access = access.apply_domain(reverse_map)
    cdef object reverse_schedule = schedule.apply_range(reverse_map)
    return qops, read_dep, access, reverse_access, schedule, reverse_schedule, write_dep
