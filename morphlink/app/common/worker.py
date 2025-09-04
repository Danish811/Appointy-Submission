from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=4)

def submit_task(fn, *args, **kwargs):
    executor.submit(fn, *args, **kwargs)
