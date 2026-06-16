"""
力学仿真独立Worker进程模块
使用多进程隔离力学仿真计算，避免阻塞主线程

核心组件:
1. MechanicsWorkerProcess - 独立Worker进程管理器
2. AsyncSimulationClient - 异步仿真客户端
3. SimulationTask - 仿真任务封装

使用场景:
- 大规模参数扫描仿真
- 多工况并行计算
- 实时交互下的后台计算
"""
import multiprocessing
import queue
import threading
import time
from dataclasses import dataclass, asdict, is_dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Callable
from enum import Enum
import uuid

from mechanics import (
    WaterWheelSimulator, SimulationInput, SimulationOutput,
    WaterWheelGeometry, MaterialProperties
)


__all__ = [
    "SimulationTaskStatus",
    "SimulationTask",
    "MechanicsWorkerProcess",
    "AsyncSimulationClient",
    "create_worker_pool",
    "run_simulation_async",
]


class SimulationTaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class SimulationTask:
    task_id: str
    input_data: Dict[str, Any]
    status: SimulationTaskStatus = SimulationTaskStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    priority: int = 5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "input_data": self.input_data,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "priority": self.priority,
        }


def _worker_process(
    task_queue: multiprocessing.Queue,
    result_queue: multiprocessing.Queue,
    stop_event: multiprocessing.Event,
    worker_id: int,
):
    simulator = WaterWheelSimulator()

    while not stop_event.is_set():
        try:
            task = task_queue.get(timeout=0.1)
        except queue.Empty:
            continue

        if task is None:
            break

        task["started_at"] = time.time()
        result_queue.put({
            "type": "status",
            "task_id": task["task_id"],
            "status": "running",
            "worker_id": worker_id,
        })

        try:
            input_params = task["input"]
            sim_input = SimulationInput(
                rotational_speed=input_params.get("rotational_speed", 15.0),
                water_level_diff=input_params.get("water_level_diff", 2.0),
                water_lift=input_params.get("water_lift", 0.0),
                chain_wear_factor=input_params.get("chain_wear_factor", 0.0),
                lubrication_factor=input_params.get("lubrication_factor", 1.0),
                temperature=input_params.get("temperature", 20.0),
            )

            if "geometry" in input_params:
                geom = WaterWheelGeometry(**input_params["geometry"])
                mat = MaterialProperties(**input_params.get("material", {}))
                simulator = WaterWheelSimulator(geometry=geom, material=mat)

            sim_output = simulator.simulate(sim_input)

            result_dict = _simulation_output_to_dict(sim_output)

            result_queue.put({
                "type": "result",
                "task_id": task["task_id"],
                "status": "completed",
                "result": result_dict,
                "worker_id": worker_id,
                "completed_at": time.time(),
            })

        except Exception as e:
            result_queue.put({
                "type": "result",
                "task_id": task["task_id"],
                "status": "failed",
                "error": str(e),
                "worker_id": worker_id,
                "completed_at": time.time(),
            })


def _simulation_output_to_dict(output: SimulationOutput) -> Dict[str, Any]:
    result = {}
    for field_name in output.__dataclass_fields__:
        value = getattr(output, field_name)
        if hasattr(value, 'value'):
            result[field_name] = value.value
        elif hasattr(value, 'tolist'):
            result[field_name] = value.tolist()
        else:
            result[field_name] = value
    return result


