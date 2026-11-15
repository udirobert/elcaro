"""Metering storage — Dev C's lane (docs/roadmap-gateway.md §7.1 C2).

Neon-backed UsageSink + KeyStore satisfying the ``core.usage`` protocols.
Install once at gateway boot: ``metering.install_from_env()``.
"""

from metering.neon import NeonMetering, from_env, hash_key, install_from_env

__all__ = ["NeonMetering", "from_env", "hash_key", "install_from_env"]
