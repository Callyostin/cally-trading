import asyncio
from typing import Dict, Coroutine, Any
from utils.logger import logger

class TaskManager:
    def __init__(self):
        self._tasks: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def start_task(self, name: str, coro: Coroutine) -> bool:
        """Starts a background task if it's not already running."""
        async with self._lock:
            if name in self._tasks and not self._tasks[name].done():
                logger.warning(f"Task '{name}' is already running. Skipping duplicate.")
                return False
            
            task = asyncio.create_task(self._run_with_error_handling(name, coro))
            self._tasks[name] = task
            logger.info(f"Started background task '{name}'.")
            return True

    async def _run_with_error_handling(self, name: str, coro: Coroutine):
        """Wrapper to handle exceptions in background tasks gracefully."""
        try:
            await coro
        except asyncio.CancelledError:
            logger.info(f"Task '{name}' was cancelled.")
        except Exception as e:
            logger.exception(f"Unhandled exception in task '{name}': {e}")
        finally:
            # We don't remove it from self._tasks here to keep a record, 
            # but start_task checks if it's done().
            logger.info(f"Task '{name}' has stopped.")

    async def cancel_task(self, name: str):
        """Cancels a specific background task."""
        async with self._lock:
            if name in self._tasks and not self._tasks[name].done():
                logger.info(f"Cancelling task '{name}'...")
                self._tasks[name].cancel()
                try:
                    await self._tasks[name]
                except asyncio.CancelledError:
                    pass
                logger.info(f"Task '{name}' successfully cancelled.")

    async def cancel_all(self):
        """Cancels all registered background tasks."""
        logger.info("Cancelling all background tasks...")
        tasks_to_cancel = []
        async with self._lock:
            for name, task in self._tasks.items():
                if not task.done():
                    tasks_to_cancel.append(name)
                    task.cancel()
        
        # Wait for all to finish cancelling
        for name in tasks_to_cancel:
            try:
                await self._tasks[name]
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error while cancelling task '{name}': {e}")
        logger.info("All background tasks cancelled.")

    def get_active_task_count(self) -> int:
        return sum(1 for task in self._tasks.values() if not task.done())

    def get_task_status(self) -> Dict[str, str]:
        return {name: "Running" if not task.done() else "Stopped" for name, task in self._tasks.items()}

# Global shared instance
task_manager = TaskManager()
