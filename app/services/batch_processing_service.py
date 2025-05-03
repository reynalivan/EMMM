# app/services/batch_processing_service.py

from PyQt6.QtCore import QObject, pyqtSignal, QThreadPool
from app.services.mod_management_service import ModManagementService
from app.utils.async_utils import Worker
from app.utils.logger_utils import logger
from app.utils.async_utils import AsyncStatusManager
import os


class BatchProcessingService(QObject):
    """Service to perform batch enable/disable operations asynchronously."""

    batchOperationFinished = pyqtSignal(dict)
    show_notification = pyqtSignal(str, str)  # title, content

    def __init__(
        self, mod_manager: ModManagementService, parent: QObject | None = None
    ):
        super().__init__(parent)
        self._mod_manager = mod_manager
        self._status_manager = AsyncStatusManager(self)

    def batch_set_mod_enabled_async(
        self, item_paths: list[str], enable: bool, item_type: str
    ):
        """Perform batch enable/disable operation."""
        processed = 0
        success = 0
        failed = 0

        def on_worker_result(result: dict):
            logger.debug(f"Worker result: {result}")
            nonlocal processed, success, failed
            processed += 1
            if result.get("success"):
                success += 1
            else:
                failed += 1
            if processed == len(item_paths):
                self.batchOperationFinished.emit(
                    {
                        "processed": processed,
                        "success": success,
                        "failed": failed,
                    }
                )

        def on_worker_error(err_info):
            nonlocal processed, failed
            processed += 1
            failed += 1
            if processed == len(item_paths):
                self.batchOperationFinished.emit(
                    {
                        "processed": processed,
                        "success": success,
                        "failed": failed,
                    }
                )

        for path in item_paths:
            if not path or not os.path.isdir(path):
                processed += 1
                failed += 1
                continue
            worker = Worker(
                self._mod_manager._set_mod_enabled_task, path, enable, item_type
            )
            worker.signals.result.connect(on_worker_result)
            worker.signals.error.connect(on_worker_error)
            QThreadPool.globalInstance().start(worker)

    def batch_enable_disable_items(
        self, item_paths: list[str], enable: bool, item_type: str
    ):
        if item_type not in ("object", "folder"):
            raise ValueError(f"Invalid item_type: {item_type}")
        self._status_manager.begin_batch(item_paths)
        self.batch_set_mod_enabled_async(item_paths, enable, item_type)

    def _on_batch_operation_finished(self, summary: dict):
        processed = summary.get("processed", 0)
        success = summary.get("success", 0)
        failed = summary.get("failed", 0)

        logger.info(
            f"Batch Operation Finished. Processed={processed}, Success={success}, Failed={failed}"
        )

        # Emit infobar atau notification ke Panel
        title = "Batch Operation Completed"
        content = f"{success} succeeded, {failed} failed out of {processed} items."
        self.show_notification.emit(
            title, content
        )  # Signal ini perlu dihubungkan ke Panel, kalau belum

        # Update all pending items back to interactive
        self._status_manager.end_batch()
