from concurrent.futures import ThreadPoolExecutor



def run_with_timeout(fn, seconds):
    with ThreadPoolExecutor() as pool:
        future = pool.submit(fn)
        return future.result(timeout=seconds)


def invoke_with_global_timeout(graph,initial_state,config,seconds):
    with ThreadPoolExecutor() as executor:

        future = executor.submit(
            graph.invoke,
            initial_state,
            config
        )

        return future.result(timeout=seconds)