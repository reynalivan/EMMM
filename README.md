<p align="center">
    <img src="https://raw.githubus### 🗂️ **Explorer-Style Navigation**
- **Familiar Interface**: Browse mods like browsing files in Windows Explorer
- **Breadcrumb Navigation**: Quick navigation with visual path indicators
- **Nested Folder Support**: Handle complex mod structures effortlesslyrcontent.com/PKief/vscode-material-icon-theme/ec559a9f6bfd399b82bb44393651661b08aaf7ba/icons/folder-markdown-open.svg" align="center" width="30%">
</p>
<p align="center"><h1 align="center">EMMM</h1></p>
<p align="center">
	<em><code>❯ Enhanced Model Mods Manager - Your flexible, intelligent mod management solution</code></em>
</p>
<p align="center">
	<img src="https://img.shields.io/github/license/reynalivan/EMMM?style=default&logo=opensourceinitiative&logoColor=white&color=0080ff" alt="license">
	<img src="https://img.shields.io/github/last-commit/reynalivan/EMMM?style=default&logo=git&logoColor=white&color=0080ff" alt="last-commit">
	<img src="https://img.shields.io/github/languages/top/reynalivan/EMMM?style=default&color=0080ff" alt="repo-top-language">
	<img src="https://img.shields.io/github/languages/count/reynalivan/EMMM?style=default&color=0080ff" alt="repo-language-count">
</p>
<p align="center"><!-- default option, no dependency badges. -->
</p>
<p align="center">
	<!-- default option, no dependency badges. -->
</p>
<br>

## 🔗 Table of Contents

