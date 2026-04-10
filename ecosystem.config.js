module.exports = {
    apps: [
      {
        name: "django-backend",
        script: "gunicorn",
        interpreter: "/root/general-backend-django/venv/bin/python",
        args: "myproject.wsgi:application --bind 127.0.0.1:8001 --workers 3",
        cwd: "/root/general-backend-django",
        env: {
          DJANGO_SETTINGS_MODULE: "myproject.settings.production",
          PYTHONPATH: "/root/general-backend-django"
        }
      }
    ]
  }