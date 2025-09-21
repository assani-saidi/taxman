# Useful commands for managing the Django project
## load data
- Load initial data into the database from JSON files. **Example:**
``` bash
python manage.py loaddata tax_providers.json
```
## add cronjob for auto fiscal close day (linux only)
- Run this after installing `django-crontab`
``` bash
python manage.py crontab add
```
