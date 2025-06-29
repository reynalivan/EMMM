# app/services/mod_service.py
import shutil
import uuid
import os
import json
import hashlib
import dataclasses
from pathlib import Path
from typing import Tuple
from app.utils.system_utils import SystemUtils

# Import models
from app.models.mod_item_model import (
    BaseModItem,
    ObjectItem,
    FolderItem,
    ModType,
    ModStatus,
    CharacterObjectItem,
    GenericObjectItem,
)

# Import constants for naming rules
from app.core.constants import (
    PROPERTIES_JSON_NAME,
    INFO_JSON_NAME,
    CONTEXT_OBJECTLIST,
    CONTEXT_FOLDERGRID,
    OBJECT_THUMBNAIL_SUFFIX,
    OBJECT_THUMBNAIL_EXACT,
    FOLDER_PREVIEW_PREFIX,
    SUPPORTED_IMAGE_EXTENSIONS,
    PIN_SUFFIX,
    DISABLED_PREFIX_PATTERN,
    DEFAULT_DISABLED_PREFIX,
)
from app.utils.logger_utils import logger

# Import other services for dependency injection
from .database_service import DatabaseService
from app.utils.image_utils import ImageUtils


class ModService:
    """Handles all atomic file system and JSON operations for a single mod item."""

    def __init__(
        self,
        database_service: DatabaseService,
        image_utils: ImageUtils,
        system_utils: SystemUtils,
    ):
        # --- Injected Services & Utilities ---
        self.database_service = database_service
        self.image_utils = image_utils
        self.system_utils = system_utils

    # --- Loading & Hydration ---
    def _parse_folder_name(self, folder_name: str) -> Tuple[str, ModStatus, bool]:
        """
        A robust helper to parse status and pin state from a folder name.
        Returns a tuple of (actual_name, status, is_pinned).
        """
        # Use regex for robust prefix matching (e.g., 'DISABLED ', 'disabled_')
        match = DISABLED_PREFIX_PATTERN.match(folder_name)
        if match:
            status = ModStatus.DISABLED
            # Remove the matched prefix part from the name
            clean_name = folder_name[match.end() :]
        else:
            status = ModStatus.ENABLED
            clean_name = folder_name

        # Check and remove pin suffix
        is_pinned = clean_name.lower().endswith(PIN_SUFFIX)
        if is_pinned:
            clean_name = clean_name[: -len(PIN_SUFFIX)]

        return clean_name.strip(), status, is_pinned

    def get_item_skeletons(self, path: Path, context: str) -> dict:
        """
        Flow 2.2: Scans a directory to create skeleton models quickly and robustly.
        """
        logger.info(f"Scanning for skeletons in '{path}' with context '{context}'")
        skeletons = []
        try:
            with os.scandir(path) as it:
                for entry in it:
                    if not entry.is_dir():
                        continue

                    # 1. Parse name, status, and pin state using the helper
                    actual_name, status, is_pinned = self._parse_folder_name(entry.name)
                    item_path = Path(entry.path)

                    # 2. Generate a stable, unique ID using relative path and SHA1
                    relative_path = item_path.relative_to(path)
                    item_id = hashlib.sha1(
                        relative_path.as_posix().encode("utf-8")
                    ).hexdigest()

                    # 3. Create the appropriate skeleton model based on context
                    skeleton: BaseModItem | None = None
                    if context == CONTEXT_OBJECTLIST:
                        object_type = ModType.OTHER
                        # Peek into properties.json just to get the type
                        try:
                            props_path = item_path / PROPERTIES_JSON_NAME
                            if props_path.is_file():
                                with open(props_path, "r", encoding="utf-8") as f:
                                    object_type = ModType(
                                        json.load(f).get("object_type", "Other")
                                    )
                        except (json.JSONDecodeError, KeyError, ValueError) as e:
                            logger.warning(
                                f"Could not parse object_type for '{actual_name}': {e}. Defaulting to 'Other'."
                            )

                        # Instantiate the correct skeleton class based on type
                        skeleton_class = (
                            CharacterObjectItem
                            if object_type == ModType.CHARACTER
                            else GenericObjectItem
                        )
                        skeleton = skeleton_class(
                            id=item_id,
                            actual_name=actual_name,
                            folder_path=item_path,
                            status=status,
                            is_pinned=is_pinned,
                            object_type=object_type,
                        )

                    elif context == CONTEXT_FOLDERGRID:
                        skeleton = FolderItem(
                            id=item_id,
                            actual_name=actual_name,
                            folder_path=item_path,
                            status=status,
                            is_pinned=is_pinned,
                        )

                    if skeleton:
                        skeletons.append(skeleton)

            return {"success": True, "items": skeletons, "error": None}

        except FileNotFoundError:
            msg = f"Invalid path specified for skeleton scan: {path}"
            logger.error(msg)
            return {"success": False, "items": [], "error": msg}
        except PermissionError:
            msg = f"Permission denied while scanning: {path}"
            logger.error(msg)
            return {"success": False, "items": [], "error": msg}

    def hydrate_item(
        self, skeleton_item: BaseModItem, game_name: str, context: str
    ) -> BaseModItem:
        """
        Flow 2.2 & 2.3: Hydrates a single skeleton item with detailed data.
        This version is robust and handles all item types correctly.
        """
        if not skeleton_item.is_skeleton:
            return skeleton_item

        try:
            # --- CONTEXT: OBJECTLIST (Character, Weapon, etc.) ---
            if isinstance(skeleton_item, ObjectItem):
                props_path = skeleton_item.folder_path / PROPERTIES_JSON_NAME
                properties = {}
                needs_json_update = False

                if props_path.is_file():
                    try:
                        with open(props_path, "r", encoding="utf-8") as f:
                            properties = json.load(f)
                    except json.JSONDecodeError:
                        logger.warning(
                            f"{PROPERTIES_JSON_NAME} for '{skeleton_item.actual_name}' is corrupted. Overwriting."
                        )
                        needs_json_update = True
                else:
                    needs_json_update = True

                # --- Reality Check (Suffix Logic) ---
                found_thumb_path: Path | None = None
                for file in skeleton_item.folder_path.iterdir():
                    if (
                        file.is_file()
                        and file.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
                    ):
                        file_stem = file.stem.lower()  # Nama file tanpa ekstensi
                        if (
                            file_stem.endswith(OBJECT_THUMBNAIL_SUFFIX)
                            or file_stem in OBJECT_THUMBNAIL_EXACT
                        ):
                            found_thumb_path = file
                            break  # Ambil yang pertama ditemukan

                # --- Reconcile ---
                json_thumb_str = properties.get("thumbnail_path", "")
                if found_thumb_path and found_thumb_path.name != json_thumb_str:
                    logger.info(
                        f"Found physical thumbnail '{found_thumb_path.name}' for '{skeleton_item.actual_name}', updating JSON."
                    )
                    properties["thumbnail_path"] = found_thumb_path.name
                    needs_json_update = True

                if needs_json_update:
                    self._write_json(props_path, properties)

                # Get other metadata
                metadata = (
                    self.database_service.get_metadata_for_object(
                        game_name, skeleton_item.actual_name
                    )
                    or {}
                )

                data_payload = {
                    "tags": properties.get("tags", []),
                    "thumbnail_path": (
                        skeleton_item.folder_path / p
                        if (p := properties.get("thumbnail_path"))
                        else None
                    ),
                    "is_skeleton": False,
                }

                # Add attributes specific to Character or Generic types
                if isinstance(skeleton_item, CharacterObjectItem):
                    data_payload.update(
                        {
                            "gender": metadata.get("gender"),
                            "rarity": metadata.get("rarity"),
                            "element": metadata.get("element"),
                            "weapon": metadata.get("weapon"),
                            "region": metadata.get("region"),
                        }
                    )
                elif isinstance(skeleton_item, GenericObjectItem):
                    data_payload.update(
                        {
                            "subtype": metadata.get("subtype"),
                        }
                    )

                return dataclasses.replace(skeleton_item, **data_payload)

            # --- CONTEXT: FOLDERGRID (Final Mods or Navigable Folders) ---
            elif isinstance(skeleton_item, FolderItem):
                if not any(
                    p.suffix.lower() == ".ini"
                    for p in skeleton_item.folder_path.iterdir()
                ):
                    return dataclasses.replace(
                        skeleton_item, is_navigable=True, is_skeleton=False
                    )

                # It's a final mod, read info.json
                info_path = skeleton_item.folder_path / INFO_JSON_NAME
                info = {}
                needs_json_update = False

                if info_path.is_file():
                    try:
                        with open(info_path, "r", encoding="utf-8") as f:
                            info = json.load(f)
                    except json.JSONDecodeError:
                        needs_json_update = True
                else:
                    needs_json_update = True

                # --- Reality Check (Prefix Logic) ---
                found_images = sorted(
                    [
                        p
                        for p in skeleton_item.folder_path.iterdir()
                        if p.is_file()
                        and p.stem.lower().startswith(FOLDER_PREVIEW_PREFIX)
                        and p.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
                    ]
                )

                # --- Reconcile ---
                json_image_paths = {
                    skeleton_item.folder_path / p for p in info.get("image_paths", [])
                }
                if set(found_images) != json_image_paths:
                    logger.info(
                        f"Physical image files for '{skeleton_item.actual_name}' do not match info.json. Syncing."
                    )
                    info["image_paths"] = [p.name for p in found_images]
                    needs_json_update = True

                if needs_json_update:
                    self._write_json(info_path, info)

                image_paths = [
                    skeleton_item.folder_path / img
                    for img in info.get("image_paths", [])
                ]

                return dataclasses.replace(
                    skeleton_item,
                    author=info.get("author"),
                    description=info.get("description", ""),
                    tags=info.get("tags", []),
                    preview_images=image_paths,
                    is_safe=info.get("is_safe", False),
                    preset_name=info.get("preset_name"),
                    is_navigable=False,
                    is_skeleton=False,
                )

        except PermissionError:
            logger.error(
                f"Permission denied while hydrating: {skeleton_item.folder_path}"
            )

        # Fallback if something goes wrong
        logger.warning(
            f"Hydration failed for '{skeleton_item.actual_name}'. Returning skeleton."
        )
        return skeleton_item

    # --- Core Item Actions ---
    def toggle_status(
        self, item: BaseModItem, target_status: ModStatus | None = None
    ) -> dict:
        """
        Flow 3.1: Enables/disables a mod by renaming its folder.
        This is a core file system operation.

        Parameters
        ----------
        item : BaseModItem
            The mod item object to be toggled.
        target_status : ModStatus | None, optional
            If provided, forces the status to ENABLED or DISABLED (for bulk actions).
            If None, the status is inverted (for single toggles).

        Returns
        -------
        dict
            A dictionary indicating success or failure.
            On success: {"success": True, "data": {"new_path": Path, "new_status": ModStatus}}
            On failure: {"success": False, "error": "Error message"}
        """
        try:
            # check if path exists

            if not item.folder_path.exists():
                logger.warning(f"Folder path '{item.folder_path}' does not exist.")
                return {"success": False, "error": "Folder path does not exist."}

            # 1. Determine the new status
            if target_status is not None:
                # This path is for bulk actions. If status is already correct, do nothing.
                if item.status == target_status:
                    return {"success": True, "data": item}
                new_status = target_status
            else:
                # This path is for single toggles. Invert the current status.
                new_status = (
                    ModStatus.DISABLED
                    if item.status == ModStatus.ENABLED
                    else ModStatus.ENABLED
                )

            # 2. Construct the new folder name
            prefix = DEFAULT_DISABLED_PREFIX if new_status == ModStatus.DISABLED else ""
            suffix = PIN_SUFFIX if item.is_pinned else ""
            new_name = f"{prefix}{item.actual_name}{suffix}"
            new_path = item.folder_path.with_name(new_name)
            logger.info(f"Renaming '{item.folder_path.name}' to '{new_path.name}'")

            # 3. Perform the rename operation
            os.rename(item.folder_path, new_path)

            # 4. --- Create a new model object with the changes ---
            data_to_update = {"folder_path": new_path, "status": new_status}
            new_item = dataclasses.replace(item, **data_to_update)

            # 5. Return success with the new data
            return {"success": True, "data": new_item}

        except FileExistsError:
            error_msg = f"Folder name conflict: '{new_path.name}' already exists."
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        except PermissionError:
            error_msg = "Permission denied. The folder or its contents may be in use by another program."
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"An unexpected error occurred during rename: {e}"
            logger.critical(error_msg, exc_info=True)
            return {"success": False, "error": error_msg}

    def toggle_pin_status(self, item: object) -> dict:
        """Flow 6.3: Pins/unpins a mod by renaming its folder with a suffix."""
        # TODO: Implement actual pin/unpin logic
        return {}

    def rename_item(self, item: object, new_name: str) -> dict:
        """Flow 4.2.A: Renames a mod folder and updates its internal 'actual_name' in JSON."""
        # TODO: Implement actual rename logic
        return {}

    def delete_item(self, item: object) -> dict:
        """Flow 4.2.B: Moves a mod folder to the system's recycle bin."""
        # TODO: Implement actual delete logic
        return {}

    # --- Creation Actions ---
    def create_foldergrid_item(self, parent_path: Path, task: dict) -> dict:
        """Flow 4.1.A: Creates a single new mod in foldergrid from a task dict."""
        # Handles creation from zip, folder, or manual input based on task type.
        # TODO: Implement actual creation logic
        return {}

    def create_objectlist_item(self, parent_path: Path, task: dict) -> dict:
        """Flow 4.1.B: Creates a single new object in objectlist from a task dict."""
        # Creates folder and a pre-filled properties.json.
        # TODO: Implement actual creation logic
        return {}

    # --- JSON & Metadata Updates ---
    def update_item_properties(self, item: FolderItem, data_to_update: dict) -> dict:
        """
        Flow 5.2, 6.2.A: Updates key-value pairs in an item's JSON file.
        This is a generic method for editing description, author, tags, etc.
        """
        if not isinstance(item, FolderItem):
            return {"success": False, "error": "Invalid item type for property update."}

        info_path = item.folder_path / INFO_JSON_NAME
        info = {}

        # Read existing data first (this part is correct)
        if info_path.is_file():
            try:
                with open(info_path, "r", encoding="utf-8") as f:
                    info = json.load(f)
            except json.JSONDecodeError:
                logger.warning(
                    f"Corrupted {INFO_JSON_NAME} for '{item.actual_name}'. It will be overwritten."
                )

        # Update the dictionary for JSON in memory with new data
        info.update(data_to_update)

        try:
            # Write the updated dictionary back to the JSON file
            self._write_json(info_path, info)

            # Prepare arguments for the dataclass, mapping JSON keys to dataclass fields if necessary.
            dataclass_args = data_to_update.copy()
            if "preview_images" in dataclass_args:
                base_path = item.folder_path
                string_paths = dataclass_args["preview_images"]
                # Create full Path objects for the in-memory model
                dataclass_args["preview_images"] = [base_path / p for p in string_paths]

            # Create a new immutable model with the correctly mapped updated data
            new_item = dataclasses.replace(item, **dataclass_args)
            # --- FIX ENDS HERE ---

            logger.info(f"Successfully updated properties for '{item.actual_name}'")
            return {"success": True, "data": new_item}

        except Exception as e:
            error_msg = f"Failed to save properties for '{item.actual_name}': {e}"
            logger.error(error_msg, exc_info=True)
            return {"success": False, "error": error_msg}

    def _write_json(self, json_path: Path, data: dict):
        """
        A helper function to safely write a dictionary to a JSON file.
        It uses an indent of 4 for human readability.
        """
        logger.debug(f"Writing updated data to {json_path}...")
        try:
            # Ensure the parent directory exists
            json_path.parent.mkdir(parents=True, exist_ok=True)

            with open(json_path, "w", encoding="utf-8") as f:
                # Use indent=4 to make the JSON file readable
                json.dump(data, f, indent=4)
        except (IOError, PermissionError) as e:
            logger.error(f"Failed to write to JSON file {json_path}: {e}")

    def add_preview_image(self, item: FolderItem, image_data) -> dict:
        """Flow 5.2 Part C: Adds a new preview image to a mod."""
        if not isinstance(item, FolderItem) or not image_data:
            return {"success": False, "error": "Invalid item or image data provided."}

        try:
            # 1. Use the utility to find the next available filename
            target_path = self.image_utils.find_next_available_preview_path(
                item.folder_path, base_name=FOLDER_PREVIEW_PREFIX
            )
            unique_name = target_path.name  # Get the relative name for JSON

            # 2. Process and save the image using the implemented utility
            self.image_utils.compress_and_save_image(
                source_image=image_data, target_path=target_path
            )

            # 3. Read current metadata
            info_path = item.folder_path / INFO_JSON_NAME
            info = {}
            if info_path.is_file():
                try:
                    with open(info_path, "r", encoding="utf-8") as f:
                        info = json.load(f)
                except json.JSONDecodeError:
                    logger.warning(
                        f"Corrupted {INFO_JSON_NAME} for '{item.actual_name}'."
                    )

            # 4. Update image list and save back using the helper method
            image_list = info.get("preview_images", [])
            image_list.append(unique_name)

            return self.update_item_properties(item, {"preview_images": image_list})

        except ValueError as e:  # Catches errors from compress_and_save_image
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(
                f"Failed to add preview image for '{item.actual_name}': {e}",
                exc_info=True,
            )
            return {"success": False, "error": f"An unexpected error occurred: {e}"}

    def _handle_image_removal(
        self, item: FolderItem, paths_to_delete: list[Path], final_image_list: list[str]
    ) -> dict:
        """
        A private helper to robustly handle the physical deletion of images
        and the subsequent metadata update.
        """
        if not paths_to_delete:
            # If there's nothing to delete, return success immediately.
            return {"success": True, "data": item, "deleted_paths": []}

        # 1. Attempt to delete all specified physical files, tracking results
        successfully_deleted_paths = []
        failed_deletions = []
        for full_path in paths_to_delete:
            if full_path.is_file():
                if self.system_utils.move_to_recycle_bin(full_path):
                    successfully_deleted_paths.append(full_path)
                else:
                    failed_deletions.append(full_path.name)
            else:
                logger.warning(f"Attempted to delete non-existent file: {full_path}")

        # 2. If any deletion failed, stop and report the error.
        if failed_deletions:
            error_msg = f"Failed to delete {len(failed_deletions)} image(s): {', '.join(failed_deletions)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

        # 3. If all deletions were successful, update the metadata with the new list.
        logger.info(
            f"Successfully deleted {len(successfully_deleted_paths)} image(s). Updating metadata."
        )
        update_result = self.update_item_properties(
            item, {"preview_images": final_image_list}
        )

        # 4. Augment the result with the list of deleted paths for cache invalidation.
        if update_result.get("success"):
            update_result["deleted_paths"] = successfully_deleted_paths

        return update_result

    def remove_preview_image(self, item: FolderItem, image_path: Path) -> dict:
        """
        Flow 5.2 Part C: Removes a single preview image from a mod.
        This method now prepares the data and delegates the core logic to a helper.
        """
        if (
            not isinstance(item, FolderItem)
            or not image_path
            or not image_path.is_file()
        ):
            return {"success": False, "error": "Invalid item or image path provided."}

        try:
            # Prepare the arguments for the helper
            info_path = item.folder_path / INFO_JSON_NAME
            current_image_list = []
            if info_path.is_file():
                with open(info_path, "r", encoding="utf-8") as f:
                    current_image_list = json.load(f).get("preview_images", [])

            # Create the new list of images for the JSON file
            final_image_list = [
                name for name in current_image_list if name != image_path.name
            ]

            # Delegate the actual work to the helper
            return self._handle_image_removal(
                item=item,
                paths_to_delete=[image_path],
                final_image_list=final_image_list,
            )
        except Exception as e:
            error_msg = (
                f"An unexpected error occurred while preparing to remove image: {e}"
            )
            logger.error(error_msg, exc_info=True)
            return {"success": False, "error": error_msg}

    def remove_all_preview_images(self, item: FolderItem) -> dict:
        """
        Removes all preview images associated with a mod.
        This method now prepares the data and delegates the core logic to a helper.
        """
        if not isinstance(item, FolderItem):
            return {"success": False, "error": "Invalid item type for this operation."}

        try:
            # Prepare the arguments for the helper
            info_path = item.folder_path / INFO_JSON_NAME
            if not info_path.is_file():
                return {"success": True, "data": item, "deleted_paths": []}

            with open(info_path, "r", encoding="utf-8") as f:
                relative_paths_to_delete = json.load(f).get("preview_images", [])

            # Create a list of full Path objects to delete
            full_paths_to_delete = [
                item.folder_path / name for name in relative_paths_to_delete
            ]

            # Delegate the actual work to the helper
            return self._handle_image_removal(
                item=item,
                paths_to_delete=full_paths_to_delete,
                final_image_list=[],  # The final list will be empty
            )
        except Exception as e:
            error_msg = (
                f"An unexpected error occurred while preparing to clear images: {e}"
            )
            logger.error(error_msg, exc_info=True)
            return {"success": False, "error": error_msg}

    def create_manual_object(self, parent_path: Path, object_data: dict) -> dict:
        """
        Flow 4.1.B Step 5: Creates a new object folder and its properties.json file.
        This is the core filesystem operation for manual object creation.
        """
        try:
            folder_name = object_data.get("name")
            if not folder_name:
                raise ValueError("Folder name is missing in object data.")

            folder_path = parent_path / folder_name
            logger.info(f"Attempting to create new object folder at: {folder_path}")

            folder_path.mkdir(exist_ok=False)

            # prepare properties.json data
            properties = {
                "id": f"emm-obj-{uuid.uuid4()}", # Generate a unique ID
                "actual_name": folder_name,
                "is_pinned": False,
                "object_type": object_data.get("object_type", "Other"),
                "tags": object_data.get("tags", []),
                # get all metadata
                "rarity": object_data.get("rarity"),
                "element": object_data.get("element"),
                "gender": object_data.get("gender"),
                "weapon": object_data.get("weapon"),
                "region": object_data.get("region"),
                "release_date": object_data.get("release_date"),
                "thumbnail_path": "" # first is empty, will be updated later
            }

            # Remove keys with None values to keep the JSON file clean
            properties = {k: v for k, v in properties.items() if v is not None}

            # Copy thumbnail if the path exists
            source_thumb_path_str = object_data.get("thumbnail_path")
            if source_thumb_path_str:
                # Assume the path in JSON is relative to the project root
                source_thumb_path = Path(source_thumb_path_str)
                # Create a consistent destination thumbnail filename
                dest_thumb_filename = f"_thumb{source_thumb_path.suffix}"
                dest_thumb_path = folder_path / dest_thumb_filename

                try:
                    if source_thumb_path.is_file():
                        shutil.copy(source_thumb_path, dest_thumb_path)
                        # If successful, update path in properties.json
                        properties["thumbnail_path"] = dest_thumb_filename
                        logger.info(f"Copied thumbnail for '{folder_name}' to '{dest_thumb_path}'")
                    else:
                        logger.warning(f"Thumbnail source file not found for '{folder_name}': {source_thumb_path}")
                except Exception as e:
                    logger.error(f"Failed to copy thumbnail for '{folder_name}': {e}")

            # write file properties.json
            json_path = folder_path / "properties.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(properties, f, indent=4)

            logger.info(f"Successfully created object '{folder_name}' with full metadata.")
            return {"success": True, "data": {"folder_path": folder_path}}

        except FileExistsError:
            error_msg = f"Folder '{folder_name}' already exists."
            logger.warning(error_msg)
            return {"success": False, "error": error_msg}
        except PermissionError:
            error_msg = "Permission denied. Could not create folder."
            logger.error(error_msg, exc_info=True)
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"An unexpected error occurred: {e}"
            logger.critical(error_msg, exc_info=True)
            return {"success": False, "error": error_msg}
