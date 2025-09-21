# 🛠️ Starting the Project (Development Mode)

## 1. Start Django Development Server

Run the following command to start the Django development server:

```bash
python manage.py runserver
```

Alternatively, you can run it directly from **PyCharm** if it's configured.

---

## 2. Run Tailwind DaisyUI CSS Watcher

Run Tailwind CSS in watch mode to compile styles:

```bash
static/taxman/tailwindcss.exe -i static/taxman/input.css -o static/taxman/output.css --watch
```

## 3. Expose App via Ngrok

To make your app publicly accessible, use **ngrok**:

```bash
ngrok http --url https://hopefully-destined-amoeba.ngrok-free.app/ 8000
```

> ⚠️ **Note:** Make sure the Django server is running *before* starting ngrok.