class MechanicsWorkerProcess:
    def __init__(self, num_workers: int = 2):
        self.num_workers = max(1, min(8, num_workers))
        self._task_queue: multiprocessing.Queue = multiprocessing.Queue()
        self._result_queue: multiprocessing.Queue = multiprocessing.Queue()
        self._stop_event: multiprocessing.Event = multiprocessing.Event()
        self._workers: List[multiprocessing.Process] = []
        self._tasks: Dict[str, SimulationTask] = {}
        self._result_callbacks: Dict[str, Callable] = {}
        self._result_handler_thread: Optional[threading.Thread] = None
        self._running = False

    def start(self):
        if self._running:
            return

        self._stop_event.clear()
        self._workers = []

        for i in range(self.num_workers):
            p = multiprocessing.Process(
                target=_worker_process,
                args=(self._task_queue, self._result_queue, self._stop_event, i),
                daemon=True,
            )
            p.start()
            self._workers.append(p)

        self._result_handler_thread = threading.Thread(
            target=self._result_handler_loop,
            daemon=True,
        )
        self._result_handler_thread.start()
        self._running = True

    def stop(self):
        if not self._running:
            return

        self._stop_event.set()
        for _ in self._workers:
            self._task_queue.put(None)

        for p in self._workers:
            p.join(timeout=2.0)
            if p.is_alive():
                p.terminate()

        self._running = False
        self._workers = []

    def _result_handler_loop(self):
        while self._running and not self._stop_event.is_set():
            try:
                msg = self._result_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            task_id = msg["task_id"]
            task = self._tasks.get(task_id)
            if not task:
                continue

            if msg["type"] == "status" and msg["status"] == "running":
                task.status = SimulationTaskStatus.RUNNING
                task.started_at = time.time()
            elif msg["type"] == "result":
                if msg["status"] == "completed":
                    task.status = SimulationTaskStatus.COMPLETED
                    task.result = msg["result"]
                elif msg["status"] == "failed":
                    task.status = SimulationTaskStatus.FAILED
                    task.error = msg["error"]
                task.completed_at = msg["completed_at"]

                callback = self._result_callbacks.pop(task_id, None)
                if callback:
                    try:
                        callback(task)
                    except Exception:
                        pass

    def submit_task(
        self,
        sim_input: Dict[str, Any],
        callback: Optional[Callable[[SimulationTask], Any]] = None,
        priority: int = 5,
    ) -> str:
        if not self._running:
            raise RuntimeError("Worker pool is not started. Call start() first.")

        task_id = str(uuid.uuid4())
        task = SimulationTask(
            task_id=task_id,
            input_data=sim_input,
            priority=priority,
        )
        self._tasks[task_id] = task

        if callback:
            self._result_callbacks[task_id] = callback

        self._task_queue.put({
            "task_id": task_id,
            "input": sim_input,
            "priority": priority,
        })

        return task_id

    def get_task(self, task_id: str) -> Optional[SimulationTask]:
        return self._tasks.get(task_id)

    def wait_for_task(self, task_id: str, timeout: float = 30.0) -> Optional[SimulationTask]:
        start = time.time()
        while time.time() - start < timeout:
            task = self._tasks.get(task_id)
            if task and task.status in (
                SimulationTaskStatus.COMPLETED,
                SimulationTaskStatus.FAILED,
                SimulationTaskStatus.CANCELLED,
            ):
                return task
            time.sleep(0.05)
        return self._tasks.get(task_id)

    def run_batch(
        self,
        sim_inputs: List[Dict[str, Any]],
        timeout_per_task: float = 10.0,
    ) -> List[SimulationTask]:
        task_ids = [self.submit_task(inp) for inp in sim_inputs]
        results = []
        for tid in task_ids:
            task = self.wait_for_task(tid, timeout=timeout_per_task)
            results.append(task)
        return results

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


class AsyncSimulationClient:
    def __init__(self, num_workers: int = 2):
        self._worker = MechanicsWorkerProcess(num_workers=num_workers)

    def start(self):
        self._worker.start()

    def stop(self):
        self._worker.stop()

    def simulate(
        self,
        rotational_speed: float = 15.0,
        water_level_diff: float = 2.0,
        chain_wear_factor: float = 0.0,
        geometry: Optional[Dict] = None,
        material: Optional[Dict] = None,
        callback: Optional[Callable] = None,
    ) -> str:
        sim_input = {
            "rotational_speed": rotational_speed,
            "water_level_diff": water_level_diff,
            "chain_wear_factor": chain_wear_factor,
        }
        if geometry:
            sim_input["geometry"] = geometry
        if material:
            sim_input["material"] = material
        return self._worker.submit_task(sim_input, callback=callback)

    def get_result(self, task_id: str, timeout: float = 30.0) -> Optional[Dict]:
        task = self._worker.wait_for_task(task_id, timeout=timeout)
        if task and task.status == SimulationTaskStatus.COMPLETED:
            return task.result
        return None

    def optimize_speed_async(
        self,
        water_level_diff: float,
        target_area: float,
        min_speed: float = 5.0,
        max_speed: float = 30.0,
        num_points: int = 20,
        callback: Optional[Callable] = None,
    ) -> List[str]:
        import numpy as np
        speeds = np.linspace(min_speed, max_speed, num_points)
        task_ids = []
        for speed in speeds:
            task_ids.append(self.simulate(
                rotational_speed=speed,
                water_level_diff=water_level_diff,
            ))
        return task_ids

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


def create_worker_pool(num_workers: int = 2) -> MechanicsWorkerProcess:
    worker = MechanicsWorkerProcess(num_workers=num_workers)
    worker.start()
    return worker


def run_simulation_async(
    sim_input: Dict[str, Any],
    callback: Optional[Callable] = None,
) -> str:
    if not hasattr(run_simulation_async, "_worker"):
        run_simulation_async._worker = create_worker_pool(num_workers=2)

    return run_simulation_async._worker.submit_task(sim_input, callback=callback)


def run_simulation_sync(sim_input: Dict[str, Any], timeout: float = 10.0) -> Optional[Dict]:
    worker = MechanicsWorkerProcess(num_workers=1)
    with worker:
        task_id = worker.submit_task(sim_input)
        task = worker.wait_for_task(task_id, timeout=timeout)
        if task and task.status == SimulationTaskStatus.COMPLETED:
            return task.result
        return None


if __name__ == "__main__":
    print("Testing mechanics worker...")

    with MechanicsWorkerProcess(num_workers=2) as worker:
        task_id = worker.submit_task({
            "rotational_speed": 15.0,
            "water_level_diff": 2.0,
        })
        print(f"Submitted task: {task_id}")

        task = worker.wait_for_task(task_id, timeout=5.0)
        if task:
            print(f"Task status: {task.status.value}")
            if task.result:
                print(f"Overall efficiency: {task.result['overall_efficiency']}")
                print(f"Drive torque: {task.result['drive_torque']}")
            elif task.error:
                print(f"Error: {task.error}")

    print("Done.")
