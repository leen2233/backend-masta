import os
from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path


class Command(BaseCommand):
    help = 'Renames the Django project'

    def add_arguments(self, parser):
        parser.add_argument('new_project_name', type=str, help='The new name of the project')

    def get_current_project_name(self):
        # Read manage.py to find the current project name
        manage_py_path = os.path.join(str(settings.BASE_DIR), 'manage.py')
        with open(manage_py_path, 'r', encoding='utf-8') as file:
            content = file.read()

        # Find the settings module string
        import re
        match = re.search(r"DJANGO_SETTINGS_MODULE', '(.*?)\.settings'", content)
        if match:
            return match.group(1)
        return None

    def handle(self, *args, **kwargs):
        new_project_name = kwargs['new_project_name']

        # Get the root directory of the project
        project_root = str(settings.BASE_DIR)

        # Get the current project name
        current_project_name = self.get_current_project_name()

        if not current_project_name:
            self.stdout.write(
                self.style.ERROR('Could not determine current project name')
            )
            return

        # Files to rename
        files_to_rename = [
            os.path.join(project_root, f'{current_project_name}/settings.py'),
            os.path.join(project_root, f'{current_project_name}/wsgi.py'),
            os.path.join(project_root, f'{current_project_name}/asgi.py'),
            os.path.join(project_root, f'{current_project_name}/urls.py'),
        ]

        # Folder to rename
        folder_to_rename = os.path.join(project_root, current_project_name)

        try:
            # First, update manage.py
            manage_py_path = os.path.join(project_root, 'manage.py')
            if os.path.exists(manage_py_path):
                with open(manage_py_path, 'r', encoding='utf-8') as file:
                    filedata = file.read()

                # Update the settings module path
                filedata = filedata.replace(
                    f"os.environ.setdefault('DJANGO_SETTINGS_MODULE', '{current_project_name}.settings')",
                    f"os.environ.setdefault('DJANGO_SETTINGS_MODULE', '{new_project_name}.settings')"
                )

                with open(manage_py_path, 'w', encoding='utf-8') as file:
                    file.write(filedata)

            # Then update the content of other files
            for filepath in files_to_rename:
                if os.path.exists(filepath):
                    with open(filepath, 'r', encoding='utf-8') as file:
                        filedata = file.read()

                    # Replace old project name with new project name
                    filedata = filedata.replace(current_project_name, new_project_name)

                    # Special handling for settings.py
                    if 'settings.py' in filepath:
                        # Update ROOT_URLCONF
                        filedata = filedata.replace(
                            f"ROOT_URLCONF = '{current_project_name}.urls'",
                            f"ROOT_URLCONF = '{new_project_name}.urls'"
                        )
                        # Update WSGI_APPLICATION
                        filedata = filedata.replace(
                            f"WSGI_APPLICATION = '{current_project_name}.wsgi.application'",
                            f"WSGI_APPLICATION = '{new_project_name}.wsgi.application'"
                        )
                        # Update ASGI_APPLICATION if it exists
                        filedata = filedata.replace(
                            f"ASGI_APPLICATION = '{current_project_name}.asgi.application'",
                            f"ASGI_APPLICATION = '{new_project_name}.asgi.application'"
                        )

                    with open(filepath, 'w', encoding='utf-8') as file:
                        file.write(filedata)

            # Rename the project folder last
            if os.path.exists(folder_to_rename):
                new_folder_path = os.path.join(project_root, new_project_name)
                os.rename(folder_to_rename, new_folder_path)

            self.stdout.write(
                self.style.SUCCESS(f'Project has been renamed from "{current_project_name}" to "{new_project_name}"')
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'An error occurred: {str(e)}')
            )
