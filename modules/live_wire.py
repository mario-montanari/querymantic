#!/usr/bin/env python3
"""Live Wire module (opt-in).

Brings observed data into the run-state and pairs it with the offline estimates,
so the two are visible side by side and never mixed. It is the only place where a
measured citation share, the competitor split, and measured organic clicks enter
the analysis. Everything else in the suite is offline by design.

Live Wire reads a single capture file, ``livewire_capture.json``, that the analyst
fills from two sources:

- ``search_console``: per-query rows from a Google Search Console performance
  export (query, clicks, impressions, ctr, position). These give measured current
  clicks, which override the modelled current-clicks estimate of Click Ceiling.
- ``ai_citations``: per-query observations of which domains an AI answer surface
  cited (the client and its competitors). These give an observed citation share
  and a competitor split, which Citation Grid can only approximate offline as a
  within-portfolio expected distribution.

The module never overwrites the offline slots. It writes its own ``live_wire``
slot, where each cluster carries the expected value next to the observed one, with
``mode: observed``. A downstream consumer (Output Forge) reads observed when it is
present and falls back to expected otherwise. This keeps the offline modules pure
and deterministic and honours the rule that expected and observed are never
conflated.

This is a pure step: ``live_wire(run_state, capture=...) -> run_state'``. It fills
the ``live_wire`` slot and leaves everything else untouched. It reads the Click
Ceiling and Citation Grid slots when present and degrades gracefully without them.
The capture, like Demand Pulse's series, is an input and never enters ``run.json``;
only the computed comparison does.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from querymantic.text import tokenize

# How many competitor domains to list per split, longest tail folded into "other".
MAX_COMPETITORS = 8

# Sentinel key for the client's own citation weight while aggregating domains.
_CLIENT_KEY = "__client__"


class ModuleError(Exception):
    """Raised when a module cannot run against the current run-state."""


class LiveWireError(Exception):
    """Raised when the capture file cannot be parsed or is malformed."""


def _norm(text: str) -> str:
    """Normalise a query for joining the capture to the engine corpus."""
    return " ".join(tokenize(text))


def _norm_domain(domain: str) -> str:
    """Normalise a domain for client and competitor comparison.

    Lowercases, strips a scheme, a leading ``www.``, and any path, so
    ``https://www.Example.com/page`` and ``example.com`` compare equal.
    """
    value = domain.strip().lower()
    for prefix in ("https://", "http://"):
        if value.startswith(prefix):
            value = value[len(prefix) :]
    value = value.split("/", 1)[0]
    if value.startswith("www."):
        value = value[4:]
    return value


def _is_client_domain(domain: str, client: str) -> bool:
    """True when ``domain`` is the client's own domain or a subdomain of it."""
    if not client:
        return False
    d = _norm_domain(domain)
    c = _norm_domain(client)
    return d == c or d.endswith("." + c)


# --- capture parsing --------------------------------------------------------


