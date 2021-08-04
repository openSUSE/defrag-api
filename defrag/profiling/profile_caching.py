from typing import Any, List
import asyncio


async def profile_caching():
    with RedisPool() as conn:
        conn.flushall()
    test_redis_key = "profile_caching_redis_key"
    store = QStore(test_redis_key)

    async def fetch_items() -> List[Any]:
        print("Faking fetching operation for 2 secs...")
        return fake_fetched_items
    store.fetch_items = fetch_items

    def filter_fresh_items(fetch_items: List[Any]) -> List[Any]:
        return list(filter(lambda n: n % 2 == 0, fetch_items))
    store.filter_fresh_items = filter_fresh_items

    fake_fetched_items = [x for x in range(1, 1501)]
    fetched_items = await store.fetch_items()
    filtered = store.filter_fresh_items(fetched_items)
    await store.update_on_filtered_fresh(filtered)
    print(len(list(store.container)))

def main():
    asyncio.run(profile_caching())


if __name__ == "__main__":
    # Bringing defrag on PATH
    import os
    import sys
    p = os.path.abspath('.')
    sys.path.insert(1, p)
    # Profiling tools
    import cProfile
    import pstats
    from datetime import datetime
    # defrag modules
    from defrag.modules.helpers.caching import QStore
    from defrag.modules.db.redis import RedisPool
    # the profiling itself
    profiler = cProfile.Profile()
    profiler.enable()
    main()
    profiler.disable()
    stats = pstats.Stats(profiler).sort_stats('tottime')
    # output
    output_dir = os.environ["PROFILE_STATS_OUTPUT_DIR"]
    stats.dump_stats(
        f"{output_dir}{str(datetime.now())}.dat")
    stats.print_stats()
