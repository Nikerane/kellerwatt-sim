"""KellerWatt arbitrage simulation engine.

Pipeline: data_load -> dispatch (LP ceiling + causal walk-forward) -> economics
-> metrics -> backtest -> export. Contracts (wire format, IDs, fee bases) live in
``engine.contracts`` and the JSON Schema under ``engine/schema/``.
"""
