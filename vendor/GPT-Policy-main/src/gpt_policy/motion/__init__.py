"""Path-preserving motion timing utilities."""

__all__ = [
    "MotionLimits",
    "retime_path_segment",
    "sample_count_for_segment",
    "sample_pose_segment",
]


def __getattr__(name):
    # HTTP-backed robots do not use the native Ruckig trajectory planner.
    if name not in __all__:
        raise AttributeError(name)
    from . import trajectory
    value = getattr(trajectory, name)
    globals()[name] = value
    return value