- [📍 Overview](#-overview)
- [👾 Features](#-features)
- [� Screenshots](#-screenshots)
- [�📁 Project Structure](#-project-structure)
  - [📂 Project Index](#-project-index)
- [🚀 Getting Started](#-getting-started)
  - [☑️ Prerequisites](#-prerequisites)
  - [⚙️ Installation](#-installation)
  - [🤖 Usage](#🤖-usage)
  - [🧪 Testing](#🧪-testing)
- [📌 Project Roadmap](#-project-roadmap)
- [🔰 Contributing](#-contributing)
- [🎗 License](#-license)
- [🙌 Acknowledgments](#-acknowledgments)

---

## 📍 Overview

**EMMM (Enhanced Model Mods Manager)** is a modern, intelligent mod manager designed specifically for 3D model modification games like Genshin Impact, Star Rail, Wuthering Waves, and Zenless Zone Zero. Built with PyQt6 and Fluent UI design principles, EMMM breaks free from traditional rigid folder structures and adapts to your existing mod organization.

Unlike conventional mod managers that force you into specific workflows, EMMM intelligently discovers and works with your current setup while providing powerful tools for organization, preview, and management. Whether you're a casual modder or managing hundreds of modifications, EMMM streamlines your workflow with intuitive navigation and automated features.

**Key Philosophy**: Flexibility first. EMMM adapts to your workflow, not the other way around.

---

## 👾 Features

### 🔄 **Dynamic & Adaptive Management**
- **Folder Structure Freedom**: No rigid rules or forced reorganization
- **Intelligent Discovery**: Automatically detects and works with existing mod folders
- **Multi-Game Support**: Compatible with GIMI, SRMI, WWMI, and ZZMI
- Explorer-Style Navigation: Browse your mods just like you browse files. Double-click to enter subfolders and use the breadcrumb bar to navigate back instantly. It’s intuitive and familiar.
### 🔄 **Database Sync & Reconciliation**
- **Auto-Complete Collection**: Create missing mod folders from comprehensive databases
- **Metadata Updates**: Sync rarity, element, tags, and descriptions
- **Thumbnail Management**: Bulk update thumbnails with database images
- **One-Click Synchronization**: Keep everything up-to-date automatically

### 🖼️ **Visual Mod Management**
- **Thumbnail Support**: Visual previews for all your mods
- **Clipboard Integration**: Paste images directly from clipboard
- **Multiple Preview Images**: Support for multiple screenshots per mod
- **Optimized Loading**: Smart caching system for fast performance

### 🔍 **Powerful Organization Tools**
- **Pin Favorites**: Keep important mods at the top
- **Advanced Search**: Search across names, authors, tags, and descriptions
- **Context-Aware Filters**: Filter by element, rarity, gender, and more
- **Smart Categorization**: Automatic organization based on mod properties

### 📁 **Drag & Drop Simplicity**
- **Universal File Support**: Handle folders, .zip, .rar, and .7z files
- **Auto-Extraction**: Intelligent archive handling
- **Batch Operations**: Process multiple mods simultaneously

### ⚙️ **Live Configuration Editing**
- **3DMigoto .ini Support**: Parse and edit configuration files directly
- **Visual Keybinding Editor**: Edit key bindings with intuitive interface
- **Cycle Key Management**: Set default values for cycle keys ($dress, etc.)
- **Safety Backups**: Automatic backup creation before modifications

### 🎮 **Game Integration**
- **"Enable Only This"**: Quick single-mod testing
- **Launcher Integration**: Start games directly from EMMM
- **Auto-Play Option**: Launch game automatically on startup
- **Mod Conflict Detection**: Identify and resolve mod conflicts

### ⚡ **Performance Optimized**
- **Smart Caching**: Fast image loading and mod data retrieval
- **Lazy Loading**: Load content only when needed
- **Responsive UI**: Smooth performance even with hundreds of mods
- **Background Processing**: Non-blocking operations for better UX

---

## 📸 Screenshots

> **Note**: Screenshots will be added in future updates to showcase the modern Fluent UI design and key features.

### Main Interface
- Clean, modern design with intuitive navigation
- Explorer-style folder browsing with breadcrumb navigation
- Thumbnail previews with mod information cards

### Key Features in Action
- Live .ini file editing with syntax highlighting
- Drag & drop mod installation process
- Database synchronization and metadata updates
- Advanced filtering and search capabilities

---

## 📁 Project Structure

```sh
└── EMMM/
    ├── app
    │   ├── __init__.py
    │   ├── assets
    │   ├── core
    │   ├── models
    │   ├── services
    │   ├── utils
    │   ├── viewmodels
    │   └── views
    ├── main.py
    └── requirements.txt
```
This project is structured to follow a modular architecture, separating concerns into distinct directories for core functionality, models, views, and utilities. The main entry point is `main.py`, which initializes the application.

### 📂 Project Index
<details open>
	<summary><b><code>EMMM/</code></b></summary>
	<details> <!-- __root__ Submodule -->
		<summary><b>__root__</b></summary>
		<blockquote>
			<table>
			<tr>
				<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/main.py'>main.py</a></b></td>
				<td><code>❯ Application entry point and main window initialization</code></td>
			</tr>
			<tr>
				<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/requirements.txt'>requirements.txt</a></b></td>
				<td><code>❯ Python dependencies and package requirements</code></td>
			</tr>
			</table>
		</blockquote>
	</details>
	<details> <!-- app Submodule -->
		<summary><b>app</b></summary>
		<blockquote>
			<details>
				<summary><b>core</b></summary>
				<blockquote>
					<table>
					<tr>
						<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/core/signals.py'>signals.py</a></b></td>
						<td><code>❯ Qt signals and event handling definitions</code></td>
					</tr>
					<tr>
						<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/core/constants.py'>constants.py</a></b></td>
						<td><code>❯ Application constants and configuration values</code></td>
					</tr>
					</table>
				</blockquote>
			</details>
			<details>
				<summary><b>models</b></summary>
				<blockquote>
					<table>
					<tr>
						<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/models/game_model.py'>game_model.py</a></b></td>
						<td><code>❯ REPLACE-ME</code></td>
					</tr>
					<tr>
						<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/models/config_model.py'>config_model.py</a></b></td>
						<td><code>❯ REPLACE-ME</code></td>
					</tr>
					<tr>
						<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/models/mod_item_model.py'>mod_item_model.py</a></b></td>
						<td><code>❯ REPLACE-ME</code></td>
					</tr>
					</table>
				</blockquote>
			</details>
			<details>
				<summary><b>views</b></summary>
				<blockquote>
					<table>
					<tr>
						<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/views/main_window.py'>main_window.py</a></b></td>
						<td><code>❯ REPLACE-ME</code></td>
					</tr>
					</table>
					<details>
						<summary><b>sections</b></summary>
						<blockquote>
							<table>
							<tr>
								<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/views/sections/foldergrid_panel.py'>foldergrid_panel.py</a></b></td>
								<td><code>❯ REPLACE-ME</code></td>
							</tr>
							<tr>
								<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/views/sections/preview_panel.py'>preview_panel.py</a></b></td>
								<td><code>❯ REPLACE-ME</code></td>
							</tr>
							<tr>
								<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/views/sections/objectlist_panel.py'>objectlist_panel.py</a></b></td>
								<td><code>❯ REPLACE-ME</code></td>
							</tr>
							</table>
						</blockquote>
					</details>
					<details>
						<summary><b>components</b></summary>
						<blockquote>
							<table>
							<tr>
								<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/views/components/thumbnail_widget.py'>thumbnail_widget.py</a></b></td>
								<td><code>❯ REPLACE-ME</code></td>
							</tr>
							<tr>
								<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/views/components/sync_candidate_widget.py'>sync_candidate_widget.py</a></b></td>
								<td><code>❯ REPLACE-ME</code></td>
							</tr>
							<tr>
								<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/views/components/progress_flyout.py'>progress_flyout.py</a></b></td>
								<td><code>❯ REPLACE-ME</code></td>
							</tr>
							<tr>
								<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/views/components/objectlist_widget.py'>objectlist_widget.py</a></b></td>
								<td><code>❯ REPLACE-ME</code></td>
							</tr>
							<tr>
								<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/views/components/foldergrid_widget.py'>foldergrid_widget.py</a></b></td>
								<td><code>❯ REPLACE-ME</code></td>
							</tr>
							<tr>
								<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/views/components/breadcrumb_widget.py'>breadcrumb_widget.py</a></b></td>
								<td><code>❯ REPLACE-ME</code></td>
							</tr>
							<tr>
								<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/views/components/creation_task_widget.py'>creation_task_widget.py</a></b></td>
								<td><code>❯ REPLACE-ME</code></td>
							</tr>
							</table>
							<details>
								<summary><b>common</b></summary>
								<blockquote>
									<table>
									<tr>
										<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/views/components/common/keybinding_widget.py'>keybinding_widget.py</a></b></td>
										<td><code>❯ REPLACE-ME</code></td>
									</tr>
									<tr>
										<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/views/components/common/flow_grid_widget.py'>flow_grid_widget.py</a></b></td>
										<td><code>❯ REPLACE-ME</code></td>
									</tr>
									<tr>
										<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/views/components/common/ini_file_group_widget.py'>ini_file_group_widget.py</a></b></td>
										<td><code>❯ REPLACE-ME</code></td>
									</tr>
									<tr>
										<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/views/components/common/shimmer_frame.py'>shimmer_frame.py</a></b></td>
										<td><code>❯ REPLACE-ME</code></td>
									</tr>
									</table>
								</blockquote>
							</details>
						</blockquote>
					</details>
					<details>
						<summary><b>dialogs</b></summary>
						<blockquote>
							<table>
							<tr>
								<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/views/dialogs/settings_dialog.py'>settings_dialog.py</a></b></td>
								<td><code>❯ REPLACE-ME</code></td>
							</tr>
							<tr>
								<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/views/dialogs/password_dialog.py'>password_dialog.py</a></b></td>
								<td><code>❯ REPLACE-ME</code></td>
							</tr>
							<tr>
								<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/views/dialogs/edit_game_dialog.py'>edit_game_dialog.py</a></b></td>
								<td><code>❯ REPLACE-ME</code></td>
							</tr>
							<tr>
								<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/views/dialogs/edit_object_dialog.py'>edit_object_dialog.py</a></b></td>
								<td><code>❯ REPLACE-ME</code></td>
							</tr>
							<tr>
								<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/views/dialogs/rename_dialog.py'>rename_dialog.py</a></b></td>
								<td><code>❯ REPLACE-ME</code></td>
							</tr>
							<tr>
								<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/views/dialogs/progress_dialog.py'>progress_dialog.py</a></b></td>
								<td><code>❯ REPLACE-ME</code></td>
							</tr>
							<tr>
								<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/views/dialogs/confirmation_list_dialog.py'>confirmation_list_dialog.py</a></b></td>
								<td><code>❯ REPLACE-ME</code></td>
							</tr>
							<tr>
								<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/views/dialogs/create_object_dialog.py'>create_object_dialog.py</a></b></td>
								<td><code>❯ REPLACE-ME</code></td>
							</tr>
							<tr>
								<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/views/dialogs/select_game_type_dialog.py'>select_game_type_dialog.py</a></b></td>
								<td><code>❯ REPLACE-ME</code></td>
							</tr>
							<tr>
								<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/views/dialogs/failure_report_dialog.py'>failure_report_dialog.py</a></b></td>
								<td><code>❯ REPLACE-ME</code></td>
							</tr>
							<tr>
								<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/views/dialogs/sync_selection_dialog.py'>sync_selection_dialog.py</a></b></td>
								<td><code>❯ REPLACE-ME</code></td>
							</tr>
							</table>
						</blockquote>
					</details>
				</blockquote>
			</details>
			<details>
				<summary><b>utils</b></summary>
				<blockquote>
					<table>
					<tr>
						<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/utils/image_utils.py'>image_utils.py</a></b></td>
						<td><code>❯ REPLACE-ME</code></td>
					</tr>
					<tr>
						<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/utils/ui_utils.py'>ui_utils.py</a></b></td>
						<td><code>❯ REPLACE-ME</code></td>
					</tr>
					<tr>
						<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/utils/async_utils.py'>async_utils.py</a></b></td>
						<td><code>❯ REPLACE-ME</code></td>
					</tr>
					<tr>
						<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/utils/logger_utils.py'>logger_utils.py</a></b></td>
						<td><code>❯ REPLACE-ME</code></td>
					</tr>
					<tr>
						<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/utils/system_utils.py'>system_utils.py</a></b></td>
						<td><code>❯ REPLACE-ME</code></td>
					</tr>
					</table>
				</blockquote>
			</details>
			<details>
				<summary><b>services</b></summary>
				<blockquote>
					<table>
					<tr>
						<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/services/Iniparsing_service.py'>Iniparsing_service.py</a></b></td>
						<td><code>❯ REPLACE-ME</code></td>
					</tr>
					<tr>
						<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/services/mod_service.py'>mod_service.py</a></b></td>
						<td><code>❯ REPLACE-ME</code></td>
					</tr>
					<tr>
						<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/services/game_service.py'>game_service.py</a></b></td>
						<td><code>❯ REPLACE-ME</code></td>
					</tr>
					<tr>
						<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/services/config_service.py'>config_service.py</a></b></td>
						<td><code>❯ REPLACE-ME</code></td>
					</tr>
					<tr>
						<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/services/Workflow_service.py'>Workflow_service.py</a></b></td>
						<td><code>❯ REPLACE-ME</code></td>
					</tr>
					<tr>
						<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/services/thumbnail_service.py'>thumbnail_service.py</a></b></td>
						<td><code>❯ REPLACE-ME</code></td>
					</tr>
					<tr>
						<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/services/database_service.py'>database_service.py</a></b></td>
						<td><code>❯ REPLACE-ME</code></td>
					</tr>
					</table>
				</blockquote>
			</details>
			<details>
				<summary><b>viewmodels</b></summary>
				<blockquote>
					<table>
					<tr>
						<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/viewmodels/preview_panel_vm.py'>preview_panel_vm.py</a></b></td>
						<td><code>❯ REPLACE-ME</code></td>
					</tr>
					<tr>
						<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/viewmodels/settings_vm.py'>settings_vm.py</a></b></td>
						<td><code>❯ REPLACE-ME</code></td>
					</tr>
					<tr>
						<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/viewmodels/main_window_vm.py'>main_window_vm.py</a></b></td>
						<td><code>❯ REPLACE-ME</code></td>
					</tr>
					<tr>
						<td><b><a href='https://github.com/reynalivan/EMMM/blob/master/app/viewmodels/mod_list_vm.py'>mod_list_vm.py</a></b></td>
						<td><code>❯ REPLACE-ME</code></td>
					</tr>
					</table>
				</blockquote>
			</details>
		</blockquote>
	</details>
</details>

---
## 🚀 Getting Started

### ☑️ Prerequisites

Before getting started with EMMM, ensure your runtime environment meets the following requirements:

- **Operating System**: Windows 10/11 (Primary), macOS, or Linux
- **Python**: Version 3.8 or higher
- **Memory**: Minimum 4GB RAM (8GB recommended for large mod collections)
- **Storage**: At least 1GB free space (plus space for your mods)
- **Display**: 1280x720 minimum resolution (1920x1080 recommended)

**Required for mod management:**
- **Supported Games**: Genshin Impact, Honkai: Star Rail, Wuthering Waves, or Zenless Zone Zero
- **3DMigoto**: Installed and configured for your game (for .ini editing features)


### ⚙️ Installation

Install EMMM using one of the following methods:

**Build from source:**

1. Clone the EMMM repository:
```sh
❯ git clone https://github.com/reynalivan/EMMM
```

2. Navigate to the project directory:
```sh
❯ cd EMMM
```

3. Install the project dependencies:


**Using `pip`** &nbsp; [<img align="center" src="https://img.shields.io/badge/Pip-3776AB.svg?style={badge_style}&logo=pypi&logoColor=white" />](https://pypi.org/project/pip/)

```sh
❯ pip install -r requirements.txt
```




### 🤖 Usage

Run EMMM using the following command:

```sh
❯ python main.py
```

**First Run Setup:**
1. On first launch, EMMM will ask you to select your game type and mod directory
2. Browse to your game's mod folder (usually where 3DMigoto is installed)
3. EMMM will scan and organize your existing mods automatically
4. Start managing your mods with the intuitive interface!

**Command Line Options:**
```sh
❯ python main.py --help          # Show all available options
❯ python main.py --debug         # Run with debug logging
❯ python main.py --config path   # Use custom config file location
```


### 🧪 Testing

EMMM uses automated testing to ensure reliability. Run tests using:

```sh
❯ python -m pytest tests/               # Run all tests
❯ python -m pytest tests/ -v            # Verbose output
❯ python -m pytest tests/ --cov=app     # With coverage report
```

**Manual Testing:**
- Test with different game types (GIMI, SRMI, WWMI, ZZMI)
- Verify drag & drop functionality with various archive formats
- Test .ini file parsing and editing features
- Validate thumbnail loading and caching performance


---
## 📌 Project Roadmap

### ✅ **Completed Features**
- [x] **Core UI Framework**: Modern Fluent UI with PyQt6 implementation
- [x] **Multi-Game Support**: GIMI, SRMI, WWMI, and ZZMI compatibility
- [x] **Dynamic Folder Detection**: Intelligent mod folder discovery and organization
- [x] **Database Integration**: Comprehensive mod databases with metadata sync
- [x] **Thumbnail Management**: Visual preview system with caching optimization
- [x] **Live .ini Editing**: 3DMigoto configuration file parsing and editing

### 🚧 **In Development**
- [ ] **Preset Management**: Save and load custom mod combinations
- [ ] **Safe Mode**: Add tag safe to spesific object mods
- [ ] **Batch Operations**: Multi-mod enable/disable and bulk editing tools

### 🔮 **Future Enhancements**
- [ ] **Cloud Sync**: Backup and sync mod configurations across devices


---

## 🔰 Contributing

- **💬 [Join the Discussions](https://github.com/reynalivan/EMMM/discussions)**: Share your insights, provide feedback, or ask questions.
- **🐛 [Report Issues](https://github.com/reynalivan/EMMM/issues)**: Submit bugs found or log feature requests for the `EMMM` project.
- **💡 [Submit Pull Requests](https://github.com/reynalivan/EMMM/blob/main/CONTRIBUTING.md)**: Review open PRs, and submit your own PRs.

<details closed>
<summary>Contributing Guidelines</summary>

1. **Fork the Repository**: Start by forking the project repository to your github account.
2. **Clone Locally**: Clone the forked repository to your local machine using a git client.
   ```sh
   git clone https://github.com/reynalivan/EMMM
   ```
3. **Create a New Branch**: Always work on a new branch, giving it a descriptive name.
   ```sh
   git checkout -b new-feature-x
   ```
4. **Make Your Changes**: Develop and test your changes locally.
5. **Commit Your Changes**: Commit with a clear message describing your updates.
   ```sh
   git commit -m 'Implemented new feature x.'
   ```
6. **Push to github**: Push the changes to your forked repository.
   ```sh
   git push origin new-feature-x
   ```
7. **Submit a Pull Request**: Create a PR against the original project repository. Clearly describe the changes and their motivations.
8. **Review**: Once your PR is reviewed and approved, it will be merged into the main branch. Congratulations on your contribution!
</details>

<details closed>
<summary>Contributor Graph</summary>
<br>
<p align="left">
   <a href="https://github.com{/reynalivan/EMMM/}graphs/contributors">
      <img src="https://contrib.rocks/image?repo=reynalivan/EMMM">
   </a>
</p>
</details>

---

## 🎗 License

This project is protected under the [SELECT-A-LICENSE](https://choosealicense.com/licenses) License. For more details, refer to the [LICENSE](https://choosealicense.com/licenses/) file.

---

## 🙌 Acknowledgments

### 🙏 **Special Thanks**
- **PyQt6 Team**: For the excellent Qt bindings that power EMMM's UI
- **qfluentwidgets**: For the beautiful Fluent UI components and theming
- **3DMigoto Community**: For the amazing modding framework and documentation
- **Modding Communities**: GIMI, SRMI, WWMI, and ZZMI communities for inspiration and feedback

### 📚 **Resources & Inspiration**
- **Microsoft Fluent Design System**: UI/UX design principles and guidelines
- **Qt Documentation**: Comprehensive framework documentation and examples
- **Python Community**: For the robust ecosystem of libraries and tools
- **GitHub Community**: For hosting, collaboration tools, and CI/CD infrastructure


### 💡 **Contributors**
We appreciate all contributors who help make EMMM better through code, documentation, testing, and feedback. Check out our [contributor graph](https://github.com/reynalivan/EMMM/graphs/contributors) to see everyone who has contributed to this project.

---
