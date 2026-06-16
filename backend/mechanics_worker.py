"""
力学仿真独立Worker进程 - 重构版本

将 WaterWheelSimulator 仿真计算放入独立进程，避免阻塞主事件循环。
使用 multiprocessing.Queue 进行任务分发与结果回传。

使用方式：
    worker = MechanicsWorker()
    worker.start()
    task_id = worker.submit_task(sim_input_dict, geometry_dict, material_dict)
    result = worker.wait_result(task_id, timeout=5.0)
    worker.stop()
"""
import multiprocessing as mp
import time
import uuid
from typing import Dict, Optional, Any
from dataclasses import asdict

from mechanics import (
    WaterWheelSimulator, SimulationInput,
    WaterWheelGeometry, MaterialProperties,
    SimulationOutput,
)


class MechanicsWorker:
    """
    力学仿真独立Worker进程管理器
    负责在单独进程中执行计算密集型的水车力学仿真
    """

    POISON_PILL = "__POISON__"

    def __init__(self, queue_size: int = 100):
        self._task_queue: mp.Queue = mp.Queue(maxsize=queue_size)
        self._result_queue: mp.Queue = mp.Queue(maxsize=queue_size)
        self._process: Optional[mp.Process] = None
        self._pending_tasks: Dict[str, float] = {}
        self._results_cache: Dict[str, Any] = {}
        self._is_running = False
        self._timeout_s = 30.0

    @staticmethod
    def _worker_loop(task_queue: mp.Queue, result_queue: mp.Queue):
        """
        Worker进程主循环 - 在独立进程中执行
        从task_queue取任务→执行仿真→结果写入result_queue
        """
        simulator_cache: Dict[str, WaterWheelSimulator] = {}

        while True:
            try:
                msg = task_queue.get()
                if msg == MechanicsWorker.POISON_PILL:
                    break

                task_id, payload = msg
                start_ts = time.time()
                try:
                    sim_input_dict = payload["sim_input"]
                    geom_dict = payload["geometry"]
                    mat_dict = payload["material"]
                    cache_key = payload.get("cache_key")

                    geom = WaterWheelGeometry(**geom_dict)
                    mat = MaterialProperties(**mat_dict)
                    sim_input = SimulationInput(**sim_input_dict)

                    if cache_key and cache_key in simulator_cache:
                        simulator = simulator_cache[cache_key]
                    else:
                        simulator = WaterWheelSimulator(geometry=geom, material=mat)
                        if cache_key:
                            simulator_cache[cache_key] = simulator

                    output = simulator.simulate(sim_input)
                    elapsed = time.time() - start_ts

                    result_queue.put((
                        task_id,
                        {
                            "status": "success",
                            "result": asdict(output),
                            "elapsed_s": round(elapsed, 6),
                            "worker_pid": mp.current_process().pid,
                        },
                    ))
                except Exception as e:
                    elapsed = time.time() - start_ts
                    result_queue.put((
                        task_id,
                        {
                            "status": "error",
                            "error": str(e),
                            "elapsed_s": round(elapsed, 6),
                            "worker_pid": mp.current_process().pid,
                        },
                    ))
            except Exception as loop_e:
                try:
                    result_queue.put(("__SYSTEM__", {"status": "fatal", "error": str(loop_e)}))
                except Exception:
                    pass

    def start(self) -> int:
        """
        启动Worker进程，返回进程PID
        """
        if self._is_running:
            return self._process.pid if self._process else -1

        self._process = mp.Process(
            target=MechanicsWorker._worker_loop,
            args=(self._task_queue, self._result_queue),
            daemon=True,
            name="mechanics-worker",
        )
        self._process.start()
        self._is_running = True
        self._results_cache.clear()
        self._pending_tasks.clear()
        return self._process.pid

    def stop(self, timeout: float = 3.0):
        """
        优雅停止Worker进程
        """
        if not self._is_running:
            return
        try:
            self._task_queue.put(MechanicsWorker.POISON_PILL, timeout=0.5)
        except Exception:
            pass

        if self._process:
            self._process.join(timeout=timeout)
            if self._process.is_alive():
                self._process.terminate()
                self._process.join(timeout=1.0)

        self._is_running = False
        self._pending_tasks.clear()

    def submit_task(
        self,
        sim_input: Dict,
        geometry: Dict,
        material: Dict,
        cache_key: Optional[str] = None,
    ) -> str:
        """
        提交仿真任务到Worker进程
        返回任务ID用于后续获取结果
        """
        if not self._is_running:
            raise RuntimeError("MechanicsWorker not started, call start() first")

        task_id = str(uuid.uuid4())
        payload = {
            "sim_input": sim_input,
            "geometry": geometry,
            "material": material,
            "cache_key": cache_key,
        }
        self._task_queue.put((task_id, payload))
        self._pending_tasks[task_id] = time.time()
        return task_id

    def _drain_results(self):
        """
        从结果队列中取出所有可用结果并缓存
        """
        while not self._result_queue.empty():
            try:
                task_id, result = self._result_queue.get_nowait()
                self._results_cache[task_id] = result
                self._pending_tasks.pop(task_id, None)
            except Exception:
                break

    def wait_result(self, task_id: str, timeout: float = 5.0) -> Optional[Dict]:
        """
        等待指定任务的结果
        超时返回 None，任务失败返回 error 字段
        """
        if task_id in self._results_cache:
            return self._results_cache.pop(task_id)

        self._drain_results()
        if task_id in self._results_cache:
            return self._results_cache.pop(task_id)

        deadline = time.time() + timeout
        while time.time() < deadline:
            self._drain_results()
            if task_id in self._results_cache:
                return self._results_cache.pop(task_id)
            if task_id not in self._pending_tasks:
                return None
            time.sleep(0.01)

        return None

    def is_alive(self) -> bool:
        return self._is_running and self._process and self._process.is_alive()

    @property
    def pending_count(self) -> int:
        self._drain_results()
        return len(self._pending_tasks)

    @property
    def result_cache_size(self) -> int:
        return len(self._results_cache)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False


class MechanicsWorkerPool:
    """
    多Worker进程池 - 用于大规模并行仿真
    """

    def __init__(self, num_workers: int = 2):
        self.num_workers = max(1, num_workers)
        self._workers = [MechanicsWorker() for _ in range(self.num_workers)]
        self._round_robin = 0

    def start(self):
        for w in self._workers:
            w.start()

    def stop(self):
        for w in self._workers:
            w.stop()

    def submit_task(self, *args, **kwargs) -> str:
        worker = self._workers[self._round_robin % self.num_workers]
        self._round_robin += 1
        return worker.submit_task(*args, **kwargs)

    def wait_result(self, task_id: str, timeout: float = 5.0):
        for w in self._workers:
            res = w.wait_result(task_id, timeout=0.05)
            if res is not None:
                return res
        return None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False
