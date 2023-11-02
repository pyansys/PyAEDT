"""Miscellaneous Methods for PyAEDT."""
import os
import warnings


def list_installed_ansysem():
    """Return a list of installed AEDT versions on ``ANSYSEM_ROOT``."""
    aedt_env_var_prefix = "ANSYSEM_ROOT"
    version_list = sorted([x for x in os.environ if x.startswith(aedt_env_var_prefix)], reverse=True)
    aedt_env_var_sv_prefix = "ANSYSEMSV_ROOT"
    version_list += sorted([x for x in os.environ if x.startswith(aedt_env_var_sv_prefix)], reverse=True)

    if not version_list:
        warnings.warn(
            "No installed versions of AEDT are found in the system environment variables ``ANSYSEM_ROOTxxx``."
        )

    return version_list


def installed_versions():
    """Get the installed AEDT versions.

    This method returns a dictionary, with version as the key and installation path
    as the value.
    """
    return_dict = {}
    version_list = list_installed_ansysem()
    for version_env_var in version_list:
        if "ANSYSEMSV_ROOT" in version_env_var:
            current_version_id = version_env_var.replace("ANSYSEMSV_ROOT", "")
            student = True
        else:
            current_version_id = version_env_var.replace("ANSYSEM_ROOT", "")
            student = False
        try:
            version = int(current_version_id[0:2])
            release = int(current_version_id[2])
            if version < 20:
                if release < 3:
                    version -= 1
                else:
                    release -= 2
            if student:
                v_key = "20{0}.{1}SV".format(version, release)
            else:
                v_key = "20{0}.{1}".format(version, release)
            return_dict[v_key] = os.environ[version_env_var]
        except:  # pragma: no cover
            pass
    return return_dict


def current_version():
    """Get the current AEDT version."""
    try:
        return list(installed_versions().keys())[0]
    except (NameError, IndexError):
        return ""


def current_student_version():
    """Get the current AEDT student version."""
    for version_key in installed_versions():
        if "SV" in version_key:
            return version_key
    return ""
