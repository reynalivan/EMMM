from pathlib import Path

from app.utils.logger_utils import logger


class WorkflowService:
    """
    Orchestrates complex, multi-step, and/or transactional workflows.
    This service contains the business logic for operations that involve
    multiple items or multiple services.
    """

    def __init__(self, mod_service, config_service):
        # --- Injected Services ---
        self.mod_service = mod_service
        self.config_service = config_service

    # --- Bulk Modification Workflows ---
    def execute_bulk_action(self, items: list, action_type: str, **kwargs) -> dict:
        """Flow 3.2: Handles simple bulk actions like enable, disable, or tag."""
        # Iterates through items, calls the appropriate ModService method for each,
        # and collects success/failure results.
        return {}

    # --- Creation Workflows ---
    def execute_creation(self, tasks: list, parent_path: Path) -> dict:
        """Flow 4.1.A: Creates multiple foldergrid items from a list of tasks."""
        # Iterates through tasks and calls mod_service.create_foldergrid_item for each.
        return {}

    def execute_object_creation(self, tasks: list, parent_path: Path, progress_callback=None) -> dict:
        """
        Flow 4.1.B Step 5: Orchestrates the creation of multiple objectlist items.
        """
        successful_creations = []
        failed_creations = []
        total_tasks = len(tasks)

        logger.info(f"Starting object creation workflow for {total_tasks} task(s).")

        for idx, task in enumerate(tasks):
            try:
                # Delegate the actual creation to ModService
                result = self.mod_service.create_manual_object(parent_path, task["data"])

                if result["success"]:
                    successful_creations.append(result["data"])
                else:
                    failed_creations.append({"task": task, "reason": result["error"]})

            except Exception as e:
                logger.error(f"Critical error during creation task {task}: {e}", exc_info=True)
                failed_creations.append({"task": task, "reason": str(e)})

            # Emit progress if a callback is provided
            if progress_callback:
                progress_callback.emit(idx + 1, total_tasks)

        return {"success": successful_creations, "failed": failed_creations}

    # --- High-Risk Transactional Workflows ---
    def apply_safe_mode(self, items: list, is_on: bool) -> dict:
        """Flow 6.1: Applies the Safe Mode state with rollback-on-failure logic."""
        # 1. Plan all required file system actions.
        # 2. Execute the plan, building an undo_log.
        # 3. If any step fails, execute the undo_log in reverse.
        return {}

    def apply_preset(self, items: list, preset_name: str) -> dict:
        """Flow 6.2.A: Applies a mod preset with rollback-on-failure logic."""
        # Similar to apply_safe_mode: Plan -> Execute with Undo -> Rollback.
        return {}

    # --- Randomization Workflows ---
    def apply_randomize(self, items: list) -> dict:
        """Flow 6.2.B: Disables all items in a list and enables one at random."""
        # A simpler bulk action that plans to disable all but one winner.
        return {}

    def apply_global_randomize(self, game_path: Path) -> dict:
        """Flow 6.2.B: Disables ALL mods in a game and enables one at random."""
        # 1. Recursively scans the entire game_path to find all valid mod folders.
        # 2. Plans and executes the randomization.
        return {}

    # --- Preset Management Workflows ---
    def rename_preset(self, old_name: str, new_name: str, game_path: Path) -> dict:
        """Flow 6.2.A: Renames a preset in config.ini and all relevant info.json files."""
        # A heavy operation that involves recursively scanning the mod directory.
        return {}

    def delete_preset(self, preset_name: str, game_path: Path) -> dict:
        """Flow 6.2.A: Deletes a preset from config.ini and all relevant info.json files."""
        # A heavy operation that involves recursively scanning the mod directory.
        return {}

    # --- Private/Internal Logic ---
    def _execute_rollback(self, undo_log: list):
        """A helper method to reverse a series of file operations after a failure."""
        return {}
