




def extract_multi_qubit_gates(access_map):
    return access_map.subtract(  access_map.lexmin().intersect(access_map.lexmax())).domain()


def access_to_gates( read_dependencies_map , schedule_map):
    return schedule_map.reverse().apply_range(read_dependencies_map)


def filter_multi_qubit_gates(schedule_map,read_dependencies_map,domain):
    new_domain = extract_multi_qubit_gates(read_dependencies_map)
    new_schedule = access_to_gates(read_dependencies_map,schedule_map.intersect_domain(new_domain))
    new_read_dependicies = read_dependencies_map.intersect_domain(new_domain)

    return {
        "domain": new_domain,
        "schedule": new_schedule,
        "read_dependencies": new_read_dependicies
    }
