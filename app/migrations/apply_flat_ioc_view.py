import os
import re
from pathlib import Path

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def apply_migration():
    """Replace the render_ioc_view function in main.py with the flat layout version."""
    try:
        # Get file paths
        script_dir = Path(__file__).parent
        main_py_path = script_dir.parent / 'main.py'
        update_view_path = script_dir / 'update_ioc_view.py'

        # Validate files exist
        if not main_py_path.exists():
            raise FileNotFoundError(f"main.py not found at: {main_py_path}")
        if not update_view_path.exists():
            raise FileNotFoundError(f"update_ioc_view.py not found at: {update_view_path}")

        # Read files
        main_content = read_file(main_py_path)
        new_function = read_file(update_view_path)

        # Find and replace the render_ioc_view function
        pattern = r'def render_ioc_view\([^)]*\):.*?(?=def|$)'
        match = re.search(pattern, main_content, re.DOTALL)
        if not match:
            raise ValueError("render_ioc_view function not found in main.py")

        # Create backup
        backup_path = main_py_path.with_suffix('.py.bak')
        write_file(backup_path, main_content)
        print(f"Created backup at: {backup_path}")

        # Replace function
        updated_content = re.sub(pattern, new_function, main_content, flags=re.DOTALL)
        write_file(main_py_path, updated_content)
        
        print("Successfully updated render_ioc_view with flat layout")
        print("Backup created at:", backup_path)
        
    except Exception as e:
        print("Error updating render_ioc_view:", str(e))
        # Attempt to restore from backup if it exists
        if 'backup_path' in locals() and backup_path.exists():
            write_file(main_py_path, read_file(backup_path))
            print("Restored from backup due to error")
        raise

if __name__ == "__main__":
    apply_migration()
