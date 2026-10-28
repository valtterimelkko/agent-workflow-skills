<!-- Companion to routing.md. Read it before adding, removing or re-ordering a route. Numbers move, so re-read the live sources rather than trusting anything written here. -->

# Why routing is shaped the way it is

`routing.md` says *what* the routes are. This file says *why*, so an edit keeps the intent instead of reacting to a price list.

**List price is the wrong yardstick on subscription providers.** Providers meter differently: rolling windows, per-model request allowances, weighted caps, and pay-per-use balances. A route can be cheap or dear in *plan* terms, which can differ wildly from the per-token price, so read the provider's own dashboard rather than a price list. A metered pay-per-use route is never a default and needs the operator's explicit say-so.

**A fallback on the same pool is not a fallback.** If two routes share a provider, inference path or quota pool, one cannot rescue the other: the same outage or exhausted window takes both. Same-model twins on different pools are *balancing alternates*, not failovers — compare measured headroom and pick. A real fallback lives on a different pool.

**Before you edit a route table:**

1. Read the request allowance, not the price, from the provider's own plan page or dashboard, and record where you read it.
2. Probe the exact selector with one tiny prompt before relying on it — availability changes without notice and pages lag.
3. Check capability and fit: context window, vision, speed, the thinking levels actually advertised.
4. Check peak multipliers and window resets for every pool you use.
5. Keep family diversity: reviewers must come from a different family than the implementer, so never let the roster collapse to one family.
6. Check pool headroom and your own burn before every dispatch; a parent on the same pool drains it faster than the read suggests.
7. Record the change with the date and the evidence, and keep the Class 1 / 2 / 3 structure unless the operator restructures it.

**Catalogue freshness is part of routing.** Every selector must exist in the live catalogue: a stale SDK or cached catalogue keeps retired models listed and hides new ones. After any catalogue or SDK change, re-read `/models` for every selector you rely on.
