# Copyright (C) 2018-2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

import os
import queue
import threading

from ..backend.backend import TelemetryBackend
from ..utils.message import Message

MAX_QUEUE_SIZE = 1000


class TelemetrySender:
    """
    Sends messages from a pool of daemon worker threads. Unlike ThreadPoolExecutor, whose workers are joined (and
    process all queued messages) at the interpreter exit, daemon threads do not delay the exit if there is no Internet
    connection.
    """

    def __init__(self, max_workers=None):
        # the same default as for ThreadPoolExecutor
        self.max_workers = max_workers or min(32, (os.cpu_count() or 1) + 4)
        self.queue_size = 0
        self._queue = queue.SimpleQueue()
        self._cond = threading.Condition()
        self._threads = []
        self._idle_workers = 0
        self._closed = False
        self._shutdown = False

    def send(self, backend: TelemetryBackend, message: Message):
        with self._cond:
            if self._closed or self._shutdown or self.queue_size >= MAX_QUEUE_SIZE:
                return  # dropping a message because the sender is stopped or the queue is full
            self.queue_size += 1
            self._queue.put((backend, message))
            try:
                if self._idle_workers > 0:
                    self._idle_workers -= 1
                elif len(self._threads) < self.max_workers:
                    thread = threading.Thread(target=self._worker, name='openvino_telemetry_sender', daemon=True)
                    thread.start()
                    self._threads.append(thread)
            except Exception as err:
                pass  # nosec

    def _worker(self):
        while True:
            try:
                backend, message = self._queue.get_nowait()
            except queue.Empty:
                with self._cond:
                    self._idle_workers += 1
                backend, message = self._queue.get()
            if backend is None or self._shutdown:
                return
            try:
                backend.send(message)
            except Exception as err:
                pass  # nosec
            with self._cond:
                if self._shutdown:
                    return
                self.queue_size -= 1
                self._cond.notify_all()

    def flush(self, timeout: float):
        """
        Waits up to timeout for the queued messages to be sent. Unlike force_shutdown, the sender keeps working.

        :param timeout: maximum time to wait for the queued messages to be sent
        :return: None
        """
        with self._cond:
            self._cond.wait_for(lambda: self.queue_size == 0, timeout)

    def close(self):
        """
        Stops accepting new messages. The worker threads exit after the already queued messages are sent, so the
        sender and its workers are released. Does not wait.

        :return: None
        """
        with self._cond:
            if self._closed or self._shutdown:
                return
            self._closed = True
            for _ in self._threads:
                self._queue.put((None, None))  # each worker exits when it gets this after the queued messages

    def force_shutdown(self, timeout: float):
        """
        Waits up to timeout for the queued messages to be sent, then stops the worker threads. Not yet sent messages
        are dropped. Messages which are being sent do not delay the interpreter exit as the workers are daemon threads.

        :param timeout: maximum time to wait for the queued messages to be sent
        :return: None
        """
        with self._cond:
            self._cond.wait_for(lambda: self.queue_size == 0, timeout)
            self._shutdown = True
            self.queue_size = 0
            for _ in self._threads:
                self._queue.put((None, None))  # wake up the workers so they can exit
