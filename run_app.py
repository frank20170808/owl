# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
OWL Intelligent Assistant Platform Launch Script
"""

import os
import sys
from pathlib import Path


def main():
    """Main function to launch the OWL Intelligent Assistant Platform"""
    # Ensure the current directory is the project root
    project_root = Path(__file__).resolve().parent
    os.chdir(project_root)

    # Create log directory
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)

    # Add project root to Python path
    sys.path.insert(0, str(project_root))

    try:
        from owl.app_en import create_ui

        # Create and launch the application
        app = create_ui()
        app.queue().launch(share=False)

    except ImportError as e:
        print(
            f"Error: Unable to import necessary modules. Please ensure all dependencies are installed: {e}"
        )
        print("Tip: Run 'pip install -r requirements.txt' to install all dependencies")
        sys.exit(1)
    except Exception as e:
        print(f"Error occurred while starting the application: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
