from django.apps import AppConfig


class AppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'
    def ready(self):
        self._patch_jazzmin_paginator()


    def _patch_jazzmin_paginator(self):
        """
        Patch jazzmin's paginator to work with Django 6.0.

        django-jazzmin 3.0.1 calls format_html(html_str) without args, which is
        not allowed in Django 6.0. This patches the affected function to use mark_safe.
        See: https://code.djangoproject.com/ticket/34609
        """
        try:
            from django.contrib.admin.views.main import PAGE_VAR
            from django.utils.safestring import mark_safe
            from jazzmin.templatetags import jazzmin as jazzmin_tags

            def patched_jazzmin_paginator_number(cl, i):
                """Patched version that uses mark_safe instead of format_html."""
                if i == "." or i == "…":
                    html_str = (
                        '<li class="page-item disabled"><a class="page-link" href="#">...</a></li>'
                    )
                elif i == cl.page_num:
                    html_str = (
                        f'<li class="page-item active"><a class="page-link" href="#">{i}</a></li>'
                    )
                else:
                    link = cl.get_query_string({PAGE_VAR: i})
                    html_str = (
                        f'<li class="page-item"><a class="page-link" href="{link}">{i}</a></li>'
                    )

                return mark_safe(html_str)

            # Apply the patch
            jazzmin_tags.jazzmin_paginator_number = patched_jazzmin_paginator_number
            # Also register it in the template library
            jazzmin_tags.register.simple_tag(
                patched_jazzmin_paginator_number, name="jazzmin_paginator_number"
            )
            print("Applied jazzmin_paginator_number patch for Django 6.0 compatibility")
        except ImportError:
            pass  # jazzmin not installed