def _to_float(value: Any) -> float | None:
    """Parse a number that may be a fraction, an int, or a percent string.

    Accepts the Search Console export rendering (``"6.7%"``) and the API fraction
    (``0.067``). A trailing percent sign divides by 100. Returns None when the
    cell is empty or cannot be read, so a missing value never becomes a zero.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    percent = text.endswith("%")
    if percent:
        text = text[:-1].strip()
    try:
        number = float(text)
    except ValueError:
        return None
    return number / 100.0 if percent else number


def _capture_body(data: Any, path: Path) -> dict[str, Any]:
    """Return the capture body, accepting either the wrapped or bare object."""
    if not isinstance(data, dict):
        raise LiveWireError(f"capture must be a JSON object: {path}")
    body = data.get("livewire_capture", data)
    if not isinstance(body, dict):
        raise LiveWireError(f"'livewire_capture' must be an object: {path}")
    return body


def _parse_search_console(block: Any, path: Path) -> dict[str, Any]:
    if not isinstance(block, dict):
        raise LiveWireError(f"'search_console' must be an object: {path}")
    raw_rows = block.get("rows")
    if not isinstance(raw_rows, list):
        raise LiveWireError(f"'search_console.rows' must be an array: {path}")
    rows: list[dict[str, Any]] = []
    for i, row in enumerate(raw_rows, start=1):
        if not isinstance(row, dict):
            raise LiveWireError(f"{path}: search_console row {i} is not an object")
        query = str(row.get("query", "")).strip()
        if not query:
            raise LiveWireError(f"{path}: search_console row {i} has no query")
        clicks = _to_float(row.get("clicks"))
        impressions = _to_float(row.get("impressions"))
        # clicks and impressions are measured fields, not optional. A missing value
        # must not silently become a measured zero (that would understate current
        # clicks and overstate the re-anchored winnable band), so reject it.
        if clicks is None or impressions is None:
            raise LiveWireError(
                f"{path}: search_console row {i} needs numeric clicks and impressions"
            )
        ctr = _to_float(row.get("ctr"))
        position = _to_float(row.get("position"))
        if clicks < 0 or impressions < 0:
            raise LiveWireError(f"{path}: search_console row {i} has a negative count")
        rows.append(
            {
                "query": query,
                "clicks": clicks,
                "impressions": impressions,
                "ctr": ctr if (ctr is None or 0.0 <= ctr <= 1.0) else None,
                "position": position,
            }
        )
    return {"date_range": str(block.get("date_range", "")), "rows": rows}


def _parse_ai_citations(block: Any, path: Path) -> dict[str, Any]:
    if not isinstance(block, dict):
        raise LiveWireError(f"'ai_citations' must be an object: {path}")
    raw_rows = block.get("rows")
    if not isinstance(raw_rows, list):
        raise LiveWireError(f"'ai_citations.rows' must be an array: {path}")
    rows: list[dict[str, Any]] = []
    surfaces: set[str] = set()
    for i, row in enumerate(raw_rows, start=1):
        if not isinstance(row, dict):
            raise LiveWireError(f"{path}: ai_citations row {i} is not an object")
        query = str(row.get("query", "")).strip()
        if not query:
            raise LiveWireError(f"{path}: ai_citations row {i} has no query")
        raw_cites = row.get("citations")
        if not isinstance(raw_cites, list) or not raw_cites:
            raise LiveWireError(f"{path}: ai_citations row {i} has no citations")
        cites: list[dict[str, Any]] = []
        for c in raw_cites:
            if not isinstance(c, dict):
                raise LiveWireError(f"{path}: a citation in row {i} is not an object")
            domain = str(c.get("domain", "")).strip()
            if not domain:
                raise LiveWireError(f"{path}: a citation in row {i} has no domain")
            cites.append({"domain": domain, "is_client": c.get("is_client")})
        surface = str(row.get("surface", "")).strip()
        if surface:
            surfaces.add(surface)
        rows.append({"query": query, "surface": surface, "citations": cites})
    return {"surfaces": sorted(surfaces), "rows": rows}


def load_capture(path: Path) -> dict[str, Any]:
    """Parse and validate a ``livewire_capture.json`` file.

    Returns a normalised mapping with a ``client_domain`` and, when present, a
    parsed ``search_console`` and ``ai_citations`` block. Raises ``LiveWireError``
    on a malformed file. At least one of the two observed blocks must be present.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise LiveWireError(f"capture file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise LiveWireError(f"capture is not valid JSON: {path}") from exc

    body = _capture_body(data, path)
    parsed: dict[str, Any] = {
        "version": str(body.get("version", "")),
        "client_domain": str(body.get("client_domain", "")).strip(),
    }
    if body.get("search_console") is not None:
        parsed["search_console"] = _parse_search_console(body["search_console"], path)
    if body.get("ai_citations") is not None:
        parsed["ai_citations"] = _parse_ai_citations(body["ai_citations"], path)
    if "search_console" not in parsed and "ai_citations" not in parsed:
        raise LiveWireError(
            f"capture has neither a search_console nor an ai_citations block: {path}"
        )
    return parsed


# --- run-state readers ------------------------------------------------------


def _keyword_maps(
    keywords: list[dict[str, Any]], clusters: list[dict[str, Any]]
) -> tuple[dict[str, int], dict[int, int]]:
    """Build (normalised query -> keyword index) and (keyword index -> cluster)."""
    norm_to_kw: dict[str, int] = {}
    for idx, keyword in enumerate(keywords):
        nq = _norm(str(keyword.get("keyword", "")))
        if nq and nq not in norm_to_kw:
            norm_to_kw[nq] = idx
    kw_to_cluster: dict[int, int] = {}
    for ci, cluster in enumerate(clusters):
        for m in cluster.get("members") or []:
            if isinstance(m, int) and 0 <= m < len(keywords) and m not in kw_to_cluster:
                kw_to_cluster[m] = ci
    return norm_to_kw, kw_to_cluster


def _keyword_volume(keyword: dict[str, Any]) -> float:
    vol = (keyword.get("metrics") or {}).get("volume")
    return float(vol) if isinstance(vol, (int, float)) and vol > 0 else 1.0


def _click_ceiling_by_cluster(state: dict[str, Any]) -> dict[int, dict[str, Any]]:
    cc = (state.get("modules") or {}).get("click_ceiling")
    if not isinstance(cc, dict):
        return {}
    out: dict[int, dict[str, Any]] = {}
    for row in cc.get("clusters") or []:
        idx = row.get("cluster_index")
        if isinstance(idx, int):
            out[idx] = row
    return out


def _expected_share_by_cluster(state: dict[str, Any]) -> dict[int, float]:
    cg = (state.get("modules") or {}).get("citation_grid")
    if not isinstance(cg, dict):
        return {}
    out: dict[int, float] = {}
    for row in cg.get("clusters") or []:
        idx = row.get("cluster_index")
        share = row.get("expected_share")
        if isinstance(idx, int) and isinstance(share, (int, float)):
            out[idx] = float(share)
    return out


# --- Search Console override ------------------------------------------------


def _search_console_override(
    sc: dict[str, Any],
    keywords: list[dict[str, Any]],
    clusters: list[dict[str, Any]],
    norm_to_kw: dict[str, int],
    kw_to_cluster: dict[int, int],
    cc_by_cluster: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    """Override Click Ceiling's modelled current clicks with measured clicks.

    Per cluster the measured current is the sum of the matched queries' clicks. The
    winnable band is re-anchored: the ceiling endpoints stay as Click Ceiling
    modelled them (the reachable rank range), and winnable becomes ceiling minus the
    measured current, floored at zero. The average position is impression-weighted.
    """
    # accumulators per cluster
    agg: dict[int, dict[str, float]] = {}
    matched = 0
    unmatched: list[str] = []
    for row in sc["rows"]:
        kwidx = norm_to_kw.get(_norm(row["query"]))
        if kwidx is None:
            unmatched.append(row["query"])
            continue
        ci = kw_to_cluster.get(kwidx)
        if ci is None:
            unmatched.append(row["query"])
            continue
        matched += 1
        bucket = agg.setdefault(
            ci, {"clicks": 0.0, "impressions": 0.0, "pos_weight": 0.0, "matched": 0.0}
        )
        bucket["clicks"] += row["clicks"]
        bucket["matched"] += 1
        if row["position"] is not None and row["impressions"] > 0:
            bucket["pos_weight"] += row["position"] * row["impressions"]
            bucket["impressions"] += row["impressions"]

    reports: list[dict[str, Any]] = []
    port_obs = 0.0
    port_exp_current = 0.0
    port_exp_low = 0.0
    port_exp_high = 0.0
    port_obs_low = 0.0
    port_obs_high = 0.0
    for ci in sorted(agg):
        bucket = agg[ci]
        observed_current = bucket["clicks"]
        avg_position = (
            round(bucket["pos_weight"] / bucket["impressions"], 2)
            if bucket["impressions"] > 0
            else None
        )
        cc_row = cc_by_cluster.get(ci)
        entry: dict[str, Any] = {
            "cluster_index": ci,
            "head": clusters[ci].get("head", ""),
            "matched_members": int(bucket["matched"]),
            "observed_current_clicks": int(round(observed_current)),
            "observed_avg_position": avg_position,
        }
        port_obs += observed_current
        if cc_row is not None:
            # Re-anchor against Click Ceiling's integer ceiling band. Clicks are whole
            # events, so the integer band is the right domain here; the subtraction
            # loses no meaningful precision.
            ceiling = cc_row.get("ceiling_band") or [0, 0]
            exp_current = cc_row.get("current_clicks_estimate", 0)
            exp_band = cc_row.get("winnable_band") or [0, 0]
            obs_low = max(0.0, float(ceiling[0]) - observed_current)
            obs_high = max(0.0, float(ceiling[1]) - observed_current)
            obs_low, obs_high = min(obs_low, obs_high), max(obs_low, obs_high)
            entry["expected_current_clicks"] = int(exp_current)
            entry["expected_winnable_band"] = [int(exp_band[0]), int(exp_band[1])]
            entry["observed_winnable_band"] = [
                int(round(obs_low)),
                int(round(obs_high)),
            ]
            port_exp_current += float(exp_current)
            port_exp_low += float(exp_band[0])
            port_exp_high += float(exp_band[1])
            port_obs_low += obs_low
            port_obs_high += obs_high
        reports.append(entry)

    portfolio: dict[str, Any] = {
        "observed_current_clicks": int(round(port_obs)),
    }
    if cc_by_cluster:
        portfolio["expected_current_clicks"] = int(round(port_exp_current))
        portfolio["expected_winnable_band"] = [
            int(round(port_exp_low)),
            int(round(port_exp_high)),
        ]
        portfolio["observed_winnable_band"] = [
            int(round(port_obs_low)),
            int(round(port_obs_high)),
        ]

    return {
        "total_sc_rows": len(sc["rows"]),
        "matched_queries": matched,
        "anchored_to_click_ceiling": bool(cc_by_cluster),
        "portfolio": portfolio,
        "clusters": reports,
        "unmatched_queries": sorted(set(unmatched)),
    }


# --- AI citations override --------------------------------------------------


def _competitor_split(
    weights: dict[str, float], total: float, limit: int
) -> list[dict[str, Any]]:
    """Competitor domains by demand-weighted citation share, longest tail folded."""
    rows = [
        {"domain": dom, "share": round(100.0 * wt / total, 4)}
        for dom, wt in weights.items()
        if dom != _CLIENT_KEY and wt > 0
    ]
    rows.sort(key=lambda r: (-r["share"], r["domain"]))
    if len(rows) > limit:
        head = rows[:limit]
        tail_share = round(sum(r["share"] for r in rows[limit:]), 4)
        head.append({"domain": "other", "share": tail_share})
        return head
    return rows


def _ai_citations_override(
    ai: dict[str, Any],
    client_domain: str,
    keywords: list[dict[str, Any]],
    clusters: list[dict[str, Any]],
    norm_to_kw: dict[str, int],
    kw_to_cluster: dict[int, int],
    expected_share: dict[int, float],
) -> dict[str, Any]:
    """Measure the client's citation share and the competitor split from observations.

    Each observed query contributes a weight equal to its search volume (or one when
    the query is not in the corpus). Within a query, each of its citations carries an
    equal fraction of that weight, so the client's share and every competitor's share
    sum to 100. Per cluster the same is computed over the queries that map to it.
    """
    port_weights: dict[str, float] = {}
    port_total = 0.0
    cluster_weights: dict[int, dict[str, float]] = {}
    cluster_total: dict[int, float] = {}
    observed_queries = 0
    unmatched: list[str] = []
    explicit_client = False

    for row in ai["rows"]:
        kwidx = norm_to_kw.get(_norm(row["query"]))
        if kwidx is None:
            weight = 1.0
            ci = None
            unmatched.append(row["query"])
        else:
            weight = _keyword_volume(keywords[kwidx])
            ci = kw_to_cluster.get(kwidx)
        cites = row["citations"]
        n = len(cites)
        if n == 0:
            continue
        observed_queries += 1
        per = weight / n
        for c in cites:
            is_client = c.get("is_client")
            if is_client is None:
                is_client = _is_client_domain(c["domain"], client_domain)
            elif is_client:
                explicit_client = True
            key = _CLIENT_KEY if is_client else _norm_domain(c["domain"])
            port_weights[key] = port_weights.get(key, 0.0) + per
            if ci is not None:
                cw = cluster_weights.setdefault(ci, {})
                cw[key] = cw.get(key, 0.0) + per
        port_total += weight
        if ci is not None:
            cluster_total[ci] = cluster_total.get(ci, 0.0) + weight

    # The client share is only meaningful if the client could be identified, either
    # from a non-empty client_domain or from an explicit is_client flag on a citation.
    # Without that, a 0 share is "unknown", not a measured zero, so say so rather than
    # report a confident 0 next to a competitor split that sums to 100.
    client_identified = bool(client_domain) or explicit_client
    portfolio = {
        "observed_queries": observed_queries,
        "client_identified": client_identified,
        "observed_citation_share": round(
            100.0 * port_weights.get(_CLIENT_KEY, 0.0) / port_total, 4
        )
        if port_total
        else 0.0,
        "competitor_split": _competitor_split(port_weights, port_total, MAX_COMPETITORS)
        if port_total
        else [],
    }

    reports: list[dict[str, Any]] = []
    for ci in sorted(cluster_weights):
        total = cluster_total.get(ci, 0.0)
        weights = cluster_weights[ci]
        reports.append(
            {
                "cluster_index": ci,
                "head": clusters[ci].get("head", ""),
                "observed_citation_share": round(
                    100.0 * weights.get(_CLIENT_KEY, 0.0) / total, 4
                )
                if total
                else 0.0,
                "expected_share": round(expected_share[ci], 4)
                if ci in expected_share
                else None,
                "competitor_split": _competitor_split(weights, total, MAX_COMPETITORS)
                if total
                else [],
            }
        )

    warnings: list[str] = []
    if not client_identified:
        warnings.append(
            "client could not be identified (no client_domain and no is_client flag); "
            "the observed client citation share reads 0 but is undetermined"
        )

    return {
        "surfaces": ai["surfaces"],
        "portfolio": portfolio,
        "clusters": reports,
        "unmatched_queries": sorted(set(unmatched)),
        "warnings": warnings,
    }


# --- entry point ------------------------------------------------------------


def live_wire(
    state: dict[str, Any], capture: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Write the observed overlay to the run-state from a parsed capture.

    ``capture`` is the mapping returned by ``load_capture``. Without it the module
    cannot run, since observed data is the whole point; raise ``ModuleError`` so a
    misconfigured pipeline fails loudly rather than writing an empty observed slot.
    """
    if not isinstance(capture, dict):
        raise ModuleError("live_wire needs a parsed capture; none was provided")
    engine = state.get("engine")
    if not isinstance(engine, dict):
        raise ModuleError("live_wire needs the engine analysis; engine is empty")
    keywords = engine.get("keywords")
    clusters = engine.get("clusters")
    if not isinstance(keywords, list) or not isinstance(clusters, list) or not clusters:
        raise ModuleError("engine analysis has no clusters to work on")

    client_domain = capture.get("client_domain", "")
    norm_to_kw, kw_to_cluster = _keyword_maps(keywords, clusters)
    cc_by_cluster = _click_ceiling_by_cluster(state)
    expected_share = _expected_share_by_cluster(state)

    overrides: dict[str, Any] = {}
    capture_summary: dict[str, Any] = {
        "client_domain": client_domain,
        "version": capture.get("version", ""),
    }

    if "search_console" in capture:
        sc = capture["search_console"]
        overrides["click_ceiling"] = _search_console_override(
            sc, keywords, clusters, norm_to_kw, kw_to_cluster, cc_by_cluster
        )
        capture_summary["search_console"] = {
            "present": True,
            "date_range": sc.get("date_range", ""),
            "rows": len(sc["rows"]),
        }
    else:
        capture_summary["search_console"] = {"present": False}

    if "ai_citations" in capture:
        ai = capture["ai_citations"]
        overrides["citation_grid"] = _ai_citations_override(
            ai,
            client_domain,
            keywords,
            clusters,
            norm_to_kw,
            kw_to_cluster,
            expected_share,
        )
        capture_summary["ai_citations"] = {
            "present": True,
            "surfaces": ai.get("surfaces", []),
            "rows": len(ai["rows"]),
        }
    else:
        capture_summary["ai_citations"] = {"present": False}

    state["modules"]["live_wire"] = {
        "mode": "observed",
        "opt_in": True,
        "capture": capture_summary,
        "reads": {
            "click_ceiling": bool(cc_by_cluster),
            "citation_grid": bool(expected_share),
        },
        "overrides": overrides,
        "method_note": (
            "Live Wire pairs observed data with the offline estimate; it never "
            "overwrites the expected slots. Observed current clicks come from a "
            "Search Console export and re-anchor the Click Ceiling band (ceiling "
            "minus measured current). The observed citation share and competitor "
            "split come from AI-surface observations and are demand-weighted; they "
            "measure the client's share of real citations, which is a different "
            "quantity from Citation Grid's within-portfolio expected share. Queries "
            "that do not match the corpus are listed under unmatched_queries."
        ),
        "positioning_note": (
            "Observed figures are only as representative as the capture behind them. "
            "AI answer surfaces vary by session and personalization and are not "
            "reproducible; treat the citation share as a sample, not a guarantee."
        ),
    }
    return state
