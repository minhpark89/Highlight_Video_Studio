"""Phase 1 local-first desktop components and optional cloud control plane.

Import submodules directly (for example ``multi_pc.hardware``) so the local
renderer never requires the optional cloud control plane to be importable.
"""

__all__ = ["hardware", "profile_cache", "adapter", "connector", "control_plane"]
