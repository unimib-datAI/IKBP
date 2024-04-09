import time
import psutil
import torch
import threading
import signal

class TimeoutException(Exception):
    pass

class MemoryLimitExceededException(Exception):
    pass

class GPUMemoryLimitExceededException(Exception):
    pass

class WatchdogThread(threading.Thread):
    def __init__(self, timeout, memory, gpu, loop_time = 10, alarm_time = 1, stop=True, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.timeout = timeout
        self.memory = memory
        self.gpu = gpu
        self.loop_time = loop_time
        self.alarm_time = alarm_time
        self.stop = stop

        self.stop_flag = False
        self.exception = None

    def set_handler(self):
        def handler(signum, frame):
            if self.stop:
                self.stop_flag = True
            print('raising', self.exception)
            raise self.exception
        signal.signal(signal.SIGALRM, handler)

    def reset_time(self):
        self.time_limit = time.time() + self.timeout

    def get_time(self):
        return time.time()

    def get_memory(self):
        return psutil.Process().memory_info().rss

    def get_gpu(self):
        return torch.cuda.memory_allocated()

    def check(self):

        time = self.get_time()
        mem = self.get_memory()
        gpu = self.get_gpu()

        if time > self.time_limit:
            self.exception = TimeoutException("Function execution time exceeded: {} > {}".format(time, self.time_limit))
        if mem > self.memory:
            self.exception = MemoryLimitExceededException("Memory usage exceeded: {} > {}".format(mem, self.memory))
        if gpu > self.gpu:
            self.exception = GPUMemoryLimitExceededException("GPU Memory usage exceeded: {} > {}".format(gpu, self.gpu))

        if self.exception is not None:
            signal.alarm(self.alarm_time)

    def run(self):
        self.reset_time()
        while not self.stop_flag:
            self.check()
            time.sleep(self.loop_time)
