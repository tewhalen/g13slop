import os
import pwd


def is_running_as_root() -> bool:
    """Check if the current process is running with root privileges."""
    return os.geteuid() == 0


def drop_root_privs():
    """Drop root privileges by switching to a non-root user."""
    if not is_running_as_root():
        return  # Not running as root, nothing to do

    # Get the username to switch to from environment variable or default to 'nobody'
    user_name = os.getenv("SUDO_USER") or "nobody"
    try:
        pw_record = pwd.getpwnam(user_name)
    except KeyError:
        raise RuntimeError(
            f"User '{user_name}' not found. Cannot drop root privileges."
        )

    uid = pw_record.pw_uid
    gid = pw_record.pw_gid

    # Drop group privileges
    os.setgid(gid)
    # Drop user privileges
    os.setuid(uid)

    # Verify that we have dropped privileges
    if is_running_as_root():
        raise RuntimeError("Failed to drop root privileges.")
