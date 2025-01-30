
import islpy as isl


def dict_to_isl_map(input_dict: dict) -> str:
    """
    Convert a dictionary of {key: [values]} to an ISL Map string format.
    """

    entries = []
    for key, values in input_dict.items():
        for val in values:
            entries.append(f"[{key}]->[{val}]")

    return isl.Map("{" + ";".join(entries) + "}")
