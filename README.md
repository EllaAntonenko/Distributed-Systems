- Tunable write concern `w` (semi-synchronous replication):
  - `w=1` — only master required
  - `w=2` — master + 1 secondary
  - ... up to `w=n` — all nodes
- Master assigns `seq` (total ordering) and `id` (deduplication)
- Thread-safe storage (locks) on master & secondaries
- Parallel replication (ThreadPoolExecutor)
- Artificial delay on secondaries via `SECONDARY_DELAY_SEC` (to emulate inconsistency)
- Increased timeout for replication (`SECONDARY_TIMEOUT=30s`)

```bash
docker compose up --build